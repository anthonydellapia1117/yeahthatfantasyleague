#!/usr/bin/env python3
"""Guards for the VONA draft-path tree (docs/VONA_TREE_SPEC.md).

Validates out/data/vona_tree_2026.json and the paths page. The point of
these guards is that the approved decisions cannot drift: depth stays
structural, branching stays data-driven at every slot, no BULLISH marker
appears on a node, and every threshold stays derived rather than typed.
"""
import json
import contextlib
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "out", "data")
FAILS = []


def ok(cond, label, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + ("" if cond or not detail
                                                      else "  -> " + detail))
    if not cond:
        FAILS.append(label)


t = json.load(open(os.path.join(D, "vona_tree_2026.json")))
prov, th = t["provenance"], t["thresholds"]
engine_artifact = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
ok(prov.get("engine_content_sha256") == engine_artifact.get("content_sha256") and
   len(prov.get("engine_content_sha256", "")) == 64,
   "tree records the exact engine content it consumed")

# --- the approved decisions ---
ok(prov["depth"] == 7, "depth is 7")
ok(prov["value_lookahead_rounds"] == 8,
   "seven displayed rounds are valued through the real round-8 owner pick")
ok("seven skill slots" in prov["depth_rationale"]
   and "not a noise cutoff" in prov["depth_rationale"],
   "depth 7 carries its structural rationale, not a noise argument")
ok("never gated on slot number" in prov["branch_rule"],
   "branching is data-driven at every slot")
ok("deliberately absent" in prov["bullish_on_nodes"],
   "the no-BULLISH-on-nodes decision is recorded")

# --- thresholds derived, not typed ---
ok("p25" in th["branch_eps_source"], "branch threshold is derived from the board")
ok("p25" in th["narrow_band_source"], "coin-flip band is derived from the board")
ok(th["margins_observed"] > 0, "the coin-flip band saw real margins")
ok("STRICT domination" in th["prune_rule"] and "forward_policy" in th["prune_rule"],
   "pruning runs on shared lineup value under strict domination")
ok("Raw VOR sums are NOT used" in th["prune_rule"],
   "the prune rule states it rejects raw VOR sums")
ok(len(th["branch_eps_by_depth"]) == 7, "a branch threshold exists per round")

# --- the P1-A conditioning law and P1-B feasibility law ---
ok("conditioning" in prov and "ONE frame" in prov["conditioning"],
   "one conditioning frame is stated on the artifact")
ok("feasibility" in prov and "forward_policy" in prov["feasibility"],
   "starter feasibility comes from the shared layer, stated")
sys.path.insert(0, os.path.join(ROOT, "src"))
from build_vona_tree import main as build_vona, vona_at
from engine_2026 import snake_picks
from forward_policy import starter_caps
eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
CAPS = starter_caps(eng.get("flex_allocation", {}))
try:
    vona_at({"RB": [p for p in eng["players"] if p["pos"] == "RB"][:2]},
            1, None)
    rejected_missing_next = False
except ValueError:
    rejected_missing_next = True
ok(rejected_missing_next, "runtime rejects a VONA call without a next owner pick")
neg = []
feas = []
mono = []
def check(nodes, counts, slot):
    for n in nodes:
        if n["vona"] < -1e-9:
            neg.append((slot, n["round"], n["pos"], n["vona"]))
        c = dict(counts); c[n["pos"]] = c.get(n["pos"], 0) + 1
        if c[n["pos"]] > CAPS.get(n["pos"], 99):
            feas.append((slot, n["round"], n["pos"], c[n["pos"]]))
        if n["e_now"] >= 0 and n["e_next"] > n["e_now"] + 1e-6:
            mono.append((slot, n["round"], n["pos"]))
        check(n.get("children", []), c, slot)
for _slot, _v in t["slots"].items():
    check(_v["roots"], {}, _slot)
ok(not neg, "no rendered node carries negative VONA", str(neg[:3]))
ok(not feas, "every path respects the shared starter caps - no position "
             "beyond its startable count", str(feas[:3]))
ok(not mono, "E[next] never exceeds E[now] on an above-replacement pool",
   str(mono[:3]))

