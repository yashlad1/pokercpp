#!/bin/bash
# Local build of the C++ engine as a Python extension. Run from the repo root.
#   PY=/path/to/python tools/build_engine.sh [default|native] [--metal]
# default = the plain -O2 build; native adds -O3 -mcpu=apple-m4 -flto (local only,
# the Docker image keeps its own flags).
set -e
: "${PY:?set PY to the python that has pybind11 installed}"
MODE=default; METAL=
for a in "$@"; do
  case $a in
    default|native) MODE=$a ;;
    --metal) METAL=1 ;;
    *) echo "usage: $0 [default|native] [--metal]" >&2; exit 2 ;;
  esac
done
FLAGS="-std=c++17 -O2"
if [ "$MODE" = native ]; then
  CPU=-mcpu=apple-m4
  echo 'int main(){}' | clang++ $CPU -x c++ - -o /dev/null 2>/dev/null || CPU=-mcpu=native
  echo "native cpu flag: $CPU" >&2
  FLAGS="-std=c++17 -O3 $CPU -flto"
fi
SRC="chipzen/pokercpp_engine.cpp montecarlo/MonteCarloSimulator.cpp model/advanced_hand_evaluator.cpp model/card.cpp"
EXTRA=
[ -n "$METAL" ] && { EXTRA="-DUSE_METAL -fobjc-arc"; SRC="$SRC montecarlo/metal/MetalEquity.mm"; EXTRA="$EXTRA -framework Metal -framework Foundation"; }
SHA=$(git rev-parse --short HEAD 2>/dev/null || true)
if [ -n "$SHA" ]; then
  git diff --quiet HEAD -- chipzen/ montecarlo/ model/ || SHA="$SHA-dirty"
  EXTRA="$EXTRA -DPOKERCPP_GIT_SHA=\"$SHA\""
fi
EXT=$("$PY" -c 'import sysconfig;print(sysconfig.get_config_var("EXT_SUFFIX"))')
clang++ $FLAGS -shared -fPIC -undefined dynamic_lookup $("$PY" -m pybind11 --includes) $EXTRA $SRC -o "chipzen/pokercpp_engine$EXT"
echo "built chipzen/pokercpp_engine$EXT ($MODE)"
