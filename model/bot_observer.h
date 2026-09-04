#ifndef BOT_OBSERVER_H
#define BOT_OBSERVER_H

#include "card.h"
#include "hand_types.h"
#include <string>
#include <vector>

/**
 * Reporting hook for a bot's reasoning.
 *
 * BotPlayer used to call BotThinkingVisualizer directly, which meant the model
 * layer depended on the view: the bot could not think without writing to a
 * console, and unit tests were forced to render simulation panels to stdout.
 *
 * The bot now reports through this interface. A front end supplies an
 * implementation; passing none leaves the bot silent.
 */
class BotObserver
{
public:
    virtual ~BotObserver() = default;

    virtual void onThinkingStarted(const std::string &botName, const std::string &difficulty) = 0;
    virtual void onHandEvaluated(const HandValue &eval, const std::vector<Card> &hand) = 0;
    virtual void onDecisionFactors(const std::string &stage, const HandValue &eval,
                                   bool hasDraws, double handStrength) = 0;
    virtual void onDrawingHand(bool flushDraw, bool straightDraw,
                              const std::vector<Card> &fullHand) = 0;
    virtual void onBluffConsidered(HandRank rank, int bluffChance, bool willBluff) = 0;
    virtual void onSimulationStarted(int simulations) = 0;
    virtual void onSimulationFinished(double winRate, int wins, int losses,
                                      int ties, int simulations) = 0;
    virtual void onConfidenceInterval(double lower, double upper, double confidence) = 0;
    virtual void onExpectedValue(double ev, int pot, int callAmount) = 0;
    virtual void onKelly(double winProbability, double potOdds, double kellyFraction) = 0;
    virtual void onDecision(bool willCall, const std::string &reasoning) = 0;
};

#endif // BOT_OBSERVER_H
