"""Run the per-street luck tool (slumbot_luck.py at fec2a10, PR for #190 P1b) with the preflop Monte Carlo cut from 20,000 to 1,000 boards. Tool file untouched.

Usage: PYTHONPATH=chipzen python results/2026-11-28-slumbot-overnight-scripts/luck_p1b_1000.py TOOLS_DIR LOG [LOG ...] [--out FILE.json]
  TOOLS_DIR is the tools/ folder of a checkout at fec2a10. Output is deterministic (seeded).
"""
import multiprocessing
import sys

if __name__ == "__main__":
    sys.path.insert(0, sys.argv.pop(1))
    import slumbot_luck as L
    multiprocessing.set_start_method("fork")  # so the pool workers see the changed constant
    L.MC_BOARDS = 1000
    L.main()
