/**
 * Unit Tests for Game Logic
 *
 * Covers chip accounting, hand descriptions and bot betting decisions -
 * the parts that decide who wins chips and how many.
 */

#include "../model/player.h"
#include "../model/deck.h"
#include "../montecarlo/MonteCarloSimulator.h"
#include "../model/poker_math.h"
#include <cmath>
#include "../model/bot_player.h"
#include "../model/advanced_hand_evaluator.h"
#include "../model/hand_types.h"
#include <iostream>
#include <vector>
#include <string>

// Defined in controller/poker_controller.cpp
std::string handValueToString(const HandValue &hv);
bool parseDifficulty(const std::string &raw, BotDifficulty &out);

#define TEST(name) void test_##name()
#define RUN_TEST(name) do { \
    std::cout << "Running " << #name << "... "; \
    test_##name(); \
    std::cout << "PASSED\n"; \
} while(0)

#define ASSERT_TRUE(expr) do { \
    if (!(expr)) { \
        std::cerr << "FAILED: " << #expr << " at line " << __LINE__ << "\n"; \
        exit(1); \
    } \
} while(0)

#define ASSERT_EQ(a, b) do { \
    if ((a) != (b)) { \
        std::cerr << "FAILED: " << #a << " != " << #b << " at line " << __LINE__ \
                  << " (got " << (a) << ")\n"; \
        exit(1); \
    } \
} while(0)

// ---------------------------------------------------------------------------
// Chip accounting
// ---------------------------------------------------------------------------

// bet() must report what it actually staked, so the pot can be kept exact.
TEST(bet_returns_amount_wagered) {
    Player p("You", 1000);
    ASSERT_EQ(p.bet(100), 100);
    ASSERT_EQ(p.getChipCount(), 900);
}

// A bet larger than the stack is an all-in for the stack, not a silent no-op.
// The old version deducted nothing and returned void, so the caller counted
// chips into the pot that were never actually staked.
TEST(bet_clamps_to_stack_as_all_in) {
    Player p("You", 40);
    ASSERT_EQ(p.bet(100), 40);
    ASSERT_EQ(p.getChipCount(), 0);
}

TEST(bet_rejects_nonpositive) {
    Player p("You", 100);
    ASSERT_EQ(p.bet(0), 0);
    ASSERT_EQ(p.bet(-50), 0);
    ASSERT_EQ(p.getChipCount(), 100);
}

// Chips must be conserved: what leaves the stacks equals what the pot pays.
TEST(chips_are_conserved_across_a_round) {
    Player human("You", 1000);
    Player bot("Bot", 1000);
    const int startingTotal = human.getChipCount() + bot.getChipCount();

    int pot = 0;
    // Three betting rounds of 100 each, both players matching.
    for (int i = 0; i < 3; ++i) {
        pot += human.bet(100);
        pot += bot.bet(100);
    }
    ASSERT_EQ(pot, 600);

    // Winner takes the whole pot.
    bot.addChips(pot);
    pot = 0;

    ASSERT_EQ(human.getChipCount() + bot.getChipCount(), startingTotal);
    ASSERT_EQ(human.getChipCount(), 700);
    ASSERT_EQ(bot.getChipCount(), 1300);
}

// An odd pot must split without losing or inventing a chip.
TEST(odd_pot_splits_without_losing_a_chip) {
    Player human("You", 0);
    Player bot("Bot", 0);
    int pot = 601;

    int half = pot / 2;
    human.addChips(half);
    bot.addChips(pot - half);

    ASSERT_EQ(human.getChipCount() + bot.getChipCount(), 601);
}

// ---------------------------------------------------------------------------
// Hand descriptions
// ---------------------------------------------------------------------------

// The showdown that started this: both players hold two pair and the label
// must explain which one wins.
TEST(two_pair_description_names_the_kicker) {
    HandValue you{HandRank::TwoPair, {13, 9, 8}};
    HandValue bot{HandRank::TwoPair, {13, 9, 11}};

    ASSERT_EQ(handValueToString(you), std::string("Two Pair, Kings and Nines (Eight kicker)"));
    ASSERT_EQ(handValueToString(bot), std::string("Two Pair, Kings and Nines (Jack kicker)"));
    ASSERT_TRUE(bot > you);
}

