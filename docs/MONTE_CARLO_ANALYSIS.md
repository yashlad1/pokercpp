# Monte Carlo Simulation Analysis

## Overview

This document provides a rigorous mathematical analysis of the Monte Carlo simulation system used in the poker bot's decision-making process.

## Methodology

### Simulation Process

The bot uses **Monte Carlo simulation** to estimate win probability by:

1. **Sampling**: Running N simulations with random opponent hands
2. **Evaluation**: Comparing hand strengths at showdown
3. **Aggregation**: Computing win/tie/loss statistics

### Mathematical Foundation

#### Win Rate Estimation

The estimated win rate is calculated as:

```
p̂ = W / N
```

Where:
- `p̂` = estimated win probability
- `W` = number of wins in simulation
- `N` = total number of simulations

#### Standard Deviation

For binomial outcomes, the standard deviation is:

```
σ = √(p(1-p)/N)
```

This represents the **standard error** of our win rate estimate.

#### Confidence Intervals

We use the **normal approximation** to the binomial distribution to calculate confidence intervals:

```
CI = p̂ ± z * σ
```

Where `z` is the z-score for the desired confidence level:
- 90% confidence: z = 1.645
- 95% confidence: z = 1.96
- 99% confidence: z = 2.576

**Example**: With 2000 simulations and a 70% win rate:
- σ = √(0.7 × 0.3 / 200) = 0.032
- 95% CI = 0.70 ± (1.96 × 0.032) = [0.637, 0.763]

## Implementation Details

### Simulation Parameters

| Parameter | Fast | Standard | Accurate |
|-----------|------|----------|----------|
| Simulations | 200 | 1,000 | 10,000 |
| Threads | 4 | 4 | 4 |
| Time | ~50ms | ~250ms | ~2.5s |
| Margin of Error (95% CI) | ±7% | ±3% | ±1% |

### Performance Characteristics

#### Time Complexity
- **Per simulation**: O(7C2 × 52) ≈ O(1092) hand comparisons
- **Total**: O(N) where N = number of simulations
- **Parallel**: O(N/T) where T = thread count

#### Space Complexity
- O(52) for deck representation
- O(1) for result accumulation

#### Convergence Rate

The margin of error decreases with √N:

```
Margin ∝ 1/√N
```

| Simulations | Approximate Margin (95% CI) |
|-------------|----------------------------|
| 100 | ±10% |
| 400 | ±5% |
| 1,600 | ±2.5% |
| 10,000 | ±1% |

## Statistical Validation

### Properties

1. **Unbiased Estimator**: E[p̂] = p (expected value equals true probability)
2. **Consistent**: p̂ → p as N → ∞
3. **Asymptotically Normal**: For large N, p̂ ~ N(p, σ²)

### Assumptions

1. **Independence**: Each simulation is independent
2. **Identically Distributed**: Opponent hands are uniformly random
3. **Large N Approximation**: N > 30 for normal approximation validity

## Decision-Making Framework

### Call/Fold Threshold

The bot uses a **40% win rate threshold**:

```
Decision = {
    CALL  if p̂ ≥ 0.40
    FOLD  if p̂ < 0.40
}
```

### Risk-Adjusted Decision (Future Enhancement)

Using the confidence interval lower bound for conservative play:

```
Conservative Decision = {
    CALL  if p̂_lower ≥ 0.40
    FOLD  otherwise
}
```

Where `p̂_lower = p̂ - 1.96σ` (95% confidence)

## Example Scenarios

### Scenario 1: Strong Position

**Setup**: Pocket Aces, flop shows 2-7-9 rainbow
- Simulations: 200
- Win Rate: 85%
- Standard Deviation: 2.5%
- 95% CI: [80.1%, 89.9%]
- **Decision**: CALL (high confidence)

### Scenario 2: Marginal Hand

