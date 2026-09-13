// Decision logic shared by the CLI solver and the Python extension module.
//
// Kept in one header so the binary the tests drive and the module the bot
// imports cannot drift apart — they compile the same source.

#ifndef CHIPZEN_DECIDE_H
#define CHIPZEN_DECIDE_H

#include "../montecarlo/MonteCarloSimulator.h"
#include "../model/poker_math.h"
#include "../model/card.h"

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

// Clamp a desired total bet into the band the server will accept. Returns 0
// when raising is illegal this turn (the server reports both bounds as 0).
inline int boundedRaise(int target, int minRaise, int maxRaise) {
    if (minRaise <= 0 || maxRaise <= 0) return 0;
    return std::max(minRaise, std::min(target, maxRaise));
}

// How wide a range to credit the opponent with, from what they have done
// this hand. Heads-up opens are wide; re-raises are not.
//
// ponytail: a step function fitted by hand, not from data. The right version
// learns these from observed showdowns. Replace it once there are hands to
// learn from - the shape below is a starting prior, not a finding.
inline double villainRangeFraction(int villainRaises, int toCall, int pot) {
    double f = 1.0;
    if (villainRaises >= 1) f = 0.45;
    if (villainRaises >= 2) f = 0.18;
    if (villainRaises >= 3) f = 0.08;

    // Within that band, the price asked says something too: betting large
    // is a stronger action than betting small.
    if (toCall > 0 && pot > 0) {
        double betFraction = static_cast<double>(toCall) / pot;
        if (betFraction > 0.75) f *= 0.7;
        else if (betFraction < 0.35) f *= 1.3;
    }

    return std::max(0.05, std::min(1.0, f));
}

// Share of raw equity a hand can expect to actually collect.
//
// Monte Carlo equity assumes every hand runs to showdown for free. It does
// not: calling now means surviving the betting still to come, and a hand
// that has to fold the turn never collects the river equity counted here.
// The further from showdown, the less of it is real. On the river the board
// is complete and the number is exact, so realization is 1.
//
// ponytail: depends only on the street, not on position, stack depth or
// whether the hand is the kind that flops well. Those are the next terms if
// this proves to matter.
inline double equityRealization(size_t boardSize) {
    switch (boardSize) {
        case 0:  return 0.75;   // preflop: three streets to navigate
        case 3:  return 0.82;   // flop
        case 4:  return 0.90;   // turn
        default: return 1.00;   // river: showdown next, nothing left to lose
    }
}

// Fraction of a betting range that should be bluffs, for a bet of `bet`
// into a pot of `pot`.
//
// Villain calling `bet` to win `pot + bet` needs bet/(pot + 2*bet) to break
// even. Make bluffs exactly that share of the betting range and villain
// gains nothing by calling or by folding - the bluffs pay for the times the
// value bets get paid. This is arithmetic, not an opponent model: it holds
// whoever is sitting there.
inline double bluffShare(int pot, int bet) {
    if (pot <= 0 || bet <= 0) return 0.0;
    return static_cast<double>(bet) / (pot + 2.0 * bet);
}

// Deterministic pseudo-random draw in [0,1) from the cards themselves.
//
// Bluffing has to be a frequency, not a rule, or it is readable. Deriving it
// from the hole cards and board rather than an RNG means the same spot always
// resolves the same way - reproducible in tests, and still unguessable to an
// opponent who cannot see the hole cards. No generator state to thread
// through, and no seeding question across decisions.
inline double cardHash(const std::vector<Card> &hole, const std::vector<Card> &board) {
    unsigned long long h = 1469598103934665603ULL;  // FNV-1a offset basis
    for (const std::vector<Card> *v : {&hole, &board}) {
        for (const Card &c : *v) {
            h ^= static_cast<unsigned long long>(static_cast<int>(c.rank) * 4 +
                                                 static_cast<int>(c.suit));
            h *= 1099511628211ULL;
        }
    }
    return static_cast<double>((h >> 11) % 100000) / 100000.0;
}

