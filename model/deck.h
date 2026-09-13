#ifndef DECK_H
#define DECK_H

#include "card.h"
#include <vector>
#include <random>
#include <algorithm>
#include <cstdint>

class Deck
{
private:
	std::vector<Card> cards;
	std::mt19937 rng; // Mersenne Twister random number generator

	void populate(); // fills `cards` with all 52 cards

public:
	// Builds and shuffles a deck. Seeded from std::random_device, so two decks
	// created in the same second still shuffle differently. The old version
	// seeded from std::time(nullptr), whose one-second resolution meant every
	// round starting within the same second dealt identical cards.
	Deck();

	// Deterministic deck for tests and reproducible play.
	explicit Deck(std::uint_fast32_t seed);
	void shuffle();		  // Reshuffles the deck
	Card dealCard();	  // Deals one card
	bool isEmpty() const; // Checks if the deck is empty
	int size() const;	  // Number of cards remaining
};

#endif