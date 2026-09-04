#include "poker_controller.h"
#include "../model/deck.h"
#include "../model/player.h"
#include "../model/hand_types.h"
#include "../model/advanced_hand_evaluator.h"
#include "../view/cli_view.h"
#include "../animation/spinner.h"
#include "../model/bot_player.h"
#include "../utils/game_logger.h"

#include <iostream>
#include <vector>
#include <string>
#include <thread>
#include <chrono>
#include <cctype>
#include <cstdlib>

// ANSI color codes
#define RESET "\033[0m"
#define BOLD "\033[1m"
#define CYAN "\033[36m"
#define GREEN "\033[32m"
#define YELLOW "\033[33m"
#define RED "\033[31m"
#define BLUE "\033[34m"
#define MAGENTA "\033[35m"

std::vector<Card> getCombinedHand(const Player &player, const std::vector<Card> &community)
{
    std::vector<Card> fullHand = player.getHand();
    fullHand.insert(fullHand.end(), community.begin(), community.end());
    return fullHand;
}

/**
 * Parse a difficulty name, case-insensitively.
 *
 * Returns false for anything unrecognized rather than silently substituting a
 * default. The old code initialized to Medium with no else branch, so "HARD",
 * "hardpluss" and stray buffered input all quietly produced a Medium bot while
 * the player believed otherwise.
 */
bool parseDifficulty(const std::string &raw, BotDifficulty &out)
{
    std::string s;
    for (char c : raw)
    {
        if (!std::isspace(static_cast<unsigned char>(c)))
        {
            s += static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
        }
    }

    if (s == "easy")                        { out = BotDifficulty::Easy;     return true; }
    if (s == "medium")                      { out = BotDifficulty::Medium;   return true; }
    if (s == "hard")                        { out = BotDifficulty::Hard;     return true; }
    if (s == "hardplus" || s == "hard+")    { out = BotDifficulty::HardPlus; return true; }
    return false;
}

// Human-readable difficulty name, echoed back so the player can see which
// profile actually loaded.
std::string difficultyName(BotDifficulty d)
{
    switch (d)
    {
    case BotDifficulty::Easy:     return "easy";
    case BotDifficulty::Medium:   return "medium";
    case BotDifficulty::Hard:     return "hard";
    case BotDifficulty::HardPlus: return "hardplus";
    }
    return "unknown";
}

std::string handRankToString(HandRank rank)
{
    switch (rank)
    {
    case HandRank::HighCard:
        return "High Card";
    case HandRank::OnePair:
        return "One Pair";
    case HandRank::TwoPair:
        return "Two Pair";
    case HandRank::ThreeOfAKind:
        return "Three of a Kind";
    case HandRank::Straight:
        return "Straight";
    case HandRank::Flush:
        return "Flush";
    case HandRank::FullHouse:
        return "Full House";
    case HandRank::FourOfAKind:
        return "Four of a Kind";
    case HandRank::StraightFlush:
        return "Straight Flush";
    case HandRank::RoyalFlush:
        return "Royal Flush";
    default:
        return "Unknown";
    }
}

// Single card rank, e.g. 14 -> "Ace"
static std::string rankName(int r)
{
    switch (r)
    {
    case 14: return "Ace";
    case 13: return "King";
    case 12: return "Queen";
    case 11: return "Jack";
    case 10: return "Ten";
    case 9:  return "Nine";
    case 8:  return "Eight";
    case 7:  return "Seven";
    case 6:  return "Six";
    case 5:  return "Five";
    case 4:  return "Four";
    case 3:  return "Three";
    case 2:  return "Two";
    default: return "?";
    }
}

// Plural rank, e.g. 14 -> "Aces". Used for pairs, trips and quads.
static std::string rankNamePlural(int r)
{
    if (r == 6) return "Sixes";  // the only irregular one
    return rankName(r) + "s";
}

/**
 * Describe a hand including its tie-breakers.
 *
 * handRankToString alone cannot explain a showdown: two players both holding
 * "Two Pair" gives no hint why one of them won. The evaluator already
 * computes the kickers, so spell them out.
 */
