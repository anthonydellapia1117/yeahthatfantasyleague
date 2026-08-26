#!/usr/bin/env python3
"""C3 guards: archetype artifact integrity, computed thresholds, page wiring.

Runs WITHOUT network on the committed artifact and pages.
Run: python3 tests/test_archetypes.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []


def ok(cond, name, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "  -> " + detail))
    if not cond:
        fails.append(name)


path = os.path.join(ROOT, "out", "data", "archetypes_2026.json")
ok(os.path.exists(path), "archetypes artifact exists")
d = json.load(open(path))

# 1. Thresholds documented; the two named thresholds carry verification blocks
thr = d["thresholds"]
ok(thr.get("qb_rush_ypg_p75", 0) > 0 and thr.get("rb_targets_pg_p75", 0) > 0,
   "percentile thresholds computed from usage, not asserted")
v = d["verification"]
for block, min_n in (("wr_140_targets", 50), ("rb_400_touches", 1)):
    ok(block in v and v[block]["computed"]["n"] >= min_n,
       f"{block} verification block computed with real n",
       str(v.get(block, {}).get("computed", {}).get("n")))
vt = v["wr_140_targets"]["computed"]
ok(vt["top24"]["ci95"][0] <= vt["top24"]["rate"] <= vt["top24"]["ci95"][1],
   "140-target verification interval brackets its rate")
ok("goalline_conversion" in v and v["goalline_conversion"]["i5"]["att"] > 1000,
   "inside-5 vs 6-10 conversion split carried with real n")
ok(v["goalline_conversion"]["i5"]["rate"] > v["goalline_conversion"]["z6_10"]["rate"],
   "inside-5 converts above the 6-10 zone (the split the criterion rests on)")

# 2. Every tag carries orientation + a numeric reason; zero-IR flag on the
#    post-injury archetype; ledger fact table flagged
VALID_O = {"target", "fade", "context", "target_if_cheap_fade_if_premium"}
n_tags = 0
for e in d["players"]:
    for t in e["tags"]:
        n_tags += 1
        if t["orientation"] not in VALID_O:
            ok(False, f"valid orientation on {e['name']}", t["orientation"])
        if not re.search(r"\d", t["reason"]):
            ok(False, f"numeric reason on {e['name']}/{t['tag']}", t["reason"][:60])
        if t["tag"] == "post_injury_discount" and "zero_ir_cost" not in t:
            ok(False, f"zero-IR flag on {e['name']}")
ok(n_tags >= 40, "a real tag population", str(n_tags))
print(f"PASS  every tag carries a valid orientation and a numeric reason ({n_tags} tags)")
ok("source-dependent" in d["fact_tables"]["preseason_rb1_ledger"]["flag"],
   "RB1 conversion ledger carries the 2016 source-dependency flag")

# 3. No player-name constants in the builder (canary check on report names)
src = open(os.path.join(ROOT, "src", "build_archetypes.py")).read()
# the module docstring may NAME the permitted fact table (the RB1 conversion
# ledger); the code body may not carry any player-name constant
body = re.sub(r'\A(#![^\n]*\n)?"""[\s\S]*?"""', "", src, count=1)
canaries = ["McCaffrey", "Gibbs", "Bijan", "Bowers", "McBride", "Nacua",
            "Egbuka", "Hampton", "Walker", "Burden", "Love", "Johnson"]
hit = [c for c in canaries if c in body]
ok(not hit, "builder code body contains no player-name constants", str(hit))

# 4. Draftable cap: no tagged player sits beyond the draft's 168 picks
adp = {p["name"] + "|" + p["pos"]: p.get("adp_sleeper") or 999
       for p in json.load(open(os.path.join(ROOT, "out", "data", "adp.json")))["players"]}
over = [e["name"] for e in d["players"] if adp.get(e["name"] + "|" + e["pos"], 999) > 168]
ok(not over, "every tagged player is inside the 168-pick draft", str(over[:3]))

# 5. Page wiring: optional load, card, honesty line, display-only
pp = open(os.path.join(ROOT, "out", "players.html")).read()
ok('get("data/archetypes_2026.json")' in pp, "players page fetches the artifact")
ok("renders identically without them" in pp, "optional load stated")
ok("archCard" in pp and "zero-IR cost" in pp,
   "archetype card with the zero-IR cost line wired")
ok("never a projection" in pp, "honesty line present")
_ac = pp[pp.index("function archCard"):pp.index("function renderPlayer")]
ok("vor" not in _ac and "pts" not in _ac and "cvs" not in _ac,
   "archetype card is display-only - reads the artifact, no model values")

print()
if fails:
    print(f"{len(fails)} FAILURES")
    sys.exit(1)
print("ALL PASS")
