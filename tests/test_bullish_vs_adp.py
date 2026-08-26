#!/usr/bin/env python3
"""Guards for the BULLISH-vs-ADP test artifact.

The verdict on this artifact is REPORTED, not computed: the automated
three-state rule was removed as statistically unsound (a post-hoc
minimum-detectable-effect comparison is not an equivalence test, the
significance branch searched six cells without multiplicity control, and
its BEATS label was sign-blind). These guards enforce the replacement
contract: the verdict is the reviewed INCONCLUSIVE text verbatim, every
figure it cites cross-checks against the computed cells so data drift
fails loudly instead of shipping a stale verdict, no power/three-state
machinery remains, the concentration confound stays reported, and the
limitation stays on the artifact.
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

# THE VERDICT IS REPORTED, NOT COMPUTED - the reviewed text, verbatim.
# This copy is the guard's own record of what was reviewed; the builder
# holds an independent copy. Either drifting from the other fails here.
FIXED_VERDICT = (
    "INCONCLUSIVE - incremental value over ADP is unresolved in the only "
    "band with usable overlap. Among positional ADP ranks 1-12, tagged "
    "players finished top-12 in 28/43 cases (65.1%) vs 133/257 (51.8%), "
    "+13.4pp, 95% CI [-2.1, +28.9]. That interval permits slight harm and "
    "useful lift alike. Only three tags occur at ranks 13-24 and none at "
    "25-48, so those regions are not identifiable. Coarse bands do not "
    "adjust for exact ADP, position, season, or repeated players. Tag "
    "stays display-only pending a continuous-ADP, season-held-out test.")
ok(a["verdict"] == FIXED_VERDICT,
   "the verdict is the reviewed INCONCLUSIVE text, byte-identical")
ok(a["verdict"].startswith("INCONCLUSIVE"), "the verdict reads INCONCLUSIVE")
ok("reported, fixed by review" in a.get("verdict_basis", ""),
   "the artifact states the verdict is reported, not computed")
ok("not an equivalence test" in a.get("verdict_basis", "")
   and "multiplicity" in a.get("verdict_basis", "")
   and "sign-blind" in a.get("verdict_basis", ""),
   "the basis names all three defects of the removed automation")

# the automation must actually be GONE, not just overridden
ok("significant_cells" not in a and "underpowered_bands" not in a,
   "no three-state machinery keys remain on the artifact")
ok(all("power" not in v for v in a["within_band"].values()),
   "no per-band post-hoc power block remains")
src = open(os.path.join(ROOT, "src", "bullish_vs_adp.py")).read()
ok("min_detectable" not in src,
   "the post-hoc MDE search is deleted from the builder")
ok('verdict = "' not in src and "verdict = (" not in src,
   "the builder never assigns a computed verdict")

# every figure the fixed verdict cites, recomputed from the cells - data
# drift must fail loudly, never ship under the reviewed text
top = a["within_band"]["pos1-12"]
tk, tn = top["tagged"]["hit12"]["k"], top["tagged"]["n"]
uk, un = top["untagged"]["hit12"]["k"], top["untagged"]["n"]
l12 = top["lift_hit12"]
ok((tk, tn) == (28, 43), "verdict cite 28/43 matches the computed tagged cell")
ok((uk, un) == (133, 257),
   "verdict cite 133/257 matches the computed untagged cell")
ok(round(100.0 * tk / tn, 1) == 65.1, "verdict cite 65.1% recomputes")
ok(round(100.0 * uk / un, 1) == 51.8, "verdict cite 51.8% recomputes")
ok(round(l12["diff"] * 100, 1) == 13.4, "verdict cite +13.4pp recomputes")
ok([round(x * 100, 1) for x in l12["diff_ci95"]] == [-2.1, 28.9],
   "verdict cite CI [-2.1, +28.9] recomputes")
ok(a["within_band"]["pos13-24"]["tagged"]["n"] == 3,
   "verdict cite 'three tags at ranks 13-24' matches the cell")
ok(a["within_band"]["pos25-48"]["tagged"]["n"] == 0,
   "verdict cite 'none at 25-48' matches the cell")
for k in ("28/43", "65.1%", "133/257", "51.8%", "+13.4pp", "[-2.1, +28.9]"):
    ok(k in a["verdict"], f"the verdict text actually cites {k}")
ok("verdict_cites" in a, "the cited-figure ledger ships on the artifact")

# the ADP-confound disclosure is mandatory
c = a["concentration"]
ok("tagged_by_band" in c and c["share_in_top12_band"] is not None,
   "tag concentration by ADP band is reported")
ok("measures ADP, not the tag" in c["note"],
   "the artifact names the pooled comparison as an ADP confound")
ok(a["pooled"]["tagged"]["n"] ==
   sum(v["tagged"]["n"] for v in a["within_band"].values()),
   "pooled and within-band tag counts reconcile")

# the shipped tag must stay display-only while the verdict is unresolved
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
