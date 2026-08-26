#!/usr/bin/env python3
"""C5 guards: BULLISH engine - probabilistic gates, state machine, edge
accountability, delta report, and display-only wiring.

Runs WITHOUT network on the committed artifacts and pages.
Run: python3 tests/test_bullish.py
"""
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "out", "data")
fails = []


def ok(cond, name, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "  -> " + detail))
    if not cond:
        fails.append(name)


inp = json.load(open(os.path.join(D, "bullish_inputs_2026.json")))
d = json.load(open(os.path.join(D, "bullish_2026.json")))

# 1. inputs: proportions carry k and n; thresholds carry distributions;
#    provenance states the proxy weakness and the Vegas window
thr = inp["thresholds"]
for k in ("wr_tprr", "rb_targets_pg", "te_route_part", "qb_rush_ypg"):
    ok(thr[k]["n"] >= 15 and thr[k]["p75"] > 0,
       f"threshold {k} carries a real distribution", str(thr[k]))
ok("pass-block snaps" in thr["note"], "route-proxy weakness stated")
ok("Week-1" in inp["provenance"]["vegas"]["source"],
   "Vegas window declared (the complete-coverage week)")
n_prop = sum(1 for e in inp["players"] for f in ("tprr_proxy", "first_read",
             "route_part", "inside5_share") if isinstance(e.get(f), dict)
             and "k" in e[f] and "n" in e[f])
ok(n_prop >= 100, "proportion inputs ship as k/n for interval math", str(n_prop))

# 2. QB gap derivation present with n and CI, both scorings
for key in ("league_6pt", "counterfactual_4pt"):
    g = inp["qb_gap"][key]
    ok(g["rushing"]["n"] + g["pocket"]["n"] == 120,
       f"qb gap {key} covers all 120 top-12 seasons",
       str(g["rushing"]["n"] + g["pocket"]["n"]))
    ok(g["gap_ci95"][0] < g["gap"] < g["gap_ci95"][1],
       f"qb gap {key} CI brackets the point estimate")

# 3. tags: statuses legal, scores match, criteria in [0,1], reasons on
#    demotions, TTL and timestamps present
LEGAL = {"BULLISH", "WATCH", "SUSPENDED", "REVOKED"}
for t in d["tags"]:
    if t["status"] not in LEGAL:
        ok(False, f"legal status for {t['name']}", t["status"])
    for c, p in t["criteria"].items():
        if p is not None and not (0 <= p <= 1):
            ok(False, f"criterion probability in range for {t['name']}/{c}", str(p))
    if t["status"] in ("SUSPENDED",) and not any("injury" in r for r in t["reasons"]):
        ok(False, f"suspension carries an injury reason for {t['name']}")
    if not (t.get("ttl_hours") == 72 and t.get("computed_at")):
        ok(False, f"ttl and timestamp on {t['name']}")
print(f"PASS  every tag has legal status, bounded criteria, ttl, timestamp "
      f"({len(d['tags'])} tags)")
ok(any(t["status"] == "BULLISH" for t in d["tags"]), "a nonempty BULLISH set")
ok(any(t["status"] == "WATCH" for t in d["tags"]),
   "near-misses render as WATCH, not silently dropped")

# 4. no hard cliffs: WATCH band exists between the conventions
conv = d["provenance"]["conventions"]
ok(conv["watch_p"] < conv["bullish_p"], "watch band below the bullish level")

# 5. ADP-edge accountability: the question is answered either way
edge = d["adp_edge"]
ok("what do the tags find" in edge["question"], "the edge question is stated")
ok(edge["statement"].startswith("NULL RESULT") or len(edge["divergent"]) > 0,
   "edge statement is explicit: divergence list or a recorded null")
if edge["divergent"]:
    ok(all(x["gap"] >= 4 for x in edge["divergent"]),
       "every divergent entry clears the stated margin")

# 6. TE adjudication logged with a verdict naming both reports' claims
te = d["te_scarcity_adjudication"]
ok("SUPPORTED" in te["verdict"] or "CONTRADICTED" in te["verdict"],
   "TE scarcity verdict is explicit")
ok(len(te["gaps_ppg"]["te1_te12"]) == 3, "TE gaps computed for all three seasons")

# 7. delta report structure (the T-24h diff engine)
ok(set(d["delta"].keys()) == {"previous", "gained", "lost", "status_changed"},
   "delta report structure present")

# 8. pages: chips wired display-only, beside the signal encoding
bp = open(os.path.join(ROOT, "out", "big_board.html")).read()
drp = open(os.path.join(ROOT, "out", "draft_room.html")).read()
ok("bullishChip" in bp and 'get("data/bullish_2026.json")' in bp,
   "board chip wired with optional load")
ok("bullChip" in drp and 'fetch("data/bullish_2026.json")' in drp,
   "room chip wired with optional load")
ok("never" in drp[drp.index("C5 BULLISH layer"):drp.index("C5 BULLISH layer") + 300]
   and "replacing" in drp[drp.index("C5 BULLISH layer"):drp.index("C5 BULLISH layer") + 300],
   "room states the tag sits beside the signal encoding, never replacing it")
for page, chip in ((bp, "bullishChip"), (drp, "bullChip")):
    seg = page[page.index(f"function {chip}"):]
    seg = seg[:seg.index("\n}")]
    ok("ttl_hours" in seg and "ageH" in seg, f"{chip} enforces the 72h TTL with age display")
_pe_seg = drp[drp.index("function peScore"):drp.index("function peCondition")]
ok("bullChip" not in _pe_seg and "BULL" not in _pe_seg,
   "the tag never enters the pick-engine score")

# 9. builder sources carry no player-name constants (canary, code body only)
for srcf in ("build_bullish.py", "build_bullish_inputs.py"):
    src = open(os.path.join(ROOT, "src", srcf)).read()
    body = re.sub(r'\A(#![^\n]*\n)?"""[\s\S]*?"""', "", src, count=1)
    canaries = ["McCaffrey", "Gibbs", "Bijan", "Bowers", "McBride", "Nacua",
                "Allen", "Prescott", "Chase"]
    hit = [c for c in canaries if c in body]
    ok(not hit, f"{srcf} code body has no player-name constants", str(hit))

print()
if fails:
    print(f"{len(fails)} FAILURES")
    sys.exit(1)
print("ALL PASS")
