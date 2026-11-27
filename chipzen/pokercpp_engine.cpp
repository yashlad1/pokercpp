// Python extension wrapping the C++ decision engine. The platform sandbox blocks subprocess and ctypes,
// so a compiled extension is the supported route.

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
                       int stack, int bb, int sims, int villainRaises,
                       double realizationScale, bool bluffEnabled,
                       double rangeFloor, unsigned long long seed,
                       double preflopRealization, int villainCalls, double callNarrow) {
    if (hole.size() != 2) {
        throw std::invalid_argument("need exactly 2 hole cards");
    }
    std::vector<Card> h = parseCards(hole);
    std::vector<Card> b = parseCards(board);
    if (sims <= 0) sims = 5000;

    chipzen::Decision d;
    {
        // No Python objects are touched: release the GIL so the WebSocket heartbeat keeps running.
        py::gil_scoped_release release;
        d = chipzen::decideFull(h, b, pot, toCall, minRaise, maxRaise, stack, bb,
                                sims, villainRaises, realizationScale, bluffEnabled,
                                rangeFloor, seed, preflopRealization, villainCalls, callNarrow);
    }

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

#ifndef POKERCPP_GIT_SHA
#define POKERCPP_GIT_SHA "unknown"
#endif

static py::dict build_info() {
    py::dict d;
    d["git_sha"] = std::string(POKERCPP_GIT_SHA);
    d["preflop_realization"] = chipzen::kPreflopRealization;
    d["call_narrow"] = chipzen::kCallNarrow;
    return d;
}

PYBIND11_MODULE(pokercpp_engine, m) {
    m.def("build_info", &build_info, "git_sha, preflop_realization and call_narrow this engine was built with.");
    m.doc() = "Monte Carlo poker decision engine (C++)";
    m.def("decide", &decide,
          py::arg("hole"), py::arg("board"), py::arg("pot"), py::arg("to_call"),
          py::arg("min_raise"), py::arg("max_raise"), py::arg("stack"),
          py::arg("bb"), py::arg("sims") = 5000, py::arg("villain_raises") = 0,
          py::arg("realization_scale") = 1.0, py::arg("bluff_enabled") = true,
          py::arg("range_floor") = 0.0, py::arg("seed") = 0ULL,
          py::arg("preflop_realization") = chipzen::kPreflopRealization,
          py::arg("villain_calls") = 0, py::arg("call_narrow") = chipzen::kCallNarrow,
          "Return 'fold', 'check', 'call' or 'raise <total>' for the given spot.");
}
