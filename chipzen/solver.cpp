// Chipzen decision helper.
//
// Reads one game state per line on stdin, writes one action per line on
// stdout. The Python bot in bot.py owns the WebSocket; everything that
// decides anything lives here, so the C++ engine stays the brain.
//
// Line protocol (all integers, cards as two chars "As" "Th" "2c"):
//   <nhole> <hole...> <nboard> <board...> <pot> <to_call> <min_raise> <max_raise> <stack> <bb> <sims>
// Reply:
//   fold | check | call | raise <total_bet>
//
// A line protocol rather than JSON keeps a JSON dependency out of the C++
// build entirely; `cin >>` is the whole parser.

#include "../montecarlo/MonteCarloSimulator.h"
#include "../model/poker_math.h"
#include "../model/card.h"

#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <algorithm>

static bool parseCard(const std::string &s, Card &out) {
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
static int boundedRaise(int target, int minRaise, int maxRaise) {
    if (minRaise <= 0 || maxRaise <= 0) return 0;
    return std::max(minRaise, std::min(target, maxRaise));
}

static std::string decide(const std::vector<Card> &hole,
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

int main() {
    std::ios::sync_with_stdio(false);

    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;
        std::istringstream in(line);

        std::vector<Card> hole, board;
        int n = 0;
        bool ok = true;

        for (auto *dest : {&hole, &board}) {
            if (!(in >> n)) { ok = false; break; }
            for (int i = 0; i < n && ok; ++i) {
                std::string tok;
                Card c(Rank::Two, Suit::Clubs);
                if (!(in >> tok) || !parseCard(tok, c)) ok = false;
                else dest->push_back(c);
            }
            if (!ok) break;
        }

        int pot = 0, toCall = 0, minRaise = 0, maxRaise = 0, stack = 0, bb = 0, sims = 0;
        if (ok) ok = static_cast<bool>(in >> pot >> toCall >> minRaise >> maxRaise >> stack >> bb >> sims);

        // A malformed line must still get an answer: the Python side is
        // waiting on exactly one reply and would otherwise block until the
        // server's decision budget expires.
        if (!ok || hole.size() != 2) {
            std::cout << (toCall > 0 ? "fold" : "check") << std::endl;
            continue;
        }

        if (sims <= 0) sims = 5000;
        std::cout << decide(hole, board, pot, toCall, minRaise, maxRaise, stack, bb, sims)
                  << std::endl;
    }
    return 0;
}
