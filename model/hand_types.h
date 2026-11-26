#ifndef HAND_TYPES_H
#define HAND_TYPES_H

#include <vector>

enum class HandRank
{
    HighCard = 0,
    OnePair,
    TwoPair,
    ThreeOfAKind,
    Straight,
    Flush,
    FullHouse,
    FourOfAKind,
    StraightFlush,
    RoyalFlush
};

struct HandValue
{
    HandRank rank;
    std::vector<int> kickers;

    bool operator>(const HandValue &other) const;
    bool operator==(const HandValue &other) const;
};

inline bool HandValue::operator>(const HandValue &other) const
{
    if (rank != other.rank)
        return static_cast<int>(rank) > static_cast<int>(other.rank);

    for (size_t i = 0; i < kickers.size() && i < other.kickers.size(); ++i)
    {
        if (kickers[i] != other.kickers[i])
            return kickers[i] > other.kickers[i];
    }
    return false;
}

inline bool HandValue::operator==(const HandValue &other) const
{
    return rank == other.rank && kickers == other.kickers;
}

#endif