TEST(descriptions_cover_every_rank) {
    ASSERT_EQ(handValueToString({HandRank::RoyalFlush, {14}}),
              std::string("Royal Flush"));
    ASSERT_EQ(handValueToString({HandRank::StraightFlush, {10}}),
              std::string("Straight Flush, Ten-high"));
    ASSERT_EQ(handValueToString({HandRank::FourOfAKind, {14, 13}}),
              std::string("Four of a Kind, Aces (King kicker)"));
    ASSERT_EQ(handValueToString({HandRank::FullHouse, {9, 6}}),
              std::string("Full House, Nines over Sixes"));
    ASSERT_EQ(handValueToString({HandRank::Flush, {14, 11, 9, 5, 3}}),
              std::string("Flush, Ace-high"));
    ASSERT_EQ(handValueToString({HandRank::Straight, {10}}),
              std::string("Straight, Ten-high"));
    ASSERT_EQ(handValueToString({HandRank::ThreeOfAKind, {12, 9, 2}}),
              std::string("Three of a Kind, Queens"));
    ASSERT_EQ(handValueToString({HandRank::OnePair, {10, 7}}),
              std::string("One Pair, Tens (Seven kicker)"));
    ASSERT_EQ(handValueToString({HandRank::HighCard, {13, 9, 8, 6, 2}}),
              std::string("High Card, King"));
}

// "Six" is the one rank whose plural is irregular.
TEST(sixes_plural_is_irregular) {
    ASSERT_EQ(handValueToString({HandRank::ThreeOfAKind, {6, 9, 2}}),
              std::string("Three of a Kind, Sixes"));
}

// A malformed HandValue must not crash; fall back to the bare rank name.
TEST(missing_kickers_fall_back_to_rank_name) {
    ASSERT_EQ(handValueToString({HandRank::TwoPair, {}}), std::string("Two Pair"));
    ASSERT_EQ(handValueToString({HandRank::Straight, {}}), std::string("Straight"));
}

// ---------------------------------------------------------------------------
// Bot decisions
// ---------------------------------------------------------------------------

// Pre-flop there are only two cards, too few to evaluate. This used to reach
// hasStraightDraw with 2 distinct ranks, whose loop bound underflowed and read
// off the end of the vector.
TEST(bot_survives_preflop_with_two_cards) {
    std::vector<Card> hole = {Card(Rank::Seven, Suit::Hearts), Card(Rank::Seven, Suit::Spades)};
    std::vector<Card> board;

    for (auto diff : {BotDifficulty::Easy, BotDifficulty::Medium,
                      BotDifficulty::Hard, BotDifficulty::HardPlus}) {
        BotPlayer bot("Bot", 1000, diff);
        // Must not crash or throw.
        bot.shouldCallBet(hole, board, GameStage::PreFlop, 200, 100);
        ASSERT_TRUE(!bot.shouldBetWhenChecked(hole, board, GameStage::PreFlop, 200, 100));
    }
}

// Trips on a paired board leaves only two distinct ranks - the exact shape
// that overflowed the old straight-draw scan.
TEST(bot_survives_two_distinct_ranks_on_flop) {
    std::vector<Card> hole = {Card(Rank::Nine, Suit::Clubs), Card(Rank::Nine, Suit::Diamonds)};
    std::vector<Card> board = {Card(Rank::Nine, Suit::Hearts),
                               Card(Rank::King, Suit::Clubs),
                               Card(Rank::King, Suit::Diamonds)};

    BotPlayer bot("Bot", 1000, BotDifficulty::Hard);
    bot.shouldCallBet(hole, board, GameStage::Flop, 200, 100);  // must not crash
}

