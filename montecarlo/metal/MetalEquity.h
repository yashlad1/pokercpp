// Apple Metal GPU path for Monte Carlo equity. Research/local only: compiled
// in solely with -DUSE_METAL on macOS. Plain C++17, no Objective-C.
#ifndef METAL_EQUITY_H
#define METAL_EQUITY_H

#include "../../model/card.h"
#include <array>
#include <utility>
#include <vector>

struct EquityJob {
    Card hero[2];
    std::vector<Card> board;                          // 0, 3, 4 or 5 cards
    std::vector<std::pair<Card, Card>> villainCombos; // allowed villain holdings
    int trials;
    unsigned long long seed;                          // 0 = random
};

struct EquityResult { int wins, ties, trials; };

// True when a Metal device exists and the kernels compiled. Set the env var
// POKER_NO_METAL=1 to force false (A/B runs).
bool metalAvailable();

// One GPU dispatch for all jobs. Combos that clash with hero/board are dropped;
// if none remain, every non-conflicting combo is used (as the CPU path does).
// Nonzero seed: repeatable for the same batch contents.
std::vector<EquityResult> metalEquityBatch(const std::vector<EquityJob>&);

// Test hook. Each deal is hero 2, villain 2, board 5. Result per deal:
// +1 hero wins, 0 tie, -1 hero loses.
std::vector<int> metalCompare(const std::vector<std::array<Card, 9>>& deals);

#endif
