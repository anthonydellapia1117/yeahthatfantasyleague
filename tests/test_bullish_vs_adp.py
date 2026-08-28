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
    "INCONCLUSIVE — incremental value over ADP remains unresolved in the "
    "RB/WR scope after suspending the non-discriminating TE matrix. Among "
    "positional ADP ranks 1-12, tagged players finished top-12 in 22/35 cases "
    "(62.9%) vs 86/164 (52.4%), +10.4pp, 95% CI [-7.3, +28.2], p=0.261. "
    "Restricting the earlier mixed RB/WR/TE scope to RB/WR reduced the "
    "top-band sample from 300 to 199 players (43 to 35 tagged) and widened "
    "the interval from 31.0pp to 35.5pp. That is the expected direction when "
    "a non-discriminating group is removed: fewer observations mean more "
    "uncertainty. Because the verdict held while uncertainty increased, the "
    "unresolved limitation is the ADP-gated design, not one individual "
    "criterion. The current interval permits harm and useful lift alike. "
    "Only three tags occur "
    "at ranks 13-24 and none at 25-48, so those regions are not identifiable. "
    "Coarse bands do not adjust for exact ADP, position, season, or repeated "
    "players. Tags stay display-only pending continuous-ADP, season-held-out "
    "testing.")
ok(a["verdict"] == FIXED_VERDICT,
   "the verdict is the reviewed INCONCLUSIVE text, byte-identical")
ok(a["verdict"].startswith("INCONCLUSIVE"), "the verdict reads INCONCLUSIVE")
ok("reported, fixed by review" in a.get("verdict_basis", ""),
   "the artifact states the verdict is reported, not computed")
ok("not an equivalence test" in a.get("verdict_basis", "")
   and "multiplicity" in a.get("verdict_basis", "")
   and "sign-blind" in a.get("verdict_basis", ""),
   "the basis names all three defects of the removed automation")
scope_change = a.get("scope_change", {})
prior_scope = scope_change.get("prior", {})
current_scope = scope_change.get("current", {})
top_lift = a["within_band"]["pos1-12"]["lift_hit12"]
current_width = round(
    100 * (top_lift["diff_ci95"][1] - top_lift["diff_ci95"][0]), 1)
ok(prior_scope.get("scope") == ["RB", "WR", "TE"] and
   prior_scope.get("top_band_total_n") == 300 and
   prior_scope.get("top_band_tagged_n") == 43 and
   prior_scope.get("diff_ci95_width_pp") == 31.0 and
   prior_scope.get("source_commit") ==
   "242ae6b284a82e81f575eb42805bcf638a65ebbf" and
   prior_scope.get("source_content_sha256") ==
   "405cac582f5b953d9ba46a53b670123c8870892b37dc79bdfb2e5ffe2ee172b4",
   "the prior mixed-position scope is pinned to the reviewed artifact")
ok(current_scope.get("scope") == ["RB", "WR"] and
   current_scope.get("top_band_total_n") ==
   a["within_band"]["pos1-12"]["tagged"]["n"] +
   a["within_band"]["pos1-12"]["untagged"]["n"] and
   current_scope.get("top_band_tagged_n") ==
   a["within_band"]["pos1-12"]["tagged"]["n"] and
   current_scope.get("diff_ci95_width_pp") == current_width == 35.5,
   "the current scope and widened interval rederive from computed cells")
ok("fewer observations" in scope_change.get("interpretation", "") and
   "ADP-gated design" in scope_change.get("interpretation", ""),
   "the scope-change interpretation explains expected widening and its cause")

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
ok((tk, tn) == (22, 35), "verdict cite 22/35 matches the computed tagged cell")
ok((uk, un) == (86, 164),
   "verdict cite 86/164 matches the computed untagged cell")
ok(round(100.0 * tk / tn, 1) == 62.9, "verdict cite 62.9% recomputes")
ok(round(100.0 * uk / un, 1) == 52.4, "verdict cite 52.4% recomputes")
ok(round(l12["diff"] * 100, 1) == 10.4, "verdict cite +10.4pp recomputes")
ok([round(x * 100, 1) for x in l12["diff_ci95"]] == [-7.3, 28.2],
   "verdict cite CI [-7.3, +28.2] recomputes")
ok(round(l12["p_two_sided"], 3) == 0.261,
   "verdict cite p=0.261 recomputes")
ok(a["within_band"]["pos13-24"]["tagged"]["n"] == 3,
   "verdict cite 'three tags at ranks 13-24' matches the cell")
ok(a["within_band"]["pos25-48"]["tagged"]["n"] == 0,
   "verdict cite 'none at 25-48' matches the cell")
for k in ("22/35", "62.9%", "86/164", "52.4%", "+10.4pp",
          "[-7.3, +28.2]", "p=0.261"):
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
