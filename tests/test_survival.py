#!/usr/bin/env python3
"""Guards on the survival model. Each encodes a bug that was live and shipped.

Run: python3 tests/test_survival.py
"""
import importlib.util, math, os, sys, csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))
spec = importlib.util.spec_from_file_location("eng", os.path.join(ROOT, "src", "engine_2026.py"))
eng = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eng)
from draft_order import _complete_slot_map

fails = []


def ok(cond, name, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "  -> " + detail))
    if not cond:
        fails.append(name)


# 1. CONTINUITY. The shipped 4-band step made ADP 24 vs 25 differ by 8,284x at
#    pick 48. No adjacent ADP pair may move survival by more than 5 points anywhere.
# The failure mode was a RATIO blowup from a step discontinuity, not a small
# absolute gap. Near the top of the board adjacent ADP slots legitimately differ by
# ~0.1 because sd is small there and the model is correctly confident. What must
# never happen is one ADP slot changing survival by a multiple.
def max_adjacent_ratio(surv):
    worst, where = 1.0, None
    for a in range(1, 200):
        for k in range(1, 169):
            lo, hi = surv(a, k), surv(a + 1, k)
            # Only where the number drives a decision. Deep in the Gaussian tail
            # every model has large ratios between tiny probabilities, and 0.0002
            # versus 0.0014 both read as "he is gone". At a 2 percent floor the
            # smooth model peaks at 2.5x and the old step function at 10.5x.
            if lo < 0.02 or hi < 0.02:
                continue
            r = max(hi / lo, lo / hi)
            if r > worst:
                worst, where = r, (a, k)
    return worst, where

worst, where = max_adjacent_ratio(eng.survival)
ok(worst < 4.0, "no ADP cliff: one ADP slot never multiplies survival",
   f"max {worst:.1f}x at ADP {where[0]}->{where[0]+1}, pick {where[1]}")

# And prove the guard actually bites: the shipped step function must fail it.
OLD = [(24, 5.46), (60, 13.63), (120, 24.01), (10 ** 9, 23.81)]
def old_survival(a, k):
    sd = next(s for hi, s in OLD if a <= hi)
    return max(0.0, min(1.0, 0.5 * math.erfc((k - a) / (sd * math.sqrt(2)))))
old_worst, _ = max_adjacent_ratio(old_survival)
ok(old_worst >= 4.0, "the guard would have caught the original step-function bug",
   f"old model max ratio only {old_worst:.1f}x")

# 1b. Nothing has been drafted at pick 1, so everyone is available.
ok(all(abs(eng.survival(a, 1) - 1.0) < 1e-9 for a in (1, 2, 5, 30, 150)),
   "survival at pick 1 is 1.0 for every player",
   f"ADP 1 gives {eng.survival(1, 1):.3f}")

# 2. sd is continuous and stays inside the observed range. It is NOT monotone -
#    that is INTERP's entire point: the empirical curve peaks near ADP 100 and
#    declines toward the end of the draft, which the audit showed a monotone
#    power law cannot express (docs/AUDIT_SURVIVAL_2026-08-12.md item C).
sds = [eng.sd_for(a) for a in range(1, 200)]
ok(max(abs(b - a) for a, b in zip(sds, sds[1:])) < 0.5, "sd has no jump")
lo = min(s for _, s in eng.ADP_SD_CURVE)
hi = max(s for _, s in eng.ADP_SD_CURVE)
ok(all(lo - 1e-9 <= s <= hi + 1e-9 for s in sds),
   "sd stays inside the observed bin range", f"range {min(sds):.2f}-{max(sds):.2f}")
ok(len(eng.ADP_SD_CURVE) == 12, "sd curve is the 12 audited bins")

# 3. MONOTONE + BOUNDED in the pick number.
ok(all(eng.survival(30, k) >= eng.survival(30, k + 1) - 1e-12 for k in range(1, 168)),
   "survival non-increasing in pick")
ok(all(0.0 <= eng.survival(a, k) <= 1.0 for a in (1, 30, 90, 150) for k in (1, 50, 168)),
   "survival stays in [0,1]")

# 4. DEEP TAIL. 1-erf collapses to exactly 0 past z~5 and trips the zero guard;
#    erfc keeps the real value.
ok(eng.survival(5, 60) > 0.0, "deep tail is positive, not a cancelled zero",
   f"got {eng.survival(5, 60)}")

