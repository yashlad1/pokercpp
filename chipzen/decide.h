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

inline std::string decide(const std::vector<Card> &hole,
                          const std::vector<Card> &board,
                          int pot, int toCall, int minRaise, int maxRaise,
                          int stack, int bb, int sims) {
    MonteCarloSimulator sim(hole, board, sims);
    sim.runSimulation();
    double equity = sim.getEquity();

    // The simulator deals the opponent a uniform random hand. A real
    // opponent who is betting into us holds better than random, so raw
    // equity overstates our share by more the larger the bet is. Shade it
    // down in proportion to the price being asked.
    //
    // ponytail: flat linear discount, no opponent model. Replace with a
    // range model built from action_history if the rating says it matters.
    double shaded = equity;
    if (toCall > 0 && pot > 0) {
        double betFraction = static_cast<double>(toCall) / pot;
        shaded = equity - 0.10 * std::min(1.0, betFraction);
    }

    double stackInBB = (bb > 0) ? static_cast<double>(stack) / bb : 100.0;

    // Short stack: the fold-or-shove zone. With under 10 big blinds there is
    // no room to bet and still fold later, so flat-calling just leaks.
    if (stackInBB <= 10.0 && shaded >= 0.55) {
        int shove = boundedRaise(maxRaise, minRaise, maxRaise);
        if (shove > 0) return "raise " + std::to_string(shove);
    }

    if (toCall <= 0) {
        // Nothing to call: bet for value, otherwise take the free card.
        if (shaded >= 0.62) {
            int target = boundedRaise(static_cast<int>(pot * 0.66), minRaise, maxRaise);
            if (target > 0) return "raise " + std::to_string(target);
        }
        return "check";
    }

    double required = PokerMath::calculatePotOddsPercentage(pot, toCall);
    if (shaded <= required) return "fold";

    // Strong enough that getting more money in beats just calling.
    if (shaded >= 0.75) {
        int target = boundedRaise(static_cast<int>((pot + toCall) * 0.75) + toCall,
                                  minRaise, maxRaise);
        if (target > 0) return "raise " + std::to_string(target);
    }

    return "call";
}


} // namespace chipzen

#endif
