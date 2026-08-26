#!/usr/bin/env python3
"""Guards for the BULLISH-vs-ADP null test artifact.

The point of these guards is that the null cannot be quietly upgraded: the
verdict must follow the intervals, the concentration must be reported, and
the limitation must stay on the artifact.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "out", "data")
FAILS = []


def ok(cond, label):
    print(("PASS  " if cond else "FAIL  ") + label)
    if not cond:
        FAILS.append(label)


a = json.load(open(os.path.join(D, "bullish_vs_adp.json")))
prov = a["provenance"]
ok(all(k in prov for k in ("question", "method", "scoring", "limitation")),
   "provenance states the question, method, scoring, and limitation")
ok("PROXY" in prov["limitation"],
   "the artifact says plainly that it backtests a proxy, not the shipped matrix")

# every reported cell carries n and a Wilson interval
for band, v in a["within_band"].items():
    for side in ("tagged", "untagged"):
        c = v[side]
        ok("n" in c and c["hit12"]["ci95"] is not None or c["n"] == 0,
           f"{band}/{side}: n and Wilson interval present")
        if c["n"]:
            ok(c["hit12"]["ci95"][0] <= c["hit12"]["rate"] <= c["hit12"]["ci95"][1],
               f"{band}/{side}: the interval brackets its own rate")

# the verdict is DERIVED from the intervals, never asserted
sig = [b for b, v in a["within_band"].items()
       for key in ("lift_hit12", "lift_hit24")
       if v[key] and (v[key]["diff_ci95"][0] > 0 or v[key]["diff_ci95"][1] < 0)]
ok(sig == a["significant_cells"],
   "the significant-cell list recomputes from the artifact's own intervals")
ok((a["verdict"].startswith("NULL") and not sig) or
   (not a["verdict"].startswith("NULL") and sig),
   "the verdict matches whether any within-band interval excludes zero")

# the ADP-confound disclosure is mandatory
c = a["concentration"]
ok("tagged_by_band" in c and c["share_in_top12_band"] is not None,
   "tag concentration by ADP band is reported")
ok("measures ADP, not the tag" in c["note"],
   "the artifact names the pooled comparison as an ADP confound")
ok(a["pooled"]["tagged"]["n"] ==
   sum(v["tagged"]["n"] for v in a["within_band"].values()),
   "pooled and within-band tag counts reconcile")

# the shipped tag must stay display-only while this test reads NULL
room = open(os.path.join(ROOT, "out", "draft_room.html")).read()
board = open(os.path.join(ROOT, "out", "big_board.html")).read()
ok("bullChip" in room and "sigBadge" in room,
   "the room still renders the tag BESIDE the signal encoding")
ok("bullishChip" in board, "the board still renders the tag inline")
for src, name in ((room, "room"), (board, "board")):
    verdicty = [ln for ln in src.splitlines()
                if "BULL" in ln and ("verdict =" in ln or "liveVerdict =" in ln)]
    ok(not verdicty, f"{name}: no verdict assignment reads the BULLISH tag")

if FAILS:
    print(f"\n{len(FAILS)} FAILURES")
    sys.exit(1)
print("\nALL PASS")
