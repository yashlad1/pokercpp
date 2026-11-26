#ifndef MONTE_CARLO_SIMULATOR_H
#define MONTE_CARLO_SIMULATOR_H

#include "../model/card.h"
#include <vector>
#include <utility>  // for std::pair
#ifdef USE_METAL
#include "metal/MetalEquity.h"
#endif

class MonteCarloSimulator
{
public:
    MonteCarloSimulator(const std::vector<Card> &playerHand,
                        const std::vector<Card> &communityCards,
                        int simulations = 10000);

    void runSimulation();

#ifdef USE_METAL
    // This simulation as a GPU job (range, seed and trial count included).
    EquityJob metalJob() const;
#endif

    // Fix the generator's seed so a run is repeatable (bench only). 0, the
    // default, seeds from std::random_device as before.
    void setSeed(unsigned long long s) { seed = s; }

    // Restrict the opponent to the strongest `fraction` of starting hands
    // (1.0 = any two cards, the default). Dealing the opponent a uniformly
    // random hand overstates our equity against anyone who only puts money
    // in with good ones, which is the single largest source of error in a
    // decision made from this number.
    void setVillainRange(double fraction);
    double getWinPercentage() const;
    double getTiePercentage() const;
    double getLosePercentage() const;
    
    // Statistical rigor methods
    double getWinRateStdDev() const;  // Standard deviation of win rate
    std::pair<double, double> getConfidenceInterval(double confidence = 0.95) const;

    // Equity = win% + half of tie%, i.e. the expected share of the pot. This
    // is the quantity betting decisions are made on, so it needs its own
    // interval: a win-rate interval does not contain the equity whenever ties
    // are possible.
    double getEquity() const;
    double getEquityStdDev() const;

private:
    std::vector<Card> playerHand;
    std::vector<Card> communityCards;
    int numSimulations;
    int winCount;
    int tieCount;
    int loseCount;
    double villainRangeFraction;  // 1.0 means unrestricted
    unsigned long long seed = 0;  // 0 means random_device

    std::vector<Card> getRemainingDeck() const;

    // Concrete two-card holdings from `deck` that fall inside the range.
    std::vector<std::pair<Card, Card>> villainCombos(const std::vector<Card> &deck) const;
    std::pair<std::vector<Card>, std::vector<Card>> dealRandomOpponentAndBoard(const std::vector<Card> &deck) const;
};

#endif