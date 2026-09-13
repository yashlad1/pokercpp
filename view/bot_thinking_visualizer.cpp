#include "bot_thinking_visualizer.h"
#include "bot_thinking_config.h"
#include <iostream>
#include <iomanip>
#include <sstream>
#include <cmath>

// Helper macro to get output stream
#define OUT BotThinkingConfig::getOutputStream()

// ANSI color codes
#define RESET "\033[0m"
#define BOLD "\033[1m"
#define DIM "\033[2m"
#define CYAN "\033[36m"
#define GREEN "\033[32m"
#define YELLOW "\033[33m"
#define RED "\033[31m"
#define BLUE "\033[34m"
#define MAGENTA "\033[35m"
#define WHITE "\033[37m"
#define BG_BLUE "\033[44m"
#define BG_GREEN "\033[42m"
#define BG_YELLOW "\033[43m"
#define BG_RED "\033[41m"

void BotThinkingVisualizer::showThinkingHeader(const std::string& botName, const std::string& difficulty)
{

    for (int i = 0; i < 60; i++) OUT << "=";
    OUT << "\n";
    OUT << BOLD << CYAN << "       🤖 BOT THINKING PROCESS - " << botName 
              << " [" << difficulty << "] 🧠" << RESET << "\n";
    for (int i = 0; i < 60; i++) OUT << "=";
    OUT << "\n";
    OUT << "\n";
}

void BotThinkingVisualizer::showHandEvaluation(const HandValue& eval, const std::vector<Card>& hand)
{
    OUT << BOLD << YELLOW << "┌─ HAND EVALUATION ─────────────────────────────────┐" << RESET << "\n";
    
    // Show the hand
    OUT << YELLOW << "│" << RESET << " Cards: ";
    for (const auto& card : hand) {
        std::string color = (card.suit == Suit::Hearts || card.suit == Suit::Diamonds) ? RED : WHITE;
        OUT << color;
        
        // Print rank
        if (static_cast<int>(card.rank) <= 10 && static_cast<int>(card.rank) >= 2) {
            OUT << static_cast<int>(card.rank);
        } else {
            switch (card.rank) {
                case Rank::Jack: OUT << "J"; break;
                case Rank::Queen: OUT << "Q"; break;
                case Rank::King: OUT << "K"; break;
                case Rank::Ace: OUT << "A"; break;
                default: OUT << "?"; break;
            }
        }
        
        // Print suit
        switch (card.suit) {
            case Suit::Hearts: OUT << "♥"; break;
            case Suit::Diamonds: OUT << "♦"; break;
            case Suit::Clubs: OUT << "♣"; break;
            case Suit::Spades: OUT << "♠"; break;
        }
        
        OUT << RESET << " ";
    }
    OUT << "\n";
    
    // Show hand rank
    std::string emoji = getHandRankEmoji(eval.rank);
    std::string rankStr = getHandRankString(eval.rank);
    
    OUT << YELLOW << "│" << RESET << " Hand Rank: " << BOLD << GREEN << emoji << " " 
              << rankStr << RESET << "\n";
    
    // Show hand strength meter
    OUT << YELLOW << "│" << RESET << " Strength:  ";
    showHandStrengthMeter(eval);
    
    OUT << YELLOW << "└───────────────────────────────────────────────────┘" << RESET << "\n\n";
}

void BotThinkingVisualizer::showDrawingHandAnalysis(bool hasFlushDraw, bool hasStraightDraw, 
                                                    const std::vector<Card>& /* fullHand */)
{
    if (!hasFlushDraw && !hasStraightDraw) {
        return; // Don't show if no draws
    }
    
    OUT << BOLD << BLUE << "┌─ DRAWING HAND ANALYSIS ───────────────────────────┐" << RESET << "\n";
    
    if (hasFlushDraw) {
        OUT << BLUE << "│" << RESET << " 🎯 " << GREEN << "FLUSH DRAW DETECTED!" << RESET << "\n";
        OUT << BLUE << "│" << RESET << "    └─ 4 cards of same suit (need 1 more)\n";
    }
    
    if (hasStraightDraw) {
        OUT << BLUE << "│" << RESET << " 🎯 " << GREEN << "STRAIGHT DRAW DETECTED!" << RESET << "\n";
        OUT << BLUE << "│" << RESET << "    └─ Sequential cards detected (need to fill)\n";
    }
    
    OUT << BLUE << "└───────────────────────────────────────────────────┘" << RESET << "\n\n";
}

