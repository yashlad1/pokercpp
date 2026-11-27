# syntax=docker/dockerfile:1.7
#
# Both stages share one base: the extension is tied to the interpreter's ABI.
#
# Build from the repo root for amd64 (the platform runs x86-64):
#   docker build --platform linux/amd64 -f chipzen/Dockerfile -t pokercpp:v1 .
#   docker save pokercpp:v1 | gzip > pokercpp.tar.gz

FROM python:3.11-alpine AS builder

RUN apk add --no-cache g++ musl-dev \
    && pip install --no-cache-dir pybind11

WORKDIR /build
COPY model/ ./model/
COPY montecarlo/ ./montecarlo/
COPY chipzen/decide.h chipzen/pokercpp_engine.cpp ./chipzen/

ARG GIT_SHA=unknown

# libstdc++ is linked statically: the runtime stage installs no compiler, so
# the shared one is not there to find.
RUN g++ -std=c++17 -O2 -shared -fPIC \
        -DPOKERCPP_GIT_SHA=\"$GIT_SHA\" \
        -static-libstdc++ -static-libgcc \
        $(python -m pybind11 --includes) \
        chipzen/pokercpp_engine.cpp \
        montecarlo/MonteCarloSimulator.cpp \
        model/advanced_hand_evaluator.cpp \
        model/card.cpp \
        -o /pokercpp_engine$(python3-config --extension-suffix) \
    && strip /pokercpp_engine*.so

FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /bot

# Pinned: an unpinned build picks up a newer SDK, which changed the validator once.
RUN pip install chipzen-bot==0.7.1 \
    && rm -rf /root/.cache \
    && find /usr/local/lib/python3.11 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

COPY --from=builder /pokercpp_engine*.so /bot/
# Dockerfile and .dockerignore are copied only for `chipzen-sdk validate .`.
COPY chipzen/bot.py chipzen/opponent.py chipzen/Dockerfile chipzen/.dockerignore /bot/

ARG GIT_SHA=unknown
ENV POKERCPP_COMMIT=$GIT_SHA

RUN adduser -D -u 10001 -s /bin/sh bot && chown -R bot:bot /bot
USER bot

ENTRYPOINT ["python", "-u", "/bot/bot.py"]
