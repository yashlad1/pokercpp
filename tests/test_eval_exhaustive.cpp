// Classifies every one of the C(52,7) = 133,784,560 hands with fast_eval.h and compares each category total to the
// published figures. Category index 0..8 is score >> 20; royal counts as straight flush.
// Run:  ./tests/test_eval_exhaustive     (make test_eval_exhaustive, also part of make test)

#include "../model/advanced_hand_evaluator.h"
#include "../model/fast_eval.h"

#include <cstdint>
#include <cstdio>
#include <random>

static const char *NAMES[9] = {"high card", "one pair", "two pair", "three of a kind", "straight",
                               "flush", "full house", "four of a kind", "straight flush"};
static const uint64_t EXPECTED[9] = {23294460, 58627800, 31433400, 6461620, 6180020,
                                     4047644,  3473184,  224848,   41584};
static const uint64_t TOTAL = 133784560;

static int advancedCategory(const std::vector<Card> &cards)
{
    int r = static_cast<int>(AdvancedHandEvaluator::evaluate(cards).rank);
    return r > 8 ? 8 : r;
}

int main()
{
    uint64_t counts[9] = {0};
    uint64_t seen = 0;
    for (int a = 0; a < 46; ++a) { uint64_t ma = 1ULL << a;
    for (int b = a + 1; b < 47; ++b) { uint64_t mb = ma | 1ULL << b;
    for (int c = b + 1; c < 48; ++c) { uint64_t mc = mb | 1ULL << c;
    for (int d = c + 1; d < 49; ++d) { uint64_t md = mc | 1ULL << d;
    for (int e = d + 1; e < 50; ++e) { uint64_t me = md | 1ULL << e;
    for (int f = e + 1; f < 51; ++f) { uint64_t mf = me | 1ULL << f;
    for (int g = f + 1; g < 52; ++g) {
        ++counts[fast_eval::evalMask(mf | 1ULL << g) >> 20];
        ++seen;
    }}}}}}}

    int failures = 0;
    for (int i = 8; i >= 0; --i) {
        bool ok = counts[i] == EXPECTED[i];
        std::printf("%-16s %12llu  expected %12llu  %s\n", NAMES[i], (unsigned long long)counts[i],
                    (unsigned long long)EXPECTED[i], ok ? "ok" : "MISMATCH");
        failures += !ok;
    }
    bool totalOk = seen == TOTAL;
    std::printf("%-16s %12llu  expected %12llu  %s\n", "total", (unsigned long long)seen,
                (unsigned long long)TOTAL, totalOk ? "ok" : "MISMATCH");
    failures += !totalOk;

    std::mt19937 rng(30);
    const int SAMPLES = 2000000;
    int disagreements = 0;
    for (int n = 0; n < SAMPLES; ++n) {
        uint64_t m = 0;
        std::vector<Card> cards;
        while (cards.size() < 7) {
            int id = static_cast<int>(rng() % 52);
            if (m >> id & 1) continue;
            m |= 1ULL << id;
            cards.push_back(Card(static_cast<Suit>(id / 13), static_cast<Rank>(id % 13 + 2)));
        }
        if (static_cast<int>(fast_eval::evalMask(m) >> 20) != advancedCategory(cards)) ++disagreements;
    }
    std::printf("advanced vs fast category disagreements on %d seeded hands: %d\n", SAMPLES, disagreements);
    failures += disagreements != 0;

    std::printf(failures ? "FAILED\n" : "All exhaustive evaluator checks passed\n");
    return failures ? 1 : 0;
}