void BotThinkingVisualizer::showBluffCalculation(HandRank handRank, int bluffChance, bool willBluff)
{
    OUT << BOLD << MAGENTA << "┌─ BLUFF CALCULATION ───────────────────────────────┐" << RESET << "\n";
    
    OUT << MAGENTA << "│" << RESET << " Current Hand: " << getHandRankString(handRank) << "\n";
    OUT << MAGENTA << "│" << RESET << " Bluff Chance: " << bluffChance << "%\n";
    OUT << MAGENTA << "│" << RESET << " \n";
    OUT << MAGENTA << "│" << RESET << " Probability: [";
    
    int filled = bluffChance / 2;
    for (int i = 0; i < 50; i++) {
        if (i < filled) {
            OUT << MAGENTA << "█" << RESET;
        } else {
            OUT << DIM << "░" << RESET;
        }
    }
    OUT << "] " << bluffChance << "%\n";
    
    OUT << MAGENTA << "│" << RESET << " \n";
    OUT << MAGENTA << "│" << RESET << " Decision: ";
    if (willBluff) {
        OUT << BOLD << RED << "🎭 BLUFFING!" << RESET << "\n";
    } else {
        OUT << DIM << "Not bluffing" << RESET << "\n";
    }
    
    OUT << MAGENTA << "└───────────────────────────────────────────────────┘" << RESET << "\n\n";
}

void BotThinkingVisualizer::showFinalDecision(bool shouldCall, const std::string& reasoning)
{
    OUT << BOLD;
    if (shouldCall) {
        OUT << BG_GREEN << WHITE << "┌─ FINAL DECISION: CALL ────────────────────────────┐" << RESET << "\n";
        OUT << BOLD << GREEN << "│" << RESET << " ✓ Bot decides to " << BOLD << GREEN << "CALL" << RESET << "\n";
    } else {
        OUT << BG_RED << WHITE << "┌─ FINAL DECISION: FOLD ────────────────────────────┐" << RESET << "\n";
        OUT << BOLD << RED << "│" << RESET << " ✗ Bot decides to " << BOLD << RED << "FOLD" << RESET << "\n";
    }
    
    if (!reasoning.empty()) {
        OUT << (shouldCall ? GREEN : RED) << "│" << RESET << " Reasoning: " << reasoning << "\n";
    }
    
    if (shouldCall) {
        OUT << BOLD << GREEN << "└───────────────────────────────────────────────────┘" << RESET << "\n";
    } else {
        OUT << BOLD << RED << "└───────────────────────────────────────────────────┘" << RESET << "\n";
    }
    
    for (int i = 0; i < 60; i++) OUT << "=";
    OUT << "\n";
    OUT << "\n";
    OUT.flush(); // Ensure output is written immediately for real-time viewing
}

void BotThinkingVisualizer::showMonteCarloHeader(int simulations)
{
    OUT << BOLD << CYAN << "┌─ MONTE CARLO SIMULATION ──────────────────────────┐" << RESET << "\n";
    OUT << CYAN << "│" << RESET << " Running " << BOLD << simulations << RESET 
              << " simulations to estimate win probability...\n";
    OUT << CYAN << "│" << RESET << "\n";
}

void BotThinkingVisualizer::showMonteCarloProgress(int current, int total, int wins, int /* ties */, int /* losses */)
{
    // Guard against a zero total, which would divide by zero.
    if (total <= 0) {
        return;
    }

    // Only update every 10% to avoid spam. This deliberately avoids a function
    // -local static: one would be shared across every simulation and every
    // thread that called in.
    int percentComplete = (current * 100) / total;

    if (percentComplete % 10 == 0) {
        OUT << CYAN << "│" << RESET << " Progress: ";
        drawProgressBar(static_cast<double>(current) / total);
        
        double winRate = (current > 0) ? (static_cast<double>(wins) / current * 100.0) : 0.0;
        OUT << " " << percentComplete << "% (Win: " << std::fixed << std::setprecision(1) 
                  << winRate << "%)\n";
    }
}

