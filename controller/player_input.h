#ifndef PLAYER_INPUT_H
#define PLAYER_INPUT_H

#include <deque>
#include <iostream>
#include <string>

/**
 * Source of the human player's decisions.
 *
 * The controller used to read std::cin inline, which meant a betting round
 * could not run without a terminal attached. Nothing about the round flow -
 * pot accounting, folds, all-ins, uncalled bets - was reachable from a test.
 * Routing input through this interface lets tests drive a full hand with a
 * scripted sequence of actions.
 */
class PlayerInput
{
public:
    virtual ~PlayerInput() = default;

    // One of "check", "bet" or "fold".
    virtual std::string requestAction() = 0;

    // One of "call" or "fold", asked when the bot has bet.
    virtual std::string requestCallResponse() = 0;

    // "yes"/"no" after a hand completes.
    virtual std::string requestAnotherRound() = 0;

    // Difficulty name, re-asked until it parses.
    virtual bool requestDifficulty(std::string &out) = 0;

    // Pause between streets. A no-op when there is no human watching.
    virtual void waitForContinue() = 0;
};

/** Reads from standard input. */
class ConsoleInput : public PlayerInput
{
public:
    std::string requestAction() override { return readToken(); }
    std::string requestCallResponse() override { return readToken(); }
    std::string requestAnotherRound() override { return readToken(); }

    bool requestDifficulty(std::string &out) override
    {
        return static_cast<bool>(std::cin >> out);
    }

    void waitForContinue() override
    {
        std::cin.ignore();
    }

private:
    static std::string readToken()
    {
        std::string token;
        if (!(std::cin >> token))
        {
            return "fold";  // EOF: end the hand rather than spin forever
        }
        return token;
    }
};

/**
 * Replays a fixed list of responses. Used by tests to play a whole hand
 * without a terminal; exhausting the script folds so nothing can hang.
 */
class ScriptedInput : public PlayerInput
{
public:
    explicit ScriptedInput(std::deque<std::string> responses)
        : script(std::move(responses)) {}

    std::string requestAction() override { return next("fold"); }
    std::string requestCallResponse() override { return next("fold"); }
    std::string requestAnotherRound() override { return next("no"); }

    bool requestDifficulty(std::string &out) override
    {
        if (script.empty()) return false;
        out = next("medium");
        return true;
    }

    void waitForContinue() override {}

    bool exhausted() const { return script.empty(); }

private:
    std::string next(const std::string &fallback)
    {
        if (script.empty()) return fallback;
        std::string v = script.front();
        script.pop_front();
        return v;
    }

    std::deque<std::string> script;
};

#endif // PLAYER_INPUT_H
