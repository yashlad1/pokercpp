#ifndef POKER_CONTROLLER_H
#define POKER_CONTROLLER_H

#include "../model/player.h"
#include "../model/bot_player.h"
#include "player_input.h"
#include <chrono>

class PokerController
{
public:
    PokerController() = default;

    // Injecting an input source lets tests drive a full hand without a
    // terminal. Defaults to reading std::cin.
    explicit PokerController(PlayerInput *in) : input(in) {}

    void runGame();

    // Plays one hand and returns the pot that was awarded. Exposed so the
    // round flow can be exercised directly in tests.
    int playSingleRound(Player &human, Player &bot);

    // Cosmetic pause while the bot "thinks". It dwarfs the real computation
    // (a decision costs ~10ms), so tests set it to zero.
    void setThinkingDelay(std::chrono::milliseconds d) { thinkingDelay = d; }

private:
    std::chrono::milliseconds thinkingDelay{2000};

    ConsoleInput consoleInput;
    PlayerInput *input = &consoleInput;

    void playRound(Player &human, Player &bot);

    // `pot` is carried by reference through the whole round so every chip
    // staked is accounted for exactly once.
    bool handleBetting(Player &human, Player &bot, const std::vector<Card> &community,
                       GameStage stage, int &pot);
    void showdown(Player &human, Player &bot, const std::vector<Card> &community, int &pot);
    void awardPot(Player &winner, int &pot);

    // Gives back the part of a bet the opponent could not cover.
    void returnUncalled(Player &bettor, int uncalled, int &pot);

    // Writes the finished hand to the analytics CSV.
    void logRoundOutcome(Player &human, Player &bot, const std::vector<Card> &community,
                         int humanStart, int botStart);
};

#endif // Poker_CONTROLLER_H