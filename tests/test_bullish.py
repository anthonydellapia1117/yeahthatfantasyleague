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
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "out", "data")
sys.path.insert(0, os.path.join(ROOT, "src"))
from analyze_recency import HISTORY
from engine_lineage import json_content_sha256
fails = []


def ok(cond, name, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "  -> " + detail))
    if not cond:
        fails.append(name)


inp = json.load(open(os.path.join(D, "bullish_inputs_2026.json")))
d = json.load(open(os.path.join(D, "bullish_2026.json")))
try:
    _computed_at = datetime.datetime.fromisoformat(
        d["provenance"]["computed_at"])
    _computed_is_utc = (_computed_at.utcoffset() == datetime.timedelta(0))
    _computed_utc_date = _computed_at.astimezone(
        datetime.timezone.utc).date().isoformat()
except (KeyError, TypeError, ValueError):
    _computed_is_utc = False
    _computed_utc_date = None
ok(_computed_is_utc and
   d.get("provenance", {}).get("generated") == _computed_utc_date,
   "BULLISH timestamp is UTC and generated is its UTC date",
   f"generated {d.get('provenance', {}).get('generated')}, "
   f"computed_at {d.get('provenance', {}).get('computed_at')}")
inp_digest = inp.get("provenance", {}).get("engine_content_sha256", "")
tag_digest = d.get("provenance", {}).get("engine_content_sha256", "")
ok(len(inp_digest) == 64 and tag_digest == inp_digest,
   "BULLISH inputs and tags record one exact engine payload")
source_payloads = {
    name: json.load(open(os.path.join(D, name)))
    for name in ("ceiling_2026.json", "usage_2025.json", "goalline_2025.json",
                 "depth_charts.json", "crosswalk.json")
}
ok(inp.get("provenance", {}).get("input_content_sha256") ==
   {name: json_content_sha256(payload)
    for name, payload in source_payloads.items()},
   "BULLISH inputs record every committed source payload exactly")
ok(d.get("provenance", {}).get("inputs_content_sha256") ==
   json_content_sha256(inp),
   "BULLISH tags record the exact computed-input payload")
if os.environ.get("REQUIRE_DISPLAY_ENGINE_MATCH") == "1":
    eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
    ok(all(a.get("provenance", {}).get("engine_content_sha256") ==
           eng.get("content_sha256")
           for a in (source_payloads["ceiling_2026.json"], inp, d)),
       "pages-data repaired every display artifact to the current engine")

# 1. inputs: proportions carry k and n; thresholds carry distributions;
#    provenance states the proxy weakness and the Vegas window
thr = inp["thresholds"]
for k in ("wr_tprr", "rb_targets_pg", "te_route_part", "qb_rush_ypg"):
    ok(thr[k]["n"] >= 15 and thr[k]["p75"] > 0,
       f"threshold {k} carries a real distribution", str(thr[k]))
ok("pass-block snaps" in thr["note"], "route-proxy weakness stated")
ok("Week-1" in inp["provenance"]["vegas"]["source"],
   "Vegas window declared (the complete-coverage week)")
try:
    datetime.date.fromisoformat(inp["provenance"]["vegas"]["pulled"])
    _pulled_is_date = True
except (KeyError, TypeError, ValueError):
    _pulled_is_date = False
ok(_pulled_is_date, "Vegas provenance carries a parseable source pull date")
_games = os.path.join(HISTORY, "games.csv")
if os.path.exists(_games):
    _games_date = datetime.datetime.fromtimestamp(
        os.path.getmtime(_games), tz=datetime.timezone.utc).date().isoformat()
    ok(inp["provenance"]["vegas"]["pulled"] == _games_date,
       "Vegas provenance reports the cached source file's UTC fetch date",
       f"artifact {inp['provenance']['vegas']['pulled']}, file {_games_date}")
else:
    ok(_pulled_is_date and
       inp["provenance"]["vegas"]["pulled"] <=
       inp["provenance"]["generated"],
       "Vegas source date is plausible when the local cache is absent",
       f"pulled {inp['provenance']['vegas'].get('pulled')}, "
       f"generated {inp['provenance'].get('generated')}")
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
engine_for_ids = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
engine_ids = {str(p.get("sleeper_id") or "")
              for p in engine_for_ids["players"]}
tag_ids = [str(t.get("sleeper_id") or "") for t in d["tags"]]
ok(all(tag_ids) and len(tag_ids) == len(set(tag_ids)) and
   set(tag_ids).issubset(engine_ids),
   "every BULLISH tag carries one unique canonical Sleeper identity")
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
ok("bullishTag" in bp and "x.name === p.name" not in bp and
   "x.pos === p.pos" not in bp,
   "big board joins BULLISH tags by Sleeper identity, never raw name")
ok("bullChip" in drp and 'fetch("data/bullish_2026.json")' in drp,
   "room chip wired with optional load")
ok("never" in drp[drp.index("C5 BULLISH layer"):drp.index("C5 BULLISH layer") + 300]
   and "replacing" in drp[drp.index("C5 BULLISH layer"):drp.index("C5 BULLISH layer") + 300],
   "room states the tag sits beside the signal encoding, never replacing it")
for page, chip in ((bp, "bullishChip"), (drp, "bullChip")):
    seg = page[page.index(f"function {chip}"):]
    seg = seg[:seg.index("\n}")]
    ok("ttl_hours" in seg and "ageH" in seg, f"{chip} enforces the 72h TTL with age display")
ok("TAGS STALE" in bp and "TAGS STALE" in drp,
   "engine mismatch renders a neutral stale tag, never a current verdict")
players_page = open(os.path.join(ROOT, "out", "players.html")).read()
ok("pBullCurrent" in players_page and
   "BULLISH tags stale versus current board" in players_page,
   "players filter disables stale BULLISH semantics visibly")
builder = open(os.path.join(ROOT, "src", "build_bullish.py")).read()
ok("inputs_digest != engine_digest" in builder and
   "build_bullish_inputs.py first" in builder,
   "tag builder refuses inputs from a different engine payload")
inputs_builder = open(os.path.join(ROOT, "src", "build_bullish_inputs.py")).read()
ok("ceiling_digest != engine_digest" in inputs_builder and
   "build_ceiling.py first" in inputs_builder,
   "input builder refuses ceiling values from a different engine payload")
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
