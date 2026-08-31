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
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "out", "data")
FAILS = []


def ok(cond, label):
    print(("PASS  " if cond else "FAIL  ") + label)
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

if FAILS:
    print(f"\n{len(FAILS)} FAILURES")
    sys.exit(1)
print("\nALL PASS")