// The behaviour that prompted this work: holding two pair on the river with
// the opponent checking, the bot must bet rather than check it back.
TEST(hard_bot_value_bets_two_pair_on_river) {
    // Bot holds Jd 9d on Kc 8c 9h Kd 2d -> kings and nines.
    std::vector<Card> hole = {Card(Rank::Jack, Suit::Diamonds), Card(Rank::Nine, Suit::Diamonds)};
    std::vector<Card> board = {Card(Rank::King, Suit::Clubs), Card(Rank::Eight, Suit::Clubs),
                               Card(Rank::Nine, Suit::Hearts), Card(Rank::King, Suit::Diamonds),
                               Card(Rank::Two, Suit::Diamonds)};

    BotPlayer bot("Bot", 1000, BotDifficulty::Hard);
    ASSERT_TRUE(bot.shouldBetWhenChecked(hole, board, GameStage::River, 400, 100));
}

// A bot with fewer chips than the bet cannot bet.
TEST(bot_cannot_bet_without_chips) {
    std::vector<Card> hole = {Card(Rank::Jack, Suit::Diamonds), Card(Rank::Nine, Suit::Diamonds)};
    std::vector<Card> board = {Card(Rank::King, Suit::Clubs), Card(Rank::Eight, Suit::Clubs),
                               Card(Rank::Nine, Suit::Hearts), Card(Rank::King, Suit::Diamonds),
                               Card(Rank::Two, Suit::Diamonds)};

    BotPlayer broke("Bot", 50, BotDifficulty::Hard);
    ASSERT_TRUE(!broke.shouldBetWhenChecked(hole, board, GameStage::River, 400, 100));
}

// Nothing to call is never a fold.
TEST(hardplus_never_folds_for_free) {
    std::vector<Card> hole = {Card(Rank::Two, Suit::Hearts), Card(Rank::Three, Suit::Spades)};
    std::vector<Card> board = {Card(Rank::King, Suit::Clubs), Card(Rank::Queen, Suit::Clubs),
                               Card(Rank::Jack, Suit::Hearts), Card(Rank::Nine, Suit::Diamonds),
                               Card(Rank::Eight, Suit::Diamonds)};

    BotPlayer bot("Bot", 1000, BotDifficulty::HardPlus);
    ASSERT_TRUE(bot.shouldCallBet(hole, board, GameStage::River, 400, 0));
}

// HardPlus prices its calls off the real pot. The nuts must always be a call;
// the worst possible hand facing a huge bet must not be.
TEST(hardplus_respects_pot_odds) {
    // Nut straight flush - always call.
    std::vector<Card> nutHole = {Card(Rank::Ace, Suit::Hearts), Card(Rank::King, Suit::Hearts)};
    std::vector<Card> nutBoard = {Card(Rank::Queen, Suit::Hearts), Card(Rank::Jack, Suit::Hearts),
                                  Card(Rank::Ten, Suit::Hearts), Card(Rank::Two, Suit::Clubs),
                                  Card(Rank::Three, Suit::Diamonds)};
    BotPlayer strong("Bot", 10000, BotDifficulty::HardPlus);
    ASSERT_TRUE(strong.shouldCallBet(nutHole, nutBoard, GameStage::River, 200, 100));

    // Worst hand on a scary board, priced badly: 10 pot, 1000 to call needs
    // over 99% equity. Must fold.
    std::vector<Card> weakHole = {Card(Rank::Two, Suit::Clubs), Card(Rank::Three, Suit::Diamonds)};
    std::vector<Card> weakBoard = {Card(Rank::Ace, Suit::Hearts), Card(Rank::King, Suit::Hearts),
                                   Card(Rank::Queen, Suit::Hearts), Card(Rank::Jack, Suit::Hearts),
                                   Card(Rank::Nine, Suit::Spades)};
    BotPlayer weak("Bot", 10000, BotDifficulty::HardPlus);
    ASSERT_TRUE(!weak.shouldCallBet(weakHole, weakBoard, GameStage::River, 10, 1000));
}

// ---------------------------------------------------------------------------
// Deck shuffling
// ---------------------------------------------------------------------------

