#!/usr/bin/env python3
"""C1 guards: exact-scoring VOR, derived flex allocation, derived tier breaks.

Runs WITHOUT network: operates on draft_board.py logic, the committed flex
artifact, and the committed engine payload.
Run: python3 tests/test_vor.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import draft_board as db

fails = []


def ok(cond, name, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "  -> " + detail))
    if not cond:
        fails.append(name)


# 1. SCORING EXACTNESS. The table below is league ground truth, verified live
#    against BOTH league ids (2025: 1245905122328846336, 2026:
#    1389378429505241088) on 2026-08-26 - a fact table in the sense of the
#    governance exception, not an imported document constant. score() must
#    reproduce it to the tenth of a point, 6-pt passing TDs included.
SCORING = {
    "pass_yd": 0.04, "pass_td": 6.0, "pass_2pt": 2.0, "pass_int": -1.0,
    "rush_yd": 0.1, "rush_td": 6.0, "rush_2pt": 2.0,
    "rec": 1.0, "rec_yd": 0.1, "rec_td": 6.0, "rec_2pt": 2.0,
    "fum_lost": -2.0, "fum_rec_td": 6.0,
    "fgm_0_19": 3.0, "fgm_20_29": 3.0, "fgm_30_39": 3.0, "fgm_40_49": 4.0,
    "fgm_50p": 5.0, "xpm": 1.0, "fgmiss": -1.0, "xpmiss": -1.0,
    "def_td": 6.0, "sack": 1.0, "int": 2.0, "fum_rec": 2.0, "ff": 1.0,
    "safe": 2.0, "blk_kick": 2.0,
    "pts_allow_0": 10.0, "pts_allow_1_6": 7.0, "pts_allow_7_13": 4.0,
    "pts_allow_14_20": 1.0, "pts_allow_28_34": -1.0, "pts_allow_35p": -4.0,
    "def_st_td": 6.0, "def_st_ff": 1.0, "def_st_fum_rec": 1.0,
}

qb = {"pass_yd": 4000, "pass_td": 30, "pass_int": 10,
      "rush_yd": 300, "rush_td": 2, "fum_lost": 2}
# 160 + 180 - 10 + 30 + 12 - 4
ok(db.score(qb, SCORING) == 368.0, "QB line scores exactly under 6-pt passing TDs",
   str(db.score(qb, SCORING)))

wr = {"rec": 90, "rec_yd": 1200, "rec_td": 8, "rush_yd": 50, "rush_td": 1}
# 90 + 120 + 48 + 5 + 6
ok(db.score(wr, SCORING) == 269.0, "WR line scores exactly under full PPR",
   str(db.score(wr, SCORING)))

wr_with_generic = dict(wr, pts_ppr=999.0, adp_ppr=12.3)
ok(db.score(wr_with_generic, SCORING) == 269.0,
   "Sleeper's precomputed pts_ppr and adp_ fields never enter the score",
   str(db.score(wr_with_generic, SCORING)))

dst = {"pts_allow_0": 1, "sack": 3, "int": 2, "def_td": 1}
# 10 + 3 + 4 + 6
ok(db.score(dst, SCORING) == 23.0, "DEF line pays the points-allowed tier",
   str(db.score(dst, SCORING)))

k = {"fgm_0_19": 1, "fgm_40_49": 2, "fgm_50p": 1, "xpm": 3, "fgmiss": 1, "xpmiss": 1}
# 3 + 8 + 5 + 3 - 1 - 1
ok(db.score(k, SCORING) == 17.0, "K line pays distance tiers and miss penalties",
   str(db.score(k, SCORING)))

ok(db.score({"made_up_stat": 100}, SCORING) == 0.0,
   "stats the league does not pay are ignored")

# 2. FLEX ARTIFACT. Observed-behavior allocation, never an assumed split.
fx_path = os.path.join(ROOT, "out", "data", "flex_usage_2025.json")
ok(os.path.exists(fx_path), "flex usage artifact exists")
fx = json.load(open(fx_path))
n = fx["provenance"]["n"]
ok(sum(fx["counts"].values()) == n, "flex counts sum to n",
   f"{sum(fx['counts'].values())} vs {n}")
ok(abs(sum(fx["shares"].values()) - 1.0) < 0.01, "flex shares sum to ~1")
ok(sum(fx["allocation"].values()) == fx["flex_slots"],
   "allocation consumes exactly the league's flex slots")
for pos, (lo, hi) in fx["wilson95"].items():
    ok(lo <= fx["shares"][pos] <= hi, f"wilson interval brackets the {pos} share",
       f"{fx['shares'][pos]} not in [{lo},{hi}]")
ok("1092592577628426240" in fx["provenance"]["excluded"],
   "the 2024 shell exclusion is stated in provenance")
ok(n >= 150, "flex sample is a real season, not a fragment", str(n))

# 3. REPLACEMENT RANKS derive from lineup + allocation; the 50/50 assumption
#    is dead in the source.
slots = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF"]
rr = db.replacement_ranks(slots, 12, fx["allocation"])
ok(rr == {"QB": 12, "RB": 24 + fx["allocation"]["RB"],
          "WR": 24 + fx["allocation"]["WR"], "TE": 12 + fx["allocation"]["TE"],
          "K": 12, "DEF": 12},
   "replacement ranks = starters x teams + observed flex allocation", str(rr))
src = open(os.path.join(ROOT, "draft_board.py")).read()
ok("flex * teams * 0.5" not in src,
   "the assumed 50/50 flex split no longer exists in the source")
ok("load_flex_usage" in src and "greedy_flex_alloc" in src,
   "observed-behavior artifact with projection-greedy fallback, never a constant")

# 4. GREEDY FALLBACK fills flex with the best remaining player by points.
by_pos = {
    "RB": [{"pts": 300.0}, {"pts": 100.0}],
    "WR": [{"pts": 290.0}, {"pts": 120.0}],
    "TE": [{"pts": 280.0}, {"pts": 250.0}],
}
alloc = db.greedy_flex_alloc(by_pos, {"RB": 1, "WR": 1, "TE": 1}, 1, 1)
ok(alloc == {"RB": 0, "WR": 0, "TE": 1},
   "greedy flex takes the highest marginal player (TE2 250 beats WR2 120, RB2 100)",
   str(alloc))

# 5. TIER BREAKS derive per position from the drop distribution.
flat = [{"vor": 100.0 - i, "adp": i + 1} for i in range(20)]
ok(len(db.tiers(flat)) <= 2, "a flat VOR curve does not fragment into tiers",
   str(len(db.tiers(flat))))
cliff = ([{"vor": 100.0 - i, "adp": i + 1} for i in range(10)]
         + [{"vor": 40.0 - i, "adp": 11 + i} for i in range(10)])
ok(len(db.tiers(cliff)) == 2, "a 50-point cliff splits into exactly two tiers",
   str(len(db.tiers(cliff))))
tiny = [{"vor": 50.0 - 10 * i, "adp": i + 1} for i in range(5)]
ok(len(db.tiers(tiny)) == 1,
   "fewer than eight draftable players never claims tier structure")
ok(db.tiers(cliff, gap=1000.0) and len(db.tiers(cliff, gap=1000.0)) == 1,
   "an explicit gap still overrides the derivation")

# 6. ENGINE PAYLOAD carries the derivation.
eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
ok(eng.get("flex_source") == "observed_2025",
   "payload flex source is the observed-behavior artifact",
   str(eng.get("flex_source")))
ok(eng.get("flex_allocation") == fx["allocation"],
   "payload flex allocation matches the committed artifact")
pr = eng["replacement_ranks"]
ok(pr["RB"] == 24 + fx["allocation"]["RB"] and pr["WR"] == 24 + fx["allocation"]["WR"],
   "payload replacement ranks reflect the derived allocation", str(pr))

# FORWARD-PICK LAW: a multi-pick projection consumes its own selections.
# No player may appear more than once in any slot's forward sequence, and
# the sequence must respect the shared roster caps (the live bug: the same
# WR recommended at picks 24 AND 25 across the snake turn).
sys.path.insert(0, os.path.join(ROOT, "src"))
from forward_policy import roster_caps
caps = roster_caps(eng.get("flex_allocation", {}))
_primary = eng.get("draft_order_context", {}).get("primary_slot")
_reported_picks = eng.get("draft_order_context", {}).get("primary_picks")
ok(_primary == 4 and _reported_picks ==
   [4, 21, 28, 45, 52, 69, 76, 93, 100, 117, 124, 141, 148, 165] and
   [r["pick"] for r in eng["slots"]["4"]] == _reported_picks,
   "primary forward sequence is the exact reported slot-4 snake geometry",
   str((_primary, _reported_picks)))
for slot, rounds in eng["slots"].items():
    names = [r["primary"]["name"] for r in rounds if r.get("primary")]
    ok(len(set(names)) == len(names),
       f"slot {slot}: no player repeats in the forward-pick sequence")
    from collections import Counter as _C
    pc = _C(r["primary"]["pos"] for r in rounds if r.get("primary"))
    ok(all(pc[p] <= caps.get(p, 99) for p in pc),
       f"slot {slot}: forward sequence respects the shared roster caps",
       str(dict(pc)))

print()
if fails:
    print(f"{len(fails)} FAILURES")
    sys.exit(1)
print("ALL PASS")