**Setup**: K-Q unsuited, flop shows A-8-3
- Simulations: 200
- Win Rate: 42%
- Standard Deviation: 3.5%
- 95% CI: [35.1%, 48.9%]
- **Decision**: CALL (but close, high variance)

### Scenario 3: Weak Position

**Setup**: 7-4 offsuit, flop shows A-K-J
- Simulations: 200
- Win Rate: 18%
- Standard Deviation: 2.7%
- 95% CI: [12.7%, 23.3%]
- **Decision**: FOLD (low confidence)

## Comparison with Analytical Methods

| Method | Accuracy | Speed | Complexity |
|--------|----------|-------|------------|
| Monte Carlo (N=200) | ~±7% | Fast | Low |
| Monte Carlo (N=10K) | ~±1% | Slow | Low |
| Combinatorial | Exact | Moderate | High |
| Lookup Tables | Exact | Very Fast | Very High (memory) |

**Trade-off**: Monte Carlo provides good approximations with minimal code complexity and no pre-computation.

## Future Improvements

### 1. Adaptive Sampling
Automatically adjust N based on variance:
```cpp
while (confidence_width > threshold && N < max_sims) {
    run_more_simulations();
}
```

### 2. Importance Sampling
Weight simulations based on opponent playing style.

### 3. Variance Reduction
- **Antithetic Variates**: Use complementary random numbers
- **Control Variates**: Use known expected values
- **Stratified Sampling**: Sample uniformly across hand ranges

### 4. Sequential Testing
Stop simulation early if result is clear:
```cpp
if (wins / trials > 0.9) {
    return CALL;  // Already confident
}
```

## References

1. **Simulation Theory**: Law, A. M. (2015). *Simulation Modeling and Analysis*
2. **Poker Mathematics**: Chen & Ankenman (2006). *The Mathematics of Poker*
3. **Monte Carlo Methods**: Metropolis, N. (1987). *The Beginning of the Monte Carlo Method*
4. **Statistical Inference**: Wasserman, L. (2004). *All of Statistics*

## Validation

See `tests/test_monte_carlo.cpp` for empirical validation of:
- Confidence interval coverage
- Standard deviation accuracy
- Convergence properties
- Edge case handling

---

**Key Insight**: With 2000 simulations the 95% interval is about ±1.4%. Note that sampling error is not the dominant error: the simulator assumes a uniformly random opponent holding, which overstates equity by roughly 13 percentage points against a tight range. See "Known limitations" below.

---

## Known limitations

### The opponent is modelled as a uniformly random hand

`MonteCarloSimulator` deals the opponent two cards at random from the unseen
deck. Every one of the 1326 starting combinations is equally likely. A real
opponent folds weak hands, so a player still betting on the river holds a
much stronger distribution than that.

Measured over 3000 random river spots, with all opponent holdings enumerated
exactly and restricted by **preflop** hand strength:

| Opponent range | Mean equity | vs uniform | Decision flips @33% pot odds |
|---|---|---|---|
| All hands (what the simulator assumes) | 0.508 | — | — |
| Top 40% | 0.412 | −0.096 | 13.0% |
| Top 25% | 0.380 | −0.128 | 16.9% |
| Top 15% | 0.348 | −0.160 | 22.2% |

The bias is systematic and one-directional: the bot overestimates its equity
and therefore calls too often. Against a top-25% range it is about **13
percentage points optimistic**, which flips the call/fold decision in roughly
**one spot in six**.

For comparison, sampling error at 2000 trials is ±1.4 points. The modelling
assumption costs about nine times more than the sampling noise, so increasing
the trial count — or parallelising it — chases the smaller of the two errors.

Fixing this requires range modelling: weighting opponent holdings by how
likely that opponent was to have played them, and updating those weights as
betting actions are observed. That is a feature, not a tuning change.

### Heads-up only

`dealRandomOpponentAndBoard` deals exactly one opponent. This matches the
game, which is one human against one bot, but the equity figures do not
generalise to multiway pots.
