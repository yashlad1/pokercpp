// montecarlo/MonteCarloSimulator.cpp
#include "MonteCarloSimulator.h"
#include "../model/advanced_hand_evaluator.h"
#include "../model/fast_eval.h"
#include "preflop_ranks.h"

#include <random>
#include <algorithm>
#include <cmath>  // for sqrt, max, min

MonteCarloSimulator::MonteCarloSimulator(const std::vector<Card> &playerHand,
                                         const std::vector<Card> &communityCards,
                                         int simulations)
    : playerHand(playerHand), communityCards(communityCards),
      numSimulations(simulations), winCount(0), tieCount(0), loseCount(0),
      villainRangeFraction(1.0)
{
}

void MonteCarloSimulator::setVillainRange(double fraction)
{
    // Clamped rather than rejected: callers derive this from observed
    // betting, and a range of "top 0%" is a modelling artefact, not a
    // request to simulate an opponent holding nothing.
    if (fraction < 0.01) fraction = 0.01;
    if (fraction > 1.0) fraction = 1.0;
    villainRangeFraction = fraction;
}

std::vector<std::pair<Card, Card>> MonteCarloSimulator::villainCombos(
    const std::vector<Card> &deck) const
{
    // Walk the ranked classes, strongest first, until the cumulative combo
    // count reaches the wanted share of all 1326 holdings. Counting in
    // combos rather than classes is what makes "top 20%" mean 20% of the
    // hands actually dealt: there are 12 ways to be dealt AKo and only 6 to
    // be dealt AA.
    const int wanted = static_cast<int>(villainRangeFraction * 1326.0 + 0.5);
    bool allowed[15][15][2] = {};
    int cumulative = 0;
    for (const chipzen::PreflopClass &c : chipzen::kPreflopRanked) {
        if (cumulative >= wanted) break;
        allowed[c.high][c.low][c.suited ? 1 : 0] = true;
        cumulative += c.combos;
    }

    std::vector<std::pair<Card, Card>> combos;
    for (size_t i = 0; i < deck.size(); ++i) {
        for (size_t j = i + 1; j < deck.size(); ++j) {
            int a = static_cast<int>(deck[i].rank);
            int b = static_cast<int>(deck[j].rank);
            int hi = std::max(a, b), lo = std::min(a, b);
            bool suited = deck[i].suit == deck[j].suit;
            if (allowed[hi][lo][suited ? 1 : 0]) {
                combos.emplace_back(deck[i], deck[j]);
            }
        }
    }
    return combos;
}

#ifdef USE_METAL
EquityJob MonteCarloSimulator::metalJob() const
{
    std::vector<Card> deck = getRemainingDeck();
    std::vector<std::pair<Card, Card>> combos;
    if (villainRangeFraction < 1.0) combos = villainCombos(deck);
    if (combos.empty()) {  // range 1.0, or a range emptied by our own cards
        for (size_t i = 0; i < deck.size(); ++i)
            for (size_t j = i + 1; j < deck.size(); ++j)
                combos.emplace_back(deck[i], deck[j]);
    }
    return EquityJob{{playerHand[0], playerHand[1]}, communityCards, std::move(combos),
                     numSimulations, seed};
}
#endif

