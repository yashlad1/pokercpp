#ifndef SPINNER_H
#define SPINNER_H

#include <atomic>

class Spinner
{
public:
    // Runs until `done` becomes true. Caller sets it to stop the animation.
    static void show(std::atomic<bool> &done);
};

#endif