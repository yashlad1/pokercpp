#ifndef POKER_CONTROLLER_H
#define POKER_CONTROLLER_H

#include "../model/player.h"
#include "../model/bot_player.h"

class PokerController
{
public:
    void runGame();

private:
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