std::string handValueToString(const HandValue &hv)
{
    const std::vector<int> &k = hv.kickers;

    switch (hv.rank)
    {
    case HandRank::RoyalFlush:
        return "Royal Flush";

    case HandRank::StraightFlush:
        if (k.empty()) break;
        return "Straight Flush, " + rankName(k[0]) + "-high";

    case HandRank::FourOfAKind:
        if (k.empty()) break;
        return "Four of a Kind, " + rankNamePlural(k[0]) +
               (k.size() > 1 && k[1] > 0 ? " (" + rankName(k[1]) + " kicker)" : "");

    case HandRank::FullHouse:
        if (k.size() < 2) break;
        return "Full House, " + rankNamePlural(k[0]) + " over " + rankNamePlural(k[1]);

    case HandRank::Flush:
        if (k.empty()) break;
        return "Flush, " + rankName(k[0]) + "-high";

    case HandRank::Straight:
        if (k.empty()) break;
        return "Straight, " + rankName(k[0]) + "-high";

    case HandRank::ThreeOfAKind:
        if (k.empty()) break;
        return "Three of a Kind, " + rankNamePlural(k[0]);

    case HandRank::TwoPair:
        if (k.size() < 2) break;
        return "Two Pair, " + rankNamePlural(k[0]) + " and " + rankNamePlural(k[1]) +
               (k.size() > 2 && k[2] > 0 ? " (" + rankName(k[2]) + " kicker)" : "");

    case HandRank::OnePair:
        if (k.empty()) break;
        return "One Pair, " + rankNamePlural(k[0]) +
               (k.size() > 1 ? " (" + rankName(k[1]) + " kicker)" : "");

    case HandRank::HighCard:
        if (k.empty()) break;
        return "High Card, " + rankName(k[0]);
    }

    // Fall back to the bare rank name if kickers are missing.
    return handRankToString(hv.rank);
}

void PokerController::runGame()
{
    CLIView::showWelcome();

    BotDifficulty botDiff = BotDifficulty::Medium;
    std::string input;

    // Reprompt on unrecognized input instead of silently falling back.
    while (true)
    {
        std::cout << BOLD << CYAN << "Choose bot difficulty " << RESET << "(" << GREEN << "easy" << RESET << " / " << YELLOW << "medium" << RESET << " / " << RED << "hard" << RESET << " / " << MAGENTA << "hardplus" << RESET << "): ";

        if (!(std::cin >> input))
        {
            // No more input (piped or EOF). Say what we settled on.
            std::cout << "\n" << YELLOW << "No input available - defaulting to medium." << RESET << "\n";
            break;
        }

        if (parseDifficulty(input, botDiff))
        {
            break;
        }

        std::cout << RED << "  '" << input << "' is not a difficulty." << RESET
                  << " Please type easy, medium, hard or hardplus.\n";
    }

    std::cout << BOLD << CYAN << "Playing against the " << difficultyName(botDiff)
              << " bot." << RESET << "\n";

    Player human("You", 1000);
    BotPlayer bot("Bot", 1000, botDiff);

    while (human.getChipCount() > 0 && bot.getChipCount() > 0)
    {
        CLIView::showDivider();
        CLIView::showChipCounts(human, bot);
        CLIView::showDivider();

        playRound(human, bot);

        std::string choice;
        std::cout << "\n" << BOLD << BLUE << "Do you want to play another round? " << RESET << "(" << GREEN << "yes" << RESET << "/" << RED << "no" << RESET << "): ";
        std::cin >> choice;

        if (choice != "yes" && choice != "y")
        {
            std::cout << BOLD << GREEN << "\nThanks for playing! 🎉" << RESET << "\n";
            break;
        }
    }

    std::cout << "\n" << BOLD << YELLOW << "🏁 Game Over!" << RESET << "\n";
    if (human.getChipCount() <= 0)
    {
        std::cout << BOLD << RED << "😞 You ran out of chips. Bot wins the game!" << RESET << "\n";
    }
    else if (bot.getChipCount() <= 0)
    {
        std::cout << BOLD << GREEN << "🎉 Bot is broke! You win the game!" << RESET << "\n";
    }
}

