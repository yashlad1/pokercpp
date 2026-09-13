# syntax=docker/dockerfile:1.7
#
# pokercpp bot image.
#
# Two stages: the first compiles the C++ equity engine into a Python
# extension module, the second ships only that .so plus the wire adapter.
# No toolchain reaches the runtime image.
#
# The engine is linked into Python rather than run as a separate process
# because the platform sandbox blocks `subprocess` and `ctypes` alike.
#
# Both stages use the same python:3.11-alpine base on purpose: a CPython
# extension is tied to the interpreter's ABI, so a mismatch here would fail
# at import, in the container, after upload.
#
# Build from the REPO ROOT, not this directory, and target amd64 — the
# platform runs x86-64, and an arm64 image built on Apple Silicon will not
# start there:
#   docker build --platform linux/amd64 -f chipzen/Dockerfile -t pokercpp:v1 .
#   docker save pokercpp:v1 | gzip > pokercpp.tar.gz

FROM python:3.11-alpine AS builder

RUN apk add --no-cache g++ musl-dev \
    && pip install --no-cache-dir pybind11

WORKDIR /build
COPY model/ ./model/
COPY montecarlo/ ./montecarlo/
COPY chipzen/decide.h chipzen/pokercpp_engine.cpp ./chipzen/

# libstdc++ is linked statically: the runtime stage installs no compiler, so
# the shared one is not there to find.
RUN g++ -std=c++17 -O2 -shared -fPIC \
        -static-libstdc++ -static-libgcc \
        $(python -m pybind11 --includes) \
        chipzen/pokercpp_engine.cpp \
        montecarlo/MonteCarloSimulator.cpp \
        model/advanced_hand_evaluator.cpp \
        model/card.cpp \
        model/deck.cpp \
        -o /pokercpp_engine$(python3-config --extension-suffix) \
    && strip /pokercpp_engine*.so

FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /bot

RUN pip install chipzen-bot \
    && rm -rf /root/.cache \
    && find /usr/local/lib/python3.11 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

COPY --from=builder /pokercpp_engine*.so /bot/
COPY chipzen/bot.py /bot/bot.py

RUN adduser -D -u 10001 -s /bin/sh bot && chown -R bot:bot /bot
USER bot

ENTRYPOINT ["python", "-u", "/bot/bot.py"]
