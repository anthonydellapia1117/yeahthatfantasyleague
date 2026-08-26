#!/usr/bin/env python3
"""C4 guards: ceiling artifact integrity and board wiring, enabled by default.

Runs WITHOUT network on the committed artifact and pages.
Run: python3 tests/test_ceiling.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []


def ok(cond, name, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "  -> " + detail))
    if not cond:
        fails.append(name)


path = os.path.join(ROOT, "out", "data", "ceiling_2026.json")
ok(os.path.exists(path), "ceiling artifact exists")
d = json.load(open(path))

prov = d["provenance"]
ok("league_average_match=1" in prov["format"],
   "the median-game setting is stated as verified, not assumed")
ok("variance-premium" in prov["limitation"],
   "the no-synthetic-lambda limitation is stated in provenance")
ok("6-pt pass TD" in prov["scoring"], "league-exact scoring declared")

players = d["players"]
ok(len(players) >= 100, "draftable pool covered", str(len(players)))
n_boom = 0
for p in players:
    if "boom" in p:
        n_boom += 1
        b = p["boom"]
        if not (0 <= b["k"] <= b["n"] and abs(b["rate"] - b["k"] / b["n"]) < 1e-3):
            ok(False, f"boom internally consistent for {p['name']}", str(b))
        if not (p["weekly_sd"] >= 0 and p["p90_week"] >= p["weekly_mean"] - 1e-9):
            ok(False, f"weekly stats coherent for {p['name']}")
    if "gp_rate_2yr" in p:
        if not (0 <= p["gp_rate_2yr"] <= 1 and p["exp_missed"] >= 0):
            ok(False, f"availability coherent for {p['name']}")
        if "avail_note" not in p:
            ok(False, f"zero-IR note on {p['name']}")
ok(n_boom >= 80, "a real boom-rate population", str(n_boom))
print(f"PASS  boom and availability blocks internally consistent ({n_boom} with series)")

# rookies: no fabricated availability
rookies = [p for p in players if "gp_rate_2yr" not in p]
ok(all(p.get("avail_note", "").startswith("no NFL sample") for p in rookies),
   "players without NFL history are declared unadjusted, never estimated")

wr = d["weekly_replacement"]
ok(all(v > 0 for v in wr.values()) and set(wr) == {"QB", "RB", "WR", "TE"},
   "weekly replacement points carried per position (the zero-IR cost basis)")

# board wiring: view enabled, honesty lines, graceful absence
bp = open(os.path.join(ROOT, "out", "big_board.html")).read()
ok('data-v="ceiling"' in bp and "renderCeiling" in bp, "CEILING view wired")
ok("scores every week twice" in bp, "median-format context stated on the view")
ok("No synthetic variance premium" in bp,
   "the lens declares its limitation instead of smuggling a lambda")
ok("ceiling artifact absent - the board runs without it" in bp,
   "graceful absence path present")
ok("zero-IR" in bp, "zero-IR cost named on the view")

print()
if fails:
    print(f"{len(fails)} FAILURES")
    sys.exit(1)
print("ALL PASS")