void MonteCarloSimulator::runSimulation()
{
    winCount = tieCount = loseCount = 0;

#ifdef USE_METAL
    if (numSimulations > 0 && playerHand.size() == 2 && metalAvailable()) {
        EquityResult r = metalEquityBatch({metalJob()})[0];
        winCount = r.wins;
        tieCount = r.ties;
        loseCount = r.trials - r.wins - r.ties;
        return;
    }
#endif

    // Seed once and reuse. Re-seeding a fresh mt19937 from random_device on
    // every iteration is expensive and gains nothing. The deck is built once
    // and re-shuffled in place, since dealing only reads from it.
    std::mt19937 g;
    if (seed) {
        std::seed_seq ss{static_cast<unsigned>(seed), static_cast<unsigned>(seed >> 32)};
        g.seed(ss);
    } else {
        std::random_device rd;
        g.seed(rd());
    }
    std::vector<Card> deck = getRemainingDeck();

    // Only build the combo list when the range is actually restricted. The
    // unrestricted path stays exactly as it was, which matters because that
    // is the path the exact-enumeration tests validate.
    std::vector<std::pair<Card, Card>> combos;
    if (villainRangeFraction < 1.0)
    {
        combos = villainCombos(deck);
        // A range narrow enough to be empty once our own cards are removed
        // tells us nothing. Fall back to dealing at random rather than
        // returning an equity computed from no opponent at all.
    }
    std::uniform_int_distribution<size_t> pick(0, combos.empty() ? 0 : combos.size() - 1);

    // Fast path: fixed arrays and the bitmask evaluator, same draws in the same
    // order as the general loop below. Only taken for the normal shape (a
    // two-card hero, at most five distinct board cards, a full-size deck).
    uint64_t heroMask = 0, boardMask = 0;
    for (const Card &c : playerHand) heroMask |= 1ULL << fast_eval::cardId(c);
    for (const Card &c : communityCards) boardMask |= 1ULL << fast_eval::cardId(c);
    const size_t need = communityCards.size() <= 5 ? 5 - communityCards.size() : 0;
    if (playerHand.size() == 2 && communityCards.size() <= 5 &&
        __builtin_popcountll(heroMask) == 2 &&
        __builtin_popcountll(boardMask) == (int)communityCards.size() &&
        !(heroMask & boardMask) && deck.size() >= 2 + need && deck.size() <= 52)
    {
        uint8_t ids[52];
        const size_t n = deck.size();
        for (size_t k = 0; k < n; ++k) ids[k] = (uint8_t)fast_eval::cardId(deck[k]);
        std::vector<std::pair<uint8_t, uint8_t>> cid;
        cid.reserve(combos.size());
        for (const auto &cb : combos)
            cid.emplace_back((uint8_t)fast_eval::cardId(cb.first), (uint8_t)fast_eval::cardId(cb.second));
        const bool ranged = !cid.empty();
        for (int i = 0; i < numSimulations; ++i)
        {
            std::shuffle(ids, ids + n, g);
            uint64_t board = boardMask, opp;
            if (ranged)
            {
                const auto &cb = cid[pick(g)];
                opp = (1ULL << cb.first) | (1ULL << cb.second);
                size_t have = communityCards.size();
                for (size_t k = 0; k < n && have < 5; ++k)
                {
                    if (ids[k] == cb.first || ids[k] == cb.second) continue;
                    board |= 1ULL << ids[k];
                    ++have;
                }
            }
            else
            {
                opp = (1ULL << ids[0]) | (1ULL << ids[1]);
                for (size_t k = 0; k < need; ++k) board |= 1ULL << ids[2 + k];
            }
            uint32_t hs = fast_eval::evalMask(heroMask | board);
            uint32_t vs = fast_eval::evalMask(opp | board);
            if (hs > vs) winCount++;
            else if (vs > hs) loseCount++;
            else tieCount++;
        }
        return;
    }

    for (int i = 0; i < numSimulations; ++i)
    {
        // Shuffle the deck
        std::shuffle(deck.begin(), deck.end(), g);

        std::vector<Card> opponentHand;
        std::vector<Card> completeBoard;
        if (!combos.empty())
        {
            const auto &combo = combos[pick(g)];
            opponentHand = {combo.first, combo.second};
            completeBoard = communityCards;
            // Fill the board from the shuffled deck, skipping the two cards
            // the opponent is holding this trial.
            for (const Card &c : deck)
            {
                if (completeBoard.size() >= 5) break;
                if (c == combo.first || c == combo.second) continue;
                completeBoard.push_back(c);
            }
        }
        else
        {
            std::tie(opponentHand, completeBoard) = dealRandomOpponentAndBoard(deck);
        }

        // Combine player hand with board
        std::vector<Card> playerFullHand = playerHand;
        playerFullHand.insert(playerFullHand.end(), completeBoard.begin(), completeBoard.end());

        // Combine opponent hand with board
        std::vector<Card> opponentFullHand = opponentHand;
        opponentFullHand.insert(opponentFullHand.end(), completeBoard.begin(), completeBoard.end());

        // Evaluate both hands
        HandValue playerValue = AdvancedHandEvaluator::evaluate(playerFullHand);
        HandValue opponentValue = AdvancedHandEvaluator::evaluate(opponentFullHand);

        // Compare results
        if (playerValue > opponentValue)
        {
            winCount++;
        }
        else if (opponentValue > playerValue)
        {
            loseCount++;
        }
        else
        {
            tieCount++;
        }
    }
}

double MonteCarloSimulator::getWinPercentage() const
{
    if (numSimulations == 0)
        return 0.0;
    return static_cast<double>(winCount) / numSimulations;
}

double MonteCarloSimulator::getTiePercentage() const
{
    if (numSimulations == 0)
        return 0.0;
    return static_cast<double>(tieCount) / numSimulations;
}

double MonteCarloSimulator::getLosePercentage() const
{
    if (numSimulations == 0)
        return 0.0;
    return static_cast<double>(loseCount) / numSimulations;
}

// Calculate standard deviation of win rate using binomial distribution
// For binary outcomes: σ = sqrt(p(1-p)/n)
double MonteCarloSimulator::getWinRateStdDev() const
{
    if (numSimulations == 0)
        return 0.0;
    
    double p = getWinPercentage();
    double variance = p * (1.0 - p) / numSimulations;
    return std::sqrt(variance);
}

