#include "game_logger.h"

// Initialize static members
std::ofstream GameLogger::logFile;
bool GameLogger::initialized = false;
int GameLogger::handNumber = 0;
std::string GameLogger::sessionId;
std::string GameLogger::filePath = "/tmp/poker_game_log.csv";
