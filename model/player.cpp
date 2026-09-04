#include "player.h"
#include <sstream>

Player::Player(const std::string &name, int startingChips)
	: name(name), chips(startingChips), folded(false) {}

// Adds one of two hole cards
void Player::recieveCard(const Card &card)
{
	// Silently ignores extras rather than writing to stderr; the caller
	// controls dealing and a model should not be reporting to a console.
	if (hand.size() < 2)
	{
		hand.push_back(card);
	}
}

// clears hand between rounds
void Player::clearHand()
{
	hand.clear();
}

// deducts chips from player's stack, returning what was actually wagered
int Player::bet(int amount)
{
	if (amount <= 0)
	{
		return 0;
	}

	// Clamp to the available stack rather than refusing the bet outright.
	// The old version returned without deducting anything, but callers had no
	// way to notice and carried on as though the chips had been staked.
	int wagered = (amount > chips) ? chips : amount;
	chips -= wagered;
	return wagered;
}

// adds chips to player's stack (for winnings)
void Player::addChips(int amount)
{
	chips += amount;
}

// Marks player as folded (out of round)
void Player::fold()
{
	folded = true;
}

// unfolds player at start of new round
void Player::resetStatus()
{
	folded = false;
}

bool Player::isFolded() const
{
	return folded;
}

int Player::getChipCount() const
{
	return chips;
}

std::string Player::getName() const
{
	return name;
}

// Renders the hand for display. Returns text instead of printing it.
std::string Player::handToString(bool showCards) const
{
	std::ostringstream out;
	if (showCards)
	{
		for (const Card &card : hand)
		{
			out << card.toString() << " ";
		}
	}
	else
	{
		for (size_t i = 0; i < hand.size(); ++i)
		{
			out << "[hidden]";
		}
	}
	return out.str();
}

std::vector<Card> Player::getHand() const
{
	return hand;
}