#ifndef BOT_THINKING_REPORTER_H
#define BOT_THINKING_REPORTER_H

#include "../model/bot_observer.h"
#include "bot_thinking_visualizer.h"

/**
 * Adapts the console visualizer to the model's BotObserver interface.
 *
 * This is the only place the two layers meet: the model knows about
 * BotObserver, the view knows about BotThinkingVisualizer, and this class
 * bridges them so neither has to include the other.
 */
class BotThinkingReporter : public BotObserver
{
public:
    void onThinkingStarted(const std::string &botName, const std::string &difficulty) override {
        BotThinkingVisualizer::showThinkingHeader(botName, difficulty);
    }
    void onHandEvaluated(const HandValue &eval, const std::vector<Card> &hand) override {
        BotThinkingVisualizer::showHandEvaluation(eval, hand);
    }
    void onDecisionFactors(const std::string &stage, const HandValue &eval,
                           bool hasDraws, double handStrength) override {
        BotThinkingVisualizer::showDecisionFactors(stage, eval, hasDraws, handStrength);
    }
    void onDrawingHand(bool flushDraw, bool straightDraw,
                       const std::vector<Card> &fullHand) override {
        BotThinkingVisualizer::showDrawingHandAnalysis(flushDraw, straightDraw, fullHand);
    }
    void onBluffConsidered(HandRank rank, int bluffChance, bool willBluff) override {
        BotThinkingVisualizer::showBluffCalculation(rank, bluffChance, willBluff);
    }
    void onSimulationStarted(int simulations) override {
        BotThinkingVisualizer::showMonteCarloHeader(simulations);
    }
    void onSimulationFinished(double winRate, int wins, int losses,
                              int ties, int simulations) override {
        BotThinkingVisualizer::showMonteCarloResult(winRate, wins, losses, ties, simulations);
    }
    void onConfidenceInterval(double lower, double upper, double confidence) override {
        BotThinkingVisualizer::showConfidenceInterval(lower, upper, confidence);
    }
    void onExpectedValue(double ev, int pot, int callAmount) override {
        BotThinkingVisualizer::showExpectedValue(ev, pot, callAmount);
    }
    void onKelly(double winProbability, double potOdds, double kellyFraction) override {
        BotThinkingVisualizer::showKellyCriterion(winProbability, potOdds, kellyFraction);
    }
    void onDecision(bool willCall, const std::string &reasoning) override {
        BotThinkingVisualizer::showFinalDecision(willCall, reasoning);
    }
};

#endif // BOT_THINKING_REPORTER_H
