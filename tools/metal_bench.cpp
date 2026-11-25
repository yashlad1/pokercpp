// Speed and agreement: CPU MonteCarloSimulator vs the Metal path.
// clang++ -std=c++17 -O2 -DUSE_METAL -fobjc-arc tools/metal_bench.cpp \
//   montecarlo/MonteCarloSimulator.cpp montecarlo/metal/MetalEquity.mm \
//   model/advanced_hand_evaluator.cpp model/card.cpp model/deck.cpp \
//   -framework Metal -framework Foundation -o metal_bench
#include "../montecarlo/MonteCarloSimulator.h"
#include "../model/advanced_hand_evaluator.h"
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <random>

using Clock = std::chrono::steady_clock;
static double ms(Clock::time_point t) {
    return std::chrono::duration<double, std::milli>(Clock::now() - t).count();
}
static Card C(Rank r, Suit s) { return Card(r, s); }

static std::vector<Card> fullDeck() {
    std::vector<Card> d;
    for (int s = 0; s < 4; ++s)
        for (int r = 2; r <= 14; ++r) d.emplace_back(static_cast<Rank>(r), static_cast<Suit>(s));
    return d;
}

int main() {
    std::printf("metalAvailable: %d\n", (int)metalAvailable());
    if (!metalAvailable()) return 1;

    Card ah = C(Rank::Ace, Suit::Hearts), as = C(Rank::Ace, Suit::Spades);
    Card kh = C(Rank::King, Suit::Hearts), ks = C(Rank::King, Suit::Spades);
    std::vector<Card> hero = {ah, ks}, board = {C(Rank::Two, Suit::Clubs), C(Rank::Seven, Suit::Diamonds), C(Rank::Jack, Suit::Hearts)};
    std::vector<Card> deck = fullDeck();

    // Reference CPU path: the same simulator, forced onto the CPU loop.
    auto cpuRun = [&](int n) {
        // Same algorithm as MonteCarloSimulator's CPU loop (Metal is cached on, so inline it).
        std::mt19937 g(1);
        std::vector<Card> d;
        for (const Card &c : deck)
            if (!(c == hero[0]) && !(c == hero[1]) && std::find(board.begin(), board.end(), c) == board.end()) d.push_back(c);
        int w = 0, t = 0;
        for (int i = 0; i < n; ++i) {
            std::shuffle(d.begin(), d.end(), g);
            std::vector<Card> opp = {d[0], d[1]}, b = board;
            for (size_t k = 2; b.size() < 5; ++k) b.push_back(d[k]);
            std::vector<Card> h = hero, o = opp;
            h.insert(h.end(), b.begin(), b.end());
            o.insert(o.end(), b.begin(), b.end());
            HandValue hv = AdvancedHandEvaluator::evaluate(h), ov = AdvancedHandEvaluator::evaluate(o);
            if (hv > ov) ++w; else if (!(ov > hv)) ++t;
        }
        return (w + 0.5 * t) / n;
    };

    auto jobFor = [&](int n, unsigned long long seed) {
        MonteCarloSimulator s(hero, board, n);
        s.setSeed(seed);
        return s.metalJob();
    };
    auto gpuEq = [](const EquityResult &r) { return (r.wins + 0.5 * r.ties) / r.trials; };

    metalEquityBatch({jobFor(100, 1)});  // warm-up: compiles kernels, first dispatch
    std::printf("%-22s %10s %10s %10s %10s\n", "case", "cpu ms", "gpu ms", "cpu eq", "gpu eq");
    for (int n : {2000, 5000, 1000000}) {
        auto t = Clock::now(); double ce = cpuRun(n); double cm = ms(t);
        t = Clock::now(); EquityResult r = metalEquityBatch({jobFor(n, 7)})[0]; double gm = ms(t);
        std::printf("%-22s %10.2f %10.2f %10.4f %10.4f\n", ("1 job x " + std::to_string(n)).c_str(), cm, gm, ce, gpuEq(r));
    }
    {
        auto t = Clock::now();
        for (int i = 0; i < 43; ++i) cpuRun(300);
        double cm = ms(t);
        std::vector<EquityJob> jobs;
        for (int i = 0; i < 43; ++i) jobs.push_back(jobFor(300, 100 + i));
        t = Clock::now(); auto rs = metalEquityBatch(jobs); double gm = ms(t);
        std::printf("%-22s %10.2f %10.2f %10s %10.4f\n", "43 x 300 batch", cm, gm, "-", gpuEq(rs[0]));
    }

    // AA vs KK (specific suits, no board): expect ~0.826 for AA.
    {
        hero = {ah, as}; board = {};
        std::vector<std::pair<Card, Card>> kk = {{kh, ks}};
        EquityJob j{{ah, as}, {}, kk, 200000, 5};
        double g = gpuEq(metalEquityBatch({j})[0]);
        // CPU: same fixed villain hand through the evaluator loop.
        std::mt19937 rng(5);
        std::vector<Card> d;
        for (const Card &c : deck) if (!(c == ah) && !(c == as) && !(c == kh) && !(c == ks)) d.push_back(c);
        int w = 0, t2 = 0, n = 200000;
        for (int i = 0; i < n; ++i) {
            std::shuffle(d.begin(), d.end(), rng);
            std::vector<Card> h = {ah, as}, o = {kh, ks};
            for (int k = 0; k < 5; ++k) { h.push_back(d[k]); o.push_back(d[k]); }
            HandValue hv = AdvancedHandEvaluator::evaluate(h), ov = AdvancedHandEvaluator::evaluate(o);
            if (hv > ov) ++w; else if (!(ov > hv)) ++t2;
        }
        std::printf("AA vs KK equity: cpu %.4f  gpu %.4f  (expect ~0.826)\n", (w + 0.5 * t2) / n, g);
    }

    // Seeded repeatability, and agreement of the evaluators on random deals.
    {
        double a = gpuEq(metalEquityBatch({jobFor(5000, 42)})[0]);
        double b = gpuEq(metalEquityBatch({jobFor(5000, 42)})[0]);
        std::printf("seed 42 twice: %.6f %.6f  %s\n", a, b, a == b ? "IDENTICAL" : "DIFFER");
        std::mt19937 rng(9);
        std::vector<std::array<Card, 9>> deals;
        for (int i = 0; i < 200000; ++i) {
            std::shuffle(deck.begin(), deck.end(), rng);
            deals.push_back({deck[0], deck[1], deck[2], deck[3], deck[4], deck[5], deck[6], deck[7], deck[8]});
        }
        auto r = metalCompare(deals);
        int bad = 0;
        for (size_t i = 0; i < deals.size(); ++i) {
            const auto &d = deals[i];
            std::vector<Card> h = {d[0], d[1]}, o = {d[2], d[3]};
            for (int k = 4; k < 9; ++k) { h.push_back(d[k]); o.push_back(d[k]); }
            HandValue hv = AdvancedHandEvaluator::evaluate(h), ov = AdvancedHandEvaluator::evaluate(o);
            int cpu = hv > ov ? 1 : (ov > hv ? -1 : 0);
            bad += cpu != r[i];
        }
        std::printf("metalCompare vs CPU evaluator: %d mismatches / %zu random deals\n", bad, deals.size());
    }
}
