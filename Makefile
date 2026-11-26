CXX = clang++
CXXFLAGS = -std=c++17 -Wall -Wextra

# Extra diagnostics used by the `strict` and `test-asan` targets. Kept out of
# the default build so day-to-day compiles stay quiet.
STRICTFLAGS = -Wshadow -Wconversion -Wsign-conversion -Wnon-virtual-dtor -Wcast-qual
SANFLAGS = -fsanitize=address,undefined -fno-omit-frame-pointer -g
SRC = main.cpp \
      controller/poker_controller.cpp \
      view/cli_view.cpp \
      view/ascii_art.cpp \
      view/bot_thinking_visualizer.cpp \
      view/bot_thinking_config.cpp \
      model/card.cpp model/deck.cpp model/player.cpp \
      model/advanced_hand_evaluator.cpp \
      model/bot_player.cpp \
      animation/spinner.cpp \
      animation/card_animation.cpp \
      montecarlo/MonteCarloSimulator.cpp \
      utils/performance_monitor.cpp \
      utils/game_logger.cpp

# Core model/library files (no main.cpp)
LIB_SRC = model/card.cpp model/deck.cpp model/player.cpp \
          model/advanced_hand_evaluator.cpp \
          model/bot_player.cpp \
          montecarlo/MonteCarloSimulator.cpp \
          utils/performance_monitor.cpp \
          utils/game_logger.cpp \
          view/bot_thinking_visualizer.cpp \
          view/bot_thinking_config.cpp

# View and animation sources the controller pulls in. Named once so the test
# targets do not have to repeat the list.
VIEW_SRC = controller/poker_controller.cpp view/cli_view.cpp view/ascii_art.cpp \
           animation/spinner.cpp animation/card_animation.cpp

TARGET = poker
TEST_MC = tests/test_monte_carlo
TEST_HAND = tests/test_hand_evaluator
TEST_GAME = tests/test_game_logic
TEST_EQUITY = tests/test_equity_exact
TEST_PROPS = tests/test_decide_properties
TEST_EXHAUSTIVE = tests/test_eval_exhaustive
TEST_ORDER = tests/test_eval_order

# Main game target
$(TARGET): $(SRC)
	$(CXX) $(CXXFLAGS) $(SRC) -o $(TARGET)

# Test targets
test_monte_carlo: tests/test_monte_carlo.cpp $(LIB_SRC)
	$(CXX) $(CXXFLAGS) tests/test_monte_carlo.cpp $(LIB_SRC) -o $(TEST_MC)
	./$(TEST_MC)

test_hand_evaluator: tests/test_hand_evaluator.cpp model/advanced_hand_evaluator.cpp model/card.cpp
	$(CXX) $(CXXFLAGS) tests/test_hand_evaluator.cpp model/advanced_hand_evaluator.cpp model/card.cpp -o $(TEST_HAND)
	./$(TEST_HAND)

test_game_logic: tests/test_game_logic.cpp $(LIB_SRC) $(VIEW_SRC)
	$(CXX) $(CXXFLAGS) tests/test_game_logic.cpp $(LIB_SRC) $(VIEW_SRC) -o $(TEST_GAME)
	./$(TEST_GAME)

# Ground truth for the equity engine: counts every case where the simulator
# samples. Pass --slow for the preflop and flop enumerations (~12s).
test_equity_exact: tests/test_equity_exact.cpp $(LIB_SRC)
	$(CXX) $(CXXFLAGS) tests/test_equity_exact.cpp $(LIB_SRC) -o $(TEST_EQUITY)
	./$(TEST_EQUITY)

# Properties of chipzen/decide.h: chip scaling, price and range monotonicity.
test_decide_properties: tests/test_decide_properties.cpp chipzen/decide.h $(LIB_SRC)
	$(CXX) $(CXXFLAGS) tests/test_decide_properties.cpp $(LIB_SRC) -o $(TEST_PROPS)
	./$(TEST_PROPS)

# Counts all 133,784,560 seven-card hands against the published category totals.
# Built with -O2: ~2.5s optimised, ~19s without.
test_eval_exhaustive: tests/test_eval_exhaustive.cpp model/fast_eval.h model/advanced_hand_evaluator.cpp model/card.cpp
	$(CXX) $(CXXFLAGS) -O2 tests/test_eval_exhaustive.cpp model/advanced_hand_evaluator.cpp model/card.cpp -o $(TEST_EXHAUSTIVE)
	./$(TEST_EXHAUSTIVE)

# Score order over all 2,598,960 five-card hands against a rules-built key, plus 7 vs best-of-5.
test_eval_order: tests/test_eval_order.cpp model/fast_eval.h model/advanced_hand_evaluator.cpp model/card.cpp
	$(CXX) $(CXXFLAGS) -O2 tests/test_eval_order.cpp model/advanced_hand_evaluator.cpp model/card.cpp -o $(TEST_ORDER)
	./$(TEST_ORDER)

# Run all tests
test: test_hand_evaluator test_monte_carlo test_game_logic test_equity_exact test_decide_properties test_eval_exhaustive test_eval_order
	@echo "\n=== All Tests Passed ==="

# Every test binary rebuilt with AddressSanitizer + UndefinedBehaviorSanitizer.
# Catches the class of bug that hid in this codebase for a long time: reading
# past the end of a vector after an unsigned loop bound underflowed.
ASAN_DIR = build-asan
test-asan:
	@mkdir -p $(ASAN_DIR)
	$(CXX) $(CXXFLAGS) $(SANFLAGS) tests/test_hand_evaluator.cpp model/advanced_hand_evaluator.cpp model/card.cpp -o $(ASAN_DIR)/test_hand_evaluator
	$(CXX) $(CXXFLAGS) $(SANFLAGS) tests/test_monte_carlo.cpp $(LIB_SRC) -o $(ASAN_DIR)/test_monte_carlo
	$(CXX) $(CXXFLAGS) $(SANFLAGS) tests/test_game_logic.cpp $(LIB_SRC) $(VIEW_SRC) -o $(ASAN_DIR)/test_game_logic
	$(CXX) $(CXXFLAGS) $(SANFLAGS) tests/test_decide_properties.cpp $(LIB_SRC) -o $(ASAN_DIR)/test_decide_properties
	@echo "\n--- running under ASan/UBSan ---"
	./$(ASAN_DIR)/test_hand_evaluator > /dev/null && echo "  hand_evaluator: clean"
	./$(ASAN_DIR)/test_monte_carlo   > /dev/null && echo "  monte_carlo:    clean"
	./$(ASAN_DIR)/test_game_logic    > /dev/null && echo "  game_logic:     clean"
	./$(ASAN_DIR)/test_decide_properties > /dev/null && echo "  decide_props:   clean"
	@echo "\n=== No sanitizer findings ==="

# Compile-only pass with the noisier warning set.
strict:
	$(CXX) $(CXXFLAGS) $(STRICTFLAGS) -fsyntax-only $(SRC)
	@echo "=== Strict warning pass clean ==="

run: $(TARGET)
	./$(TARGET)

.PHONY: test test_decide_properties test_eval_exhaustive test_eval_order test-asan strict run clean

clean:
	rm -f $(TARGET) $(TEST_MC) $(TEST_HAND) $(TEST_GAME) $(TEST_EQUITY) $(TEST_PROPS) $(TEST_EXHAUSTIVE) $(TEST_ORDER)
	rm -rf $(ASAN_DIR)