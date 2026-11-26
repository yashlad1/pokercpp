// Exact equity by enumeration: ground truth the Monte Carlo sampler must converge on.
// vs a KNOWN villain hand validates the evaluator against published values; vs a RANDOM one, the sampler.
// Run:  ./tests/test_equity_exact [--slow]
//       --slow adds the preflop vs-known checks (~10s).

#include "../montecarlo/MonteCarloSimulator.h"
#include "../model/advanced_hand_evaluator.h"
#include "../model/card.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

namespace {

int failures = 0;

std::vector<Card> remainingDeck(const std::vector<Card> &used) {
    std::vector<Card> deck;
    for (int s = 0; s < 4; ++s) {
        for (int r = 2; r <= 14; ++r) {
            Card c(static_cast<Rank>(r), static_cast<Suit>(s));
            if (std::find(used.begin(), used.end(), c) == used.end()) {
                deck.push_back(c);
            }
        }
    }
    return deck;
}

template <typename F>
void forEachCombo(const std::vector<Card> &deck, size_t start, int k,
                  std::vector<Card> &acc, F &&fn) {
    if (k == 0) {
        fn(acc);
        return;
    }
    for (size_t i = start; i + static_cast<size_t>(k) <= deck.size(); ++i) {
        acc.push_back(deck[i]);
        forEachCombo(deck, i + 1, k - 1, acc, fn);
        acc.pop_back();
    }
}

double showdown(const std::vector<Card> &hole, const std::vector<Card> &villain,
                const std::vector<Card> &board) {
    std::vector<Card> a = hole, b = villain;
    a.insert(a.end(), board.begin(), board.end());
    b.insert(b.end(), board.begin(), board.end());
    HandValue va = AdvancedHandEvaluator::evaluate(a);
    HandValue vb = AdvancedHandEvaluator::evaluate(b);
    if (va > vb) return 1.0;
    if (vb > va) return 0.0;
    return 0.5;
}

double exactVsKnown(const std::vector<Card> &hole, const std::vector<Card> &villain,
                    const std::vector<Card> &board) {
    std::vector<Card> used = hole;
    used.insert(used.end(), villain.begin(), villain.end());
    used.insert(used.end(), board.begin(), board.end());
    std::vector<Card> deck = remainingDeck(used);

    double score = 0;
    long count = 0;
    std::vector<Card> acc;
    forEachCombo(deck, 0, 5 - static_cast<int>(board.size()), acc,
                 [&](const std::vector<Card> &runout) {
                     std::vector<Card> full = board;
                     full.insert(full.end(), runout.begin(), runout.end());
                     score += showdown(hole, villain, full);
                     ++count;
                 });
    return count ? score / count : 0.0;
}

double exactVsRandom(const std::vector<Card> &hole, const std::vector<Card> &board) {
    std::vector<Card> used = hole;
    used.insert(used.end(), board.begin(), board.end());
    std::vector<Card> deck = remainingDeck(used);

    double score = 0;
    long count = 0;
    std::vector<Card> vacc;
    forEachCombo(deck, 0, 2, vacc, [&](const std::vector<Card> &villain) {
        std::vector<Card> inner;
        for (const Card &c : deck) {
            if (std::find(villain.begin(), villain.end(), c) == villain.end()) {
                inner.push_back(c);
            }
        }
        std::vector<Card> acc;
        forEachCombo(inner, 0, 5 - static_cast<int>(board.size()), acc,
                     [&](const std::vector<Card> &runout) {
                         std::vector<Card> full = board;
                         full.insert(full.end(), runout.begin(), runout.end());
                         score += showdown(hole, villain, full);
                         ++count;
                     });
    });
    return count ? score / count : 0.0;
}

Card card(const std::string &s) {
    int rank;
    switch (s[0]) {
        case 'T': rank = 10; break;
        case 'J': rank = 11; break;
        case 'Q': rank = 12; break;
        case 'K': rank = 13; break;
        case 'A': rank = 14; break;
        default:  rank = s[0] - '0';
    }
    Suit suit = s[1] == 'h' ? Suit::Hearts
              : s[1] == 'd' ? Suit::Diamonds
              : s[1] == 'c' ? Suit::Clubs
                            : Suit::Spades;
    return Card(static_cast<Rank>(rank), suit);
}

std::vector<Card> cards(const std::string &s) {
    std::vector<Card> out;
    for (size_t i = 0; i + 1 < s.size(); i += 3) out.push_back(card(s.substr(i, 2)));
    return out;
}

void checkNear(const char *what, double got, double want, double tol) {
    bool ok = std::fabs(got - want) <= tol;
    std::printf("  %-38s %7.4f  (expected %7.4f +/- %.4f)  %s\n",
                what, got, want, tol, ok ? "ok" : "FAIL");
    if (!ok) ++failures;
}

void checkSamplerAgainstExact(const char *what, const std::string &holeStr,
                              const std::string &boardStr, int sims) {
    std::vector<Card> hole = cards(holeStr), board = cards(boardStr);

    double exact = exactVsRandom(hole, board);
    MonteCarloSimulator sim(hole, board, sims);
    sim.runSimulation();
    double mc = sim.getEquity();
    // Tolerance is 4 standard errors of the sampler's own estimate, so a pass means any bias is below the noise.
    double tol = 4.0 * std::max(sim.getEquityStdDev(), 1e-4);

    std::printf("  %-38s exact %7.4f   mc %7.4f   diff %+.4f  (tol %.4f)  %s\n",
                what, exact, mc, mc - exact, tol,
                std::fabs(mc - exact) <= tol ? "ok" : "FAIL");
    if (std::fabs(mc - exact) > tol) ++failures;
}

}

