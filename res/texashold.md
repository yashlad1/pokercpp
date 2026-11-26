# ♠️ How to Play Texas Hold'em Poker

This document explains **how to play poker**.

---

## 🎯 Objective

Each player tries to make the **best possible 5-card hand** using:
- **2 private cards** (hole cards) dealt to them
- **5 shared community cards** on the table

The player with the **best hand at showdown**, or the last player remaining after others fold, wins the **pot** (all the chips bet during the round).

---

## 🔁 Game Flow

1. **Pre-Flop**:  
   Each player is dealt 2 private cards (hole cards)

2. **The Flop**:  
   3 community cards are placed face-up in the center

3. **The Turn**:  
   A fourth community card is revealed

4. **The River**:  
   A fifth and final community card is revealed

5. **The Showdown**:  
   Players reveal their hands, and the best 5-card hand wins

---

## 🃏 Hand Rankings (Best to Worst)

| Rank               | Description                      | Example                      |
|--------------------|----------------------------------|------------------------------|
| Royal Flush        | A, K, Q, J, 10 — all same suit   | A♠ K♠ Q♠ J♠ 10♠              |
| Straight Flush     | 5 cards in order, same suit      | 6♣ 7♣ 8♣ 9♣ 10♣              |
| Four of a Kind     | 4 cards of the same rank         | 9♦ 9♠ 9♥ 9♣ 2♦              |
| Full House         | 3 of a kind + 1 pair             | Q♣ Q♥ Q♠ 5♦ 5♠              |
| Flush              | 5 cards of same suit             | 2♠ 5♠ 8♠ J♠ K♠              |
| Straight           | 5 cards in sequence              | 5♣ 6♦ 7♥ 8♠ 9♦              |
| Three of a Kind    | 3 cards of same rank             | 7♣ 7♥ 7♠ Q♦ 2♥              |
| Two Pair           | 2 pairs of cards                 | 10♠ 10♦ 4♠ 4♥ 6♣            |
| One Pair           | A single pair                    | K♣ K♠ 5♠ 8♦ 2♠              |
| High Card          | No combination — highest wins    | A♦ 7♣ 5♠ 4♥ 2♣              |

---

## 🧠 Betting Options at Each Stage

- **Check**: Do nothing if no bet has been made
- **Bet**: Place chips into the pot
- **Call**: Match another player's bet
- **Raise**: Increase the amount of the current bet
- **Fold**: Surrender your hand and exit the round

---

## 👀 Example Round (You vs Bot)

- You: [A♠, K♠]  
- Bot: [10♦, 9♦]

**Flop**: [J♠, Q♠, 5♣]  
**Turn**: [10♠]  
**River**: [2♥]

- You now have an **Ace-high flush**
- Bot has just a **pair of tens**

✅ You win!

---

## 💡 Beginner Strategy

| Situation                     | Action           |
|------------------------------|------------------|
| Strong hand (e.g., top pair) | Bet or Raise     |
| Weak hand                    | Fold             |
| Drawing (e.g., flush draw)   | Call or Raise    |
| Everyone checked             | Consider bluffing|

---

## 🚀 Coming Soon in Code

- `Card`, `Deck`, and `Player` classes (you’ve already implemented!)
- `Game` engine to control the round flow
- A smart `Bot` opponent with simple poker strategy
- A `HandEvaluator` to determine the winner at showdown

---