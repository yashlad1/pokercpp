#include "spinner.h"
#include <iostream>
#include <thread>
#include <chrono>

// Spins until `done` is set by the calling thread. The parameter is the
// completion flag, not a "keep running" flag - the loop continues while it is
// still false.
void Spinner::show(std::atomic<bool> &done)
{
    const char frames[] = {'|', '/', '-', '\\'};
    const int frameCount = static_cast<int>(sizeof(frames) / sizeof(frames[0]));
    int i = 0;

    while (!done.load())
    {
        // Must be modulo, not a bitwise AND. `i & 4` yields only 0 or 4, and
        // 4 was past the end of the old 3-element array - a stack read
        // overflow on every other frame.
        std::cout << "\rBot is thinking 🤔... " << frames[i % frameCount] << std::flush;
        i = (i + 1) % frameCount;
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    std::cout << "\rBot is thinking 🤔... Done!     \n";
}