void checkHandFrequencies() {
    std::vector<Card> deck = remainingDeck({});
    std::vector<long> got(10, 0);
    std::vector<Card> h(5, Card(Rank::Two, Suit::Clubs));
    for (int a = 0; a < 52; ++a)
      for (int b = a + 1; b < 52; ++b)
        for (int c = b + 1; c < 52; ++c)
          for (int d = c + 1; d < 52; ++d)
            for (int e = d + 1; e < 52; ++e) {
                h[0]=deck[a]; h[1]=deck[b]; h[2]=deck[c]; h[3]=deck[d]; h[4]=deck[e];
                got[static_cast<int>(AdvancedHandEvaluator::evaluate(h).rank)]++;
            }

    const char *names[] = {"HighCard","OnePair","TwoPair","ThreeOfAKind","Straight",
                           "Flush","FullHouse","FourOfAKind","StraightFlush","RoyalFlush"};
    const long want[] = {1302540,1098240,123552,54912,10200,5108,3744,624,36,4};
    for (int i = 0; i < 10; ++i) {
        bool ok = got[i] == want[i];
        std::printf("  %-14s %9ld  expected %9ld  %s\n", names[i], got[i], want[i],
                    ok ? "ok" : "MISMATCH");
        if (!ok) ++failures;
    }
}

void checkTiebreaks() {
    struct { const char *what; const char *win; const char *lose; } cases[] = {
        {"AA with K kicker > AA with Q kicker", "As Ad Kh 7c 2d", "Ah Ac Qh 7s 2c"},
        {"ace-high flush > king-high flush",    "As Qs 9s 5s 3s", "Ks Qh 9h 5h 3h"},
        {"broadway straight > king straight",   "Ah Kd Qc Js Th", "Kh Qd Jc Ts 9h"},
        {"six-high straight > the wheel",       "6h 5d 4c 3s 2h", "5h 4d 3c 2s Ah"},
        {"set of aces > set of kings",          "As Ad Ac 7h 2d", "Ks Kd Kc 7s 2c"},
        {"aces full > kings full",              "As Ad Ac Kh Kd", "Ks Kd Kc Ah Ad"},
    };
    for (const auto &c : cases) {
        HandValue w = AdvancedHandEvaluator::evaluate(cards(c.win));
        HandValue l = AdvancedHandEvaluator::evaluate(cards(c.lose));
        bool ok = w > l;
        std::printf("  %-38s %s\n", c.what, ok ? "ok" : "FAIL");
        if (!ok) ++failures;
    }
}