# 5. CONDITIONAL form. Self-conditioning is identity; conditioning never exceeds 1.
ok(abs(eng.cond_survival(30, 40, 40) - 1.0) < 1e-9, "cond_survival(k,k) == 1")
ok(all(eng.cond_survival(a, k, 1) <= 1.0 + 1e-9 for a in (5, 30, 90) for k in (10, 60, 120)),
   "cond_survival never exceeds 1")
ok(eng.cond_survival(30, 40, 35) > eng.survival(30, 40) - 1e-9,
   "conditioning on availability raises survival, never lowers it")
ok(all(eng.cond_survival(30, k, 20) >= eng.cond_survival(30, k + 1, 20) - 1e-12
       for k in range(20, 168)),
   "cond_survival non-increasing in the target pick")
# Normalization invariance: the pick-1 normalization must cancel in every
# conditional ratio (it is a single S(1) factor on both sides).
ok(all(abs(eng.cond_survival(a, 60, 30)
           - (eng._raw_survival(a, 60) / eng._raw_survival(a, 30))) < 1e-9
       for a in (10, 25, 40) if eng._raw_survival(a, 30) > 1e-12),
   "conditional ratios are invariant to the pick-1 normalization")

# 5b. CALIBRATION BENCHMARK - the guard the power law showed was missing. The
#     shipped sd must beat the frozen step-function baseline on the conditional
#     decision quantity over the full historical pick table, evaluated
#     identically and deterministically. A future sd change that predicts worse
#     than the ORIGINAL model cannot ship. (In-sample eval; the leave-one-out
#     ordering that motivated INTERP is in docs/AUDIT_SURVIVAL_2026-08-12.md.)
def cond_brier(sdf):
    tot = n = 0.0
    for p in csv.DictReader(open(os.path.join(ROOT, "out", "picks.csv"))):
        d = p.get("adp_differential")
        if not d:
            continue
        try:
            d = float(d)
        except ValueError:
            continue
        y = float(p["overall"])
        adp = y - d
        c0 = 1
        while c0 <= min(y, 156):
            k = c0 + 12
            z1 = (c0 - adp) / (sdf(adp) * math.sqrt(2))
            zk = (k - adp) / (sdf(adp) * math.sqrt(2))
            s_from, s_to = 0.5 * math.erfc(z1), 0.5 * math.erfc(zk)
            pr = 0.0 if s_from <= 1e-12 else min(1.0, s_to / s_from)
            o = 1.0 if y >= k else 0.0
            tot += (pr - o) ** 2
            n += 1
            c0 += 4
    return tot / n

STEP_SD = lambda a: next(s for hi, s in OLD if a <= hi)
b_ship, b_step = cond_brier(eng.sd_for), cond_brier(STEP_SD)
ok(b_ship < b_step,
   "shipped sd beats the frozen step baseline on the decision quantity",
   f"shipped {b_ship:.5f} vs step {b_step:.5f}")

# 6. THE HARD GUARDRAIL. Franchise lift is display only and must reach no arithmetic
#    that touches a probability. Tested and rejected: pooled Brier got worse
#    (0.23030 -> 0.23050, p=0.9932). See out/tendency_backtest.json.
src = open(os.path.join(ROOT, "src", "engine_2026.py")).read()
body = src[src.index("def build_model"):]
bad = [ln.strip() for ln in body.splitlines()
       if ("gap_lift" in ln or "lift" in ln)
       and any(t in ln for t in ("survival(", "p_available", "p_gone", "vor *", "* lift"))]
ok(not bad, "franchise lift never enters a probability", "; ".join(bad[:2]))

# 7. The tendency table exists and its lifts are centred, not runaway.
tp = os.path.join(ROOT, "out", "positional_tendency.csv")
if os.path.exists(tp):
    lifts = [float(r["lift"]) for r in csv.DictReader(open(tp))]
    # K and DEF carry league base rates near 0.03, so honest ratios swing wider
    # there than for skill positions. Cambrias at 0.34 for DEF rd7-10 is 51 verified
    # picks, not noise. Bound the skill positions tightly and K/DEF loosely.
    skill = [float(r["lift"]) for r in csv.DictReader(open(tp))
             if r["pos"] in ("QB", "RB", "WR", "TE")]
    allv = lifts
    # Bounds set from what shrinkage actually produces on this data, not a guess.
    # The extremes are real and well sampled: Cambrias wait on QB (0.63, n=39,
    # their first-QB round is 8.26, latest in the league) and Pung & Tralie reach
    # for one (1.68, n=39). A runaway would be a shrinkage failure, not a habit.
    ok(0.5 < min(skill) and max(skill) < 2.0, "skill-position lifts stay plausible",
       f"range {min(skill):.2f}-{max(skill):.2f}")
    ok(0.25 < min(allv) and max(allv) < 3.0, "no runaway lift anywhere",
       f"range {min(allv):.2f}-{max(allv):.2f}")

