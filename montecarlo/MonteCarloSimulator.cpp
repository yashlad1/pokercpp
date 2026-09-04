// montecarlo/MonteCarloSimulator.cpp
#include "MonteCarloSimulator.h"
#include "../model/deck.h"
#include "../model/advanced_hand_evaluator.h"

#include <random>
#include <algorithm>
#include <iostream>
#include <map>
#include <cmath>  // for sqrt, max, min

MonteCarloSimulator::MonteCarloSimulator(const std::vector<Card> &playerHand,
                                         const std::vector<Card> &communityCards,
                                         int simulations)
    : playerHand(playerHand), communityCards(communityCards),
      numSimulations(simulations), winCount(0), tieCount(0), loseCount(0)
{
}

void MonteCarloSimulator::runSimulation()
{
    winCount = tieCount = loseCount = 0;

    // Seed once and reuse. Re-seeding a fresh mt19937 from random_device on
    // every iteration is expensive and gains nothing. The deck is built once
    // and re-shuffled in place, since dealing only reads from it.
    std::random_device rd;
    std::mt19937 g(rd());
    std::vector<Card> deck = getRemainingDeck();

    for (int i = 0; i < numSimulations; ++i)
    {
        // Shuffle the deck
        std::shuffle(deck.begin(), deck.end(), g);

        // Deal opponent hand and complete the board if needed
        auto [opponentHand, completeBoard] = dealRandomOpponentAndBoard(deck);

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

std::pair<double, double> MonteCarloSimulator::getEquityConfidenceInterval(double confidence) const
{
    if (numSimulations == 0)
        return {0.0, 0.0};
    if (confidence <= 0.0 || confidence >= 1.0)
        return {0.0, 1.0};

    double equity = getEquity();
    double margin = probit(0.5 * (1.0 + confidence)) * getEquityStdDev();

    return {std::max(0.0, equity - margin), std::min(1.0, equity + margin)};
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

double MonteCarloSimulator::getFlushDrawOdds() const
{
    // Count cards by suit
    std::map<Suit, int> suitCount;
    for (const Card &c : playerHand)
    {
        suitCount[c.suit]++;
    }
    for (const Card &c : communityCards)
    {
        suitCount[c.suit]++;
    }

    // Check if we have 4 cards of the same suit
    Suit flushSuit = Suit::Clubs; // Default
    bool hasFlushDraw = false;

    for (const auto &[suit, count] : suitCount)
    {
        if (count == 4)
        {
            hasFlushDraw = true;
            flushSuit = suit;
            break;
        }
    }

    if (!hasFlushDraw)
    {
        return 0.0;
    }

    // Calculate how many flush cards are left in the deck
    int totalCards = playerHand.size() + communityCards.size();
    int cardsRemaining = 13 - suitCount[flushSuit]; // 13 cards per suit
    int deckSize = 52 - totalCards;

    // Probability of drawing a flush card
    return static_cast<double>(cardsRemaining) / deckSize;
}

double MonteCarloSimulator::getStraightDrawOdds() const
{
    std::vector<int> ranks;
    for (const Card &c : playerHand)
    {
        ranks.push_back(static_cast<int>(c.rank));
    }
    for (const Card &c : communityCards)
    {
        ranks.push_back(static_cast<int>(c.rank));
    }

    // Sort and remove duplicates
    std::sort(ranks.begin(), ranks.end());
    auto last = std::unique(ranks.begin(), ranks.end());
    ranks.erase(last, ranks.end());

    // Note: loop bounds are written as `i + 3 < size()` rather than
    // `i < size() - 3`. size() is unsigned, so with fewer than 4 distinct
    // ranks (any preflop hand) the subtraction wraps and the loop reads
    // far past the end of the vector.
    std::vector<int> neededCards;

    // Open-ended straight draw: four consecutive ranks, completed by the
    // rank immediately below or immediately above the run.
    for (size_t i = 0; i + 3 < ranks.size(); ++i)
    {
        if (ranks[i + 1] == ranks[i] + 1 &&
            ranks[i + 2] == ranks[i] + 2 &&
            ranks[i + 3] == ranks[i] + 3)
        {
            if (ranks[i] - 1 >= 2)
            { // 2 is the lowest card
                neededCards.push_back(ranks[i] - 1);
            }
            if (ranks[i + 3] + 1 <= 14)
            { // 14 (Ace) is the highest
                neededCards.push_back(ranks[i + 3] + 1);
            }
        }
    }

    // Inside (gutshot) straight draw: four ranks spanning exactly five, so
    // the one missing rank inside that window completes the straight.
    for (size_t i = 0; i + 3 < ranks.size(); ++i)
    {
        if (ranks[i + 3] == ranks[i] + 4)
        {
            for (int want = ranks[i] + 1; want < ranks[i] + 4; ++want)
            {
                if (std::find(ranks.begin(), ranks.end(), want) == ranks.end())
                {
                    neededCards.push_back(want);
                }
            }
        }
    }

    // Remove duplicates from needed cards
    std::sort(neededCards.begin(), neededCards.end());
    auto lastUnique = std::unique(neededCards.begin(), neededCards.end());
    neededCards.erase(lastUnique, neededCards.end());

    // Calculate odds
    if (neededCards.empty())
    {
        return 0.0;
    }

    int totalCards = playerHand.size() + communityCards.size();
    int deckSize = 52 - totalCards;

    // Each rank has 4 cards (one per suit)
    int totalOuts = neededCards.size() * 4;

    // Subtract cards we already know
    for (const Card &c : playerHand)
    {
        if (std::find(neededCards.begin(), neededCards.end(), static_cast<int>(c.rank)) != neededCards.end())
        {
            totalOuts--;
    }
    }
    for (const Card &c : communityCards)
    {
        if (std::find(neededCards.begin(), neededCards.end(), static_cast<int>(c.rank)) != neededCards.end())
        {
            totalOuts--;
        }
    }

    return static_cast<double>(totalOuts) / deckSize;
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