// Black-box test for the Metal equity path. Oracle: AdvancedHandEvaluator.
#include "montecarlo/metal/MetalEquity.h"
#include "model/advanced_hand_evaluator.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <sstream>
#include <string>
#include <vector>

static int fails = 0;
#define CHECK(c, ...) do { if (!(c)) { ++fails; std::printf("FAIL %s:%d ", __FILE__, __LINE__); std::printf(__VA_ARGS__); std::printf("\n"); } } while (0)

static Card mkc(int i) { return Card((Rank)(2 + i % 13), (Suit)(i / 13)); }
static int cardIdx(const Card& c) { return (int)c.suit * 13 + ((int)c.rank - 2); }
static Card parse(const std::string& s) {
    int r = std::string("23456789TJQKA").find(s[0]);
    int su = std::string("hdcs").find(s[1]);
    return Card((Rank)(2 + r), (Suit)su);
}
static std::array<Card, 9> mk9(const std::vector<Card>& v) {
    return {v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7], v[8]};
}
static int cpuCmp(const std::array<Card, 9>& d) {
    std::vector<Card> h = {d[0], d[1], d[4], d[5], d[6], d[7], d[8]};
    std::vector<Card> v = {d[2], d[3], d[4], d[5], d[6], d[7], d[8]};
    HandValue a = AdvancedHandEvaluator::evaluate(h), b = AdvancedHandEvaluator::evaluate(v);
    return a > b ? 1 : (b > a ? -1 : 0);
}

struct T { const char* name; const char* deal; int exp; }; // hero2 villain2 board5
static const T targeted[] = {
    {"royal vs SF", "Ah Kh 9h 8h Qh Jh Th 2c 3d", 1},
    {"steel wheel vs 7-high straight", "Ah 2h 6d 7d 3h 4h 5h Kc 9d", 1},
    {"steel wheel vs 6-high straight", "Ah 2h 6d 2c 3h 4h 5h Kc 9d", 1},
    {"wheel vs pair of aces", "2c 3d Ad Qc As 4h 5c 9d Js", 1},
    {"6-high straight beats wheel", "2c Kd 6h 2h As 3d 4h 5c 9s", -1},
    {"quads A kicker vs K kicker", "Ac Kd Qc Jd 9c 9d 9h 9s 2c", 1},
    {"quads kicker on board tie", "Kd 2d Qc Jd 9c 9d 9h 9s Ac", 0},
    {"quads low hole vs low hole tie", "2d 3d 4d 5d 9c 9d 9h 9s Ks", 0},
    {"quads K vs Q kicker", "Ks 3c Qs 3d 9c 9d 9h 9s 2c", 1},
    {"quads vs full house", "8c 8d 9d 9s 8h 8s 9c 2d 3d", 1},
    {"FH higher trips wins", "Kh 3d 7d 7c Kc Kd 7h 2s 2c", 1},
    {"FH same trips higher pair", "Ac Ad Qc Qd Kc Kd Kh 5s 5c", 1},
    {"FH on board tie", "2c 3d 2d 4c Kc Kd Kh 5s 5c", 0},
    {"flush kickers 2nd", "Qh 3h Jh 4h Ah Kh 9h 5h 2c", 1},
    {"flush kickers 5th", "5h 3d 4h 3c Ah Kh Qh 9h 2c", 1},
    {"flush board plays tie", "2h 3c 2d 3d Ah Kh Qh Jh 9h", 0},
    {"flush vs straight", "Ah 2h Tc 4c 9h 8h 7h 6c 5d", 1},
    {"counterfeit two pair", "4c 4d Ac 9d Ks Kd 5h 5c 2d", -1},
    {"two pair kicker 4 vs 3", "4c 4d 3c 3d Ks Kd 5h 5c 2d", 1},
    {"counterfeit avoided, 88 beats 44", "8c 8d Ac Qd 9s 9d 4h 4c Kd", 1},
    {"trips vs two pair", "7h 3c Kc 9d 7s 7d 2h 9c Kd", 1},
    {"board straight flush plays tie", "2c 3d 4c 5d As Ks Qs Js Ts", 0},
    {"board straight tie", "2h Kd 3h Qd 2c 3d 4h 5s 6c", 0},
    {"high card kicker tie", "Qc 9c Qh 9h As Kd 7h 4c 2d", 0},
    {"high card kicker win", "Qc Jc Qh 9h As Kd 7h 4c 2d", 1},
    {"pair kicker win", "Ac Kd Ah Qd As 8d 5h 3c 2d", 1},
    {"six-card straight, highest", "9c Kd 4c 3d 5s 6d 7h 8c 2d", 1},
    {"board straight, villain higher", "4c 3d Tc 2d 5s 6d 7h 8c 9d", -1},
    {"seven-card run, hero high", "Tc Jc 4c 3d 5s 6d 7h 8c 9d", 1},
    {"ace-high straight vs queen-high", "Ac Kd 9c 8d Ts Jd Qh 2c 3d", 1},
    {"pair vs high card", "Ac Ad Kc Qd 2s 5h 8c Jd 3d", 1},
    {"two pair vs pair", "9c 8d As Ks 9d 8h 2c 3d Jc", 1},
    {"trips vs straight loses", "7c 7d 5c 6d 7h 8s 9c Kd 2h", -1},
    {"flush vs full house", "2h 3h Kc Kd Kh 7h 7s 9h 4c", -1},
    {"SF vs quads", "9h 8h Kc Kd Ks Kh 7h 6h 5h", 1},
};