# 8. SIM QUARANTINE. Simulator output must never reach verdict logic. The sim
#    lives between SIM-QUARANTINE markers in the app; outside those markers the
#    app may not reference SimState/runSims/renderSimResults except in the
#    one-time button wiring, and the sim block may not call the verdict path.
app = open(os.path.join(ROOT, "out", "draft_room.html")).read()
b0, b1 = app.index("SIM-QUARANTINE-BEGIN"), app.index("SIM-QUARANTINE-END")
sim_block = app[b0:b1]
outside = app[:b0] + app[b1:]
# sim symbols may appear outside the markers ONLY in the one-time button
# wiring block. Count occurrences outside markers; the wiring accounts for
# a known number of each - anything beyond that is a leak into app logic.
wiring_allow = {"SimState.results": 1, "SimState.running": 3,
                "runSims(": 1, "renderSimResults(": 1}
leaks = [f"{tok} x{outside.count(tok)}" for tok, allowed in wiring_allow.items()
         if outside.count(tok) > allowed]
ok(not leaks, "sim symbols never leak beyond the quarantine and its wiring",
   "; ".join(leaks))
ok(all(tok not in sim_block for tok in
       ("verdictChip(", "wait_or_reach", "p_gone", 'class="verdict', ".verdict")),
   "sim block never touches verdict logic")
ok("condSurvival(" not in sim_block,
   "sim never rewrites displayed survival numbers")
ok('class="sim"' in app and "simbadge" in app and "scenario, not a forecast" in app,
   "sim quarantine styling present (dashed border, SIM badge, caption)")

# 9. GRADE ISOLATION. The pick grade is presentation, not decision. The
#    function between GRADE markers may read only the five sanctioned input
#    families; forbidden fields are structurally absent. And the grade never
#    feeds a verdict: verdict logic and the engine contain no grade tokens.
g0, g1 = app.index("GRADE-BEGIN"), app.index("GRADE-END")
# scan CODE only - the block's documentation legitimately NAMES the banned
# inputs; what must never appear is a code reference to them
grade_code = "\n".join(ln for ln in app[g0:g1].splitlines()
                        if not ln.strip().startswith(("//", "*", "/*")))
ok(all(tok not in grade_code for tok in
       ("lift", "playcaller", "proe", "vacated", "trending", "tendency",
        "Intel.", "SimState")),
   "grade code reads none of the banned fields (lifts, team intel, trending, sim)",
   "; ".join(tok for tok in ("lift", "playcaller", "proe", "vacated",
                             "trending", "tendency", "Intel.", "SimState")
             if tok in grade_code))
ok(all(tok not in grade_code for tok in
       ("verdictChip", "wait_or_reach", 'liveVerdict')),
   "grade block contains no verdict logic")
vc0 = app.index("function verdictChip")
vc_block = app[vc0:app.index("}", vc0)]
ok("pickGrade" not in vc_block and "gradeBand" not in vc_block,
   "verdictChip never reads the grade")
ok("pickGrade" not in src and "gradeBand" not in src,
   "the engine (verdict source of truth) contains no grade code")
ok('"gnum"' in app and "GRADE_RED_MAX = 39" in app and "GRADE_AMBER_MAX = 69" in app,
   "band thresholds are the named constants the anchors pin")

# 10. OVERLAY ISOLATION (Phase B). The conviction overlay is display plus ONE
#     sanctioned decision role - the coin-flip tie-break toward bulls. It must
#     reach no survival or wait-or-reach arithmetic; with an empty board the
#     model and both renderings are byte-identical to a build with no overlay.
import copy
import inspect
import json

# 10a. the frozen math and build_model never see the overlay - it is applied
#      AFTER build_model as a pure transform, so the tokens are structurally
#      absent from everything that computes a probability or a verdict.
_overlay_tokens = ("my_board", "coin_break", "apply_overlay", "BULL", "BEAR")
_hits = []
for _f in ("fit_sd_curve", "sd_for", "_raw_survival", "survival",
           "cond_survival", "build_model"):
    _src = inspect.getsource(getattr(eng, _f))
    _hits += [f"{_f}:{t}" for t in _overlay_tokens if t in _src]
