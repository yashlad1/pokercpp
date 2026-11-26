
#include "../model/advanced_hand_evaluator.h"
#include "../model/card.h"
#include <iostream>
#include <vector>
#include <cassert>
#include "test_util.h"

#define ASSERT_EQ(a, b) do { \
    if ((a) != (b)) { \
        std::cerr << "FAILED: " << #a << " != " << #b << " at line " << __LINE__ << "\n"; \
        exit(1); \
    } \
} while(0)

TEST(royal_flush_detection) {
    std::vector<Card> hand = {
        Card(Rank::Ace, Suit::Hearts),
        Card(Rank::King, Suit::Hearts),
        Card(Rank::Queen, Suit::Hearts),
        Card(Rank::Jack, Suit::Hearts),
        Card(Rank::Ten, Suit::Hearts)
    };
    
    HandValue hv = AdvancedHandEvaluator::evaluate(hand);
    ASSERT_EQ(hv.rank, HandRank::RoyalFlush);
}

TEST(straight_flush_detection) {
    std::vector<Card> hand = {
        Card(Rank::Nine, Suit::Diamonds),
        Card(Rank::Eight, Suit::Diamonds),
        Card(Rank::Seven, Suit::Diamonds),
        Card(Rank::Six, Suit::Diamonds),
        Card(Rank::Five, Suit::Diamonds)
    };
    
    HandValue hv = AdvancedHandEvaluator::evaluate(hand);
    ASSERT_EQ(hv.rank, HandRank::StraightFlush);
}

TEST(four_of_a_kind_detection) {
    std::vector<Card> hand = {
        Card(Rank::King, Suit::Hearts),
        Card(Rank::King, Suit::Diamonds),
        Card(Rank::King, Suit::Clubs),
        Card(Rank::King, Suit::Spades),
        Card(Rank::Two, Suit::Hearts)
    };
    
    HandValue hv = AdvancedHandEvaluator::evaluate(hand);
    ASSERT_EQ(hv.rank, HandRank::FourOfAKind);
}

TEST(full_house_detection) {
    std::vector<Card> hand = {
        Card(Rank::Ace, Suit::Hearts),
        Card(Rank::Ace, Suit::Diamonds),
        Card(Rank::Ace, Suit::Clubs),
        Card(Rank::King, Suit::Hearts),
        Card(Rank::King, Suit::Diamonds)
    };
    
    HandValue hv = AdvancedHandEvaluator::evaluate(hand);
    ASSERT_EQ(hv.rank, HandRank::FullHouse);
}

TEST(flush_detection) {
    std::vector<Card> hand = {
        Card(Rank::Ace, Suit::Clubs),
        Card(Rank::Jack, Suit::Clubs),
        Card(Rank::Nine, Suit::Clubs),
        Card(Rank::Five, Suit::Clubs),
        Card(Rank::Three, Suit::Clubs)
    };
    
    HandValue hv = AdvancedHandEvaluator::evaluate(hand);
    ASSERT_EQ(hv.rank, HandRank::Flush);
}

TEST(straight_detection) {
    std::vector<Card> hand = {
        Card(Rank::Ten, Suit::Hearts),
        Card(Rank::Nine, Suit::Diamonds),
        Card(Rank::Eight, Suit::Clubs),
        Card(Rank::Seven, Suit::Spades),
        Card(Rank::Six, Suit::Hearts)
    };
    
    HandValue hv = AdvancedHandEvaluator::evaluate(hand);
    ASSERT_EQ(hv.rank, HandRank::Straight);
}

TEST(three_of_a_kind_detection) {
    std::vector<Card> hand = {
        Card(Rank::Queen, Suit::Hearts),
        Card(Rank::Queen, Suit::Diamonds),
        Card(Rank::Queen, Suit::Clubs),
        Card(Rank::Nine, Suit::Hearts),
        Card(Rank::Two, Suit::Diamonds)
    };
    
    HandValue hv = AdvancedHandEvaluator::evaluate(hand);
    ASSERT_EQ(hv.rank, HandRank::ThreeOfAKind);
}

TEST(two_pair_detection) {
    std::vector<Card> hand = {
        Card(Rank::Jack, Suit::Hearts),
        Card(Rank::Jack, Suit::Diamonds),
        Card(Rank::Five, Suit::Clubs),
        Card(Rank::Five, Suit::Spades),
        Card(Rank::Two, Suit::Hearts)
    };
    
    HandValue hv = AdvancedHandEvaluator::evaluate(hand);
    ASSERT_EQ(hv.rank, HandRank::TwoPair);
}

TEST(one_pair_detection) {
    std::vector<Card> hand = {
        Card(Rank::Ten, Suit::Hearts),
        Card(Rank::Ten, Suit::Diamonds),
        Card(Rank::Seven, Suit::Clubs),
        Card(Rank::Four, Suit::Spades),
        Card(Rank::Two, Suit::Hearts)
    };
    
    HandValue hv = AdvancedHandEvaluator::evaluate(hand);
    ASSERT_EQ(hv.rank, HandRank::OnePair);
}

