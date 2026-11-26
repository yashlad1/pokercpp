// test_eval_order.cpp: the fast evaluator's score order, checked on all 2,598,960
// five-card hands against a key built here from poker rules (nothing taken from
// the evaluator). The key is the category, then the ranks in tie-break order:
// ranks grouped by count (bigger group first), then by rank, high to low. The
// wheel A-2-3-4-5 is the lowest straight; a royal flush is the top straight flush.
//
// Checks: equal key means equal score; scores rise strictly with the key; there are
// 7,462 classes split 1277/2860/858/858/10/1277/156/156/10 from high card up; the
// reference evaluator (AdvancedHandEvaluator) orders the same hands the same way.
// Then 2,000,000 seeded seven-card hands: score == max over the 21 five-card subsets.
// test_eval_exhaustive only counts categories, so it cannot see a kicker-order bug.

#include "../model/advanced_hand_evaluator.h"
#include "../model/fast_eval.h"

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <random>
#include <vector>

struct Row { uint32_t key, score; uint64_t mask; };

// Rank index 0 (two) .. 12 (ace). Returns category << 20 | five 4-bit rank nibbles.
static uint32_t referenceKey(uint64_t mask)
{
    int count[13] = {0}, suitCount[4] = {0};
    for (int id = 0; id < 52; ++id)
        if (mask >> id & 1) { ++count[id % 13]; ++suitCount[id / 13]; }

    bool flush = false;
    for (int s = 0; s < 4; ++s) flush |= suitCount[s] == 5;

    // Ranks ordered by (count desc, rank desc).
    std::vector<int> order;
    for (int g = 4; g >= 1; --g)
        for (int r = 12; r >= 0; --r)
            if (count[r] == g) order.push_back(r);
    int groups = (int)order.size();
    int top = count[order[0]];
    int second = groups > 1 ? count[order[1]] : 0;

    bool straight = false;
    int straightTop = 0;
    if (groups == 5) {
        if (order[0] - order[4] == 4) { straight = true; straightTop = order[0]; }
        else if (order[0] == 12 && order[1] == 3) { straight = true; straightTop = 3; } // wheel
    }

    int cat;
    if (straight && flush) cat = 8;
    else if (top == 4) cat = 7;
    else if (top == 3 && second == 2) cat = 6;
    else if (flush) cat = 5;
    else if (straight) cat = 4;
    else if (top == 3) cat = 3;
    else if (top == 2 && second == 2) cat = 2;
    else if (top == 2) cat = 1;
    else cat = 0;

    if (straight) { order.assign(1, straightTop); }
    uint32_t key = (uint32_t)cat << 20;
    for (int i = 0; i < 5; ++i) key |= (uint32_t)(i < (int)order.size() ? order[i] : 0) << (16 - 4 * i);
    return key;
}

static std::vector<Card> cardsOf(uint64_t mask)
{
    std::vector<Card> v;
    for (int id = 0; id < 52; ++id)
        if (mask >> id & 1) v.push_back(Card(static_cast<Suit>(id / 13), static_cast<Rank>(id % 13 + 2)));
    return v;
}

int main()
{
    int failures = 0;
    auto fail = [&](const char *what, uint64_t mask) {
        if (++failures <= 10) std::printf("FAIL: %s (hand mask %llx)\n", what, (unsigned long long)mask);
    };

    std::vector<Row> rows;
    rows.reserve(2598960);
    for (int a = 0; a < 48; ++a) { uint64_t ma = 1ULL << a;
    for (int b = a + 1; b < 49; ++b) { uint64_t mb = ma | 1ULL << b;
    for (int c = b + 1; c < 50; ++c) { uint64_t mc = mb | 1ULL << c;
    for (int d = c + 1; d < 51; ++d) { uint64_t md = mc | 1ULL << d;
    for (int e = d + 1; e < 52; ++e) { uint64_t m = md | 1ULL << e;
        rows.push_back({referenceKey(m), fast_eval::evalMask(m), m});
    }}}}}
    std::printf("five-card hands: %zu (expected 2598960)\n", rows.size());
    failures += rows.size() != 2598960;

    std::sort(rows.begin(), rows.end(), [](const Row &x, const Row &y) { return x.key < y.key; });

    static const int CLASSES[9] = {1277, 2860, 858, 858, 10, 1277, 156, 156, 10};
    int perCategory[9] = {0}, classes = 0;
    HandValue prev{}, cur{};
    const Row *rep = nullptr;
    for (const Row &r : rows) {
        HandValue hv = AdvancedHandEvaluator::evaluate(cardsOf(r.mask));
        if (rep && r.key == rep->key) {
            if (r.score != rep->score) fail("same key, different score", r.mask);
            if (!(hv == cur)) fail("reference evaluator: same key, unequal HandValue", r.mask);
            continue;
        }
        if (rep) {
            if (!(r.score > rep->score)) fail("score does not rise with the key", r.mask);
            if (!(hv > prev)) fail("reference evaluator: HandValue does not rise with the key", r.mask);
        }
        ++classes;
        ++perCategory[r.key >> 20];
        prev = cur = hv;
        rep = &r;
    }
    std::printf("distinct classes: %d (expected 7462)\n", classes);
    failures += classes != 7462;
    for (int i = 0; i < 9; ++i) {
        std::printf("  category %d: %d classes (expected %d)\n", i, perCategory[i], CLASSES[i]);
        failures += perCategory[i] != CLASSES[i];
    }

    // Seven cards: the score is the best five-card score.
    std::mt19937 rng(104);
    const int SAMPLES = 2000000;
    int mismatches = 0;
    int ids[52];
    for (int i = 0; i < 52; ++i) ids[i] = i;
    for (int n = 0; n < SAMPLES; ++n) {
        for (int i = 0; i < 7; ++i) std::swap(ids[i], ids[i + rng() % (52 - i)]);
        uint64_t m7 = 0;
        for (int i = 0; i < 7; ++i) m7 |= 1ULL << ids[i];
        uint32_t best = 0;
        for (int skip1 = 0; skip1 < 7; ++skip1)
            for (int skip2 = skip1 + 1; skip2 < 7; ++skip2)
                best = std::max(best, fast_eval::evalMask(m7 & ~(1ULL << ids[skip1]) & ~(1ULL << ids[skip2])));
        if (fast_eval::evalMask(m7) != best) { ++mismatches; fail("seven-card score != best five-card score", m7); }
    }
    std::printf("seven-card hands where score != best of 21 five-card subsets: %d of %d\n", mismatches, SAMPLES);

    std::printf(failures ? "FAILED\n" : "All score-order checks passed\n");
    return failures ? 1 : 0;
}