// Decks built back-to-back must differ. The old constructor seeded from
// std::time(nullptr), whose one-second resolution meant every round starting
// within the same second dealt exactly the same cards.
TEST(consecutive_decks_differ) {
    auto firstNine = [](Deck &d) {
        std::string s;
        for (int i = 0; i < 9; ++i) s += d.dealCard().toString();
        return s;
    };

    Deck a, b, c;
    std::string sa = firstNine(a), sb = firstNine(b), sc = firstNine(c);

    ASSERT_TRUE(sa != sb);
    ASSERT_TRUE(sb != sc);
    ASSERT_TRUE(sa != sc);
}

// The seeded constructor stays reproducible, which is what makes deterministic
// tests possible in the first place.
TEST(seeded_decks_are_reproducible) {
    auto firstNine = [](Deck &d) {
        std::string s;
        for (int i = 0; i < 9; ++i) s += d.dealCard().toString();
        return s;
    };

    Deck a(12345), b(12345), c(99999);
    ASSERT_EQ(firstNine(a), firstNine(b));

    Deck d(12345);
    ASSERT_TRUE(firstNine(d) != firstNine(c));
}

TEST(deck_has_52_unique_cards) {
    Deck d(777);
    ASSERT_EQ(d.size(), 52);

    std::vector<Card> seen;
    for (int i = 0; i < 52; ++i) {
        Card c = d.dealCard();
        for (const Card &prev : seen) {
            ASSERT_TRUE(!(prev == c));
        }
        seen.push_back(c);
    }
    ASSERT_TRUE(d.isEmpty());
}

// ---------------------------------------------------------------------------
// Difficulty parsing
// ---------------------------------------------------------------------------

// Every one of these used to land on Medium silently.
TEST(difficulty_parsing_is_case_and_space_insensitive) {
    BotDifficulty d = BotDifficulty::Easy;

    ASSERT_TRUE(parseDifficulty("hardplus", d));
    ASSERT_TRUE(d == BotDifficulty::HardPlus);

    ASSERT_TRUE(parseDifficulty("HARDPLUS", d));
    ASSERT_TRUE(d == BotDifficulty::HardPlus);

    ASSERT_TRUE(parseDifficulty("HardPlus", d));
    ASSERT_TRUE(d == BotDifficulty::HardPlus);

    ASSERT_TRUE(parseDifficulty("  hardplus  ", d));
    ASSERT_TRUE(d == BotDifficulty::HardPlus);

    ASSERT_TRUE(parseDifficulty("hard+", d));
    ASSERT_TRUE(d == BotDifficulty::HardPlus);

    ASSERT_TRUE(parseDifficulty("HARD", d));
    ASSERT_TRUE(d == BotDifficulty::Hard);

    ASSERT_TRUE(parseDifficulty("easy", d));
    ASSERT_TRUE(d == BotDifficulty::Easy);

    ASSERT_TRUE(parseDifficulty("medium", d));
    ASSERT_TRUE(d == BotDifficulty::Medium);
}

// Unrecognized input must be rejected, not silently mapped to a default, and
// must leave the caller's value untouched.
TEST(difficulty_parsing_rejects_junk) {
    BotDifficulty d = BotDifficulty::HardPlus;

    ASSERT_TRUE(!parseDifficulty("hardpluss", d));
    ASSERT_TRUE(!parseDifficulty("kip", d));   // leftover from typing "skip"
    ASSERT_TRUE(!parseDifficulty("xyz", d));
    ASSERT_TRUE(!parseDifficulty("", d));
    ASSERT_TRUE(!parseDifficulty("hardest", d));

    // Untouched by the failed parses.
    ASSERT_TRUE(d == BotDifficulty::HardPlus);
}

// ---------------------------------------------------------------------------
// Uncalled bets
// ---------------------------------------------------------------------------