# --- honesty blocks ---
ok(len(prov["deviations"]) == 2, "both spec deviations are stated on the artifact")
ok(any("independent" in d for d in prov["deviations"]),
   "the independence assumption is stated")
corr = t["correlation"]
ok(corr["by_pos"] and all(v["ratio"] for v in corr["by_pos"].values()),
   "positional clustering is measured from league history")
ok("UNDERSTATES VONA" in corr["bias_direction"],
   "the correlation bias direction is stated")

# --- per-slot structure ---
POSITIONS = {"QB", "RB", "WR", "TE"}
ok(set(t["slots"].keys()) == {str(i) for i in range(1, 13)},
   "all twelve slots are rendered")
branch_total = 0
for slot, v in t["slots"].items():
    full_picks = snake_picks(int(slot))
    ok(v["picks"] == full_picks[:7], f"slot {slot}: seven display picks")
    ok(v["next_picks"] == full_picks[1:8],
       f"slot {slot}: every display pick has its real next owner pick")
    branch_total += v["rendered_forks"]

    def walk(nodes, path, depth):
        for n in nodes:
            ok(n["round"] == depth, f"slot {slot}: node round matches its depth")
            ok(n["pick"] == full_picks[depth - 1]
               and n["next_pick"] == full_picks[depth],
               f"slot {slot}: node uses real current and next owner picks")
            ok(n["pos"] in POSITIONS, f"slot {slot}: node position is a skill spot")
            ok(n["p_available"] >= th["surv_floor"],
               f"slot {slot}: every node clears the survival floor",
               f"{n['name']} {n['p_available']}")
            ok(n["name"] not in path,
               f"slot {slot}: no player repeats on a path", n["name"])
            ok("bullish" not in json.dumps(n).lower(),
               f"slot {slot}: no BULLISH marker on any node")
            if depth == 7:
                ok(not n.get("children"),
                   f"slot {slot}: round 7 is valued to round 8 without rendering it")
            walk(n.get("children", []), path | {n["name"]}, depth + 1)
    walk(v["roots"], set(), 1)
    ok(all(k in v["pruned"] for k in ("dominated", "narrow_kept", "budget")),
       f"slot {slot}: prune accounting reported, never silent")

# the branch rule must actually discriminate: some slots open, some forced
opens = [int(s) for s, v in t["slots"].items() if v["rendered_forks"] > 0]
forced = [int(s) for s, v in t["slots"].items() if v["rendered_forks"] == 0]
ok(branch_total > 0, "the tree finds real decision points somewhere")
ok(opens and forced,
   "branching discriminates - some slots fork, some are forced",
   f"open {sorted(opens)} forced {sorted(forced)}")

# --- page wiring ---
pg = open(os.path.join(ROOT, "out", "paths.html")).read()
ok('data-active="paths"' in pg, "paths page joins the shared nav")
ok("vona_tree_2026.json" in pg, "paths page reads the artifact")
ok("BULLISH" not in pg.upper().replace("BULLISH_ON_NODES", ""),
   "the paths page renders no BULLISH marker")
ok("bias_direction" in pg, "the page surfaces the correlation caveat")
ok("deviations" in pg, "the page surfaces the stated deviations")
nav = open(os.path.join(ROOT, "out", "nav.js")).read()
ok('"paths.html"' in nav, "nav carries the PATHS tab")

# Exact current-input proof at the shared publication boundary. Generation dates
# are useful display provenance but can collide when an engine moves twice in a
# day; the rebuilt object is the authoritative dependency check.
_artifact = os.path.join(D, "vona_tree_2026.json")
_orig = open(_artifact, "rb").read()
try:
    with contextlib.redirect_stdout(io.StringIO()):
        build_vona()
    _rebuilt = json.load(open(_artifact))
finally:
    with open(_artifact, "wb") as _fh:
        _fh.write(_orig)
_expected, _actual = dict(t), dict(_rebuilt)
_expected["provenance"] = dict(_expected["provenance"])
_actual["provenance"] = dict(_actual["provenance"])
_expected["provenance"].pop("generated", None)
_actual["provenance"].pop("generated", None)
ok(_expected == _actual,
   "VONA artifact rebuilds exactly from the current engine and league history")

if FAILS:
    print(f"\n{len(FAILS)} FAILURES")
    sys.exit(1)
print("\nALL PASS")
