#include "bot_player.h"
#include "advanced_hand_evaluator.h"
#include "poker_math.h"
#include "../montecarlo/MonteCarloSimulator.h"
#include "../utils/performance_monitor.h"
#include <random>
#include <algorithm>
#include <map>
#include <iostream>

BotPlayer::BotPlayer(const std::string &name, int chips, BotDifficulty diff)
    : Player(name, chips), difficulty(diff), rng(std::random_device{}()) {
}

BotPlayer::BotPlayer(const std::string &name, int chips, BotDifficulty diff,
                     std::uint_fast32_t seed)
    : Player(name, chips), difficulty(diff), rng(seed) {
}

BotDifficulty BotPlayer::getDifficulty() const {
    return difficulty;
}

bool BotPlayer::shouldCallBet(const std::vector<Card>& holeCards,
                              const std::vector<Card>& community,
                              GameStage stage,
                              int pot,
                              int callAmount) {
    std::vector<Card> fullHand = holeCards;
    fullHand.insert(fullHand.end(), community.begin(), community.end());

    // Show bot thinking header
    std::string diffStr;
    switch (difficulty) {
        case BotDifficulty::Easy: diffStr = "EASY"; break;
        case BotDifficulty::Medium: diffStr = "MEDIUM"; break;
        case BotDifficulty::Hard: diffStr = "HARD"; break;
        case BotDifficulty::HardPlus: diffStr = "HARD+"; break;
    }
    if (observer) observer->onThinkingStarted(getName(), diffStr);

    // Easy plays blind, and HardPlus works off simulated equity rather than
    // the current made hand, so neither needs a 5-card evaluation. Pre-flop
    // there are only 2 cards and evaluate() would throw.
    bool canEvaluate = fullHand.size() >= 5;
    HandValue eval{HandRank::HighCard, {}};
    if (canEvaluate) {
        eval = AdvancedHandEvaluator::evaluate(fullHand);
        if (observer) observer->onHandEvaluated(eval, fullHand);
    }

    // Show game stage
    std::string stageStr;
    switch (stage) {
        case GameStage::PreFlop: stageStr = "Pre-Flop"; break;
        case GameStage::Flop: stageStr = "Flop"; break;
        case GameStage::Turn: stageStr = "Turn"; break;
        case GameStage::River: stageStr = "River"; break;
    }

    // Calculate hand strength for decision factors
    double handStrength = 0.0;
    switch (eval.rank) {
        case HandRank::RoyalFlush:     handStrength = 1.0; break;
        case HandRank::StraightFlush:  handStrength = 0.95; break;
        case HandRank::FourOfAKind:    handStrength = 0.88; break;
        case HandRank::FullHouse:      handStrength = 0.78; break;
        case HandRank::Flush:          handStrength = 0.68; break;
        case HandRank::Straight:       handStrength = 0.58; break;
        case HandRank::ThreeOfAKind:   handStrength = 0.45; break;
        case HandRank::TwoPair:        handStrength = 0.35; break;
        case HandRank::OnePair:        handStrength = 0.22; break;
        case HandRank::HighCard:       handStrength = 0.08; break;
    }

    bool hasDraws = canEvaluate && hasDrawingHand(fullHand);
    if (observer) observer->onDecisionFactors(stageStr, eval, hasDraws, handStrength);

    bool decision;
    switch (difficulty) {
        case BotDifficulty::Easy:
            decision = shouldCallEasy();
            break;
        case BotDifficulty::Medium:
            decision = shouldCallMedium(eval, stage, fullHand);
            break;
        case BotDifficulty::Hard:
            decision = shouldCallHard(eval, stage, fullHand, pot, callAmount);
            break;
        case BotDifficulty::HardPlus:
            decision = shouldCallHardPlus(holeCards, community, pot, callAmount);
            break;
        default:
            decision = false;
    }

    return decision;
}