TEST(royal_flush_beats_straight_flush) {
    std::vector<Card> royal = {
        Card(Rank::Ace, Suit::Hearts),
        Card(Rank::King, Suit::Hearts),
        Card(Rank::Queen, Suit::Hearts),
        Card(Rank::Jack, Suit::Hearts),
        Card(Rank::Ten, Suit::Hearts)
    };
    
    std::vector<Card> straightFlush = {
        Card(Rank::Nine, Suit::Diamonds),
        Card(Rank::Eight, Suit::Diamonds),
        Card(Rank::Seven, Suit::Diamonds),
        Card(Rank::Six, Suit::Diamonds),
        Card(Rank::Five, Suit::Diamonds)
    };
    
    HandValue royalHV = AdvancedHandEvaluator::evaluate(royal);
    HandValue straightHV = AdvancedHandEvaluator::evaluate(straightFlush);
    
    ASSERT_TRUE(royalHV > straightHV);
}

TEST(kicker_comparison) {
    std::vector<Card> hand1 = {
        Card(Rank::Ace, Suit::Hearts),
        Card(Rank::Ace, Suit::Diamonds),
        Card(Rank::King, Suit::Clubs),
        Card(Rank::Queen, Suit::Spades),
        Card(Rank::Jack, Suit::Hearts)
    };
    
    std::vector<Card> hand2 = {
        Card(Rank::Ace, Suit::Clubs),
        Card(Rank::Ace, Suit::Spades),
        Card(Rank::Ten, Suit::Hearts),
        Card(Rank::Nine, Suit::Diamonds),
        Card(Rank::Eight, Suit::Clubs)
    };
    
    HandValue hv1 = AdvancedHandEvaluator::evaluate(hand1);
    HandValue hv2 = AdvancedHandEvaluator::evaluate(hand2);
    
    ASSERT_EQ(hv1.rank, HandRank::OnePair);
    ASSERT_EQ(hv2.rank, HandRank::OnePair);
    ASSERT_TRUE(hv1 > hv2);
}


TEST(seven_card_six_run_takes_highest_straight) {
    std::vector<Card> hand = {
        Card(Rank::Five, Suit::Spades),
        Card(Rank::Six, Suit::Hearts),
        Card(Rank::Seven, Suit::Diamonds),
        Card(Rank::Eight, Suit::Clubs),
        Card(Rank::Nine, Suit::Spades),
        Card(Rank::Ten, Suit::Hearts),
        Card(Rank::Two, Suit::Diamonds)
    };

    HandValue hv = AdvancedHandEvaluator::evaluate(hand);
    ASSERT_EQ(hv.rank, HandRank::Straight);
    ASSERT_EQ(hv.kickers[0], 10);
}

TEST(seven_card_wheel_does_not_mask_higher_straight) {
    std::vector<Card> hand = {
        Card(Rank::Ace, Suit::Spades),
        Card(Rank::Two, Suit::Hearts),
        Card(Rank::Three, Suit::Diamonds),
        Card(Rank::Four, Suit::Clubs),
        Card(Rank::Five, Suit::Spades),
        Card(Rank::Six, Suit::Hearts),
        Card(Rank::King, Suit::Diamonds)
    };

    HandValue hv = AdvancedHandEvaluator::evaluate(hand);
    ASSERT_EQ(hv.rank, HandRank::Straight);
    ASSERT_EQ(hv.kickers[0], 6);
}

TEST(seven_card_wheel_is_five_high) {
    std::vector<Card> hand = {
        Card(Rank::Ace, Suit::Spades),
        Card(Rank::Two, Suit::Hearts),
        Card(Rank::Three, Suit::Diamonds),
        Card(Rank::Four, Suit::Clubs),
        Card(Rank::Five, Suit::Spades),
        Card(Rank::King, Suit::Hearts),
        Card(Rank::Queen, Suit::Diamonds)
    };

    HandValue hv = AdvancedHandEvaluator::evaluate(hand);
    ASSERT_EQ(hv.rank, HandRank::Straight);
    ASSERT_EQ(hv.kickers[0], 5);
}

TEST(seven_card_royal_flush_not_downgraded) {
    std::vector<Card> hand = {
        Card(Rank::Nine, Suit::Hearts),
        Card(Rank::Ten, Suit::Hearts),
        Card(Rank::Jack, Suit::Hearts),
        Card(Rank::Queen, Suit::Hearts),
        Card(Rank::King, Suit::Hearts),
        Card(Rank::Ace, Suit::Hearts),
        Card(Rank::Two, Suit::Spades)
    };

    HandValue hv = AdvancedHandEvaluator::evaluate(hand);
    ASSERT_EQ(hv.rank, HandRank::RoyalFlush);
}

TEST(seven_card_straight_flush_takes_highest) {
    std::vector<Card> hand = {
        Card(Rank::Five, Suit::Hearts),
        Card(Rank::Six, Suit::Hearts),
        Card(Rank::Seven, Suit::Hearts),
        Card(Rank::Eight, Suit::Hearts),
        Card(Rank::Nine, Suit::Hearts),
        Card(Rank::Ten, Suit::Hearts),
        Card(Rank::Two, Suit::Spades)
    };

    HandValue hv = AdvancedHandEvaluator::evaluate(hand);
    ASSERT_EQ(hv.rank, HandRank::StraightFlush);
    ASSERT_EQ(hv.kickers[0], 10);
}