/**
 * Inverse of the standard normal CDF (the probit function).
 *
 * Needed to turn an arbitrary confidence level into a z-score. Uses Acklam's
 * rational approximation, accurate to roughly 1e-9 over (0, 1) - far tighter
 * than Monte Carlo sampling error, so it is never the limiting factor here.
 */
static double probit(double p)
{
    if (p <= 0.0)
        return 0.0;
    if (p >= 1.0)
        return 0.0;

    static const double a[6] = {
        -3.969683028665376e+01,  2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01,  2.506628277459239e+00};
    static const double b[5] = {
        -5.447609879822406e+01,  1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01};
    static const double c[6] = {
        -7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
        -2.549732539343734e+00,  4.374664141464968e+00,  2.938163982698783e+00};
    static const double d[4] = {
         7.784695709041462e-03,  3.224671290700398e-01,  2.445134137142996e+00,
         3.754408661907416e+00};

    const double pLow = 0.02425;
    const double pHigh = 1.0 - pLow;

    if (p < pLow)
    {
        double q = std::sqrt(-2.0 * std::log(p));
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0);
    }

    if (p > pHigh)
    {
        double q = std::sqrt(-2.0 * std::log(1.0 - p));
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
                ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0);
    }

    double q = p - 0.5;
    double r = q * q;
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q /
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0);
}

double MonteCarloSimulator::getEquity() const
{
    // A split pot returns half the money, so it counts as half a win.
    return getWinPercentage() + 0.5 * getTiePercentage();
}

/**
 * Standard error of the equity estimate.
 *
 * Equity is the mean of a three-valued outcome (1 for a win, 0.5 for a tie,
 * 0 for a loss), not a binary one, so the binomial p(1-p)/n used for the win
 * rate does not apply. For X in {1, 0.5, 0}:
 *
 *   E[X]   = pw + pt/2
 *   E[X^2] = pw + pt/4
 *   Var(X) = pw + pt/4 - (pw + pt/2)^2
 */
double MonteCarloSimulator::getEquityStdDev() const
{
    if (numSimulations == 0)
        return 0.0;

    double pw = getWinPercentage();
    double pt = getTiePercentage();
    double mean = pw + 0.5 * pt;
    double variance = pw + 0.25 * pt - mean * mean;

    if (variance <= 0.0)
        return 0.0;

    return std::sqrt(variance / numSimulations);
}

// Calculate confidence interval for win rate
// Returns pair of (lower_bound, upper_bound)
// Uses normal approximation for binomial: mean ± z * σ
std::pair<double, double> MonteCarloSimulator::getConfidenceInterval(double confidence) const
{
    if (numSimulations == 0)
        return {0.0, 0.0};
    
    if (confidence <= 0.0 || confidence >= 1.0)
        return {0.0, 1.0};

    double winRate = getWinPercentage();
    double stdDev = getWinRateStdDev();

    // Derive the z-score from the requested level instead of matching it
    // against a handful of hardcoded thresholds. The old if/else chain had no
    // branch below 0.90, so z kept its 1.96 initializer and any level under
    // 90% silently came back as a 95% interval - a requested 50% interval was
    // returned *wider* than a 90% one.
    double z = probit(0.5 * (1.0 + confidence));

    double margin = z * stdDev;
    double lowerBound = std::max(0.0, winRate - margin);
    double upperBound = std::min(1.0, winRate + margin);
    
    return {lowerBound, upperBound};
}

std::vector<Card> MonteCarloSimulator::getRemainingDeck() const
{
    std::vector<Card> deck;

    // Create a full deck
    for (int s = 0; s < 4; ++s)
    {
        for (int r = 2; r <= 14; ++r)
        {
            Card card(static_cast<Rank>(r), static_cast<Suit>(s));

            // Check if card is already in player hand or community cards
            bool isUsed = false;
            for (const Card &c : playerHand)
            {
                if (c.rank == card.rank && c.suit == card.suit)
                {
                    isUsed = true;
                    break;
                }
            }

            if (!isUsed)
            {
                for (const Card &c : communityCards)
                {
                    if (c.rank == card.rank && c.suit == card.suit)
                    {
                        isUsed = true;
                        break;
                    }
                }
            }

            if (!isUsed)
            {
                deck.push_back(card);
            }
        }
    }

    return deck;
}

std::pair<std::vector<Card>, std::vector<Card>> MonteCarloSimulator::dealRandomOpponentAndBoard(
    const std::vector<Card> &deck) const
{
    std::vector<Card> opponentHand;
    std::vector<Card> completeBoard = communityCards;

    // Deal opponent's two cards if they don't already have them
    size_t index = 0;
    while (opponentHand.size() < 2 && index < deck.size())
    {
        opponentHand.push_back(deck[index++]);
    }

    // Complete the board to 5 cards if needed
    while (completeBoard.size() < 5 && index < deck.size())
    {
        completeBoard.push_back(deck[index++]);
    }

    return {opponentHand, completeBoard};
}