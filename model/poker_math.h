#ifndef POKER_MATH_H
#define POKER_MATH_H


namespace PokerMath {

/** Pot odds as a percentage: the equity needed to break even (a $50 call into a $100 pot is 33.3%). */
inline double calculatePotOddsPercentage(int potSize, int callAmount) {
    if (potSize + callAmount <= 0) return 0.0;
    return static_cast<double>(callAmount) / (potSize + callAmount);
}

}

#endif