void BotThinkingVisualizer::showMonteCarloResult(double winRate, int /* totalWins */, int totalLosses, 
                                                 int totalTies, int simulations)
{
    OUT << CYAN << "│" << RESET << "\n";
    OUT << CYAN << "│" << RESET << " " << BOLD << "SIMULATION RESULTS:" << RESET << "\n";
    OUT << CYAN << "│" << RESET << " ┌──────────────────────────────────────────────┐\n";
    
    // Win percentage
    OUT << CYAN << "│" << RESET << " │ " << GREEN << "Wins:   " << RESET;
    drawProgressBar(winRate, 20);
    OUT << " " << std::fixed << std::setprecision(1) << (winRate * 100) << "%\n";
    
    // Tie percentage
    double tieRate = static_cast<double>(totalTies) / simulations;
    OUT << CYAN << "│" << RESET << " │ " << YELLOW << "Ties:   " << RESET;
    drawProgressBar(tieRate, 20);
    OUT << " " << std::fixed << std::setprecision(1) << (tieRate * 100) << "%\n";
    
    // Loss percentage
    double lossRate = static_cast<double>(totalLosses) / simulations;
    OUT << CYAN << "│" << RESET << " │ " << RED << "Losses: " << RESET;
    drawProgressBar(lossRate, 20, /*higherIsBetter=*/false);
    OUT << " " << std::fixed << std::setprecision(1) << (lossRate * 100) << "%\n";
    
    OUT << CYAN << "│" << RESET << " └──────────────────────────────────────────────┘\n";
    OUT << CYAN << "│" << RESET << "\n";
    
    // Overall assessment
    OUT << CYAN << "│" << RESET << " Overall Assessment: ";
    if (winRate >= 0.6) {
        OUT << BOLD << GREEN << "🔥 STRONG POSITION" << RESET;
    } else if (winRate >= 0.45) {
        OUT << BOLD << YELLOW << "⚖️  COMPETITIVE" << RESET;
    } else if (winRate >= 0.3) {
        OUT << BOLD << YELLOW << "⚠️  RISKY" << RESET;
    } else {
        OUT << BOLD << RED << "❌ WEAK POSITION" << RESET;
    }
    OUT << "\n";
    
    OUT << CYAN << "└───────────────────────────────────────────────────┘" << RESET << "\n\n";
}

void BotThinkingVisualizer::showDecisionFactors(const std::string& stage, const HandValue& /* eval */, 
                                               bool hasDraws, double handStrength)
{
    OUT << BOLD << WHITE << "┌─ DECISION FACTORS ────────────────────────────────┐" << RESET << "\n";
    
    OUT << WHITE << "│" << RESET << " Game Stage:    " << BOLD << stage << RESET << "\n";
    OUT << WHITE << "│" << RESET << " Hand Strength: ";
    
    if (handStrength >= 0.8) {
        OUT << BOLD << GREEN << "Very Strong" << RESET;
    } else if (handStrength >= 0.6) {
        OUT << BOLD << GREEN << "Strong" << RESET;
    } else if (handStrength >= 0.4) {
        OUT << BOLD << YELLOW << "Medium" << RESET;
    } else if (handStrength >= 0.2) {
        OUT << BOLD << YELLOW << "Weak" << RESET;
    } else {
        OUT << BOLD << RED << "Very Weak" << RESET;
    }
    OUT << "\n";
    
    OUT << WHITE << "│" << RESET << " Drawing Hand:  " 
              << (hasDraws ? (BOLD + std::string(GREEN) + "Yes ✓" + RESET) : 
                            (DIM + std::string("No") + RESET)) << "\n";
    
    OUT << WHITE << "└───────────────────────────────────────────────────┘" << RESET << "\n\n";
}

void BotThinkingVisualizer::drawProgressBar(double percentage, int width, bool higherIsBetter)
{
    // Clamp so a stray value out of [0,1] cannot overrun or under-fill the bar.
    double p = percentage;
    if (p < 0.0) p = 0.0;
    if (p > 1.0) p = 1.0;

    int filled = static_cast<int>(p * width);

    // Color by meaning, not magnitude. Previously an 85% loss rate rendered in
    // green because the scale only looked at the number.
    const char* color;
    double good = higherIsBetter ? p : (1.0 - p);
    if (good >= 0.7) {
        color = GREEN;
    } else if (good >= 0.4) {
        color = YELLOW;
    } else {
        color = RED;
    }

    OUT << "[";
    for (int i = 0; i < width; i++) {
        if (i < filled) {
            OUT << color << "█" << RESET;
        } else {
            OUT << DIM << "░" << RESET;
        }
    }
    OUT << "]";
}

