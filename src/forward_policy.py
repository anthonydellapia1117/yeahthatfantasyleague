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
from collections import defaultdict

FLEX_OK = ("RB", "WR", "TE")
BASE_SLOTS = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "K": 1, "DEF": 1}


def phantom_lineup_pts(players, baselines):
    """Optimal starter points with replacement-level phantoms in empty
    slots - the lineup value function the marginal policy maximizes."""
    by_pos = defaultdict(list)
    for p in sorted(players, key=lambda x: -x["pts"]):
        by_pos[p["pos"]].append(p)
    total = 0.0
    used = set()

    def take(pos, n):
        nonlocal total
        got = 0
        for p in by_pos.get(pos, []):
            if got == n:
                break
            k = p["name"] + "|" + p["pos"]
            if k not in used:
                used.add(k)
                total += max(p["pts"], baselines[pos])
                got += 1
        while got < n:
            total += baselines[pos]
            got += 1

    take("QB", 1), take("RB", 2), take("WR", 2), take("TE", 1)
    flex = [p for pos in FLEX_OK for p in by_pos.get(pos, [])
            if p["name"] + "|" + p["pos"] not in used]
    flex_phantom = max(baselines[p] for p in FLEX_OK)
    total += max([p["pts"] for p in flex] + [flex_phantom])
    take("K", 1), take("DEF", 1)
    return total


def starter_caps(flex_alloc):
    """Maximum simultaneous starters per position.

    These are useful coarse bounds, but they are not by themselves a valid
    seven-pick construction: RB and WR can each be flex-eligible while the
    lineup still has only one shared FLEX slot. Use starter_path_feasible for
    a multi-pick starter path.
    """
    caps = {}
    for pos, k in BASE_SLOTS.items():
        flexes = 1 if flex_alloc.get(pos, 0) > 0 and pos in FLEX_OK else 0
        caps[pos] = k + flexes
    return caps


def starter_targets(flex_positions):
    """Every legal seven-skill-starter composition supported by league data.

    The six fixed skill slots are QB/RB/RB/WR/WR/TE. The seventh is the one
    shared FLEX, assigned only to positions the caller verified as eligible.
    This represents the shared slot directly instead of granting one
    independent flex allowance to every eligible position.
    """
    base = {p: BASE_SLOTS[p] for p in ("QB", "RB", "WR", "TE")}
    targets = []
    for pos in FLEX_OK:
        if pos not in flex_positions:
            continue
        target = dict(base)
        target[pos] += 1
        targets.append(target)
    return targets


def starter_path_feasible(counts, picks_remaining, flex_positions):
    """Can a partial skill roster still complete one legal starter target?"""
    for target in starter_targets(flex_positions):
        if any(counts.get(pos, 0) > cap for pos, cap in target.items()):
            continue
        needed = sum(cap - counts.get(pos, 0) for pos, cap in target.items())
        if needed == picks_remaining:
            return True
    return False


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
    counts = defaultdict(int)
    for p in roster:
        counts[p["pos"]] += 1
    live = [p for p in pool
            if caps is None or counts[p["pos"]] < caps.get(p["pos"], 99)]
    if not live:
        return None
    base = phantom_lineup_pts(roster, baselines)
    return max(live, key=lambda p: (
        round(phantom_lineup_pts(roster + [p], baselines) - base, 4),
        p["vor"]))
