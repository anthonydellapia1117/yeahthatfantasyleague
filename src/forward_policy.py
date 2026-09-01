#!/usr/bin/env python3
"""The shared forward-pick policy - one layer, consumed by every multi-pick
projection (the engine's per-slot decision cards and the mock-draft
simulator alike).

THE LAW THIS MODULE EXISTS FOR: any projection that solves more than one
pick must consume its own prior selections - each projected pick leaves
the pool, and the next pick is solved with the marginal-lineup /
roster-need policy against the REMAINING pool. Solving picks
independently against an unchanged pool recommends the same player at
consecutive picks (observed live: the same WR at picks 24 and 25 across
a snake turn) and duplicates elite positions (caught by the M1 mock
validation). Both are the same defect; this module is the single fix.

The policy, identical to the one the M1 validation settled on:
  score(candidate) = improvement to the optimal starting lineup where
  every empty slot holds a replacement-level phantom (the engine's own
  baselines), VOR as the tie-break once the lineup no longer improves,
  positional caps derived from the league's observed flex allocation
  (max simultaneous starters + one injury spare, a stated convention).
"""
import math
from collections import defaultdict

FLEX_OK = ("RB", "WR", "TE")
BASE_SLOTS = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "K": 1, "DEF": 1}
POLICY_POSITIONS = ("QB", "RB", "WR", "TE")


def _finite_number(value):
    return (not isinstance(value, bool)
            and isinstance(value, (int, float))
            and math.isfinite(value))


def player_id(player):
    """Canonical action identity.

    Sleeper ids are the join key everywhere the policy makes or consumes a
    selection.  Display names are deliberately not accepted as a fallback:
    aliases and same-name players are a proven defect class in this repo.
    """
    value = player.get("player_id") or player.get("sleeper_id")
    if value is None or str(value).strip() == "":
        raise ValueError(f"policy player lacks canonical id: {player!r}")
    return str(value)


def _validate_baselines(baselines):
    missing = sorted(set(BASE_SLOTS) - set(baselines))
    if missing:
        raise ValueError(f"policy baselines incomplete: {missing}")
    bad = sorted(k for k in BASE_SLOTS if not _finite_number(baselines[k]))
    if bad:
        raise ValueError(f"policy baselines non-finite: {bad}")


def _validate_caps(caps):
    if caps is None:
        raise ValueError("policy caps are required")
    missing = sorted(set(POLICY_POSITIONS) - set(caps))
    if missing:
        raise ValueError(f"policy caps incomplete: {missing}")
    bad = sorted(k for k in POLICY_POSITIONS
                 if not _finite_number(caps[k]) or caps[k] < 0)
    if bad:
        raise ValueError(f"policy caps invalid: {bad}")


def phantom_lineup_pts(players, baselines):
    """Optimal starter points with replacement-level phantoms in empty
    slots - the lineup value function the marginal policy maximizes."""
    _validate_baselines(baselines)
    by_pos = defaultdict(list)
    for p in sorted(players, key=lambda x: -x["pts"]):
        if p.get("pos") not in BASE_SLOTS:
            raise ValueError(f"unknown policy position: {p.get('pos')!r}")
        if not _finite_number(p.get("pts")):
            raise ValueError(f"policy player has non-finite pts: {player_id(p)}")
        by_pos[p["pos"]].append(p)
    total = 0.0
    used = set()

    def take(pos, n):
        nonlocal total
        got = 0
        for p in by_pos.get(pos, []):
            if got == n:
                break
            k = player_id(p)
            if k not in used:
                used.add(k)
                total += max(p["pts"], baselines[pos])
                got += 1
        while got < n:
            total += baselines[pos]
            got += 1

    take("QB", 1), take("RB", 2), take("WR", 2), take("TE", 1)
    flex = [p for pos in FLEX_OK for p in by_pos.get(pos, [])
            if player_id(p) not in used]
    flex_phantom = max(baselines[p] for p in FLEX_OK)
    total += max([p["pts"] for p in flex] + [flex_phantom])
    take("K", 1), take("DEF", 1)
    return total


def starter_caps(flex_alloc):
    """Maximum SIMULTANEOUS starters per position - the feasibility law for
    starter-construction projections (the VONA tree's seven rounds). Base
    slots, plus the flex slot only where the league has actually flexed the
    position, with NO injury spare: a seven-round path is building the
    lineup itself, and a position beyond its startable count is a wasted
    starter slot, the exact defect class caught three times now (M1 naive
    max-VOR, the back-to-back duplicate pick, three-early-TEs in the tree).
    """
    caps = {}
    for pos, k in BASE_SLOTS.items():
        flexes = 1 if flex_alloc.get(pos, 0) > 0 and pos in FLEX_OK else 0
        caps[pos] = k + flexes
    return caps