static int runChild(const char* self) {
    std::string cmd = std::string("POKER_NO_METAL=1 '") + self + "' --child";
    return std::system(cmd.c_str());
}

int main(int argc, char** argv) {
    if (argc > 1 && std::string(argv[1]) == "--child") return metalAvailable() ? 1 : 0;
    if (!metalAvailable()) { std::printf("metal not available\n"); return 1; }

    // (a) targeted
    int nDeals = 0;
    for (const T& t : targeted) {
        std::istringstream ss(t.deal);
        std::vector<Card> v; std::string s;
        while (ss >> s) v.push_back(parse(s));
        auto d = mk9(v);
        std::array<Card, 9> sw = {d[2], d[3], d[0], d[1], d[4], d[5], d[6], d[7], d[8]};
        auto g = metalCompare({d, sw});
        nDeals += 2;
        CHECK(cpuCmp(d) == t.exp, "CPU disagrees with my expectation: %s", t.name);
        CHECK(cpuCmp(sw) == -t.exp, "CPU swapped: %s", t.name);
        CHECK(g[0] == cpuCmp(d), "GPU %d cpu %d: %s", g[0], cpuCmp(d), t.name);
        CHECK(g[1] == cpuCmp(sw), "GPU swapped %d cpu %d: %s", g[1], cpuCmp(sw), t.name);
    }
    std::printf("(a) targeted deals: %d, failures so far %d\n", nDeals, fails);
    if (fails) { std::printf("metal tests: FAILED (a)\n"); return 1; }

    // (b) random deals
    {
        std::mt19937_64 rng(12345);
        const int N = 2000000, CH = 200000;
        long mism = 0;
        std::vector<int> idx(52);
        for (int done = 0; done < N; done += CH) {
            std::vector<std::array<Card, 9>> deals; deals.reserve(CH);
            for (int k = 0; k < CH; ++k) {
                for (int i = 0; i < 52; ++i) idx[i] = i;
                for (int i = 0; i < 9; ++i) std::swap(idx[i], idx[i + rng() % (52 - i)]);
                std::vector<Card> v; for (int i = 0; i < 9; ++i) v.push_back(mkc(idx[i]));
                deals.push_back(mk9(v));
            }
            auto g = metalCompare(deals);
            CHECK(g.size() == deals.size(), "size");
            for (int k = 0; k < CH; ++k) if (g[k] != cpuCmp(deals[k])) ++mism;
        }
        std::printf("(b) random deals: %d, mismatches %ld\n", N, mism);
        CHECK(mism == 0, "random mismatches %ld", mism);
    }

    // (c) equity agreement
    {
        std::mt19937_64 rng(777);
        double maxz = 0;
        const int GT = 400000, CT = 200000;
        std::vector<EquityJob> jobs;
        std::vector<std::vector<std::pair<int,int>>> combosIdx;
        for (int s = 0; s < 60; ++s) {
            std::vector<int> idx(52); for (int i = 0; i < 52; ++i) idx[i] = i;
            int bsz = std::array<int,4>{0,3,4,5}[s % 4];
            for (int i = 0; i < 2 + bsz; ++i) std::swap(idx[i], idx[i + rng() % (52 - i)]);
            EquityJob j{{mkc(idx[0]), mkc(idx[1])}, {}, {}, 0, 0};
            for (int i = 0; i < bsz; ++i) j.board.push_back(mkc(idx[2 + i]));
            std::vector<bool> used(52, false); for (int i = 0; i < 2 + bsz; ++i) used[idx[i]] = true;
            std::vector<std::pair<int,int>> all;
            for (int a = 0; a < 52; ++a) for (int b = a + 1; b < 52; ++b) if (!used[a] && !used[b]) all.push_back({a, b});
            if (s % 2) { std::shuffle(all.begin(), all.end(), rng); all.resize(50 + rng() % 351); }
            for (auto& p : all) j.villainCombos.push_back({mkc(p.first), mkc(p.second)});
            j.trials = GT; j.seed = 1000 + s;
            jobs.push_back(j); combosIdx.push_back(all);
        }
        auto res = metalEquityBatch(jobs);
        CHECK(res.size() == jobs.size(), "result count");
        for (int s = 0; s < 60; ++s) {
            const EquityJob& j = jobs[s];
            std::vector<bool> used(52, false);
            used[cardIdx(j.hero[0])] = used[cardIdx(j.hero[1])] = true;
            for (auto& c : j.board) used[cardIdx(c)] = true;
            long cw = 0, ct = 0;
            for (int t = 0; t < CT; ++t) {
                auto& p = combosIdx[s][rng() % combosIdx[s].size()];
                std::vector<bool> u = used; u[p.first] = u[p.second] = true;
                std::vector<int> rem; for (int i = 0; i < 52; ++i) if (!u[i]) rem.push_back(i);
                std::vector<Card> h = {j.hero[0], j.hero[1]}, v = {mkc(p.first), mkc(p.second)};
                for (auto& c : j.board) { h.push_back(c); v.push_back(c); }
                int need = 5 - (int)j.board.size();
                for (int i = 0; i < need; ++i) {
                    std::swap(rem[i], rem[i + rng() % (rem.size() - i)]);
                    h.push_back(mkc(rem[i])); v.push_back(mkc(rem[i]));
                }
                HandValue a = AdvancedHandEvaluator::evaluate(h), b = AdvancedHandEvaluator::evaluate(v);
                if (a > b) ++cw; else if (!(b > a)) ++ct;
            }
            auto stat = [](double w, double t, double n, double& m, double& se) {
                m = (w + 0.5 * t) / n; double e2 = (w + 0.25 * t) / n; se = std::sqrt(std::max(e2 - m * m, 1e-12) / n);
            };
            double gm, gse, cm, cse;
            stat(res[s].wins, res[s].ties, res[s].trials, gm, gse);
            stat(cw, ct, CT, cm, cse);
            double z = std::fabs(gm - cm) / std::sqrt(gse * gse + cse * cse);
            maxz = std::max(maxz, z);
            CHECK(std::fabs(gm - cm) < 4 * std::sqrt(gse * gse + cse * cse), "spot %d gpu %.4f cpu %.4f z %.2f (board %zu)", s, gm, cm, z, j.board.size());
        }
        std::printf("(c) 60 spots, max z = %.3f\n", maxz);
    }

    // (d) seeded repeat
    {
        std::vector<EquityJob> jobs;
        for (int k = 0; k < 4; ++k) {
            EquityJob j{{parse("Ah"), parse("Kd")}, {}, {}, 0, 0};
            if (k) { j.board = {parse("Qs"), parse("7c"), parse("2d")}; }
            j.trials = 100000; j.seed = 0; jobs.push_back(j);
        }
        auto run = [&](unsigned long long seed) { for (auto& j : jobs) j.seed = seed; return metalEquityBatch(jobs); };
        auto a = run(42), b = run(42), c = run(43);
        bool same = true, diff = false;
        for (size_t i = 0; i < a.size(); ++i) {
            same &= a[i].wins == b[i].wins && a[i].ties == b[i].ties && a[i].trials == b[i].trials;
            diff |= a[i].wins != c[i].wins || a[i].ties != c[i].ties;
        }
        CHECK(same, "same seed differs");
        CHECK(diff, "different seed identical");
        std::printf("(d) seeded repeat identical=%d, other seed differs=%d\n", same, diff);
    }

    // (e) fallback
    {
        int rc = runChild(argv[0]);
        CHECK(rc == 0, "POKER_NO_METAL=1 child rc %d", rc);
        std::printf("(e) POKER_NO_METAL child reports unavailable: %s\n", rc == 0 ? "yes" : "no");
    }

    if (fails) { std::printf("metal tests: FAILED (%d)\n", fails); return 1; }
    std::printf("metal tests: all passed\n");
    return 0;
}
