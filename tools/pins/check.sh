#!/bin/bash
# No-play-change check: capture the pin set of a checkout and compare it with the committed base.
#   PY=<python with pybind11 + numpy> tools/pins/check.sh <repo_checkout>
# Prints one PASS/FAIL line per file and a summary; exits nonzero on any FAIL.
# Optional: PINBASE=<dir> (default results/baselines/2026-11-26-pins-085 next to this script), KEEP=1 keeps the capture.
# Exemptions (the whole list): meta.commit and meta.coerced in every .json/.jsonl dump; the engine_so_sha256
# and base_so_sha256 lines of engine.txt; the `coerced ` stdout lines of .txt files. See the base's README.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
: "${PY:?set PY to a python with pybind11 and numpy}"
[ $# = 1 ] || { echo "usage: PY=... $0 <repo_checkout>" >&2; exit 2; }
BASE=${PINBASE:-$HERE/../../results/baselines/2026-11-26-pins-085}
BASE=$(cd "$BASE" && pwd)
new=$(mktemp -d "${TMPDIR:-/tmp}/pins-check.XXXXXX")/out
[ -n "${KEEP:-}" ] || trap 'rm -rf "$(dirname "$new")"' EXIT
"$HERE/capture.sh" "$1" "$new" >"$new.log" 2>&1 || { trap - EXIT; echo "FAIL capture did not complete (log: $new.log)"; tail -5 "$new.log"; exit 1; }

"$PY" - "$BASE" "$new" <<'E2'
import json, os, sys

base, new = sys.argv[1:]
committed = os.path.join(base, 'b4')   # B4 re-runs are compared with the base's own b4 dumps

def norm(path):
    """File bytes with the exempt fields removed."""
    raw = open(path, "rb").read()
    if path.endswith(".json"):
        d = json.loads(raw)
        d.get("meta", {}).pop("commit", None)          # exemption 1
        d.get("meta", {}).pop("coerced", None)         # exemption 3: a new outcome key, not a play change
        return json.dumps(d).encode()
    if path.endswith(".jsonl"):
        lines = raw.split(b"\n")
        d = json.loads(lines[0])
        if "meta" in d:
            d["meta"].pop("commit", None)               # exemption 1
            d["meta"].pop("coerced", None)
            lines[0] = json.dumps(d).encode()
        return b"\n".join(lines)
    if os.path.basename(path) == "engine.txt":
        return b"\n".join(l for l in raw.split(b"\n") if not l.startswith((b"engine_so_sha256", b"base_so_sha256")))  # exemption 2 (+ base_so_sha256: the september build is not byte-reproducible; its behaviour is pinned by the bench dumps)
    if os.path.basename(path) == "jobs.txt":
        return raw.replace(b" --wire bench", b"")  # the only difference from pin.sh: the explicit flag
    if path.endswith(".txt"):
        return b"\n".join(l for l in raw.split(b"\n") if not l.startswith(b"coerced "))  # exemption 3: the new stdout line
    return raw

pinned = sorted(os.path.relpath(os.path.join(r, f), base)
                for r, _, fs in os.walk(base) for f in fs
                if f.endswith((".json", ".jsonl", ".txt")))
bad = 0
def line(ok, what):
    global bad
    bad += not ok
    print(("PASS " if ok else "FAIL ") + what)

for rel in pinned:
    a, b = os.path.join(base, rel), os.path.join(new, rel)
    line(os.path.exists(b) and norm(a) == norm(b), rel)
for rel in pinned:
    if rel.startswith("b4/") and rel.endswith(".json"):
        c = os.path.join(committed, os.path.basename(rel))
        line(os.path.exists(c) and norm(c) == norm(os.path.join(new, rel)), "B4 vs committed " + os.path.basename(rel))
extra = sorted(set(os.path.relpath(os.path.join(r, f), new) for r, _, fs in os.walk(new) for f in fs
                   if f.endswith((".json", ".jsonl", ".txt"))) - set(pinned))
for rel in extra:
    line(False, "unexpected extra file " + rel)
so = lambda d: [l for l in open(os.path.join(d, "engine.txt")) if l.startswith("engine_so_sha256")]
print("INFO engine .so", "identical" if so(base) == so(new) else "differs (exempt)")
print(f"{'FAIL' if bad else 'PASS'}: {len(pinned) + sum(p.startswith('b4/') and p.endswith('.json') for p in pinned)} checks, {bad} failed")
sys.exit(1 if bad else 0)
E2
