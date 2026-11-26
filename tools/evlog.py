"""Append one run to the evaluation log workbook (results/eval-log.xlsx).

    python tools/evlog.py paired  LOG.xlsx A.json B.json --experiment X --comparison "..."
                          --build-a ... --build-b ... --logic "..." [--hero engine|bot]
                          [--history ...] [--sims N] [--path CPU|Metal] [--wall-s S] [--notes ...]
    python tools/evlog.py match   LOG.xlsx match.log --experiment X --build B --schedule 25
                          [--wall-s S] [--dump match.json [--vs-dump other.json]]
    python tools/evlog.py timing  LOG.xlsx --operation "..." --build B --hands N --sims N
                          --path CPU|Metal --wall-s S [--notes ...]

Needs openpyxl. The paired maths is tools/paired.py's bb100_ci. Date-time is now, Eastern.
Hardware is the chip, RAM and macOS version only. Summary formulas are left untouched;
a new experiment name gets its own Summary row.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from zoneinfo import ZoneInfo

from openpyxl import load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from paired import bb100_ci

ET = ZoneInfo("America/New_York")
NR = "not recorded"
DT_FMT = "yyyy-mm-dd hh:mm"

HEADERS = {
    "Runs": ["Run ID", "Date-time (ET)", "Experiment", "Comparison", "Build A", "Build B", "Logic tested",
             "Hero (engine/bot)", "History mode", "Opponent", "Stack (bb)", "Hands", "Pairs", "Seed0", "Sims",
             "MC path (CPU/Metal)", "A bb/100", "A CI low", "A CI high", "B bb/100", "B CI low", "B CI high",
             "A-B bb/100", "CI low", "CI high", "Verdict", "A vs opponent", "Wall time (s)", "Hardware",
             "Source", "Notes"],
    "Matches": ["Run ID", "Date-time (ET)", "Experiment", "Build", "Opponent", "Schedule", "Matches", "Wins",
                "Win %", "CI low", "CI high", "Pairs lost both", "Split", "Won both", "Avg hands/match", "Seed0",
                "Paired (v4 won & v3 lost / reverse)", "Wall time", "Hardware", "Source"],
    "Timing": ["Date-time", "Operation", "Build", "Hands", "Sims", "MC path", "Wall time (s)", "ms per hand",
               "Hardware", "Notes"],
}
DATE_HEADERS = {"Date-time (ET)", "Date-time"}
ARIAL = Font(name="Arial", size=10)


def verdict(lo, hi):
    return "better" if lo > 0 else ("worse" if hi < 0 else "inconclusive")


def vs_opponent(lo, hi):
    return "Win" if lo > 0 else ("Lose" if hi < 0 else "Inconclusive")


def now_et():
    return datetime.datetime.now(ET).replace(tzinfo=None, microsecond=0)


def hardware():
    def out(*cmd):
        try:
            return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
        except Exception:
            return "?"
    mem = out("sysctl", "-n", "hw.memsize")
    gb = f"{int(mem) // 2**30} GB" if mem.isdigit() else "?"
    return f"{out('sysctl', '-n', 'machdep.cpu.brand_string')}, {gb} RAM, macOS {out('sw_vers', '-productVersion')}"


def pair_stats(a, b):
    """a, b: loaded dumps. Same checks and maths as paired.py."""
    for k in ("seed0", "bb", "stack_bb", "opponent"):
        if a[k] != b[k]:
            sys.exit(f"cannot pair: {k} differs ({a[k]!r} vs {b[k]!r})")
    if len(a["results"]) != len(b["results"]) or len(a["results"]) < 2:
        sys.exit("cannot pair: need the same number (at least 2) of pairs")
    bb = a["bb"]
    diff = [x - y for x, y in zip(a["results"], b["results"])]
    return bb100_ci(a["results"], bb), bb100_ci(b["results"], bb), bb100_ci(diff, bb)


def run_values(a, b, **f):
    """One Runs row (dict keyed by header) from two dumps; f holds the descriptive fields."""
    (am, alo, ahi), (bm, blo, bhi), (dm, dlo, dhi) = pair_stats(a, b)
    r = lambda x: round(x, 1)
    row = {"Opponent": a["opponent"], "Stack (bb)": a["stack_bb"], "Hands": 2 * len(a["results"]),
           "Pairs": len(a["results"]), "Seed0": a["seed0"],
           "A bb/100": r(am), "A CI low": r(alo), "A CI high": r(ahi),
           "B bb/100": r(bm), "B CI low": r(blo), "B CI high": r(bhi),
           "A-B bb/100": r(dm), "CI low": r(dlo), "CI high": r(dhi),
           "Verdict": verdict(dlo, dhi), "A vs opponent": vs_opponent(alo, ahi)}
    row.update(f)
    return row


def paired_legs(a, b):
    """Match dumps: legs where a won and b lost, and the reverse."""
    la = [w for p in a["won"] for w in p]
    lb = [w for p in b["won"] for w in p]
    return sum(x and not y for x, y in zip(la, lb)), sum(y and not x for x, y in zip(la, lb))


def append(ws, name, row):
    """Append a dict keyed by header (or a list) as a styled row; keeps the filter range current."""
    hs = HEADERS[name]
    vals = [row.get(h, "") for h in hs] if isinstance(row, dict) else row
    ws.append(vals)
    r = ws.max_row
    for c, h in zip(ws[r], hs):
        c.font = ARIAL
        if h in DATE_HEADERS:
            c.number_format = DT_FMT
    ws.auto_filter.ref = f"A1:{get_column_letter(len(hs))}{r}"


def next_id(ws, prefix):
    n = [int(m.group(1)) for (v,) in ws.iter_rows(min_row=2, max_col=1, values_only=True)
         if v and (m := re.fullmatch(prefix + r"(\d+)", str(v)))]
    return f"{prefix}{max(n, default=0) + 1:03d}"


def summary_formulas(r):
    rc = get_column_letter(HEADERS["Runs"].index("Verdict") + 1)
    ec = get_column_letter(HEADERS["Runs"].index("Experiment") + 1)
    mc = get_column_letter(HEADERS["Matches"].index("Experiment") + 1)
    f = [f'=COUNTIFS(Runs!${ec}:${ec},$A{r},Runs!${rc}:${rc},"{v}")' for v in ("better", "worse", "inconclusive")]
    return f + [f"=B{r}+C{r}+D{r}", f"=COUNTIFS(Matches!${mc}:${mc},$A{r})"]


def ensure_summary(wb, experiment):
    ws = wb["Summary"]
    r = 3
    while ws.cell(r, 1).value:
        if ws.cell(r, 1).value == experiment:
            return
        r += 1
    for col, v in enumerate([experiment] + summary_formulas(r), 1):
        ws.cell(r, col, v).font = ARIAL


def dump_of(path):
    return json.load(open(path))


def cmd_paired(a):
    wb = load_workbook(a.xlsx)
    ws = wb["Runs"]
    A, B = dump_of(a.a), dump_of(a.b)
    row = run_values(
        A, B, **{"Run ID": next_id(ws, "R"), "Date-time (ET)": now_et(), "Experiment": a.experiment,
                 "Comparison": a.comparison, "Build A": a.build_a, "Build B": a.build_b, "Logic tested": a.logic,
                 "Hero (engine/bot)": a.hero, "History mode": a.history, "Sims": a.sims, "MC path (CPU/Metal)": a.path,
                 "Wall time (s)": a.wall_s if a.wall_s is not None else NR, "Hardware": hardware(),
                 "Source": a.source or f"bench dumps {os.path.basename(a.a)}, {os.path.basename(a.b)}",
                 "Notes": a.notes})
    append(ws, "Runs", row)
    ensure_summary(wb, a.experiment)
    wb.save(a.xlsx)
    print(f"{row['Run ID']}: A-B {row['A-B bb/100']:+.1f} [{row['CI low']:+.1f}, {row['CI high']:+.1f}] {row['Verdict']}")


LINE = re.compile(r"vs (\S+)\s+(\d+)/(\d+) = ([\d.]+)% \[([\d.]+)%, ([\d.]+)%\]\s+pairs lost both (\d+) / split (\d+)"
                  r" / won both (\d+)\s+avg ([\d.]+) hands/match")


def cmd_match(a):
    wb = load_workbook(a.xlsx)
    ws = wb["Matches"]
    lines = LINE.findall(open(a.log).read())
    if not lines:
        sys.exit("no match.py summary line found")
    sched = f"doubling every {a.schedule} hands" if a.schedule.isdigit() else a.schedule
    seed0 = dump_of(a.dump)["seed0"] if a.dump else ""
    paired = ""
    if a.dump and a.vs_dump:
        w, l = paired_legs(dump_of(a.dump), dump_of(a.vs_dump))
        paired = f"{w} / {l}"
    for opp, w, n, pct, lo, hi, p0, p1, p2, avg in lines:
        append(ws, "Matches", {
            "Run ID": next_id(ws, "M"), "Date-time (ET)": now_et(), "Experiment": a.experiment, "Build": a.build,
            "Opponent": opp, "Schedule": sched, "Matches": int(n), "Wins": int(w), "Win %": float(pct),
            "CI low": float(lo), "CI high": float(hi), "Pairs lost both": int(p0), "Split": int(p1),
            "Won both": int(p2), "Avg hands/match": float(avg), "Seed0": seed0, "Paired (v4 won & v3 lost / reverse)": paired,
            "Wall time": a.wall_s if a.wall_s is not None else NR, "Hardware": hardware(),
            "Source": f"match log {os.path.basename(a.log)}"})
        print(f"{opp}: {w}/{n} = {pct}%")
    ensure_summary(wb, a.experiment)
    wb.save(a.xlsx)


def cmd_timing(a):
    wb = load_workbook(a.xlsx)
    append(wb["Timing"], "Timing", {
        "Date-time": now_et(), "Operation": a.operation, "Build": a.build, "Hands": a.hands, "Sims": a.sims,
        "MC path": a.path, "Wall time (s)": a.wall_s, "ms per hand": round(a.wall_s * 1000 / a.hands, 2) if a.hands else "",
        "Hardware": hardware(), "Notes": a.notes})
    wb.save(a.xlsx)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("paired")
    p.add_argument("xlsx"); p.add_argument("a"); p.add_argument("b")
    p.add_argument("--experiment", required=True); p.add_argument("--comparison", required=True)
    p.add_argument("--build-a", required=True); p.add_argument("--build-b", required=True)
    p.add_argument("--logic", required=True)
    p.add_argument("--hero", default="engine"); p.add_argument("--history", default="n/a")
    p.add_argument("--sims", type=int, default=2000); p.add_argument("--path", choices=["CPU", "Metal"], default="CPU")
    p.add_argument("--wall-s", type=float); p.add_argument("--notes", default=""); p.add_argument("--source")
    p.set_defaults(fn=cmd_paired)
    m = sub.add_parser("match")
    m.add_argument("xlsx"); m.add_argument("log")
    m.add_argument("--experiment", required=True); m.add_argument("--build", required=True)
    m.add_argument("--schedule", required=True, help="hands per doubling (25, 10) or free text")
    m.add_argument("--wall-s", type=float)
    m.add_argument("--dump", help="match.py --dump file, for seed0"); m.add_argument("--vs-dump", help="other build's dump")
    m.set_defaults(fn=cmd_match)
    t = sub.add_parser("timing")
    t.add_argument("xlsx")
    t.add_argument("--operation", required=True); t.add_argument("--build", required=True)
    t.add_argument("--hands", type=int, required=True); t.add_argument("--sims", type=int, required=True)
    t.add_argument("--path", choices=["CPU", "Metal"], required=True); t.add_argument("--wall-s", type=float, required=True)
    t.add_argument("--notes", default="")
    t.set_defaults(fn=cmd_timing)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