// How often to bluff with a hopeless hand, so that bluffs end up the right
// share of the betting range.
//
// The share above is a property of the range, not of one hand. Betting a
// fixed fraction of air hands only lands on it if air and value hands are
// equally common, and they are not: most hands miss most boards, and miss
// them worse the more cards are out. Getting this wrong over-bluffs by two
// to one, which any opponent that calls a lot collects on.
//
// So count instead of guessing. Walk our own possible holdings on this
// board, tally how many are strong enough to value bet against how many are
// hopeless, and set the frequency from the actual composition. Cheap
// simulations are fine here - this decides a frequency, not a hand.
inline double bluffFrequency(const std::vector<Card> &board, double rangeFraction,
                             double valueThreshold, double airThreshold,
                             int pot, int bet) {
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

    // Every 31st combination rather than a random sample: deterministic, so
    // the same board always yields the same frequency, and 31 is coprime
    // with the suit and rank strides so the walk does not land on one suit.
    int value = 0, air = 0, step = 0;
    for (size_t i = 0; i < deck.size(); ++i) {
        for (size_t j = i + 1; j < deck.size(); ++j) {
            if (step++ % 31 != 0) continue;
            MonteCarloSimulator sim({deck[i], deck[j]}, board, 300);
            sim.setVillainRange(rangeFraction);
            sim.runSimulation();
            const double eq = sim.getEquity();
            if (eq >= valueThreshold) ++value;
            else if (eq < airThreshold) ++air;
        }
    }

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

inline Decision decideFull(const std::vector<Card> &hole,
                          const std::vector<Card> &board,
                          int pot, int toCall, int minRaise, int maxRaise,
                          int stack, int bb, int sims, int villainRaises = 0) {
    Decision d;
    d.range = villainRangeFraction(villainRaises, toCall, pot);

    MonteCarloSimulator sim(hole, board, sims);
    sim.setVillainRange(d.range);
    sim.runSimulation();
    double equity = sim.getEquity();
    d.equity = equity;

    // Equity is already measured against the range the opponent is credited
    // with, so no bet-size fudge is needed on top. What is still needed is
    // the discount for equity we will not get to collect.
    //
    // Realization applies to continuing for a price. It does not apply when
    // betting: a bet can win the pot outright, and that fold equity is
    // exactly what a called-down hand lacks.
    const double shaded = (toCall > 0) ? equity * equityRealization(board.size())
                                       : equity;
    d.realized = shaded;

    d.required = (toCall > 0) ? PokerMath::calculatePotOddsPercentage(pot, toCall) : 0.0;

    double stackInBB = (bb > 0) ? static_cast<double>(stack) / bb : 100.0;

    // Short stack: the fold-or-shove zone, judged on raw equity for the same
    // reason - a shove ends the betting, so there is nothing left to realize.
    if (stackInBB <= 10.0 && equity >= 0.55) {
        int shove = boundedRaise(maxRaise, minRaise, maxRaise);
        if (shove > 0) { d.action = "raise"; d.amount = shove; return d; }
    }

    if (toCall <= 0) {
        const int target = boundedRaise(static_cast<int>(pot * 0.66), minRaise, maxRaise);

        // Nothing to call: bet for value...
        if (shaded >= 0.62 && target > 0) {
            d.action = "raise";
            d.amount = target;
            return d;
        }

        // ...or bluff, with hands too weak to win a showdown anyway. Betting
        // is polarised on purpose: the strong hands and the hopeless ones,
        // never the middle. A hand with some showdown value loses that value
        // by betting - it folds out everything it beats and gets called by
        // everything that beats it - so those check.
        //
        // ponytail: the 0.62 and 0.30 bucket edges are fitted. The frequency
        // between them is computed, not fitted.
        if (equity < 0.30 && target > 0 && stack > target) {
            const double freq = bluffFrequency(board, d.range, 0.62, 0.30, pot, target);
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

    // Continuing for a price is judged on equity we expect to collect...
    if (shaded <= d.required) { d.action = "fold"; return d; }

    // ...but whether to raise is judged on the raw number. Realization is
    // the cost of having to call down; raising is how a hand avoids paying
    // it, so discounting the raise threshold by it would have the best hands
    // flat-calling exactly when they should be building the pot.
    if (equity >= 0.75) {
        int target = boundedRaise(static_cast<int>((pot + toCall) * 0.75) + toCall,
                                  minRaise, maxRaise);
        if (target > 0) { d.action = "raise"; d.amount = target; return d; }
    }

    d.action = "call";
    return d;
}

// Line-protocol form, for the CLI binary the tests drive.
inline std::string decide(const std::vector<Card> &hole,
                          const std::vector<Card> &board,
                          int pot, int toCall, int minRaise, int maxRaise,
                          int stack, int bb, int sims, int villainRaises = 0) {
    Decision d = decideFull(hole, board, pot, toCall, minRaise, maxRaise, stack, bb,
                            sims, villainRaises);
    return d.action == "raise" ? d.action + " " + std::to_string(d.amount) : d.action;
}


} // namespace chipzen

#endif
