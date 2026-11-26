// Allocation-free 7-card evaluator. The score is an integer whose order matches
// HandValue::operator> and ==, so only comparisons of scores are meaningful.
// Card id = suit*13 + (rank-2); a hand is a 52-bit mask, one 13-bit field per suit.
#ifndef FAST_EVAL_H
#define FAST_EVAL_H

#include "card.h"
#include <cstdint>

namespace fast_eval {

inline int cardId(const Card &c) { return static_cast<int>(c.suit) * 13 + (static_cast<int>(c.rank) - 2); }
inline int hb(uint32_t x) { return 31 - __builtin_clz(x); }
inline int pop(uint32_t x) { return __builtin_popcount(x); }

inline uint32_t topN(uint32_t x, int n)
{
    uint32_t r = 0;
    for (int i = 0; i < n; ++i) { int h = hb(x); r = (r << 4) | (uint32_t)h; x &= ~(1u << h); }
    return r;
}

// Top rank index of the best straight in a 13-bit mask, or -1. The ace plays low too.
inline int straightTop(uint32_t m)
{
    uint32_t x = (m << 1) | (m >> 12);
    uint32_t y = x & (x >> 1) & (x >> 2) & (x >> 3) & (x >> 4);
    return y ? hb(y) + 3 : -1;
}

// Score = category<<20 | up to five 4-bit rank nibbles. Royal flush is the top straight flush.
inline uint32_t evalMask(uint64_t m)
{
    uint32_t s0 = (uint32_t)(m & 0x1FFF), s1 = (uint32_t)((m >> 13) & 0x1FFF);
    uint32_t s2 = (uint32_t)((m >> 26) & 0x1FFF), s3 = (uint32_t)((m >> 39) & 0x1FFF);
    uint32_t all = s0 | s1 | s2 | s3;
    uint32_t flush = 0;
    if (pop(s0) >= 5) flush = s0;
    if (pop(s1) >= 5) flush = s1;
    if (pop(s2) >= 5) flush = s2;
    if (pop(s3) >= 5) flush = s3;
    if (flush) { int sf = straightTop(flush); if (sf >= 0) return (8u << 20) | (uint32_t)sf; }
    uint32_t quads = s0 & s1 & s2 & s3;
    uint32_t trips = (s0 & s1 & s2) | (s0 & s1 & s3) | (s0 & s2 & s3) | (s1 & s2 & s3);
    uint32_t pairs = (s0 & s1) | (s0 & s2) | (s0 & s3) | (s1 & s2) | (s1 & s3) | (s2 & s3);
    if (quads) {
        int q = hb(quads);
        return (7u << 20) | ((uint32_t)q << 16) | ((uint32_t)hb(all & ~(1u << q)) << 12);
    }
    if (trips) {
        int t = hb(trips);
        uint32_t p = pairs & ~(1u << t);
        if (p) return (6u << 20) | ((uint32_t)t << 16) | ((uint32_t)hb(p) << 12);
    }
    if (flush) return (5u << 20) | topN(flush, 5);
    int st = straightTop(all);
    if (st >= 0) return (4u << 20) | (uint32_t)st;
    if (trips) {
        int t = hb(trips);
        return (3u << 20) | ((uint32_t)t << 16) | (topN(all & ~(1u << t), 2) << 8);
    }
    if (pop(pairs) >= 2) {
        int p1 = hb(pairs); uint32_t r = pairs & ~(1u << p1); int p2 = hb(r);
        uint32_t k = all & ~(1u << p1) & ~(1u << p2);
        return (2u << 20) | ((uint32_t)p1 << 16) | ((uint32_t)p2 << 12) | ((uint32_t)hb(k) << 8);
    }
    if (pairs) {
        int p = hb(pairs);
        return (1u << 20) | ((uint32_t)p << 16) | (topN(all & ~(1u << p), 3) << 4);
    }
    return topN(all, 5);
}

}

#endif