void BotThinkingVisualizer::showHandStrengthMeter(const HandValue& eval)
{
    // Calculate strength based on hand rank
    double strength = 0.0;
    switch (eval.rank) {
        case HandRank::RoyalFlush:     strength = 1.0; break;
        case HandRank::StraightFlush:  strength = 0.95; break;
        case HandRank::FourOfAKind:    strength = 0.88; break;
        case HandRank::FullHouse:      strength = 0.78; break;
        case HandRank::Flush:          strength = 0.68; break;
        case HandRank::Straight:       strength = 0.58; break;
        case HandRank::ThreeOfAKind:   strength = 0.45; break;
        case HandRank::TwoPair:        strength = 0.35; break;
        case HandRank::OnePair:        strength = 0.22; break;
        case HandRank::HighCard:       strength = 0.08; break;
    }
    
    drawProgressBar(strength, 30);
    OUT << " " << std::fixed << std::setprecision(0) << (strength * 100) << "%\n";
}

void BotThinkingVisualizer::showConfidenceInterval(double lowerBound, double upperBound, double confidence)
{
    OUT << BLUE << "│" << RESET << "\n";
    OUT << BLUE << "│" << RESET << " " << BOLD << YELLOW << "Statistical Confidence:" << RESET << "\n";
    OUT << BLUE << "│" << RESET << " " << std::fixed << std::setprecision(0) << (confidence * 100) 
              << "% Confidence Interval: [" 
              << BOLD << std::fixed << std::setprecision(1) << (lowerBound * 100) << "%" << RESET
              << " - " 
              << BOLD << std::fixed << std::setprecision(1) << (upperBound * 100) << "%" << RESET << "]\n";
    
    // Show margin of error
    double margin = (upperBound - lowerBound) / 2.0 * 100;
    OUT << BLUE << "│" << RESET << " Margin of Error: ±" << std::fixed << std::setprecision(1) 
              << margin << "%\n";
}

void BotThinkingVisualizer::showKellyCriterion(double winProb, double potOdds, double kellyFraction)
{
    OUT << BLUE << "│" << RESET << "\n";
    OUT << BLUE << "│" << RESET << " " << BOLD << MAGENTA << "Kelly Criterion Analysis:" << RESET << "\n";
    OUT << BLUE << "│" << RESET << " Win Probability: " << std::fixed << std::setprecision(1) 
              << (winProb * 100) << "%\n";
    OUT << BLUE << "│" << RESET << " Pot Odds Ratio: " << std::fixed << std::setprecision(2) 
              << potOdds << ":1\n";
    OUT << BLUE << "│" << RESET << " Optimal Kelly: " << BOLD << std::fixed << std::setprecision(1) 
              << (kellyFraction * 100) << "%" << RESET << " of bankroll\n";
    
    if (kellyFraction > 0.25) {
        OUT << BLUE << "│" << RESET << " Recommendation: " << BOLD << GREEN 
                  << "🔥 STRONG BET" << RESET << "\n";
    } else if (kellyFraction > 0.1) {
        OUT << BLUE << "│" << RESET << " Recommendation: " << BOLD << YELLOW 
                  << "⚠ MODERATE BET" << RESET << "\n";
    } else if (kellyFraction > 0) {
        OUT << BLUE << "│" << RESET << " Recommendation: " << BOLD << CYAN 
                  << "➤ SMALL BET" << RESET << "\n";
    } else {
        OUT << BLUE << "│" << RESET << " Recommendation: " << BOLD << RED 
                  << "✗ DON'T BET" << RESET << "\n";
    }
}

