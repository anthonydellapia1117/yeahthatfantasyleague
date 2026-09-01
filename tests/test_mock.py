#!/usr/bin/env python3
"""Post-merge item 1 guards: the mock-draft validation artifact.

Validates out/data/mock_drafts_2026.json (committed; the builder reads the
committed engine payload and picks archive, no network).
"""
import json
import contextlib
import importlib.util
import io
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "out", "data")
FAILS = []


def ok(cond, label, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label +
          ("" if cond or not detail else "  -> " + detail))
    if not cond:
        FAILS.append(label)


m = json.load(open(os.path.join(D, "mock_drafts_2026.json")))
eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))

prov = m["provenance"]
ok(all(k in prov for k in ("generated", "engine_generated",
                           "engine_content_sha256", "method",
                           "kdef_window", "finding", "scope",
                           "primary_slot", "reference_slots")),
   "provenance complete, the naive-VOR finding stated")
ok(prov["engine_content_sha256"] == eng["content_sha256"],
   "mock records the exact engine content it consumed")
ok(prov["kdef_window"]["observed_n"] > 0,
   "opponent K/DEF window derived from observed league drafts")

ok(prov["primary_slot"] == 4 and
   list(m["slots"].keys())[0] == "4" and
   set(m["slots"].keys()) == {str(s) for s in range(1, 13)} and
   set(prov["reference_slots"]) == ({*range(1, 13)} - {4}),
   "real slot 4 leads while all eleven reference slots are simulated")

CAPS = {"QB": 2, "RB": 4, "WR": 4, "TE": 2, "K": 1, "DEF": 1}
for slot, s in m["slots"].items():
    ok(len(s["picks"]) == 14, f"slot {slot}: full 14-round draft")
    names = [p["name"] + "|" + p["pos"] for p in s["picks"]]
    ok(len(set(names)) == len(names), f"slot {slot}: no duplicate players")
    ok(all(s["sanity"].values()), f"slot {slot}: sanity checks all pass")
    c = s["position_counts"]
    ok(all(c.get(pos, 0) <= cap for pos, cap in CAPS.items()),
       f"slot {slot}: roster within the derived positional caps")
    ok(c.get("K", 0) == 1 and c.get("DEF", 0) == 1,
       f"slot {slot}: exactly one K and one DEF")
    ok(len(s["starters"]) == 9, f"slot {slot}: nine starter slots filled")
    for key in ("starter_pts_board", "starter_pts_naive_vor",
                "starter_pts_adp_chalk", "board_minus_chalk",
                "board_minus_naive"):
        ok(key in s, f"slot {slot}: {key} reported")
    ok(all(p["round"] == i + 1 for i, p in enumerate(s["picks"])),
       f"slot {slot}: one pick per round in order")
    ok("naive_vor_picks" in s and len(s["naive_vor_picks"]) == 14,
       f"slot {slot}: naive-VOR comparison roster preserved")

# the validation's own accountability: the board must not lose to chalk
# at any simulated slot - if it ever does, that belongs in the artifact
# and this guard forces the conversation
for slot, s in m["slots"].items():
    ok(s["board_minus_chalk"] > 0,
       f"slot {slot}: board policy beats ADP chalk on projected starters")

# Exact current-input proof. A same-day engine rebuild once left 14 tier values
# stale while engine_generated still matched by date, so date equality alone is
# not a sufficient oracle. Rebuild, compare, and restore the committed bytes.
sys.path.insert(0, os.path.join(ROOT, "src"))
_spec = importlib.util.spec_from_file_location(
    "ytfl_mock_builder", os.path.join(ROOT, "src", "mock_draft.py"))
_builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_builder)
_artifact = os.path.join(D, "mock_drafts_2026.json")
_orig = open(_artifact, "rb").read()
try:
    with contextlib.redirect_stdout(io.StringIO()):
        _builder.main()
    _rebuilt = json.load(open(_artifact))
finally:
    with open(_artifact, "wb") as _fh:
        _fh.write(_orig)
_expected, _actual = dict(m), dict(_rebuilt)
_expected["provenance"] = dict(_expected["provenance"])
_actual["provenance"] = dict(_actual["provenance"])
_expected["provenance"].pop("generated", None)
_actual["provenance"].pop("generated", None)
ok(_expected == _actual,
   "mock artifact rebuilds exactly from the current engine and picks")

# RxR policy contract. Python is canonical; the browser mirror must reproduce
# the complete score vector, Python's four-decimal ties-to-even behavior, and
# every loud state error. The corpus includes current slot-4 geometry plus
# deterministic edge cases and is rebuilt whenever the engine moves.
from forward_policy import score_candidates
_ref_path = os.path.join(D, "rxr_policy_reference.json")
_ref = json.load(open(_ref_path))
ok(_ref.get("engine_content_sha256") == eng.get("content_sha256") and
   _ref.get("primary_slot") == eng.get("draft_order_context", {}).get("primary_slot"),
   "RxR parity corpus is tied to the exact engine and primary slot")