void PokerController::playRound(Player &human, Player &bot)
{
    Deck deck;
    human.clearHand();
    bot.clearHand();
    human.resetStatus();
    bot.resetStatus();

    // Every chip staked this round lands here and is paid out in full.
    int pot = 0;

    human.recieveCard(deck.dealCard());
    human.recieveCard(deck.dealCard());
    bot.recieveCard(deck.dealCard());
    bot.recieveCard(deck.dealCard());

    std::cout << "\n" << BOLD << GREEN << "Your Hand: " << RESET;
    human.showHand(true);
    std::cout << BOLD << CYAN << "Bot's Hand: " << RESET;
    bot.showHand(false);

    CLIView::waitForEnter();

    // Record the stacks before any betting so the log can report real chip
    // deltas rather than inferring them from the pot.
    const int humanStart = human.getChipCount();
    const int botStart = bot.getChipCount();
    GameLogger::startNewHand();

    // Flop
    std::vector<Card> community;
    for (int i = 0; i < 3; ++i)
        community.push_back(deck.dealCard());
    CLIView::showCommunityCards(community, "Flop");

    // `live` stays true while neither player has folded. Written as a flat
    // sequence rather than early returns so the hand always gets logged.
    bool live = handleBetting(human, bot, community, GameStage::Flop, pot);

    if (live)
    {
        community.push_back(deck.dealCard());
        CLIView::showCommunityCards(community, "Turn");
        live = handleBetting(human, bot, community, GameStage::Turn, pot);
    }

    if (live)
    {
        community.push_back(deck.dealCard());
        CLIView::showCommunityCards(community, "River");
        live = handleBetting(human, bot, community, GameStage::River, pot);
    }

    if (live)
    {
        showdown(human, bot, community, pot);
    }

    logRoundOutcome(human, bot, community, humanStart, botStart);
}

/**
 * Write the finished hand to the analytics log.
 *
 * GameLogger was fully implemented but had no callers, so the CSV only ever
 * contained its header row while the game advertised the log twice on startup
 * and exit.
 */
void PokerController::logRoundOutcome(Player &human, Player &bot,
                                      const std::vector<Card> &community,
                                      int humanStart, int botStart)
{
    const int humanNet = human.getChipCount() - humanStart;
    const int botNet = bot.getChipCount() - botStart;

    std::string winner = "Tie";
    if (humanNet > botNet)
        winner = "Human";
    else if (botNet > humanNet)
        winner = "Bot";

    // A fold can end the hand on the flop, leaving fewer than five community
    // cards. With two hole cards there are always at least five to evaluate.
    HandRank humanRank = HandRank::HighCard;
    HandRank botRank = HandRank::HighCard;

    auto humanFull = getCombinedHand(human, community);
    auto botFull = getCombinedHand(bot, community);
    if (humanFull.size() >= 5)
        humanRank = AdvancedHandEvaluator::evaluate(humanFull).rank;
    if (botFull.size() >= 5)
        botRank = AdvancedHandEvaluator::evaluate(botFull).rank;

    GameLogger::logHandOutcome(winner, human.getHand(), bot.getHand(), community,
                               humanRank, botRank,
                               std::abs(humanNet) + std::abs(botNet),
                               humanNet, botNet);
}

bool PokerController::handleBetting(Player &human, Player &bot, const std::vector<Card> &community,
                                    GameStage stage, int &pot)
{
    CLIView::waitForEnter();

    const int BET_AMOUNT = 100;
    BotPlayer &botPlayer = static_cast<BotPlayer &>(bot);

    std::cout << "\n" << BOLD << YELLOW << "Pot: " << pot << " chips" << RESET << "\n";
    std::cout << "\n" << BOLD << BLUE << "What do you want to do? " << RESET << "(" << GREEN << "check" << RESET << " / " << YELLOW << "bet" << RESET << " / " << RED << "fold" << RESET << "): ";
    std::string action;
    std::cin >> action;

    if (action == "fold")
    {
        std::cout << RED << "You folded. " << RESET << CYAN << "Bot wins the round." << RESET << "\n";
        std::cout << CYAN << "Bot's hand: " << RESET;
        bot.showHand(true);
        awardPot(bot, pot);
        return false;
    }

    if (action == "bet" && human.getChipCount() > 0)
    {
        // Stake the chips first and add exactly what was wagered to the pot,
        // so an all-in for less than the full bet still balances.
        int wagered = human.bet(BET_AMOUNT);
        pot += wagered;

        std::atomic<bool> done(false);
        std::thread spinner(Spinner::show, std::ref(done));

        std::this_thread::sleep_for(std::chrono::seconds(2));

        // The bot is priced on the live pot (which already includes the bet it
        // is facing) and on what it actually costs to call.
        bool botCalls = botPlayer.shouldCallBet(bot.getHand(), community, stage, pot, wagered);

        done = true;
        spinner.join();

        if (botCalls)
        {
            std::cout << CYAN << "Bot calls your bet." << RESET << "\n";
            int matched = bot.bet(wagered);
            pot += matched;
            returnUncalled(human, wagered - matched, pot);
        }
        else
        {
            std::cout << CYAN << "Bot folds." << RESET << "\n";
            bot.showHand(true);
            awardPot(human, pot);
            return false;
        }
    }
    else
    {
        std::cout << BLUE << "You checked." << RESET << "\n";

        // Give the bot a chance to bet. Previously this branch printed
        // "Bot checks" unconditionally, so the bot could never bet a made
        // hand and never won chips it was not first offered.
        std::atomic<bool> done(false);
        std::thread spinner(Spinner::show, std::ref(done));
        std::this_thread::sleep_for(std::chrono::seconds(1));
        bool botBets = botPlayer.shouldBetWhenChecked(bot.getHand(), community, stage, pot, BET_AMOUNT);
        done = true;
        spinner.join();

        if (!botBets)
        {
            std::cout << CYAN << "Bot checks." << RESET << "\n";
            return true;
        }

        int botWager = bot.bet(BET_AMOUNT);
        pot += botWager;

        std::cout << "\n" << BOLD << YELLOW << "Pot: " << pot << " chips" << RESET
                  << "  |  to call: " << BOLD << botWager << RESET << "\n";
        std::cout << BOLD << BLUE << "Bot bet " << botWager << ". Your move? " << RESET
                  << "(" << GREEN << "call" << RESET << " / " << RED << "fold" << RESET << "): ";
        std::string response;
        std::cin >> response;

        if (response == "call" && human.getChipCount() > 0)
        {
            int matched = human.bet(botWager);
            pot += matched;
            returnUncalled(bot, botWager - matched, pot);
        }
        else
        {
            std::cout << RED << "You folded. " << RESET << CYAN << "Bot wins the round." << RESET << "\n";
            std::cout << CYAN << "Bot's hand: " << RESET;
            bot.showHand(true);
            awardPot(bot, pot);
            return false;
        }
    }

    return true;
}