ok(not _hits, "overlay reaches no survival or verdict arithmetic (engine)",
   "; ".join(_hits))

# 10b. app-side quarantine: overlay symbols live only in the OVERLAY block
#      plus counted display wiring, mirroring the sim-quarantine pattern.
o0, o1 = app.index("OVERLAY-BEGIN"), app.index("OVERLAY-END")
overlay_block = app[o0:o1]
out_app = app[:o0] + app[o1:]
_allow = {"yourCallChip(": 4, "flipBreakText(": 1, "tierResort(": 1,
          "coin_break": 2, "my_board": 0, "Overlay.": 0}
_leaks = [f"{tok} x{out_app.count(tok)} (allowed {n})"
          for tok, n in _allow.items() if out_app.count(tok) > n]
ok(not _leaks, "overlay symbols never leak beyond the block and its wiring",
   "; ".join(_leaks))
ok(all(t not in overlay_block for t in
       ("verdictChip", "wait_or_reach", "liveVerdict", "setName(", "bignm",
        "condSurvival(", "survival(")),
   "overlay block computes no verdict and no probability - text only")

# 10c. byte-identity: an empty board changes nothing. The shipped board is
#      empty, so today's committed JSON and markdown are the baseline.
ok(eng.load_my_board() == [], "shipped data/my_board.csv carries zero calls")
m0 = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
md_shipped = open(os.path.join(ROOT, "out", "decision_cards_2026.md")).read()
from engine_lineage import is_valid as valid_engine_digest
ok(valid_engine_digest(m0), "engine carries a self-verifying content digest")
ok(m0["content_sha256"] in md_shipped,
   "decision cards name the exact engine content they render")
m1 = eng.apply_overlay(copy.deepcopy(m0), [])
ok(json.dumps(m1, sort_keys=True) == json.dumps(m0, sort_keys=True),
   "empty board: apply_overlay returns the model byte-identical")
ok(eng.render_markdown(m1) == md_shipped,
   "empty board: rendered markdown byte-identical to the shipped cards")

# 10d. populated board: the verdict-subject rule holds. A bull in a coin flip
#      earns the tie-break; nothing else in the model moves.
_flip_round = next(r for rounds in m0["slots"].values() for r in rounds
                   if r.get("coin_flips"))
_bull = _flip_round["coin_flips"][0]
_bear = next(p["name"] for p in m0["players"] if p["name"] != _bull)
_calls = [{"player": _bull, "call": "BULL", "move": "+1 tier",
           "reason": "guard fixture", "source": "test", "confidence": "",
           "date": "2026-08-13"},
          {"player": _bear, "call": "BEAR", "move": "-1 tier",
           "reason": "guard fixture", "source": "test", "confidence": "",
           "date": "2026-08-13"}]
m2 = eng.apply_overlay(copy.deepcopy(m0), _calls)
_subject_moved = [
    f"slot {s} rd {r2['round']}"
    for s in m0["slots"]
    for r0, r2 in zip(m0["slots"][s], m2["slots"][s])
    if (r0.get("primary") or {}).get("name") != (r2.get("primary") or {}).get("name")
    or r0.get("wait_or_reach") != r2.get("wait_or_reach")]
ok(not _subject_moved,
   "populated board: every primary and every wait-or-reach verdict unchanged",
   "; ".join(_subject_moved[:3]))
_r2 = next(r for rounds in m2["slots"].values() for r in rounds
           if r.get("coin_flips") and _bull in
           [r["primary"]["name"]] + r["coin_flips"])
ok(_r2.get("coin_break", {}).get("toward") == _bull
   if _r2["primary"]["name"] != _bull else "coin_break" in _r2,
   "bull in a coin flip earns the tie-break toward the call")
_brow = next(c for c in m2["my_board"] if c["call"] == "BULL")
ok(_brow["matched"] and all(
    0.0 <= s <= 1.0 and abs(s - round(eng.survival(_brow["adp"], k), 3)) < 1e-9
    for picks in _brow["survival_to_slots"].values() for k, s in picks),
   "bull survival-to-slot-picks recomputes exactly from frozen survival()")

