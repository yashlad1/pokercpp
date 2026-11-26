// Line protocol (all integers, cards as two chars "As" "Th" "2c"):
//   <nhole> <hole...> <nboard> <board...> <pot> <to_call> <min_raise> <max_raise> <stack> <bb> <sims> [villain_raises] [seed]
// Reply:
//   fold | check | call | raise <total_bet>

#include "decide.h"

#include <iostream>
#include <sstream>
#include <string>
#include <vector>

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

        // Trailing and optional: older callers omit it. A nonzero seed after it fixes the Monte Carlo draws.
        int villainRaises = 0;
        if (ok) in >> villainRaises;

        unsigned long long seed = 0;
        if (ok) in >> seed;

        // A malformed line must still get one reply: the Python side blocks on it until the server's budget expires.
        if (!ok || hole.size() != 2) {
            std::cout << (toCall > 0 ? "fold" : "check") << std::endl;
            continue;
        }

        if (sims <= 0) sims = 5000;
        chipzen::Decision d = chipzen::decideFull(hole, board, pot, toCall, minRaise, maxRaise,
                                                  stack, bb, sims, villainRaises,
                                                  1.0, true, 0.0, seed);
        std::cout << (d.action == "raise" ? d.action + " " + std::to_string(d.amount) : d.action)
                  << std::endl;
    }
    return 0;
}
