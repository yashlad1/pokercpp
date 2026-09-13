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

#include "decide.h"

#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <algorithm>

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
                if (!(in >> tok) || !chipzen::parseCard(tok, c)) ok = false;
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
        std::cout << chipzen::decide(hole, board, pot, toCall, minRaise, maxRaise, stack, bb, sims)
                  << std::endl;
    }
    return 0;
}
