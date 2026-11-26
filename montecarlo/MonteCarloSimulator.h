#ifndef MONTE_CARLO_SIMULATOR_H
#define MONTE_CARLO_SIMULATOR_H

#include "../model/card.h"
#include <vector>
#include <utility>
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

    // Fix the generator's seed so a run is repeatable; 0 seeds from std::random_device.
    void setSeed(unsigned long long s) { seed = s; }

    // Restrict the opponent to the strongest `fraction` of starting hands (1.0 = any two cards).
    // A uniformly random opponent hand overstates our equity against anyone who only plays good ones.
    void setVillainRange(double fraction);
    double getWinPercentage() const;
    double getTiePercentage() const;
    double getLosePercentage() const;
    
    double getWinRateStdDev() const;
    std::pair<double, double> getConfidenceInterval(double confidence = 0.95) const;

    // Equity = win% + half of tie%, the expected share of the pot.
    double getEquity() const;
    double getEquityStdDev() const;

private:
    std::vector<Card> playerHand;
    std::vector<Card> communityCards;
    int numSimulations;
    int winCount;
    int tieCount;
    int loseCount;
    double villainRangeFraction;
    unsigned long long seed = 0;

    std::vector<Card> getRemainingDeck() const;

    std::vector<std::pair<Card, Card>> villainCombos(const std::vector<Card> &deck) const;
    std::pair<std::vector<Card>, std::vector<Card>> dealRandomOpponentAndBoard(const std::vector<Card> &deck) const;
};

#endif