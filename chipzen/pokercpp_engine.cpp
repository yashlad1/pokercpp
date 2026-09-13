// Python extension wrapping the C++ decision engine.
//
// The platform sandbox blocks both `subprocess` and `ctypes`, so a Python
// bot cannot shell out to a binary or dlopen one. A compiled extension is
// the supported route — the SDK's own starter ships its strategy the same
// way, as a Cython .so — and it is faster than a subprocess besides: no
// process spawn, no pipe, no timeout supervision.

#include "decide.h"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <stdexcept>
#include <string>
#include <vector>

namespace py = pybind11;

static std::vector<Card> parseCards(const std::vector<std::string> &strs) {
    std::vector<Card> out;
    out.reserve(strs.size());
    for (const std::string &s : strs) {
        Card c(Rank::Two, Suit::Clubs);
        if (!chipzen::parseCard(s, c)) {
            throw std::invalid_argument("bad card: " + s);
        }
        out.push_back(c);
    }
    return out;
}

static py::dict decide(const std::vector<std::string> &hole,
                       const std::vector<std::string> &board,
                       int pot, int toCall, int minRaise, int maxRaise,
                       int stack, int bb, int sims, int villainRaises) {
    if (hole.size() != 2) {
        throw std::invalid_argument("need exactly 2 hole cards");
    }
    std::vector<Card> h = parseCards(hole);
    std::vector<Card> b = parseCards(board);
    if (sims <= 0) sims = 5000;

    chipzen::Decision d;
    {
        // The simulation touches no Python objects, so drop the GIL for it.
        // The SDK calls decide() from an async loop; holding the GIL through
        // a 12 ms simulation would stall the WebSocket heartbeat.
        py::gil_scoped_release release;
        d = chipzen::decideFull(h, b, pot, toCall, minRaise, maxRaise, stack, bb,
                                sims, villainRaises);
    }

    // The numbers come back with the choice so a fold can be explained from
    // the match log instead of guessed at.
    py::dict out;
    out["action"] = d.action;
    out["amount"] = d.amount;
    out["equity"] = d.equity;
    out["realized"] = d.realized;
    out["range"] = d.range;
    out["bluff"] = d.bluff;
    out["required"] = d.required;
    return out;
}

PYBIND11_MODULE(pokercpp_engine, m) {
    m.doc() = "Monte Carlo poker decision engine (C++)";
    m.def("decide", &decide,
          py::arg("hole"), py::arg("board"), py::arg("pot"), py::arg("to_call"),
          py::arg("min_raise"), py::arg("max_raise"), py::arg("stack"),
          py::arg("bb"), py::arg("sims") = 5000, py::arg("villain_raises") = 0,
          "Return 'fold', 'check', 'call' or 'raise <total>' for the given spot.");
}
