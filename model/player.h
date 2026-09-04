#ifndef PLAYER_H
#define PLAYER_H

#include "card.h"
#include <vector>
#include <string>

/**
 * Each player needs:
 * 1. A name (or ID)
 * 2. Hole cards (2 cards in Texas Hold'em)
 * 3. A chip count (how many chips/ money they have)
 * 4. A flag for whether they have folded
 * 5. Methods to recieve cards, bet, fold etc.
 **/
class Player
{
private:
	std::string name;
	std::vector<Card> hand;
	int chips;
	bool folded;

public:
	Player(const std::string &name, int startingChips);

	void recieveCard(const Card &card); // Add a card to the hand
	void clearHand();					// Reset hand (for new round)

	// Deducts chips and returns the amount actually wagered. The return value
	// is clamped to the player's stack (an all-in), so callers can add exactly
	// what was staked to the pot and keep chip totals conserved.
	int bet(int amount);
	void addChips(int amount); // add chips (for winnings)
	void fold();		  // set folded=true
	void resetStatus();	  // unfold for next round

	bool isFolded() const;
	int getChipCount() const;
	std::string getName() const;
	std::vector<Card> getHand() const;

	// Renders the hand as a string. The model does not print: returning text
	// lets the view decide how (and whether) to display it, and keeps tests
	// from writing to stdout.
	std::string handToString(bool showCards = true) const;
};

#endif

/**
 * This class holds state only. It deliberately performs no console output so
 * the same model can be driven by a different front end and so unit tests stay
 * silent.
 *
 * hand -> Stores the player's 2 private (hole) cards
 * chips -> represents their current stack for betting
 * folded -> tracks whether player is out of round
 * recieveCard() -> called twice to deal the hole cards
 * bet() -> removes chips when the player bets
 * showHand() -> used in showdown or debug mode
 **/