bool BotPlayer::shouldBetWhenChecked(const std::vector<Card>& holeCards,
                                     const std::vector<Card>& community,
                                     GameStage stage,
                                     int pot,
                                     int betAmount) {
    std::vector<Card> fullHand = holeCards;
    fullHand.insert(fullHand.end(), community.begin(), community.end());

    if (fullHand.size() < 5 || betAmount <= 0 || getChipCount() < betAmount) {
        return false;
    }

    HandValue eval = AdvancedHandEvaluator::evaluate(fullHand);

    switch (difficulty) {
        case BotDifficulty::Easy:
            // Easy stays passive.
            return false;

        case BotDifficulty::Medium: {
            // Value bets only clearly strong hands.
            if (eval.rank >= HandRank::ThreeOfAKind) {
                return true;
            }
            return false;
        }

        case BotDifficulty::Hard: {
            // Value bet two pair or better, and semi-bluff live draws before
            // the river so the draw has a card left to come.
            if (eval.rank >= HandRank::TwoPair) {
                return true;
            }
            if (stage != GameStage::River && hasDrawingHand(fullHand)) {
                std::uniform_int_distribution<int> dist(1, 100);
                return dist(rng) <= 50;  // semi-bluff half the time
            }
            // Occasional stab at an unwanted pot.
            return shouldBluff(eval.rank);
        }

        case BotDifficulty::HardPlus: {
            // Bet when equity says the hand is ahead often enough that a
            // called bet shows a profit. Checking back a winner is the mistake
            // this branch exists to prevent.
            double equity = estimateEquity(holeCards, community, simulationCount);
            if (equity >= 0.60) {
                return true;
            }
            // Semi-bluff strong draws while cards remain.
            if (stage != GameStage::River && equity >= 0.45 && hasDrawingHand(fullHand)) {
                std::uniform_int_distribution<int> dist(1, 100);
                return dist(rng) <= 50;
            }
            (void)pot;
            return false;
        }
    }

    return false;
}

bool BotPlayer::shouldCallEasy() const {
    // Use proper C++11 random distribution instead of rand()
    std::uniform_int_distribution<int> dist(0, 3);
    bool willCall = (dist(rng) == 0);  // 25% chance (1 in 4)
    
    std::string reasoning = "Random decision (25% chance to call)";
    if (observer) observer->onDecision(willCall, reasoning);
    
    return willCall;
}

bool BotPlayer::shouldCallMedium(const HandValue& eval, GameStage stage, const std::vector<Card>& fullHand) const {
    std::string reasoning;
    bool decision = false;
    
    // Base decision on hand strength and game stage
    if (eval.rank >= HandRank::ThreeOfAKind) {
        decision = true;
        reasoning = "Strong hand (Three of a Kind or better) - Always call";
        if (observer) observer->onDecision(decision, reasoning);
        return decision;
    }
    
    if (eval.rank >= HandRank::OnePair) {
        decision = true;
        reasoning = "At least one pair - Calling";
        if (observer) observer->onDecision(decision, reasoning);
        return decision;
    }
    
    // Check for drawing hands in earlier stages
    bool hasFlush = hasFlushDraw(fullHand);
    bool hasStraight = hasStraightDraw(fullHand);
    
    if (stage != GameStage::River && (hasFlush || hasStraight)) {
        if (observer) observer->onDrawingHand(hasFlush, hasStraight, fullHand);
        
        std::uniform_int_distribution<> dis(1, 100);

        // 60% chance to call with a drawing hand
        decision = dis(rng) <= 60;
        reasoning = decision ? "Drawing hand detected - Calling (60% chance)" : 
                              "Drawing hand but folding (40% chance)";
        if (observer) observer->onDecision(decision, reasoning);
        return decision;
    }
    
    // Add occasional random bluffing (10% chance)
    int bluffChance = (eval.rank == HandRank::HighCard) ? 10 : 15;
    decision = shouldBluff(eval.rank);
    
    if (decision) {
        if (observer) observer->onBluffConsidered(eval.rank, bluffChance, true);
        reasoning = "Attempting a bluff with weak hand";
    } else {
        reasoning = "Weak hand, no draws - Folding";
    }
    
    if (observer) observer->onDecision(decision, reasoning);
    return decision;
}