// When a bet cannot be fully matched, the excess belongs back with the bettor.
// Otherwise a short stack wins more than it risked.
TEST(uncalled_portion_returns_to_bettor) {
    Player human("You", 1000);
    Player bot("Bot", 40);
    const int startingTotal = human.getChipCount() + bot.getChipCount();

    int pot = 0;
    int wagered = human.bet(100);
    pot += wagered;
    int matched = bot.bet(wagered);
    pot += matched;

    // Return the uncalled remainder, as the controller does.
    int uncalled = wagered - matched;
    ASSERT_EQ(uncalled, 60);
    human.addChips(uncalled);
    pot -= uncalled;

    ASSERT_EQ(pot, 80);  // 40 contested from each side

    bot.addChips(pot);
    pot = 0;

    ASSERT_EQ(human.getChipCount() + bot.getChipCount(), startingTotal);
    ASSERT_EQ(bot.getChipCount(), 80);   // risked 40, profited 40
    ASSERT_EQ(human.getChipCount(), 960); // lost only the 40 contested
}

// ---------------------------------------------------------------------------
// Confidence intervals
// ---------------------------------------------------------------------------

// A lower confidence level must give a narrower interval. Levels below 90%
// used to fall through to the 95% z-score, so a requested 50% interval came
// back wider than a 90% one.
TEST(confidence_intervals_narrow_as_level_drops) {
    std::vector<Card> hole = {Card(Rank::Ace, Suit::Spades), Card(Rank::Ace, Suit::Hearts)};
    MonteCarloSimulator sim(hole, {}, 2000);
    sim.runSimulation();

    auto width = [&](double c) {
        auto [lo, hi] = sim.getConfidenceInterval(c);
        return hi - lo;
    };

    double w99 = width(0.99), w95 = width(0.95), w90 = width(0.90);
    double w80 = width(0.80), w50 = width(0.50);

    ASSERT_TRUE(w99 > w95);
    ASSERT_TRUE(w95 > w90);
    ASSERT_TRUE(w90 > w80);   // this pair used to be inverted
    ASSERT_TRUE(w80 > w50);
}

// The implied z-scores should match the textbook values.
TEST(confidence_interval_z_scores_are_correct) {
    std::vector<Card> hole = {Card(Rank::Seven, Suit::Spades), Card(Rank::Two, Suit::Hearts)};
    MonteCarloSimulator sim(hole, {}, 2000);
    sim.runSimulation();

    double stdDev = sim.getWinRateStdDev();
    ASSERT_TRUE(stdDev > 0.0);

    struct { double confidence; double z; } cases[] = {
        {0.99, 2.576}, {0.95, 1.960}, {0.90, 1.645}, {0.80, 1.282}, {0.50, 0.674},
    };

    for (const auto &c : cases) {
        auto [lo, hi] = sim.getConfidenceInterval(c.confidence);
        double impliedZ = (hi - lo) / (2.0 * stdDev);
        // Loose tolerance: bounds are clamped to [0,1] and z is approximated.
        ASSERT_TRUE(impliedZ > c.z - 0.02 && impliedZ < c.z + 0.02);
    }
}

// ---------------------------------------------------------------------------
// Probability and betting mathematics
// ---------------------------------------------------------------------------

// Substituting equity (win + tie/2) into EV = p*pot - (1-p)*call yields
// exactly the tie-aware expected value, where a split returns (pot-call)/2.
// This is an identity, not an approximation, so it should hold everywhere.
TEST(ev_with_equity_equals_tie_aware_ev) {
    double worst = 0.0;
    for (double pw = 0.0; pw <= 1.0001; pw += 0.1) {
        for (double pt = 0.0; pw + pt <= 1.0001; pt += 0.05) {
            for (int pot : {50, 200, 600}) {
                for (int call : {25, 100, 300}) {
                    double pl = 1.0 - pw - pt;
                    double exact = pw * pot + pt * (pot - call) / 2.0 - pl * call;
                    double viaFormula = PokerMath::calculateEV(pw + 0.5 * pt, pot, call);
                    worst = std::max(worst, std::fabs(exact - viaFormula));
                }
            }
        }
    }
    ASSERT_TRUE(worst < 1e-9);
}

// "equity > required share" must be the same test as "EV > 0".
TEST(pot_odds_rule_matches_ev_sign) {
    for (int i = 0; i <= 100; ++i) {
        double eq = i / 100.0;
        for (int pot : {10, 50, 200, 600}) {
            for (int call : {25, 100, 300, 1000}) {
                double required = PokerMath::calculatePotOddsPercentage(pot, call);
                double ev = PokerMath::calculateEV(eq, pot, call);
                // Skip the exact break-even point, where the two differ only
                // by floating-point rounding.
                if (std::fabs(eq - required) < 1e-12) continue;
                ASSERT_EQ(eq > required, ev > 0.0);
            }
        }
    }
}

