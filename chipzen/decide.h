// Decision logic shared by the CLI solver and the Python module, so the two cannot drift.

#ifndef CHIPZEN_DECIDE_H
#define CHIPZEN_DECIDE_H

#include "../montecarlo/MonteCarloSimulator.h"
#include "../model/poker_math.h"

#include <algorithm>
#include <string>
#include <vector>

namespace chipzen {

inline bool parseCard(const std::string &s, Card &out) {
    if (s.size() != 2) return false;

    int rank;
    switch (s[0]) {
        case '2': case '3': case '4': case '5': case '6':
        case '7': case '8': case '9': rank = s[0] - '0'; break;
        case 'T': rank = 10; break;
        case 'J': rank = 11; break;
        case 'Q': rank = 12; break;
        case 'K': rank = 13; break;
        case 'A': rank = 14; break;
        default: return false;
    }

    Suit suit;
    switch (s[1]) {
        case 'h': suit = Suit::Hearts; break;
        case 'd': suit = Suit::Diamonds; break;
        case 'c': suit = Suit::Clubs; break;
        case 's': suit = Suit::Spades; break;
        default: return false;
    }

    out = Card(static_cast<Rank>(rank), suit);
    return true;
}

// Returns 0 when raising is illegal (the server reports both bounds as 0).
inline int boundedRaise(int target, int minRaise, int maxRaise) {
    if (minRaise <= 0 || maxRaise <= 0) return 0;
    return std::max(minRaise, std::min(target, maxRaise));
}

// ponytail: a step function fitted by hand, not from data. The right version
// learns these from observed showdowns. Replace it once there are hands to
// learn from - the shape below is a starting prior, not a finding.
inline double villainRangeFraction(int villainRaises, int toCall, int pot) {
    double f = 1.0;
    if (villainRaises >= 1) f = 0.45;
    if (villainRaises >= 2) f = 0.18;
    if (villainRaises >= 3) f = 0.08;

    // pot already includes the bet, so measure it against the pot before: a pot-size bet is 1.0,
    // and the 0.75 / 0.35 cuts below mean 75% and 35% of that pot.
    if (toCall > 0 && pot - toCall > 0) {
        double betFraction = static_cast<double>(toCall) / (pot - toCall);
        if (betFraction > 0.75) f *= 0.7;
        else if (betFraction < 0.35) f *= 1.3;
    }

    return std::max(0.05, std::min(1.0, f));
}

constexpr double kPreflopRealization = 0.75;

// ponytail: depends only on the street, not on position, stack depth or
// whether the hand is the kind that flops well. Those are the next terms if
// this proves to matter.
// Monte Carlo equity assumes every hand reaches showdown for free; the further from showdown, the
// less of it is collected. The river is exact, so realization there is 1.
inline double equityRealization(size_t boardSize, double preflop = kPreflopRealization) {
    switch (boardSize) {
        case 0:  return preflop;
        case 3:  return 0.82;
        case 4:  return 0.90;
        default: return 1.00;
    }
}

// Villain calling `bet` to win `pot + bet` needs bet/(pot + 2*bet) to break even. Bluffs at exactly
// that share of the betting range make calling and folding equal for villain, whoever it is.
inline double bluffShare(int pot, int bet) {
    if (pot <= 0 || bet <= 0) return 0.0;
    return static_cast<double>(bet) / (pot + 2.0 * bet);
}

// Deterministic draw from the cards: reproducible in tests, unreadable without the hole cards, no RNG state.
inline double cardHash(const std::vector<Card> &hole, const std::vector<Card> &board) {
    unsigned long long h = 1469598103934665603ULL;
    for (const std::vector<Card> *v : {&hole, &board}) {
        for (const Card &c : *v) {
            h ^= static_cast<unsigned long long>(static_cast<int>(c.rank) * 4 +
                                                 static_cast<int>(c.suit));
            h *= 1099511628211ULL;
        }
    }
    return static_cast<double>((h >> 11) % 100000) / 100000.0;
}

// Bluff frequency is counted over our own holdings on this board (value vs air), not a fixed fraction
// of air hands: air is far more common than value, and a fixed fraction over-bluffs about two to one.
inline double bluffFrequency(const std::vector<Card> &board, double rangeFraction,
                             double valueThreshold, double airThreshold,
                             int pot, int bet, unsigned long long seed = 0) {
    const double share = bluffShare(pot, bet);
    if (share <= 0.0 || share >= 1.0) return 0.0;

    std::vector<Card> deck;
    for (int su = 0; su < 4; ++su) {
        for (int r = 2; r <= 14; ++r) {
            Card c(static_cast<Rank>(r), static_cast<Suit>(su));
            if (std::find(board.begin(), board.end(), c) == board.end()) {
                deck.push_back(c);
            }
        }
    }

    // Every 31st combination, not a random sample: deterministic, and 31 is coprime with the suit and
    // rank strides so the walk does not land on one suit.
    int value = 0, air = 0, step = 0;
    unsigned long long n = 0;
    auto tally = [&](double eq) {
        if (eq >= valueThreshold) ++value;
        else if (eq < airThreshold) ++air;
    };
#ifdef USE_METAL
    const bool gpu = metalAvailable();
    std::vector<EquityJob> jobs;
#endif
    for (size_t i = 0; i < deck.size(); ++i) {
        for (size_t j = i + 1; j < deck.size(); ++j) {
            if (step++ % 31 != 0) continue;
            MonteCarloSimulator sim({deck[i], deck[j]}, board, 300);
            sim.setVillainRange(rangeFraction);
            if (seed) sim.setSeed(seed + 1 + n++);
#ifdef USE_METAL
            if (gpu) { jobs.push_back(sim.metalJob()); continue; }
#endif
            sim.runSimulation();
            tally(sim.getEquity());
        }
    }
#ifdef USE_METAL
    if (gpu) {
        for (const EquityResult &r : metalEquityBatch(jobs))
            tally((r.wins + 0.5 * r.ties) / r.trials);
    }
#endif

    if (air == 0) return 0.0;
    // bluffs / (bluffs + value) = share, with bluffs = freq * air.
    const double freq = (share / (1.0 - share)) * (static_cast<double>(value) / air);
    return std::max(0.0, std::min(1.0, freq));
}

struct Decision {
    std::string action;   // "fold" | "check" | "call" | "raise"
    int amount = 0;       // total bet, when action is "raise"
    double equity = 0.0;  // Monte Carlo equity against the modelled range
    double realized = 0.0;// equity after the realization discount
    double range = 1.0;   // fraction of hands the opponent is credited with
    double required = 0.0;// equity the pot price demands
    bool bluff = false;   // true when this bet is made with a hand that cannot win a showdown
};

#ifndef OPEN_EQ
#define OPEN_EQ 0.50       // ponytail: fitted; minimum raw equity to open
#endif
#ifndef OPEN_SIZE_BB
#define OPEN_SIZE_BB 2.5
#endif
#ifndef OPEN_MAX_BB
// open only at or under this many big blinds at hand start
#define OPEN_MAX_BB 1e9
#endif

// `realizationScale`, `bluffEnabled` and `preflopRealization` exist so tools/bench.py can A/B them;
// the defaults are the shipping behaviour.
inline Decision decideFull(const std::vector<Card> &hole,
                          const std::vector<Card> &board,
                          int pot, int toCall, int minRaise, int maxRaise,
                          int stack, int bb, int sims, int villainRaises = 0,
                          double realizationScale = 1.0, bool bluffEnabled = true,
                          double rangeFloor = 0.0, unsigned long long seed = 0,
                          double preflopRealization = kPreflopRealization) {
    // The SDK passes to_call uncapped; we can only call our stack.
    if (toCall > stack && stack > 0) { pot -= toCall - stack; toCall = stack; }
    Decision d;
    d.range = std::max(villainRangeFraction(villainRaises, toCall, pot), rangeFloor);

    MonteCarloSimulator sim(hole, board, sims);
    sim.setVillainRange(d.range);
    sim.setSeed(seed);
    sim.runSimulation();
    double equity = sim.getEquity();
    d.equity = equity;

    // Realization applies to continuing for a price, not to betting (fold equity) nor to a call that
    // ends the betting (all-in, or raising closed): nothing is left to lose there.
    const bool callEndsBetting = toCall >= stack || maxRaise <= 0;
    const double shaded = (toCall > 0 && !callEndsBetting)
        ? equity * std::min(1.0, equityRealization(board.size(), preflopRealization) * realizationScale)
        : equity;
    d.realized = shaded;

    d.required = (toCall > 0) ? PokerMath::calculatePotOddsPercentage(pot, toCall) : 0.0;

    double stackInBB = (bb > 0) ? static_cast<double>(stack) / bb : 100.0;

    // Short stack: fold-or-shove, judged on raw equity because a shove ends the betting.
    // ponytail: shoving when checked to is a 5x-pot overbet. It is right against callers and wrong against folders, so sizing it by opponent type is planned (Phase 4).
    if (stackInBB <= 10.0 && equity >= 0.55) {
        int shove = boundedRaise(maxRaise, minRaise, maxRaise);
        if (shove > 0) { d.action = "raise"; d.amount = shove; return d; }
    }

    // ponytail: the 0.50 cut is fitted, not solved. A solved short-stack
    // open/shove table would replace it.
    // toCall < bb: only the blind difference is owed; more means a raise we did not count, not an open.
    if (board.empty() && villainRaises == 0 && toCall > 0 && toCall < bb && bb > 0 && equity >= OPEN_EQ &&
        (stack + bb - toCall) / static_cast<double>(bb) <= OPEN_MAX_BB) {
        int open = boundedRaise(static_cast<int>(OPEN_SIZE_BB * bb), minRaise, maxRaise);
        if (open > 0) { d.action = "raise"; d.amount = open; return d; }
    }

    if (toCall <= 0) {
        const int target = boundedRaise(static_cast<int>(pot * 0.66), minRaise, maxRaise);

        if (shaded >= 0.62 && target > 0) {
            d.action = "raise";
            d.amount = target;
            return d;
        }

        // Betting is polarised: strong hands and hopeless ones, never the middle. A hand with showdown
        // value loses it by betting, so those check.
        // ponytail: the 0.62 and 0.30 bucket edges are fitted. The frequency
        // between them is computed, not fitted.
        if (bluffEnabled && equity < 0.30 && target > 0 && stack > target) {
            const double freq = bluffFrequency(board, d.range, 0.62, 0.30, pot, target, seed);
            if (cardHash(hole, board) < freq) {
                d.action = "raise";
                d.amount = target;
                d.bluff = true;
                return d;
            }
        }

        d.action = "check";
        return d;
    }

    if (shaded <= d.required) { d.action = "fold"; return d; }

    // Raising is judged on raw equity: realization is the cost of calling down, and raising avoids it.
    if (equity >= 0.75) {
        int target = boundedRaise(static_cast<int>((pot + toCall) * 0.75) + toCall,
                                  minRaise, maxRaise);
        if (target > 0) { d.action = "raise"; d.amount = target; return d; }
    }

    d.action = "call";
    return d;
}

}

#endif