void BotThinkingVisualizer::showExpectedValue(double ev, int potSize, int callAmount)
{
    OUT << BLUE << "│" << RESET << "\n";
    OUT << BLUE << "│" << RESET << " " << BOLD << YELLOW << "Expected Value (EV):" << RESET << "\n";
    OUT << BLUE << "│" << RESET << " Pot: " << potSize << " chips, Call: " << callAmount << " chips\n";
    OUT << BLUE << "│" << RESET << " EV = " << (ev >= 0 ? BOLD GREEN : BOLD RED) 
              << std::showpos << std::fixed << std::setprecision(2) << ev << " chips" 
              << RESET << std::noshowpos << "\n";
    
    if (ev > 10) {
        OUT << BLUE << "│" << RESET << " Assessment: " << BOLD << GREEN 
                  << "💰 HIGHLY PROFITABLE" << RESET << "\n";
    } else if (ev > 0) {
        OUT << BLUE << "│" << RESET << " Assessment: " << BOLD << GREEN 
                  << "✓ Profitable" << RESET << "\n";
    } else if (ev > -10) {
        OUT << BLUE << "│" << RESET << " Assessment: " << BOLD << YELLOW 
                  << "⚠ Marginal/Break-even" << RESET << "\n";
    } else {
        OUT << BLUE << "│" << RESET << " Assessment: " << BOLD << RED 
                  << "✗ Unprofitable" << RESET << "\n";
    }
}

// `requiredEquity` is the FRACTION of the pot being risked (call / (pot+call)),
// i.e. the output of PokerMath::calculatePotOddsPercentage - not the pot-odds
// ratio from calculatePotOdds, which would print as "200%" and never compare
// meaningfully against equity.
void BotThinkingVisualizer::showPotOddsAnalysis(double requiredEquity, double equity)
{
    double potOdds = requiredEquity;

    OUT << BOLD << BLUE << "┌─ POT ODDS ANALYSIS ───────────────────────────────┐" << RESET << "\n";

    OUT << BLUE << "│" << RESET << " Needs:     " << std::fixed << std::setprecision(1) 
              << (potOdds * 100) << "%\n";
    OUT << BLUE << "│" << RESET << " Equity:    " << std::fixed << std::setprecision(1) 
              << (equity * 100) << "%\n";
    OUT << BLUE << "│" << RESET << "\n";
    
    if (equity > potOdds) {
        OUT << BLUE << "│" << RESET << " Decision: " << BOLD << GREEN 
                  << "✓ PROFITABLE CALL" << RESET << "\n";
    } else {
        OUT << BLUE << "│" << RESET << " Decision: " << BOLD << RED 
                  << "✗ UNPROFITABLE" << RESET << "\n";
    }
    
    OUT << BLUE << "└───────────────────────────────────────────────────┘" << RESET << "\n\n";
}

std::string BotThinkingVisualizer::getHandRankString(HandRank rank)
{
    switch (rank) {
        case HandRank::RoyalFlush:    return "Royal Flush";
        case HandRank::StraightFlush: return "Straight Flush";
        case HandRank::FourOfAKind:   return "Four of a Kind";
        case HandRank::FullHouse:     return "Full House";
        case HandRank::Flush:         return "Flush";
        case HandRank::Straight:      return "Straight";
        case HandRank::ThreeOfAKind:  return "Three of a Kind";
        case HandRank::TwoPair:       return "Two Pair";
        case HandRank::OnePair:       return "One Pair";
        case HandRank::HighCard:      return "High Card";
        default:                      return "Unknown";
    }
}

std::string BotThinkingVisualizer::getHandRankEmoji(HandRank rank)
{
    switch (rank) {
        case HandRank::RoyalFlush:    return "👑";
        case HandRank::StraightFlush: return "🌟";
        case HandRank::FourOfAKind:   return "💎";
        case HandRank::FullHouse:     return "🏠";
        case HandRank::Flush:         return "💧";
        case HandRank::Straight:      return "📊";
        case HandRank::ThreeOfAKind:  return "🎯";
        case HandRank::TwoPair:       return "👥";
        case HandRank::OnePair:       return "👤";
        case HandRank::HighCard:      return "🃏";
        default:                      return "❓";
    }
}

void BotThinkingVisualizer::drawSeparator(char symbol, int width)
{
    for (int i = 0; i < width; i++) {
        OUT << symbol;
    }
    OUT << "\n";
}

void BotThinkingVisualizer::drawThinSeparator(char symbol, int width)
{
    OUT << DIM;
    for (int i = 0; i < width; i++) {
        OUT << symbol;
    }
    OUT << RESET << "\n";
}