int main(int argc, char **argv) {
    bool slow = argc > 1 && std::strcmp(argv[1], "--slow") == 0;

    std::printf("Evaluator classification over all 2,598,960 five-card hands\n");
    checkHandFrequencies();
    std::printf("\nTiebreak ordering within a category\n");
    checkTiebreaks();
    std::printf("\n");

    if (slow) {
        std::printf("Preflop all-in equity, exact (regression anchors)\n");
        // Regression values from this enumerator, not external truth: the published AA vs KK 82.36% averages over
        // suit layouts (82.64% sharing both suits, 81.26% sharing none).
        checkNear("AsAd vs KsKd  (shares both suits)",
                  exactVsKnown(cards("As Ad"), cards("Ks Kd"), {}), 0.82637, 0.0001);
        checkNear("AsAd vs KsKh  (shares one suit)",
                  exactVsKnown(cards("As Ad"), cards("Ks Kh"), {}), 0.81946, 0.0001);
        checkNear("AsAd vs KhKc  (shares no suit)",
                  exactVsKnown(cards("As Ad"), cards("Kh Kc"), {}), 0.81255, 0.0001);
        checkNear("AsKs vs QhQd", exactVsKnown(cards("As Ks"), cards("Qh Qd"), {}), 0.46207, 0.0002);
        checkNear("AsKh vs 2c2d", exactVsKnown(cards("As Kh"), cards("2c 2d"), {}), 0.46962, 0.0002);
        checkNear("AsAd vs AhAc  (mirror, must be 0.5)",
                  exactVsKnown(cards("As Ad"), cards("Ah Ac"), {}), 0.5, 1e-9);
        std::printf("\n");
    }

    std::printf("Evaluator vs known villain (exact enumeration)\n");
    checkNear("AsKs on Qs Js 2s vs Ah Ad",
              exactVsKnown(cards("As Ks"), cards("Ah Ad"), cards("Qs Js 2s")),
              972.0 / 990.0, 1e-9);
    checkNear("7h 7d on 7s 7c 2h vs Ah Kh",
              exactVsKnown(cards("7h 7d"), cards("Ah Kh"), cards("7s 7c 2h")), 1.0, 0.0);
    std::printf("\n");

    std::printf("MonteCarloSimulator vs exact, uniform-random villain\n");
    checkSamplerAgainstExact("river   AsKs on Qs Js 2h 9d 3c", "As Ks", "Qs Js 2h 9d 3c", 40000);
    checkSamplerAgainstExact("river   7h2c on Ah Kd Qc 4s 9h", "7h 2c", "Ah Kd Qc 4s 9h", 40000);
    checkSamplerAgainstExact("turn    AsKs on Qs Js 2h 9d",    "As Ks", "Qs Js 2h 9d",    40000);
    checkSamplerAgainstExact("turn    9c9d on Ah Kd 2c 7s",    "9c 9d", "Ah Kd 2c 7s",    40000);
    if (slow) {
        checkSamplerAgainstExact("flop    AsKs on Qs Js 2h",   "As Ks", "Qs Js 2h",       40000);
        checkSamplerAgainstExact("flop    9c9d on Ah Kd 2c",   "9c 9d", "Ah Kd 2c",       40000);
    }

    std::printf("\n%s\n", failures ? "FAILURES ABOVE" : "all exact-equity checks passed");
    if (!slow) std::printf("(re-run with --slow for preflop and flop enumeration)\n");
    return failures ? 1 : 0;
}