TEST(seven_card_quad_kicker_considers_pairs) {
    std::vector<Card> hand = {
        Card(Rank::Ace, Suit::Spades),
        Card(Rank::Ace, Suit::Hearts),
        Card(Rank::Ace, Suit::Diamonds),
        Card(Rank::Ace, Suit::Clubs),
        Card(Rank::King, Suit::Spades),
        Card(Rank::King, Suit::Hearts),
        Card(Rank::Queen, Suit::Diamonds)
    };

    HandValue hv = AdvancedHandEvaluator::evaluate(hand);
    ASSERT_EQ(hv.rank, HandRank::FourOfAKind);
    ASSERT_EQ(hv.kickers[0], 14);
    ASSERT_EQ(hv.kickers[1], 13);
}

TEST(seven_card_two_pair_kicker_considers_third_pair) {
    std::vector<Card> hand = {
        Card(Rank::Ace, Suit::Spades),
        Card(Rank::Ace, Suit::Hearts),
        Card(Rank::King, Suit::Spades),
        Card(Rank::King, Suit::Hearts),
        Card(Rank::Queen, Suit::Spades),
        Card(Rank::Queen, Suit::Hearts),
        Card(Rank::Jack, Suit::Diamonds)
    };

    HandValue hv = AdvancedHandEvaluator::evaluate(hand);
    ASSERT_EQ(hv.rank, HandRank::TwoPair);
    ASSERT_EQ(hv.kickers[0], 14);
    ASSERT_EQ(hv.kickers[1], 13);
    ASSERT_EQ(hv.kickers[2], 12);
}

TEST(seven_card_higher_straight_beats_board_straight) {
    std::vector<Card> board = {
        Card(Rank::Five, Suit::Spades),
        Card(Rank::Six, Suit::Hearts),
        Card(Rank::Seven, Suit::Diamonds),
        Card(Rank::Eight, Suit::Clubs),
        Card(Rank::Nine, Suit::Spades)
    };

    std::vector<Card> withTen = board;
    withTen.push_back(Card(Rank::Ten, Suit::Hearts));
    withTen.push_back(Card(Rank::Two, Suit::Diamonds));

    std::vector<Card> playingBoard = board;
    playingBoard.push_back(Card(Rank::Three, Suit::Hearts));
    playingBoard.push_back(Card(Rank::Two, Suit::Clubs));

    HandValue better = AdvancedHandEvaluator::evaluate(withTen);
    HandValue worse = AdvancedHandEvaluator::evaluate(playingBoard);

    ASSERT_EQ(better.rank, HandRank::Straight);
    ASSERT_EQ(worse.rank, HandRank::Straight);
    ASSERT_TRUE(better > worse);
    ASSERT_TRUE(!(better == worse));
}

TEST(seven_card_two_trips_makes_full_house) {
    std::vector<Card> hand = {
        Card(Rank::Nine, Suit::Spades),
        Card(Rank::Nine, Suit::Hearts),
        Card(Rank::Nine, Suit::Diamonds),
        Card(Rank::Six, Suit::Spades),
        Card(Rank::Six, Suit::Hearts),
        Card(Rank::Six, Suit::Diamonds),
        Card(Rank::Two, Suit::Clubs)
    };

    HandValue hv = AdvancedHandEvaluator::evaluate(hand);
    ASSERT_EQ(hv.rank, HandRank::FullHouse);
    ASSERT_EQ(hv.kickers[0], 9);
    ASSERT_EQ(hv.kickers[1], 6);
}

int main() {
    std::cout << "=== Hand Evaluator Unit Tests ===\n\n";
    
    RUN_TEST(royal_flush_detection);
    RUN_TEST(straight_flush_detection);
    RUN_TEST(four_of_a_kind_detection);
    RUN_TEST(full_house_detection);
    RUN_TEST(flush_detection);
    RUN_TEST(straight_detection);
    RUN_TEST(three_of_a_kind_detection);
    RUN_TEST(two_pair_detection);
    RUN_TEST(one_pair_detection);
    RUN_TEST(royal_flush_beats_straight_flush);
    RUN_TEST(kicker_comparison);

    RUN_TEST(seven_card_six_run_takes_highest_straight);
    RUN_TEST(seven_card_wheel_does_not_mask_higher_straight);
    RUN_TEST(seven_card_wheel_is_five_high);
    RUN_TEST(seven_card_royal_flush_not_downgraded);
    RUN_TEST(seven_card_straight_flush_takes_highest);
    RUN_TEST(seven_card_quad_kicker_considers_pairs);
    RUN_TEST(seven_card_two_pair_kicker_considers_third_pair);
    RUN_TEST(seven_card_higher_straight_beats_board_straight);
    RUN_TEST(seven_card_two_trips_makes_full_house);
    
    std::cout << "\n✓ All tests passed!\n";
    return 0;
}
