# syntax=docker/dockerfile:1.7
#
# pokercpp bot image.
#
# Two stages: the first compiles the C++ equity solver against the sources
# in this repo, the second ships only the static binary plus the Python
# wire adapter. No toolchain reaches the runtime image.
#
# Build from the REPO ROOT, not this directory:
#   docker build -f chipzen/Dockerfile -t pokercpp:v1 .
#   docker save pokercpp:v1 | gzip > pokercpp.tar.gz

FROM alpine:3.20 AS builder

RUN apk add --no-cache g++ musl-dev

WORKDIR /build
COPY model/ ./model/
COPY montecarlo/ ./montecarlo/
COPY chipzen/solver.cpp ./chipzen/

# Statically linked so the runtime stage needs no libstdc++ at all.
RUN g++ -std=c++17 -O2 -static -o /solver \
        chipzen/solver.cpp \
        montecarlo/MonteCarloSimulator.cpp \
        model/advanced_hand_evaluator.cpp \
        model/card.cpp \
        model/deck.cpp \
    && strip /solver

FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POKERCPP_SOLVER=/bot/solver

WORKDIR /bot

RUN pip install chipzen-bot \
    && rm -rf /root/.cache \
    && find /usr/local/lib/python3.11 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

COPY --from=builder /solver /bot/solver
COPY chipzen/bot.py /bot/bot.py

RUN adduser -D -u 10001 -s /bin/sh bot && chown -R bot:bot /bot
USER bot

ENTRYPOINT ["python", "-u", "/bot/bot.py"]
