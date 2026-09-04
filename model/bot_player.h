#ifndef BOT_PLAYER_H
#define BOT_PLAYER_H

#include "player.h"
#include "hand_types.h"
#include "advanced_hand_evaluator.h"
#include <vector>
#include <string>
#include <random>

enum class GameStage 
{
    PreFlop,
    Flop,
    Turn,
    River
};

enum class BotDifficulty
{
    Easy,
    Medium,
    Hard,
    HardPlus
};

class BotPlayer : public Player
{
private:
    BotDifficulty difficulty;
    mutable std::mt19937 rng;  // Mersenne Twister RNG (mutable for const methods)

    // basic decision making methods
    bool shouldCallEasy() const;
    bool shouldCallMedium(const HandValue& eval, GameStage stage, const std::vector<Card>& fullHand) const;
    bool shouldCallHard(const HandValue& eval, GameStage stage, const std::vector<Card>& fullHand,
                       int pot, int callAmount) const;
    bool shouldCallHardPlus(const std::vector<Card>& holeCards,
                            const std::vector<Card>& community,
                            int pot, int callAmount);

    // hand strength awareness methods
    bool hasDrawingHand(const std::vector<Card>& fullHand) const;
    bool hasFlushDraw(const std::vector<Card>& fullHand) const;
    bool hasStraightDraw(const std::vector<Card>& fullHand) const;

    // Equity estimate used by the HardPlus profile. Runs a Monte Carlo
    // simulation that completes the board, so a flop decision accounts for
    // the turn and river still to come.
    double estimateEquity(const std::vector<Card>& holeCards,
                          const std::vector<Card>& community,
                          int simulations) const;

    // Bluffing Logic
    bool shouldBluff(HandRank handRank) const;

public:
    BotPlayer(const std::string &name, int chips, BotDifficulty diff);

    BotDifficulty getDifficulty() const;

    // Decide whether to call a bet of `callAmount` into a pot of `pot`.
    // Hole cards and community cards are passed separately so the bot never
    // has to guess where the board starts.
    bool shouldCallBet(const std::vector<Card> &holeCards,
                       const std::vector<Card> &community,
                       GameStage stage = GameStage::River,
                       int pot = 0,
                       int callAmount = 0);

    // Decide whether to bet when the opponent checks. Without this the bot
    // could only ever call or fold, so it checked back made hands and never
    // won a chip it was not first offered.
    bool shouldBetWhenChecked(const std::vector<Card> &holeCards,
                              const std::vector<Card> &community,
                              GameStage stage,
                              int pot,
                              int betAmount);
};

#endif