// Returns the portion of a bet the opponent could not match.
//
// If a player bets 100 but the opponent is all-in for 40, only 40 of that 100
// is actually contested. The remaining 60 is an uncalled bet and belongs back
// with the bettor - otherwise the short stack could win 100 having risked 40.
void PokerController::returnUncalled(Player &bettor, int uncalled, int &pot)
{
    if (uncalled <= 0)
    {
        return;
    }
    bettor.addChips(uncalled);
    pot -= uncalled;
    std::cout << YELLOW << "  " << uncalled << " chips uncalled - returned to "
              << bettor.getName() << "." << RESET << "\n";
}

// Hands the whole pot to one player and zeroes it, so no chips are created or
// destroyed. The pot used to be a hardcoded 200 regardless of what was staked.
void PokerController::awardPot(Player &winner, int &pot)
{
    if (pot <= 0)
    {
        return;
    }
    winner.addChips(pot);
    std::cout << BOLD << (winner.getName() == "You" ? GREEN : CYAN)
              << winner.getName() << (winner.getName() == "You" ? " win " : " wins ")
              << pot << " chips! 💰" << RESET << "\n";
    pot = 0;
}

void PokerController::showdown(Player &human, Player &bot, const std::vector<Card> &community, int &pot)
{
    CLIView::showResult(human, bot, community);

    auto humanFull = getCombinedHand(human, community);
    auto botFull = getCombinedHand(bot, community);

    HandValue hv1 = AdvancedHandEvaluator::evaluate(humanFull);
    HandValue hv2 = AdvancedHandEvaluator::evaluate(botFull);

    // Show the tie-breakers, not just the rank, so the result is explainable.
    CLIView::showHandType(human.getName(), handValueToString(hv1));
    CLIView::showHandType(bot.getName(), handValueToString(hv2));

    std::cout << "\n" << BOLD << YELLOW << "Result: " << RESET;
    if (hv1 > hv2)
    {
        std::cout << BOLD << GREEN << "You win! 🎉" << RESET << "\n";
        awardPot(human, pot);
    }
    else if (hv2 > hv1)
    {
        std::cout << BOLD << CYAN << "Bot wins! 🤖" << RESET << "\n";
        awardPot(bot, pot);
    }
    else
    {
        std::cout << BOLD << YELLOW << "It's a tie! 🤝" << RESET << "\n";
        // Split without losing the odd chip.
        int half = pot / 2;
        human.addChips(half);
        bot.addChips(pot - half);
        std::cout << YELLOW << "Pot split - " << human.getName() << " gets " << half
                  << ", " << bot.getName() << " gets " << (pot - half) << ". 💰" << RESET << "\n";
        pot = 0;
    }
}