bool BotPlayer::shouldCallHard(const HandValue& eval, GameStage stage,
                               const std::vector<Card>& fullHand,
                               int pot, int callAmount) const {
    std::string reasoning;
    bool decision = false;

    // Equity the pot demands to break even on a call. With a 200 pot and a
    // 100 call that is 33%, so marginal hands need roughly a third of the
    // pots they contest. The old version ignored price entirely.
    double requiredEquity = PokerMath::calculatePotOddsPercentage(pot, callAmount);

    if (eval.rank >= HandRank::TwoPair) {
        decision = true;
        reasoning = "Strong hand (Two Pair or better) - Always call";
        if (observer) observer->onDecision(decision, reasoning);
        return decision;
    }

    if (eval.rank >= HandRank::OnePair) {
        // One pair is roughly a coin flip against a random holding, so call
        // whenever the pot is offering better than that. Only when the price
        // is steep does this become a fold.
        const double onePairEquity = 0.50;
        if (onePairEquity > requiredEquity) {
            decision = true;
            reasoning = "One pair vs pot odds requiring " +
                        std::to_string(static_cast<int>(requiredEquity * 100)) +
                        "% - Calling";
        } else {
            std::uniform_int_distribution<int> dist(0, 4);
            decision = (dist(rng) != 0);
            reasoning = decision ? "One pair, steep price - Calling anyway"
                                 : "One pair, price too steep - Folding";
        }
        if (observer) observer->onDecision(decision, reasoning);
        return decision;
    }

    // Drawing hands: a draw is only worth chasing if a card is still to come
    // and the pot is paying enough. A flush draw is about 35% to get there by
    // the river from the flop, a straight draw about 32%.
    bool hasFlush = hasFlushDraw(fullHand);
    bool hasStraight = hasStraightDraw(fullHand);

    if (stage != GameStage::River && (hasFlush || hasStraight)) {
        if (observer) observer->onDrawingHand(hasFlush, hasStraight, fullHand);

        double drawEquity = hasFlush ? 0.35 : 0.32;
        if (stage == GameStage::Turn) {
            drawEquity = hasFlush ? 0.196 : 0.174;  // only one card left
        }

        decision = drawEquity > requiredEquity;
        reasoning = decision
            ? "Draw with " + std::to_string(static_cast<int>(drawEquity * 100)) +
              "% equity vs " + std::to_string(static_cast<int>(requiredEquity * 100)) +
              "% required - Calling"
            : "Draw too thin for the price - Folding";
        if (observer) observer->onDecision(decision, reasoning);
        return decision;
    }

    // More aggressive bluffing (20% chance with weak hands)
    int bluffChance = (eval.rank == HandRank::HighCard) ? 15 : 20;
    decision = shouldBluff(eval.rank);

    if (decision) {
        if (observer) observer->onBluffConsidered(eval.rank, bluffChance, true);
        reasoning = "Aggressive bluff attempt";
    } else {
        reasoning = "Weak hand, no draws - Folding";
    }

    if (observer) observer->onDecision(decision, reasoning);
    return decision;
}

double BotPlayer::estimateEquity(const std::vector<Card>& holeCards,
                                 const std::vector<Card>& community,
                                 int simulations) const {
    // Delegate to MonteCarloSimulator rather than hand-rolling a loop here.
    // It completes the board to five cards, so a flop decision accounts for
    // the turn and river instead of treating the flop as final.
    MonteCarloSimulator sim(holeCards, community, simulations);
    sim.runSimulation();

    // Count ties as half a win: splitting the pot is neither a win nor a loss.
    return sim.getWinPercentage() + 0.5 * sim.getTiePercentage();
}

bool BotPlayer::shouldCallHardPlus(const std::vector<Card>& holeCards,
                                   const std::vector<Card>& community,
                                   int pot, int callAmount) {
    PerformanceMonitor::start("MonteCarlo_Simulation");

    // Defaults to 2000, which puts the 95% interval near +/-2%. The old 200
    // trials left it near +/-7%, wide enough to flip a marginal decision.
    const int simulations = simulationCount;
    if (observer) observer->onSimulationStarted(simulations);

    MonteCarloSimulator sim(holeCards, community, simulations);
    sim.runSimulation();

    double winRate = sim.getWinPercentage();
    double tieRate = sim.getTiePercentage();
    double equity = winRate + 0.5 * tieRate;

    int totalWins = static_cast<int>(winRate * simulations);
    int totalTies = static_cast<int>(tieRate * simulations);
    int totalLosses = simulations - totalWins - totalTies;

    // Report the interval for EQUITY, the quantity the decision below is
    // actually made on. The win-rate interval does not contain the equity
    // whenever ties are possible - on a board where 5% of hands chop, it
    // covered the true equity well under a fifth of the time.
    auto [lowerBound, upperBound] = sim.getEquityConfidenceInterval(0.95);

    if (observer) observer->onSimulationFinished(winRate, totalWins, totalLosses, totalTies, simulations);
    if (observer) observer->onConfidenceInterval(lowerBound, upperBound, 0.95);

    // Use the real pot and the real amount to call. These used to be
    // hardcoded to 200 and 100, so every EV figure the bot reported was
    // computed against numbers that had nothing to do with the hand.
    double potOddsRatio = PokerMath::calculatePotOdds(pot, callAmount);
    double requiredEquity = PokerMath::calculatePotOddsPercentage(pot, callAmount);
    double ev = PokerMath::calculateEV(equity, pot, callAmount);
    double kelly = PokerMath::kellyFraction(equity, potOddsRatio);

    if (observer) observer->onExpectedValue(ev, pot, callAmount);
    if (observer) observer->onKelly(equity, potOddsRatio, kelly);

    // Call when equity beats the price the pot is offering. A free call
    // (nothing to call) is never a fold.
    bool decision = (callAmount <= 0) || (equity > requiredEquity);

    std::string reasoning;
    if (callAmount <= 0) {
        reasoning = "Nothing to call - Checking behind";
    } else if (decision) {
        reasoning = "Equity " + std::to_string(static_cast<int>(equity * 100)) +
                    "% beats the " + std::to_string(static_cast<int>(requiredEquity * 100)) +
                    "% the pot requires (EV " + std::to_string(static_cast<int>(ev)) +
                    " chips) - CALLING";
    } else {
        reasoning = "Equity " + std::to_string(static_cast<int>(equity * 100)) +
                    "% short of the " + std::to_string(static_cast<int>(requiredEquity * 100)) +
                    "% required (EV " + std::to_string(static_cast<int>(ev)) +
                    " chips) - FOLDING";
    }

    if (observer) observer->onDecision(decision, reasoning);
    PerformanceMonitor::stop("MonteCarlo_Simulation");

    return decision;
}

