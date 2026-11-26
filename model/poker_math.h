#ifndef POKER_MATH_H
#define POKER_MATH_H

/**
 * Poker Mathematics Utilities
 * 
 * Contains mathematical functions for optimal play:
 * - Pot odds calculations
 */

namespace PokerMath {

/**
 * Calculate pot odds as a percentage
 * 
 * Returns: Percentage of pot you're risking
 * 
 * Example: $100 pot, $50 to call = 33.3% (need 33.3% equity to break even)
 */
inline double calculatePotOddsPercentage(int potSize, int callAmount) {
    if (potSize + callAmount <= 0) return 0.0;
    return static_cast<double>(callAmount) / (potSize + callAmount);
}

} // namespace PokerMath

#endif // POKER_MATH_H