def roster_caps(flex_alloc):
    """A position may hold at most its maximum simultaneous starters (base
    slots, plus the flex slot only where the league has actually flexed the
    position) plus ONE injury spare - a stated convention."""
    caps = {}
    for pos, k in BASE_SLOTS.items():
        flexes = 1 if flex_alloc.get(pos, 0) > 0 and pos in FLEX_OK else 0
        caps[pos] = k + flexes + (1 if pos not in ("K", "DEF") else 0)
    return caps


def pick_marginal(pool, roster, baselines, caps=None):
    """Best next pick from pool given the picks already projected/made.

    pool    candidate dicts with name/pos/pts/vor (already filtered for
            availability and any survival floor by the caller)
    roster  dicts of the picks this projection has already consumed
    Returns the chosen candidate, or None on an empty/capped-out pool.
    """
    _validate_caps(caps)
    scores = score_candidates(pool, roster, baselines, caps)
    leader = next((s for s in scores if s["policy_rank"] == 1), None)
    return None if leader is None else pool[leader["input_index"]]


def score_candidates(pool, roster, baselines, caps):
    """Return the complete one-step Marginal Policy score vector.

    Records stay in the caller's input order.  Only QB/RB/WR/TE are inside the
    modeled action domain; K and DEF remain visible projection floors with no
    policy score.  Ranking exactly preserves the existing selection law:
    four-decimal marginal lineup gain, then VOR, then input-first stability.
    """
    _validate_baselines(baselines)
    _validate_caps(caps)

    roster_ids = [player_id(p) for p in roster]
    if len(set(roster_ids)) != len(roster_ids):
        raise ValueError("policy roster contains a duplicate player id")
    pool_ids = [player_id(p) for p in pool]
    if len(set(pool_ids)) != len(pool_ids):
        raise ValueError("policy pool contains a duplicate player id")
    overlap = sorted(set(roster_ids) & set(pool_ids))
    if overlap:
        raise ValueError(f"policy pool overlaps roster: {overlap}")

    counts = defaultdict(int)
    for p in roster:
        pos = p.get("pos")
        if pos not in BASE_SLOTS:
            raise ValueError(f"unknown policy position: {pos!r}")
        if not _finite_number(p.get("pts")):
            raise ValueError(f"policy player has non-finite pts: {player_id(p)}")
        counts[pos] += 1

    base = phantom_lineup_pts(roster, baselines)
    records = []
    eligible_indices = []
    for index, p in enumerate(pool):
        pos = p.get("pos")
        if pos not in BASE_SLOTS:
            raise ValueError(f"unknown policy position: {pos!r}")
        if not _finite_number(p.get("pts")):
            raise ValueError(f"policy player has non-finite pts: {player_id(p)}")
        if not _finite_number(p.get("vor")):
            raise ValueError(f"policy player has non-finite VOR: {player_id(p)}")
        rec = {
            "player_id": player_id(p),
            "name": p.get("name"),
            "pos": pos,
            "marginal_lineup_gain_raw": None,
            "marginal_lineup_gain_key": None,
            "vor_tiebreak": p.get("vor"),
            "input_index": index,
            "eligible": False,
            "cap_reason": None,
            "policy_rank": None,
            "raw_gap_from_leader": None,
            "policy_key_gap": None,
        }
        if pos in ("K", "DEF"):
            rec["cap_reason"] = "projection_floor"
        elif counts[pos] >= caps[pos]:
            rec["cap_reason"] = f"{pos.lower()}_cap"
        else:
            raw = phantom_lineup_pts(roster + [p], baselines) - base
            rec.update({
                "marginal_lineup_gain_raw": raw,
                "marginal_lineup_gain_key": round(raw, 4),
                "eligible": True,
            })
            eligible_indices.append(index)
        records.append(rec)

    ranked = sorted(eligible_indices, key=lambda i: (
        -records[i]["marginal_lineup_gain_key"],
        -records[i]["vor_tiebreak"],
        records[i]["input_index"],
    ))
    for rank, index in enumerate(ranked, 1):
        records[index]["policy_rank"] = rank
    if ranked:
        leader = records[ranked[0]]
        for index in ranked:
            rec = records[index]
            rec["raw_gap_from_leader"] = (
                leader["marginal_lineup_gain_raw"] -
                rec["marginal_lineup_gain_raw"])
            rec["policy_key_gap"] = (
                leader["marginal_lineup_gain_key"] -
                rec["marginal_lineup_gain_key"])
    return records
