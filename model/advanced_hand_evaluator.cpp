#include "advanced_hand_evaluator.h"
#include <map>
#include <algorithm>
#include <stdexcept>

static int rankToInt(Rank r)
{
    return static_cast<int>(r);
}

static bool isStraight(const std::vector<int> &sortedRanks, int &highCard)
{
    std::vector<int> uniqueRanks = sortedRanks;
    std::sort(uniqueRanks.begin(), uniqueRanks.end());
    uniqueRanks.erase(
        std::unique(uniqueRanks.begin(), uniqueRanks.end()), uniqueRanks.end());

    if (std::find(uniqueRanks.begin(), uniqueRanks.end(), 14) != uniqueRanks.end())
    {
        uniqueRanks.insert(uniqueRanks.begin(), 1);
    }

    // Keep the HIGHEST straight found, never return early: with 6+ consecutive ranks (or a wheel plus a higher
    // straight) the first run of five is the lowest. Ranks ascend, so each later update is better.
    bool found = false;
    int count = 1;
    for (size_t i = 1; i < uniqueRanks.size(); ++i)
    {
        if (uniqueRanks[i] == uniqueRanks[i - 1] + 1)
        {
            count++;
            if (count >= 5)
            {
                highCard = uniqueRanks[i];
                found = true;
            }
        }
        else
        {
            count = 1;
        }
    }

    return found;
}

/** Best 5-card hand from 5 or more cards. Throws std::invalid_argument for fewer than 5. */
HandValue AdvancedHandEvaluator::evaluate(const std::vector<Card> &cards)
{
    if (cards.size() < 5)
    {
        throw std::invalid_argument("At least 5 cards are required for hand evaluation");
    }

    std::map<int, int> rankCount;
    std::map<Suit, std::vector<Card>> suitGroups;

    std::vector<int> allRanks;
    for (const Card &c : cards)
    {
        int val = rankToInt(c.rank);
        allRanks.push_back(val);
        rankCount[val]++;
        suitGroups[c.suit].push_back(c);
    }

    std::vector<int> singles, pairs, trips, quads;
    for (auto &[rank, count] : rankCount)
    {
        if (count == 4)
        {
            quads.push_back(rank);
        }
        else if (count == 3)
        {
            trips.push_back(rank);
        }
        else if (count == 2)
        {
            pairs.push_back(rank);
        }
        else
        {
            singles.push_back(rank);
        }
    }

    std::sort(pairs.rbegin(), pairs.rend());
    std::sort(trips.rbegin(), trips.rend());
    std::sort(quads.rbegin(), quads.rend());
    std::sort(singles.rbegin(), singles.rend());

    for (auto &[suit, suitedCards] : suitGroups)
    {
        if (suitedCards.size() < 5)
            continue;
            
        std::vector<int> suitedRanks;
        for (const Card &c : suitedCards)
        {
            suitedRanks.push_back(rankToInt(c.rank));
        }

        int sfHighCard = 0;
        if (isStraight(suitedRanks, sfHighCard))
        {
            if (sfHighCard == 14)
                return HandValue{HandRank::RoyalFlush, {14}};
            else
                return HandValue{HandRank::StraightFlush, {sfHighCard}};
        }
    }

    if (!quads.empty())
    {
        // Highest card not in the quads, scanning every remaining rank, not just singles (AAAA-KK-Q plays the K).
        int kicker = 0;
        for (const auto &[rank, count] : rankCount)
        {
            if (rank != quads[0] && rank > kicker)
                kicker = rank;
        }
        return HandValue{
            HandRank::FourOfAKind, {quads[0], kicker}};
    }

    if (!trips.empty() && (!pairs.empty() || trips.size() > 1))
    {
        int trip = trips[0];
        int pair = (trips.size() > 1) ? trips[1] : pairs[0];
        return HandValue{HandRank::FullHouse, {trip, pair}};
    }

    for (auto &[suit, suitedCards] : suitGroups)
    {
        if (suitedCards.size() >= 5)
        {
            std::vector<int> flushRanks;
            for (Card c : suitedCards)
                flushRanks.push_back(rankToInt(c.rank));
            std::sort(flushRanks.rbegin(), flushRanks.rend());
            flushRanks.resize(5);
            return HandValue{HandRank::Flush, flushRanks};
        }
    }

    int straightHigh = 0;
    if (isStraight(allRanks, straightHigh))
    {
        return HandValue{HandRank::Straight, {straightHigh}};
    }

    if (!trips.empty())
    {
        std::vector<int> kickers;
        for (int r : singles)
            kickers.push_back(r);
        for (int r : pairs)
            kickers.push_back(r);
        while (kickers.size() < 2)
            kickers.push_back(0);
        return HandValue{HandRank::ThreeOfAKind, {trips[0], kickers[0], kickers[1]}};
    }

    if (pairs.size() >= 2)
    {
        // Highest card outside the top two pairs: a third pair can outrank every single (AA-KK-QQ-J plays the Q).
        int kicker = 0;
        for (const auto &[rank, count] : rankCount)
        {
            if (rank != pairs[0] && rank != pairs[1] && rank > kicker)
                kicker = rank;
        }
        return HandValue{HandRank::TwoPair, {pairs[0], pairs[1], kicker}};
    }

    if (pairs.size() == 1)
    {
        std::vector<int> kickers = {pairs[0]};
        for (size_t i = 0; i < 3 && i < singles.size(); ++i)
            kickers.push_back(singles[i]);
        return HandValue{HandRank::OnePair, kickers};
    }

    std::sort(allRanks.rbegin(), allRanks.rend());
    allRanks.resize(5);
    return HandValue{HandRank::HighCard, allRanks};
}