# 10e. Owner draft slot is identity, not roster_id. The real league's stable
#      roster_id happens to be 7, so a slot-7 implementation looks correct until
#      the draw lands anywhere else. Drive a synthetic slot-3 draw and prove the
#      overlay follows those pick windows. Before the draw, no seat may be
#      assumed: all twelve slot windows must remain available in the artifact.
_slot3 = copy.deepcopy(m0)
_slot3["overlay_pick_basis"] = {
    "status": "drawn", "slot": 3, "source": "draft_order",
    "coverage": "all_slots",
}
_slot3 = eng.apply_overlay(_slot3, _calls)
_slot3_bull = next(c for c in _slot3["my_board"] if c["call"] == "BULL")
_slot3_expected = [r["pick"] for r in _slot3["slots"]["3"]][:4]
ok([k for k, _s in _slot3_bull["survival_to_my_picks"]] == _slot3_expected,
   "overlay follows a drawn non-7 draft slot",
   f"expected {_slot3_expected}, got "
   f"{[k for k, _s in _slot3_bull['survival_to_my_picks']]}")
ok("Survival to picks (slot 3)" in eng.render_markdown(_slot3) and
   "Draft-order source: draft_order; owner slot 3" in
   eng.render_markdown(_slot3),
   "drawn overlay labels the resolved seat and its evidence")

_undrawn = copy.deepcopy(m0)
_undrawn["overlay_pick_basis"] = {
    "status": "undrawn", "slot": None, "source": "identity_placeholder",
    "coverage": "all_slots",
}
_undrawn = eng.apply_overlay(_undrawn, _calls)
_undrawn_bull = next(c for c in _undrawn["my_board"] if c["call"] == "BULL")
ok(set(_undrawn_bull.get("survival_to_slots", {})) ==
   {str(s) for s in range(1, m0["league"]["teams"] + 1)} and
   "survival_to_my_picks" not in _undrawn_bull,
   "undrawn overlay assumes no seat and carries all twelve slot windows",
   f"keys {sorted(_undrawn_bull.get('survival_to_slots', {}))}")
ok("no seat is assumed" in eng.render_markdown(_undrawn) and
   "all 12 slots precomputed; no owner slot assumed" in
   eng.render_markdown(_undrawn),
   "undrawn rendering labels the all-slot coverage instead of a default")
_unavailable = copy.deepcopy(_undrawn)
_unavailable["overlay_pick_basis"] = {
    "status": "unavailable", "slot": None,
    "source": "draft_endpoint_unavailable", "coverage": "all_slots",
}
ok("endpoint was unavailable" in eng.render_markdown(_unavailable),
   "draft-order endpoint failure is visible in the generated decision cards")

_uid, _rid = m0["league"]["anthony_user_id"], m0["league"]["anthony_roster_id"]
_primary = eng.resolve_owner_slot(
    {"status": "pre_draft", "draft_order": {_uid: 11},
     "slot_to_roster_id": {"3": _rid}},
    _uid, _rid, 12)
ok(_primary == {"drawn": True, "slot": 11, "source": "draft_order"},
   "draft_order user mapping outranks a conflicting slot map", str(_primary))
_fallback = eng.resolve_owner_slot(
    {"status": "pre_draft", "draft_order": None,
     "slot_to_roster_id": {
         str(s): (3 if s == 7 else _rid if s == 3 else s)
         for s in range(1, 13)}},
    _uid, _rid, 12)
ok(_fallback == {"drawn": True, "slot": 3,
                  "source": "slot_to_roster_id"},
   "non-identity slot map resolves by roster identity", str(_fallback))
_identity = eng.resolve_owner_slot(
    {"status": "pre_draft", "draft_order": None,
     "slot_to_roster_id": {str(s): s for s in range(1, 13)}},
    _uid, _rid, 12)
ok(_identity == {"drawn": False, "slot": None,
                  "source": "identity_placeholder"},
   "identity slot map means order undrawn, not owner in roster-id seat",
   str(_identity))
_unknown_teams_partial = eng.resolve_owner_slot(
    {"status": "pre_draft", "draft_order": None,
     "slot_to_roster_id": {"1": 2, "2": 3}},
    _uid, 2, None)
ok(_unknown_teams_partial == {
       "drawn": True, "slot": None, "source": "team_count_unavailable"},
   "unknown team count cannot turn a partial unique map into a resolved seat",
   str(_unknown_teams_partial))
ok(_complete_slot_map({"1": 2, "2": 3}, None) is None,
   "complete-permutation helper rejects unique partial maps without team count")
try:
    eng.resolve_owner_slot(
        {"status": "pre_draft", "draft_order": {_uid: 1}}, _uid, _rid)
    _omitted_team_count_rejected = False
except TypeError:
    _omitted_team_count_rejected = True
