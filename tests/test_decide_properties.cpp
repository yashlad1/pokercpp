// Properties of chipzen/decide.h decisions, as a class rather than by example.
//
//   scaling   - multiply every chip quantity by 10 and the decision is the
//               same action with an amount scaled by 10. Catches a hard-coded
//               big blind or any threshold in absolute chips.
//   price     - inside one bet-size band the range is fixed, so raising the
//               price may never turn a fold into a call.
//   range     - the opponent's credited range never widens as raises or bet
//               size grow. Checked exhaustively, no sampling.
//
//   legality  - a free check never folds; a raise lies inside
//               [min_raise, max_raise] (including the all-in-only band) and
//               never happens when raising is closed; the nuts on the river
//               never fold. Checked over a seeded sample of spots.
//
// Every engine call is seeded, so the run is deterministic.
//
// Run:  ./tests/test_decide_properties

#include "../chipzen/decide.h"

#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

using chipzen::Decision;
using chipzen::decideFull;
using chipzen::parseCard;

namespace {

int failures = 0;

void check(bool ok, const std::string &name) {
    if (!ok) { ++failures; std::printf("  FAIL: %s\n", name.c_str()); }
}

std::vector<Card> cards(const std::string &s) {
    std::vector<Card> out;
    for (size_t i = 0; i + 1 < s.size(); i += 2) {
        Card c(Rank::Two, Suit::Hearts);
        if (!parseCard(s.substr(i, 2), c)) { std::printf("bad card %s\n", s.c_str()); std::exit(2); }
        out.push_back(c);
    }
    return out;
}

const unsigned long long SEED = 12345;
const int SIMS = 1000;

Decision run(const std::vector<Card> &h, const std::vector<Card> &b, int pot, int toCall,
             int minR, int maxR, int stack, int bb, int raises) {
    return decideFull(h, b, pot, toCall, minR, maxR, stack, bb, SIMS, raises,
                      1.0, true, 0.0, SEED);
}

// ---- chip scaling ---------------------------------------------------------

struct Spot {
    const char *name, *hole, *board;
    int pot, toCall, minR, maxR, stack, bb, raises;
};

// Base values are chosen so every `int(chips * fraction)` in decide.h lands on
// a whole chip (pot a multiple of 50, pot+toCall a multiple of 4, bb even).
// Truncation breaks exact x10 scaling otherwise, and that is rounding, not a bug.
const Spot SPOTS[] = {
    {"SB open",            "AhAs", "",         150, 50,  200, 10000, 10000, 100, 0},
    {"short-stack shove",  "AhAs", "",         150, 50,  200,  1000,  1000, 100, 0},
    {"value bet",          "AhAd", "Ks7d2c",   500,  0,  100, 10000, 10000, 100, 0},
    {"raise vs bet",       "AhAd", "Ks7d2c",   600, 200, 400, 10000, 10000, 100, 0},
    {"fold to big bet",    "7h2c", "AsKdQh",   800, 400, 800, 10000, 10000, 100, 1},
    {"call",               "QhJd", "Ks7d2c",   600, 200, 400, 10000, 10000, 100, 0},
    {"facing all-in",      "KhQd", "Ks7d2c",  4000, 3000, 0,      0,  2000, 100, 0},
    {"bluff spot",         "7h2c", "AsKdQhJs", 500,  0,  100, 10000, 10000, 100, 0},
    {"river check",        "9h8d", "AsKdQh2c3s", 500, 0, 100, 10000, 10000, 100, 0},
};

void testChipScaling() {
    std::printf("chip scaling x10\n");
    const int K = 10;
    for (const Spot &s : SPOTS) {
        Decision a = run(cards(s.hole), cards(s.board), s.pot, s.toCall, s.minR, s.maxR,
                         s.stack, s.bb, s.raises);
        Decision b = run(cards(s.hole), cards(s.board), s.pot * K, s.toCall * K, s.minR * K,
                         s.maxR * K, s.stack * K, s.bb * K, s.raises);
        std::printf("  %-18s %-5s %d\n", s.name, a.action.c_str(), a.amount);
        const std::string n = std::string("scaling: ") + s.name;
        check(a.action == b.action, n + " same action");
        check(b.amount == a.amount * K, n + " amount scales by 10");
        check(a.bluff == b.bluff, n + " same bluff flag");
        check(a.range == b.range, n + " same range");
        check(a.equity == b.equity, n + " same equity (same seed)");
        check(std::fabs(a.required - b.required) < 1e-9, n + " same price");
    }
}

// ---- price monotonicity within a band -------------------------------------

void testPriceMonotonic() {
    std::printf("price monotonic within a band\n");
    // pot-before-bet fixed at 1000; the middle band is toCall/before in
    // [0.35, 0.75], so every price from 350 to 750 gets the same range.
    const int before = 1000;
    const char *boards[] = {"Ks7d2c", "Ks7d2c9h", "Ks7d2c9h4s"};
    const char *holes[] = {"AhQd", "KhJd", "QhJd", "9h8d", "Th9d", "7h2c", "AhAd", "5s4s"};
    int foldAfterCall = 0;  // non-vacuity: some sweep must actually cross the cut
    for (const char *bd : boards) {
        for (const char *h : holes) {
            for (int raises = 0; raises <= 1; ++raises) {
                bool folded = false, called = false;
                for (int toCall = 350; toCall <= 750; toCall += 25) {
                    Decision d = run(cards(h), cards(bd), before + toCall, toCall, 2 * toCall,
                                     100000, 100000, 100, raises);
                    if (d.action == "fold") folded = true;
                    else if (folded)
                        check(false, std::string("fold became ") + d.action + ": " + h + " on " +
                                         bd + " at price " + std::to_string(toCall));
                    else called = true;
                }
                if (folded && called) ++foldAfterCall;
            }
        }
    }
    std::printf("  sweeps that cross call->fold: %d\n", foldAfterCall);
    check(foldAfterCall > 0, "price sweep crosses the fold cut at least once");
}

// ---- range monotonicity, exhaustive ---------------------------------------

void testRangeMonotonic() {
    std::printf("range monotonic (exhaustive)\n");
    long n = 0;
    for (int before = 1; before <= 300; ++before) {
        for (int raises = 0; raises <= 5; ++raises) {
            double prev = 2.0;
            for (int toCall = 1; toCall <= 600; ++toCall, ++n) {
                double f = chipzen::villainRangeFraction(raises, toCall, before + toCall);
                check(f >= 0.05 && f <= 1.0, "range inside [0.05, 1]");
                if (f > prev + 1e-12) {
                    check(false, "range widened with bet size: pot-before " + std::to_string(before) +
                                     " raises " + std::to_string(raises) + " toCall " + std::to_string(toCall));
                    return;
                }
                prev = f;
            }
        }
        // More raises never widen the range, at any price.
        for (int toCall = 0; toCall <= 600; ++toCall) {
            double prev = 2.0;
            for (int raises = 0; raises <= 5; ++raises) {
                double f = chipzen::villainRangeFraction(raises, toCall, before + toCall);
                if (f > prev + 1e-12) {
                    check(false, "range widened with raises: pot-before " + std::to_string(before) +
                                     " toCall " + std::to_string(toCall) + " raises " + std::to_string(raises));
                    return;
                }
                prev = f;
            }
        }
    }
    std::printf("  checked %ld (raises, price) pairs\n", n);
}

// ---- legality --------------------------------------------------------------

// Fixed-seed LCG so the sampled spots are the same on every run and platform.
struct Lcg {
    unsigned long long s;
    int pick(int n) { s = s * 6364136223846793005ULL + 1442695040888963407ULL; return int((s >> 33) % n); }
};

void testLegality() {
    std::printf("legality over a seeded sample of spots\n");
    // No card appears in both a hole and a board.
    const char *holes[] = {"AhAd", "QhJd", "8h6d", "Th3d", "5h5d", "8c3h", "AcKd", "JhTh"};
    const char *boards[] = {"", "Ks7d2c", "Ks7d2c9h", "Ks7d2c9h4s"};
    // Whole-chip values: pot a multiple of 50, price a whole fraction of it.
    const int pots[] = {150, 500, 1200, 4000};
    const double fracs[] = {0.0, 0.0, 0.25, 0.5, 1.0, 2.0};  // free checks are over-weighted
    const int stacks[] = {300, 800, 1000, 5000, 20000};
    const int bb = 100;
    Lcg rng{2024};
    const int N = 600;
    int freeChecks = 0, raises = 0, shoves = 0, closed = 0;
    for (int i = 0; i < N; ++i) {
        const char *h = holes[rng.pick(8)];
        const char *b = boards[rng.pick(4)];
        const int before = pots[rng.pick(4)];
        const int toCall = int(before * fracs[rng.pick(6)]);
        const int stack = stacks[rng.pick(5)];
        const int nr = rng.pick(4);
        int minR = std::max(2 * toCall, bb), maxR = stack;   // open band
        const int mode = rng.pick(3);
        if (mode == 1 || minR > maxR) minR = maxR;           // only the all-in is possible
        if (mode == 2) minR = maxR = 0;                      // raising is closed
        const bool open = minR > 0 && maxR > 0;

        // Draw a fresh 200-sim estimate; the sample size is irrelevant to legality.
        Decision d = decideFull(cards(h), cards(b), before + toCall, toCall, minR, maxR, stack, bb,
                                200, nr, 1.0, true, 0.0, SEED);
        const std::string n = std::string(h) + " on '" + b + "' pot " + std::to_string(before) +
                              " toCall " + std::to_string(toCall) + " stack " + std::to_string(stack) +
                              " band [" + std::to_string(minR) + "," + std::to_string(maxR) + "] raises " +
                              std::to_string(nr);
        if (toCall == 0) { ++freeChecks; check(d.action != "fold", "free check never folds: " + n); }
        if (d.action == "raise") {
            ++raises;
            check(open, "no raise when raising is closed: " + n);
            check(d.amount >= minR && d.amount <= maxR, "raise inside band, got " + std::to_string(d.amount) + ": " + n);
            if (minR == maxR) ++shoves;
        }
        if (!open) ++closed;
    }
    std::printf("  %d spots: %d free checks, %d raises (%d into an all-in-only band), %d raising closed\n",
                N, freeChecks, raises, shoves, closed);
    check(freeChecks > 100 && raises > 100 && shoves > 0 && closed > 100, "legality sample covers every case");
}

void testNutsNeverFoldOnRiver() {
    std::printf("nuts on the river never fold\n");
    struct Nuts { const char *hole, *board; };
    // Royal flush, and the best possible quads on a paired-free board.
    const Nuts NUTS[] = {{"Ts3d", "AsKsQsJs2c"}, {"AsKd", "AdAcAh7s2d"}, {"Ah2d", "KhQhJhTh3c"}};
    const int pots[] = {150, 1200, 4000};
    const double fracs[] = {0.0, 0.5, 1.0, 2.0, 10.0};
    const int stacks[] = {300, 1000, 20000};
    int n = 0;
    for (const Nuts &w : NUTS)
        for (int before : pots)
            for (double f : fracs)
                for (int stack : stacks)
                    for (int nr = 0; nr <= 3; ++nr, ++n) {
                        const int toCall = int(before * f);
                        Decision d = run(cards(w.hole), cards(w.board), before + toCall, toCall,
                                         std::max(2 * toCall, 100), 100000, stack, 100, nr);
                        check(d.action != "fold", std::string("nuts folded: ") + w.hole + " on " + w.board +
                                                      " pot " + std::to_string(before) + " toCall " +
                                                      std::to_string(toCall) + " stack " + std::to_string(stack) +
                                                      " raises " + std::to_string(nr));
                    }
    std::printf("  checked %d river spots\n", n);
}

} // namespace

int main() {
    testChipScaling();
    testPriceMonotonic();
    testRangeMonotonic();
    testLegality();
    testNutsNeverFoldOnRiver();
    if (failures) { std::printf("\n%d check(s) FAILED\n", failures); return 1; }
    std::printf("\nAll decide.h property checks passed\n");
    return 0;
}
