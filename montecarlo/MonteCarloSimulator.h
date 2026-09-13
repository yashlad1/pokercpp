#ifndef MONTE_CARLO_SIMULATOR_H
#define MONTE_CARLO_SIMULATOR_H

#include "../model/card.h"
#include <vector>
#include <utility>  // for std::pair

class MonteCarloSimulator
{
public:
    MonteCarloSimulator(const std::vector<Card> &playerHand,
                        const std::vector<Card> &communityCards,
                        int simulations = 10000);

    void runSimulation();

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
    std::pair<double, double> getEquityConfidenceInterval(double confidence = 0.95) const;
    int getSampleSize() const { return numSimulations; }

    // Drawing hand probability methods
    double getFlushDrawOdds() const;
    double getStraightDrawOdds() const;

private:
    std::vector<Card> playerHand;
    std::vector<Card> communityCards;
    int numSimulations;
    int winCount;
    int tieCount;
    int loseCount;
    double villainRangeFraction;  // 1.0 means unrestricted

    std::vector<Card> getRemainingDeck() const;

    // Concrete two-card holdings from `deck` that fall inside the range.
    std::vector<std::pair<Card, Card>> villainCombos(const std::vector<Card> &deck) const;
    std::pair<std::vector<Card>, std::vector<Card>> dealRandomOpponentAndBoard(const std::vector<Card> &deck) const;
};

#endif