// New helper methods for hand evaluation
bool BotPlayer::hasDrawingHand(const std::vector<Card>& fullHand) const {
    return hasFlushDraw(fullHand) || hasStraightDraw(fullHand);
}

bool BotPlayer::hasFlushDraw(const std::vector<Card>& fullHand) const {
    // Count cards by suit
    std::map<Suit, int> suitCount;
    for (const Card& c : fullHand) {
        suitCount[c.suit]++;
    }
    
    // 4 cards of same suit is a flush draw
    for (const auto& [suit, count] : suitCount) {
        if (count == 4) {
            return true;
        }
    }
    return false;
}

bool BotPlayer::hasStraightDraw(const std::vector<Card>& fullHand) const {
    std::vector<int> ranks;
    for (const Card& c : fullHand) {
        ranks.push_back(static_cast<int>(c.rank));
    }

    // Get unique ranks
    std::sort(ranks.begin(), ranks.end());
    auto last = std::unique(ranks.begin(), ranks.end());
    ranks.erase(last, ranks.end());

    // Treat an ace as low as well, so A-2-3-4 registers as a draw.
    if (!ranks.empty() && ranks.back() == 14) {
        ranks.insert(ranks.begin(), 1);
    }

    // Open-ended draw: four ranks in a row.
    int consecutive = 1;
    int maxConsecutive = 1;
    for (size_t i = 1; i < ranks.size(); ++i) {
        if (ranks[i] == ranks[i - 1] + 1) {
            consecutive++;
            maxConsecutive = std::max(maxConsecutive, consecutive);
        } else {
            consecutive = 1;
        }
    }

    if (maxConsecutive >= 4) {
        return true;
    }

    // Gutshot: four ranks spanning exactly five, leaving one gap in the
    // middle. The old check tested for four *consecutive* ranks, which is an
    // open-ended draw already covered above, so real gutshots never matched.
    //
    // Bound is `i + 3 < size()` rather than `i < size() - 3`: size() is
    // unsigned, so with fewer than four distinct ranks the subtraction wraps
    // and the loop reads past the end of the vector.
    for (size_t i = 0; i + 3 < ranks.size(); ++i) {
        if (ranks[i + 3] == ranks[i] + 4) {
            return true;
        }
    }

    return false;
}

// Bluffing logic
bool BotPlayer::shouldBluff(HandRank handRank) const {
    // Uses the member RNG. Seeding a fresh generator from random_device on
    // every call is slow and buys nothing.
    int bluffChance;
    switch (handRank) {
        case HandRank::HighCard:
            bluffChance = (difficulty == BotDifficulty::Hard) ? 15 : 10; 
            break;
        case HandRank::OnePair:
            bluffChance = (difficulty == BotDifficulty::Hard) ? 20 : 15;
            break;
        default:
            bluffChance = 0; // No need to bluff with better hands
    }
    
    std::uniform_int_distribution<> dis(1, 100);
    return dis(rng) <= bluffChance;
}