ok(_omitted_team_count_rejected,
   "owner-slot resolver requires its team-count contract explicitly")
for _invalid_teams in (None, 0, -1, True, 12.9, "12", float("inf")):
    try:
        _invalid_team_result = eng.resolve_owner_slot(
            {"status": "pre_draft", "draft_order": {_uid: 1},
             "slot_to_roster_id": {str(s): s for s in range(1, 13)}},
            _uid, _rid, _invalid_teams)
    except Exception as exc:
        _invalid_team_result = {"exception": type(exc).__name__}
    ok(_invalid_team_result == {
           "drawn": True, "slot": None,
           "source": "team_count_unavailable"},
       f"invalid team count {_invalid_teams!r} fails closed",
       str(_invalid_team_result))
_unknown_teams_complete = eng.resolve_owner_slot(
    {"status": "pre_draft", "draft_order": None,
     "slot_to_roster_id": {
         str(s): (3 if s == 7 else _rid if s == 3 else s)
         for s in range(1, 13)}},
    _uid, _rid, None)
ok(_unknown_teams_complete == {
       "drawn": True, "slot": None, "source": "team_count_unavailable"},
   "unknown team count refuses even a plausible full-looking slot map",
   str(_unknown_teams_complete))
_unknown_teams_order = eng.resolve_owner_slot(
    {"status": "pre_draft", "draft_order": {_uid: 3},
     "slot_to_roster_id": None},
    _uid, _rid, None)
ok(_unknown_teams_order == {
       "drawn": True, "slot": None, "source": "team_count_unavailable"},
   "unknown team count cannot validate a draft_order slot either",
   str(_unknown_teams_order))
for _invalid_slot in (True, 3.5, float("inf")):
    _invalid_slot_result = eng.resolve_owner_slot(
        {"status": "drafting", "draft_order": {_uid: _invalid_slot},
         "slot_to_roster_id": None},
        _uid, _rid, 12)
    ok(_invalid_slot_result == {
           "drawn": True, "slot": None, "source": "drawn_unresolved"},
       f"malformed draft_order slot {_invalid_slot!r} fails closed",
       str(_invalid_slot_result))
_boolean_roster_map = {str(s): s for s in range(1, 13)}
_boolean_roster_map["1"] = True
ok(_complete_slot_map(_boolean_roster_map, 12) is None,
   "boolean roster id cannot masquerade as slot-map value 1")
try:
    eng.derive_overlay_pick_basis({
        "draft_order": {"somebody-else": 4},
        "slot_to_roster_id": {"2": 99, "7": 98},
    })
    _unresolved_loud = False
except RuntimeError:
    _unresolved_loud = True
ok(_unresolved_loud,
   "drawn-but-unresolvable owner slot fails before artifact generation")
for _bad_draft, _label in [
    ({"status": "drafting", "draft_order": None,
      "slot_to_roster_id": None}, "started draft with missing order data"),
    ({"status": "pre_draft", "draft_order": None,
      "slot_to_roster_id": {"1": 1}}, "partial identity map"),
    ({"status": "pre_draft", "draft_order": None,
      "slot_to_roster_id": {str(s): (7 if s in (2, 3) else s)
                             for s in range(1, 13)}},
     "duplicate roster assignment"),
]:
    try:
        eng.derive_overlay_pick_basis(_bad_draft)
        _bad_loud = False
    except RuntimeError:
        _bad_loud = True
    ok(_bad_loud, f"{_label} fails loud instead of choosing a plausible seat")
_overlay_source = inspect.getsource(eng.apply_overlay)
ok(".get(7)" not in _overlay_source and "slot-7" not in _overlay_source,
   "overlay contains no seat-7 lookup or claim")
m3 = copy.deepcopy(m2)
m3.pop("my_board")
for rounds in m3["slots"].values():
    for r in rounds:
        r.pop("coin_break", None)
ok(json.dumps(m3, sort_keys=True) == json.dumps(m0, sort_keys=True),
   "overlay adds ONLY my_board and coin_break - nothing else in the model moves")
_md2 = eng.render_markdown(m2)
ok("MY BOARD" in _md2 and f"break toward your call - {_bull}" in _md2,
   "populated board renders the MY BOARD section and the tie-break line")
ok(eng.render_markdown(m3) == md_shipped,
   "strip the overlay fields and the markdown is the shipped cards again")

print()
print(f"{len(fails)} FAILURES" if fails else "ALL PASS")
sys.exit(1 if fails else 0)
