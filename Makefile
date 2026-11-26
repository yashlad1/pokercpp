CXX = clang++
CXXFLAGS = -std=c++17 -Wall -Wextra

# Extra diagnostics used by the `strict` and `test-asan` targets. Kept out of
# the default build so day-to-day compiles stay quiet.
STRICTFLAGS = -Wshadow -Wconversion -Wsign-conversion -Wnon-virtual-dtor -Wcast-qual
SANFLAGS = -fsanitize=address,undefined -fno-omit-frame-pointer -g

# Plain `make` runs the tests.
.DEFAULT_GOAL := test

# The sources the Chipzen engine compiles (tools/build_engine.sh adds only the
# Python wrapper). Tests that need more than the evaluator link all of them.
ENGINE_SRC = model/card.cpp \
             model/advanced_hand_evaluator.cpp \
             montecarlo/MonteCarloSimulator.cpp

TEST_MC = tests/test_monte_carlo
TEST_HAND = tests/test_hand_evaluator
TEST_EQUITY = tests/test_equity_exact
TEST_PROPS = tests/test_decide_properties
TEST_EXHAUSTIVE = tests/test_eval_exhaustive

# Test targets
test_monte_carlo: tests/test_monte_carlo.cpp $(ENGINE_SRC)
	$(CXX) $(CXXFLAGS) tests/test_monte_carlo.cpp $(ENGINE_SRC) -o $(TEST_MC)
	./$(TEST_MC)

test_hand_evaluator: tests/test_hand_evaluator.cpp model/advanced_hand_evaluator.cpp model/card.cpp
	$(CXX) $(CXXFLAGS) tests/test_hand_evaluator.cpp model/advanced_hand_evaluator.cpp model/card.cpp -o $(TEST_HAND)
	./$(TEST_HAND)

# Ground truth for the equity engine: counts every case where the simulator
# samples. Pass --slow for the preflop and flop enumerations (~12s).
test_equity_exact: tests/test_equity_exact.cpp $(ENGINE_SRC)
	$(CXX) $(CXXFLAGS) tests/test_equity_exact.cpp $(ENGINE_SRC) -o $(TEST_EQUITY)
	./$(TEST_EQUITY)

# Properties of chipzen/decide.h: chip scaling, price and range monotonicity.
test_decide_properties: tests/test_decide_properties.cpp chipzen/decide.h $(ENGINE_SRC)
	$(CXX) $(CXXFLAGS) tests/test_decide_properties.cpp $(ENGINE_SRC) -o $(TEST_PROPS)
	./$(TEST_PROPS)

# Counts all 133,784,560 seven-card hands against the published category totals.
# Built with -O2: ~2.5s optimised, ~19s without.
test_eval_exhaustive: tests/test_eval_exhaustive.cpp model/fast_eval.h model/advanced_hand_evaluator.cpp model/card.cpp
	$(CXX) $(CXXFLAGS) -O2 tests/test_eval_exhaustive.cpp model/advanced_hand_evaluator.cpp model/card.cpp -o $(TEST_EXHAUSTIVE)
	./$(TEST_EXHAUSTIVE)

# Run all tests
test: test_hand_evaluator test_monte_carlo test_equity_exact test_decide_properties test_eval_exhaustive
	@echo "\n=== All Tests Passed ==="

# Every test binary rebuilt with AddressSanitizer + UndefinedBehaviorSanitizer.
# Catches the class of bug that hid in this codebase for a long time: reading
# past the end of a vector after an unsigned loop bound underflowed.
ASAN_DIR = build-asan
test-asan:
	@mkdir -p $(ASAN_DIR)
	$(CXX) $(CXXFLAGS) $(SANFLAGS) tests/test_hand_evaluator.cpp model/advanced_hand_evaluator.cpp model/card.cpp -o $(ASAN_DIR)/test_hand_evaluator
	$(CXX) $(CXXFLAGS) $(SANFLAGS) tests/test_monte_carlo.cpp $(ENGINE_SRC) -o $(ASAN_DIR)/test_monte_carlo
	$(CXX) $(CXXFLAGS) $(SANFLAGS) tests/test_decide_properties.cpp $(ENGINE_SRC) -o $(ASAN_DIR)/test_decide_properties
	@echo "\n--- running under ASan/UBSan ---"
	./$(ASAN_DIR)/test_hand_evaluator > /dev/null && echo "  hand_evaluator: clean"
	./$(ASAN_DIR)/test_monte_carlo   > /dev/null && echo "  monte_carlo:    clean"
	./$(ASAN_DIR)/test_decide_properties > /dev/null && echo "  decide_props:   clean"
	@echo "\n=== No sanitizer findings ==="

# Compile-only pass with the noisier warning set.
strict:
	$(CXX) $(CXXFLAGS) $(STRICTFLAGS) -fsyntax-only $(ENGINE_SRC)
	@echo "=== Strict warning pass clean ==="

.PHONY: test test_decide_properties test_eval_exhaustive test-asan strict clean

clean:
	rm -f $(TEST_MC) $(TEST_HAND) $(TEST_EQUITY) $(TEST_PROPS) $(TEST_EXHAUSTIVE)
	rm -rf $(ASAN_DIR)