ok(len(_ref.get("cases", [])) >= 12 and len(_ref.get("error_cases", [])) >= 4,
   "RxR parity corpus covers real geometry, cap, identity, floor, and error states")
for _case in _ref["cases"]:
    ok(score_candidates(_case["pool"], _case["roster"],
                        _case["baselines"], _case["caps"]) == _case["expected"],
       f"RxR Python reference reproduces: {_case['name']}")
for _case in _ref["error_cases"]:
    try:
        score_candidates(_case["pool"], _case["roster"],
                         _case["baselines"], _case["caps"])
        _err = ""
    except ValueError as _exc:
        _err = str(_exc)
    ok(_case["error"] in _err,
       f"RxR Python fails loud: {_case['name']}", _err)

_same = next(c for c in _ref["cases"]
             if c["name"] == "same_display_name_distinct_ids")
ok(_same["roster"][0]["name"] == _same["pool"][0]["name"] and
   _same["roster"][0]["sleeper_id"] != _same["pool"][0]["sleeper_id"] and
   _same["expected"][0]["eligible"] and
   _same["expected"][0]["marginal_lineup_gain_raw"] > 0,
   "same display name with a different Sleeper id remains a distinct action")
_mutation = next(c for c in _ref["cases"]
                 if c["name"] == _ref["mutation_case"])
_canonical_leader = next(r["player_id"] for r in _mutation["expected"]
                         if r["policy_rank"] == 1)
_mutated_leader = max(_mutation["pool"], key=lambda p: p["vor"])["sleeper_id"]
ok(_canonical_leader != _mutated_leader,
   "deliberate VOR-first scoring mutation breaks the parity fixture")

_node_script = r'''
const fs=require("fs"),vm=require("vm");
vm.runInThisContext(fs.readFileSync("out/rxr_policy.js","utf8"));
const ref=JSON.parse(fs.readFileSync("out/data/rxr_policy_reference.json"));
for(const x of ref.round4){
  if(RxRPolicy.pythonRound4(x.input)!==x.expected) throw new Error("round4");
}
for(const c of ref.cases){
  const got=RxRPolicy.scoreCandidates(c.pool,c.roster,c.baselines,c.caps);
  if(JSON.stringify(got)!==JSON.stringify(c.expected)) throw new Error(c.name);
}
for(const c of ref.error_cases){
  let msg=""; try{ RxRPolicy.scoreCandidates(c.pool,c.roster,c.baselines,c.caps); }
  catch(e){ msg=e.message; }
  if(!msg.includes(c.error)) throw new Error("error:"+c.name+":"+msg);
}
console.log("RXR JS PARITY OK");
'''
_node = subprocess.run(["node", "-e", _node_script], cwd=ROOT,
                       capture_output=True, text=True)
ok(_node.returncode == 0 and "RXR JS PARITY OK" in _node.stdout,
   "RxR JavaScript score vectors and state errors match Python",
   (_node.stderr or _node.stdout).strip())

from build_rxr_reference import main as _build_rxr_reference
_ref_orig = open(_ref_path, "rb").read()
try:
    with contextlib.redirect_stdout(io.StringIO()):
        _build_rxr_reference()
    _ref_rebuilt = open(_ref_path, "rb").read()
finally:
    with open(_ref_path, "wb") as _fh:
        _fh.write(_ref_orig)
ok(_ref_orig == _ref_rebuilt,
   "RxR parity corpus rebuilds byte-exactly from the current engine")

_engine_source = open(os.path.join(ROOT, "src", "engine_2026.py")).read()
ok("pick_marginal([r for r, _s in likely], proj_roster,\n                                     baseline, None)" not in _engine_source,
   "engine has no uncapped Marginal Policy fallback")
ok('r["name"] not in consumed' not in _engine_source and
   'consumed.add(prim["name"])' not in _engine_source and
   "player_id(r) not in consumed" in _engine_source and
   "consumed.add(player_id(prim))" in _engine_source,
   "engine forward state consumes canonical player ids, never display names")
_mock_source = open(os.path.join(ROOT, "src", "mock_draft.py")).read()
ok('["name"] + "|" + p["pos"]' not in _mock_source and
   "player_id(p)" in _mock_source,
   "mock taken and lineup state use canonical player ids, never display names")

if FAILS:
    print(f"\n{len(FAILS)} FAILURES")
    sys.exit(1)
print("\nALL PASS")