// Kelly must be continuous at certainty. It used to return 0 for p >= 1.0,
// so holding the nuts the bot's own analysis panel advised "DON'T BET".
TEST(kelly_is_continuous_at_certainty) {
    const double b = 2.0;
    ASSERT_TRUE(PokerMath::kellyFraction(1.0, b) > 0.99);
    ASSERT_TRUE(PokerMath::kellyFraction(0.9999, b) > 0.99);

    // Monotonic in win probability across the whole range.
    double previous = -1.0;
    for (int i = 0; i <= 100; ++i) {
        double f = PokerMath::kellyFraction(i / 100.0, b);
        ASSERT_TRUE(f >= previous - 1e-12);
        ASSERT_TRUE(f >= 0.0 && f <= 1.0);
        previous = f;
    }
}

// No odds on offer means the formula divides by zero; it must stay finite.
TEST(kelly_handles_zero_odds) {
    double f = PokerMath::kellyFraction(0.8, 0.0);
    ASSERT_TRUE(std::isfinite(f));
    ASSERT_EQ(f, 0.0);
    ASSERT_EQ(PokerMath::kellyFraction(0.0, 2.0), 0.0);
}

// Equity is a three-valued mean, so its standard error is not the binomial
// p(1-p)/n used for the win rate. Check it against the definition.
TEST(equity_std_dev_uses_the_right_variance) {
    std::vector<Card> hole = {Card(Rank::Nine, Suit::Clubs), Card(Rank::Six, Suit::Clubs)};
    std::vector<Card> board = {Card(Rank::King, Suit::Clubs), Card(Rank::Eight, Suit::Clubs),
                               Card(Rank::Nine, Suit::Hearts), Card(Rank::King, Suit::Diamonds),
                               Card(Rank::Two, Suit::Diamonds)};
    const int n = 4000;
    MonteCarloSimulator sim(hole, board, n);
    sim.runSimulation();

    double pw = sim.getWinPercentage();
    double pt = sim.getTiePercentage();
    double mean = pw + 0.5 * pt;

    ASSERT_TRUE(std::fabs(sim.getEquity() - mean) < 1e-12);

    double variance = pw + 0.25 * pt - mean * mean;
    double expected = std::sqrt(variance / n);
    ASSERT_TRUE(std::fabs(sim.getEquityStdDev() - expected) < 1e-12);

    // This board produces chops, so the two standard errors must differ.
    ASSERT_TRUE(pt > 0.0);
    ASSERT_TRUE(std::fabs(sim.getEquityStdDev() - sim.getWinRateStdDev()) > 1e-9);
}

// The equity interval must actually bracket the equity estimate, and narrow
// as the requested confidence drops.
TEST(equity_confidence_interval_is_well_formed) {
    std::vector<Card> hole = {Card(Rank::Ace, Suit::Spades), Card(Rank::Ace, Suit::Hearts)};
    MonteCarloSimulator sim(hole, {}, 3000);
    sim.runSimulation();

    double equity = sim.getEquity();
    auto [lo, hi] = sim.getEquityConfidenceInterval(0.95);
    ASSERT_TRUE(lo <= equity && equity <= hi);
    ASSERT_TRUE(lo >= 0.0 && hi <= 1.0);

    auto width = [&](double c) {
        auto [a, b] = sim.getEquityConfidenceInterval(c);
        return b - a;
    };
    ASSERT_TRUE(width(0.99) > width(0.95));
    ASSERT_TRUE(width(0.95) > width(0.80));
    ASSERT_TRUE(width(0.80) > width(0.50));
}

// The simulator must be unbiased: with the whole board known, it should agree
// with exhaustive enumeration over all 990 opponent holdings.
TEST(simulation_matches_exact_enumeration) {
    std::vector<Card> hole = {Card(Rank::Jack, Suit::Diamonds), Card(Rank::Nine, Suit::Diamonds)};
    std::vector<Card> board = {Card(Rank::King, Suit::Clubs), Card(Rank::Eight, Suit::Clubs),
                               Card(Rank::Nine, Suit::Hearts), Card(Rank::King, Suit::Diamonds),
                               Card(Rank::Two, Suit::Diamonds)};

    // Exhaustive: every two-card holding from the 45 unseen cards.
    std::vector<Card> known = hole;
    known.insert(known.end(), board.begin(), board.end());
    std::vector<Card> rest;
    for (int r = 2; r <= 14; ++r) {
        for (int su = 0; su < 4; ++su) {
            Card c(static_cast<Rank>(r), static_cast<Suit>(su));
            bool used = false;
            for (const Card &k : known) if (k == c) { used = true; break; }
            if (!used) rest.push_back(c);
        }
    }

    std::vector<Card> mine = hole;
    mine.insert(mine.end(), board.begin(), board.end());
    HandValue my = AdvancedHandEvaluator::evaluate(mine);

    long wins = 0, ties = 0, total = 0;
    for (size_t i = 0; i < rest.size(); ++i) {
        for (size_t j = i + 1; j < rest.size(); ++j) {
            std::vector<Card> opp = {rest[i], rest[j]};
            opp.insert(opp.end(), board.begin(), board.end());
            HandValue ov = AdvancedHandEvaluator::evaluate(opp);
            if (my > ov) ++wins;
            else if (!(ov > my)) ++ties;
            ++total;
        }
    }
    ASSERT_EQ(total, 990);
    double exact = (wins + 0.5 * ties) / static_cast<double>(total);

    MonteCarloSimulator sim(hole, board, 40000);
    sim.runSimulation();

    // 40k trials puts the standard error near 0.002; allow a generous margin.
    ASSERT_TRUE(std::fabs(sim.getEquity() - exact) < 0.02);
}

int main() {
    std::cout << "=== Game Logic Unit Tests ===\n\n";

    RUN_TEST(bet_returns_amount_wagered);
    RUN_TEST(bet_clamps_to_stack_as_all_in);
    RUN_TEST(bet_rejects_nonpositive);
    RUN_TEST(chips_are_conserved_across_a_round);
    RUN_TEST(odd_pot_splits_without_losing_a_chip);

    RUN_TEST(two_pair_description_names_the_kicker);
    RUN_TEST(descriptions_cover_every_rank);
    RUN_TEST(sixes_plural_is_irregular);
    RUN_TEST(missing_kickers_fall_back_to_rank_name);

    RUN_TEST(bot_survives_preflop_with_two_cards);
    RUN_TEST(bot_survives_two_distinct_ranks_on_flop);
    RUN_TEST(hard_bot_value_bets_two_pair_on_river);
    RUN_TEST(bot_cannot_bet_without_chips);
    RUN_TEST(hardplus_never_folds_for_free);
    RUN_TEST(hardplus_respects_pot_odds);

    RUN_TEST(consecutive_decks_differ);
    RUN_TEST(seeded_decks_are_reproducible);
    RUN_TEST(deck_has_52_unique_cards);

    RUN_TEST(difficulty_parsing_is_case_and_space_insensitive);
    RUN_TEST(difficulty_parsing_rejects_junk);

    RUN_TEST(uncalled_portion_returns_to_bettor);

    RUN_TEST(confidence_intervals_narrow_as_level_drops);
    RUN_TEST(confidence_interval_z_scores_are_correct);

    RUN_TEST(ev_with_equity_equals_tie_aware_ev);
    RUN_TEST(pot_odds_rule_matches_ev_sign);
    RUN_TEST(kelly_is_continuous_at_certainty);
    RUN_TEST(kelly_handles_zero_odds);
    RUN_TEST(equity_std_dev_uses_the_right_variance);
    RUN_TEST(equity_confidence_interval_is_well_formed);
    RUN_TEST(simulation_matches_exact_enumeration);

    std::cout << "\n✓ All tests passed!\n";
    return 0;
}
