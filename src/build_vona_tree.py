#!/usr/bin/env python3
"""Draft Path Tree - VONA (Value Over Next Available), per docs/VONA_TREE_SPEC.md.

VONA(pos) at a node = E[best available at THIS pick] - E[best available at
MY NEXT pick]. The position with the largest expected loss is the one to
take now: the "QB dropoff is shallow so wait, RB dropoff R3 to R5 is
severe so do not" logic as a computed number.

APPROVED DECISIONS (spec section 7):
  depth 7      structural - the starting lineup is exactly seven skill
               slots (QB RB RB WR WR TE FLEX), so the tree covers lineup
               construction completely and stops where the lineup is full
  branching    data-driven at EVERY slot, never gated on slot number; the
               threshold decides and the artifact reports the per-slot
               branch count so the shape is observable
  no BULLISH   the tree is a decision surface; a marker nudges regardless
               of its label (finding N.1)

TWO DELIBERATE DEVIATIONS FROM THE SPEC TEXT, both stated here and in the
artifact rather than made silently:

  1. The expectation runs over the WHOLE positional pool, not only players
     above the survival floor. Truncating the sum at the floor would bias
     E[best available] downward at exactly the picks where a high-VOR
     player is unlikely-but-possible. The floor is a RENDERING rule - no
     node is drawn for a player below it - which is what "realistic yet
     optimistic" asks for. Applying it to the math too would be a
     different, worse thing.
  2. Survival is modeled INDEPENDENTLY across players because that is
     what the frozen functions provide. Real drafts run in positional
     bursts, so same-position survival is positively correlated. The
     builder measures that overdispersion from this league's own 2,339
     picks and reports it with the direction of the bias, rather than
     leaving the assumption unexamined. See "correlation" in the output.

Run: python3 src/build_vona_tree.py
Output: out/data/vona_tree_2026.json
"""
import csv
import datetime
import json
import os
import statistics
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

# the frozen survival model is CALLED, never reimplemented
from engine_2026 import survival, snake_picks, TEAMS  # noqa: E402
from forward_policy import phantom_lineup_pts, starter_caps  # noqa: E402

OUT = os.path.join(ROOT, "out", "data", "vona_tree_2026.json")
SKILL = ("QB", "RB", "WR", "TE")
DEPTH = 7                    # = the seven skill starter slots
SURV_FLOOR = 0.40            # the room's shipped "going, going" threshold
MAX_NODES = 80               # render budget per slot, a UI constraint


def e_best(pool, prob):
    """Survival-weighted expected VOR of the top surviving player.

    sum_i VOR_i * P(i available) * prod_{j<i} (1 - P(j available)), the pool
    ordered by VOR descending. Runs over the WHOLE pool (deviation 1).
    """
    total, gone = 0.0, 1.0
    for p in pool:
        pr = prob(p)
        total += p["vor"] * pr * gone
        gone *= (1 - pr)
        if gone < 1e-6:
            break
    return total


def vona_at(pool_by_pos, pick, nxt):
    """VONA per position at a pick, plus the best renderable player."""
    out = {}
    for pos, pool in pool_by_pos.items():
        if not pool:
            continue
        # ONE CONDITIONING FRAME (review finding P1-A). Both expectations
        # are taken from the same pre-draft information state, so both use
        # the unconditional survival curve. The first build mixed
        # unconditional survival for "now" with per-player cond_survival
        # for "next"; cond(next|now) >= surv(next) always, so E[next] was
        # inflated and 28% of nodes carried negative VONA - an expected
        # best available that RISES as the pool shrinks is impossible.
        # With one frame, availability is monotone in the pick number and
        # VONA >= 0 holds structurally (asserted below and in the guards).
        now = e_best(pool, lambda p: survival(p["adp"], pick))
        later = (e_best(pool, lambda p: survival(p["adp"], nxt))
                 if nxt else 0.0)
        # In VOR units "everyone gone" IS replacement level (0), so for an
        # above-replacement pool availability is monotone in the pick number
        # and E[next] <= E[now]. A BELOW-replacement pool can legitimately
        # drift up toward 0 by waiting - negative VONA there reads "waiting
        # costs nothing, the position is below replacement," which is true.
        if nxt is not None and now >= 0:
            assert later <= now + 1e-9, (pos, pick, nxt, now, later)
        # the player actually takeable here: best VOR still plausibly there
        cand = [p for p in pool if survival(p["adp"], pick) >= SURV_FLOOR]
        if not cand:
            continue
        out[pos] = {"vona": round(now - later, 2),
                    "e_now": round(now, 2), "e_next": round(later, 2),
                    "player": cand[0]}
    return out


def overdispersion(picks_path):
    """Do same-position picks cluster beyond independent draws?

    For each window of TEAMS consecutive picks in the league's own draft
    history, count each position. Compare the observed variance of those
    counts against the binomial variance implied by the same mean. A ratio
    above 1 means runs cluster - the independence assumption understates
    how often a whole position tier vanishes between turns.
    """
    seq = defaultdict(list)
    for r in csv.DictReader(open(picks_path)):
        try:
            seq[r["season"]].append(r["pos"])
        except KeyError:
            continue
    counts = defaultdict(list)
    W = TEAMS
    for _s, positions in seq.items():
        for i in range(0, len(positions) - W, W):
            win = positions[i:i + W]
            for pos in SKILL:
                counts[pos].append(win.count(pos))
    out = {}
    for pos, vals in counts.items():
        if len(vals) < 8:
            continue
        m = statistics.mean(vals)
        var = statistics.variance(vals)
        binom = m * (1 - m / W)          # Binomial(W, m/W) variance
        out[pos] = {"windows": len(vals), "mean_per_window": round(m, 3),
                    "observed_var": round(var, 3),
                    "binomial_var": round(binom, 3),
                    "ratio": round(var / binom, 3) if binom > 0 else None}
    return out


def build_slot(slot, players, eps_by_depth, stats, baselines, narrow_band,
               caps):
    """Walk one slot's tree, branching only where the data says to."""
    picks = snake_picks(slot)[:DEPTH]
    nodes = {"count": 0}
    pos_of = {p["name"]: p["pos"] for p in players}
    pruned = {"dominated": 0, "budget": 0, "narrow_kept": 0}
    branches = {"count": 0, "collapsed": 0}

    def pool_for(taken):
        by_pos = defaultdict(list)
        for p in players:
            if p["name"] in taken:
                continue
            by_pos[p["pos"]].append(p)
        for pos in by_pos:
            by_pos[pos].sort(key=lambda x: -x["vor"])
        return by_pos

    def walk(depth, taken, roster):
        if depth >= len(picks):
            return []
        pick = picks[depth]
        nxt = picks[depth + 1] if depth + 1 < len(picks) else None
        v = vona_at(pool_for(taken), pick, nxt)
        # ROSTER FEASIBILITY (review finding P1-B, the third occurrence of
        # this defect class): a position at its startable maximum for the
        # path so far is not a choice. Caps come from the shared
        # forward_policy layer, derived from the league's own observed flex
        # allocation - never typed here.
        counts = {}
        for name in taken:
            p_pos = pos_of.get(name)
            counts[p_pos] = counts.get(p_pos, 0) + 1
        v = {pos: d for pos, d in v.items()
             if counts.get(pos, 0) < caps.get(pos, 99)}
        if not v:
            return []
        ranked = sorted(v.items(), key=lambda kv: -kv[1]["vona"])
        eps = eps_by_depth.get(depth, 0.0)
        # BRANCH RULE: every position whose VONA is within eps of the best.
        # No slot gating - the threshold alone decides, at any slot.
        chosen = [ranked[0]]
        for pos, d in ranked[1:]:
            if ranked[0][1]["vona"] - d["vona"] <= eps:
                chosen.append((pos, d))
        if len(chosen) > 1:
            branches["count"] += 1
        base_roster = roster
        made = []
        for pos, d in chosen:
            if nodes["count"] >= MAX_NODES:
                pruned["budget"] += 1
                continue
            nodes["count"] += 1
            p = d["player"]
            s_now = survival(p["adp"], pick)
            tier_left = sum(1 for q in pool_for(taken)[pos]
                            if q.get("tier") == p.get("tier")
                            and survival(q["adp"], pick) >= SURV_FLOOR)
            node = {
                "round": depth + 1, "pick": pick, "pos": pos,
                "name": p["name"], "vor": p["vor"], "adp": p["adp"],
                "pts": p["pts"],
                "p_available": round(s_now, 3),
                "vona": d["vona"], "e_now": d["e_now"], "e_next": d["e_next"],
                "tier": p.get("tier"), "tier_left": tier_left,
                "forced": len(chosen) == 1,
                "why": (f"VONA gap {round(ranked[0][1]['vona'] - ranked[1][1]['vona'], 1)}"
                        f" over {ranked[1][0]}; not a decision"
                        if len(chosen) == 1 and len(ranked) > 1
                        else f"within {eps} of the best option - a real fork"),
                "children": walk(depth + 1, taken | {p["name"]},
                                 roster + [{"name": p["name"], "pos": pos,
                                            "pts": p["pts"]}]),
            }
            stats["vona_by_depth"][depth].append(d["vona"])
            made.append(node)
        # PRUNE dominated siblings. The comparison runs on LINEUP VALUE from
        # the shared forward_policy - phantom-filled optimal starters for the
        # roster a path builds - not on a raw VOR sum. Summing VOR is the
        # objective the M1 validation already disproved: it prices a
        # duplicate at starter value, so a VOR-sum prune would rate a path
        # that stacks one position above a path that fills the lineup.
        # Domination is STRICT and needs no tolerance: a branch is dominated
        # only when its best attainable lineup is worse than a sibling's
        # worst attainable lineup.
        if len(made) > 1:
            def paths(n, acc):
                roster = acc + [{"name": n["name"], "pos": n["pos"],
                                 "pts": n["pts"]}]
                if not n["children"]:
                    return [phantom_lineup_pts(roster, baselines)]
                out = []
                for c in n["children"]:
                    out += paths(c, roster)
                return out

            def best(n):
                return max(paths(n, base_roster))

            def worst(n):
                return min(paths(n, base_roster))
            keep = []
            for n in made:
                margin = min((worst(o) - best(n) for o in made if o is not n),
                             default=float("-inf"))
                if margin > 0:
                    stats["margins"].append(margin)
                # A hairline domination is not a decision the board has made
                # for you. Branches dominated by less than NARROW_BAND are
                # kept and flagged; the band is derived the same way the
                # branch threshold is - p25 of the domination margins this
                # board actually produces - so "narrow" means narrow by the
                # standard of this board, not a typed-in number.
                if margin > narrow_band:
                    pruned["dominated"] += 1
                else:
                    if margin > 0:
                        n["narrowly_dominated"] = round(margin, 2)
                        n["why"] = (f"kept: dominated by only {margin:.1f} "
                                    f"lineup pts, inside the {narrow_band:.1f} "
                                    f"narrow band - a real coin flip")
                        pruned["narrow_kept"] += 1
                    keep.append(n)
            cut = len(made) - len(keep)
            made = keep or made
            # a fork whose siblings were all pruned is not a fork on screen:
            # relabel it rather than leaving a marker with nothing to compare
            if cut and len(made) == 1:
                made[0]["forced"] = True
                made[0]["why"] = (f"fork collapsed - {cut} sibling"
                                  f"{'s' if cut > 1 else ''} pruned as dominated")
                branches["count"] -= 1
                branches["collapsed"] += 1
        return made

    roots = walk(0, frozenset(), [])
    return {"slot": slot, "roots": roots, "nodes": nodes["count"],
            "rendered_forks": branches["count"],
            "forks_collapsed_by_pruning": branches["collapsed"],
            "pruned": pruned, "picks": picks}


def main():
    eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
    players = [p for p in eng["players"]
               if p["pos"] in SKILL and p.get("adp", 999) < 900]
    players.sort(key=lambda p: -p["vor"])

    caps = starter_caps(eng.get("flex_allocation", {}))

    # PASS 1: greedy walk per slot to observe the VONA gaps this board
    # actually produces at each depth, so the branch threshold is
    # calibrated to the board rather than typed in.
    gaps = defaultdict(list)
    for slot in range(1, TEAMS + 1):
        picks = snake_picks(slot)[:DEPTH]
        taken = set()
        for depth, pick in enumerate(picks):
            nxt = picks[depth + 1] if depth + 1 < len(picks) else None
            by_pos = defaultdict(list)
            for p in players:
                if p["name"] not in taken:
                    by_pos[p["pos"]].append(p)
            for pos in by_pos:
                by_pos[pos].sort(key=lambda x: -x["vor"])
            v = vona_at(by_pos, pick, nxt)
            cnt = {}
            for nm in taken:
                pp = next((q["pos"] for q in players if q["name"] == nm), None)
                cnt[pp] = cnt.get(pp, 0) + 1
            v = {pos: d for pos, d in v.items()
                 if cnt.get(pos, 0) < caps.get(pos, 99)}
            if len(v) < 2:
                break
            ranked = sorted(v.items(), key=lambda kv: -kv[1]["vona"])
            gaps[depth].append(ranked[0][1]["vona"] - ranked[1][1]["vona"])
            taken.add(ranked[0][1]["player"]["name"])

    def p25(vals):
        vals = sorted(vals)
        if not vals:
            return 0.0
        i = max(0, min(len(vals) - 1, int(round(0.25 * (len(vals) - 1)))))
        return round(vals[i], 2)

    eps_by_depth = {d: p25(v) for d, v in gaps.items()}

    # PASS 2a: build once with the narrow band wide open, purely to observe
    # the domination margins this board produces. PASS 2b rebuilds with the
    # band set to their p25.
    probe = {"vona_by_depth": defaultdict(list), "margins": []}
    for slot in range(1, TEAMS + 1):
        build_slot(slot, players, eps_by_depth, probe, eng["baselines"],
                   float("inf"), caps)
    narrow_band = p25(probe["margins"]) if probe["margins"] else 0.0

    # PASS 2b: build for real
    stats = {"vona_by_depth": defaultdict(list), "margins": []}
    slots = {}
    for slot in range(1, TEAMS + 1):
        slots[str(slot)] = build_slot(slot, players, eps_by_depth, stats,
                                      eng["baselines"], narrow_band, caps)

    corr = overdispersion(os.path.join(ROOT, "out", "picks.csv"))
    clustered = [p for p, d in corr.items() if d["ratio"] and d["ratio"] > 1.0]

    out = {
        "provenance": {
            "generated": datetime.date.today().isoformat(),
            "engine_generated": eng["generated"],
            "objective": ("VONA(pos) = E[best available at this pick] - "
                          "E[best available at my next pick], both survival-"
                          "weighted over the whole positional pool"),
            "survival": ("frozen survival model called from "
                         "src/engine_2026.py - the pre-draft convention every "
                         "artifact uses; the adopted calibration applies to "
                         "conditional survival in the LIVE room only, and "
                         "after the one-frame fix this builder uses no "
                         "conditional survival at all"),
            "conditioning": ("ONE frame: both expectations use unconditional "
                             "survival from the same pre-draft information "
                             "state. E[next] <= E[now] and VONA >= 0 are "
                             "structural and guarded - the first build mixed "
                             "frames and 28% of nodes went negative"),
            "feasibility": ("starter caps from the shared forward_policy "
                            "layer (max simultaneous starters, flex from the "
                            "observed allocation): no path may hold more of "
                            "a position than the lineup can start"),
            "depth": DEPTH,
            "depth_rationale": ("structural: the starting lineup is exactly "
                                "seven skill slots (QB RB RB WR WR TE FLEX), "
                                "so depth 7 covers lineup construction "
                                "completely and stops where the lineup is "
                                "full - not a noise cutoff"),
            "branch_rule": ("branch wherever the top options fall within the "
                            "derived threshold, at ANY slot - never gated on "
                            "slot number"),
            "bullish_on_nodes": ("deliberately absent - the tree is a "
                                 "decision surface and a marker nudges "
                                 "regardless of its label (finding N.1)"),
            "deviations": [
                ("the expectation runs over the whole positional pool, not "
                 "only players above the survival floor: truncating would "
                 "bias E[best available] downward. The floor is a RENDERING "
                 "rule - no node is drawn below it"),
                ("survival is independent across players because that is what "
                 "the frozen model provides; the correlation block below "
                 "measures the real clustering and states the bias direction"),
            ],
        },
        "thresholds": {
            "surv_floor": SURV_FLOOR,
            "surv_floor_source": ("the room's shipped 'going, going' "
                                  "threshold - reused, not reinvented"),
            "branch_eps_by_depth": eps_by_depth,
            "branch_eps_source": ("p25 of the top-two VONA gaps this board "
                                  "produces at each depth: a fork fires when "
                                  "the gap is in the narrowest quartile of "
                                  "gaps actually observed"),
            "prune_rule": ("STRICT domination on lineup value from "
                           "src/forward_policy.py (phantom-filled optimal "
                           "starters), no tolerance parameter: a branch goes "
                           "only when its best attainable lineup is worse "
                           "than a sibling's worst. Raw VOR sums are NOT used "
                           "- that objective was disproved by the M1 "
                           "validation, which caught it stacking elite TEs"),
            "max_nodes_per_slot": MAX_NODES,
            "narrow_band": narrow_band,
            "narrow_band_source": ("p25 of the domination margins this board "
                                   "produces, in lineup points: a branch "
                                   "dominated by less than this is kept and "
                                   "flagged as a coin flip rather than "
                                   "silently decided"),
            "margins_observed": len(probe["margins"]),
        },
        "correlation": {
            "method": ("same-position counts in each 12-pick window of the "
                       "league's own draft history, observed variance vs the "
                       "binomial variance implied by the same mean"),
            "by_pos": corr,
            "clustered_positions": clustered,
            "bias_direction": (
                "ratios above 1 mean same-position picks cluster in runs. "
                "Independent survival then UNDERSTATES the chance that a "
                "whole position tier is gone by the next turn, which "
                "OVERSTATES E[best available next] and therefore UNDERSTATES "
                "VONA - the tree is biased toward WAIT, not toward reaching. "
                "Read a marginal WAIT at a clustered position as closer to a "
                "coin flip than the number suggests."),
        },
        "slots": slots,
    }
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}")
    print("branch eps by depth:", eps_by_depth)
    print(f"narrow band: {narrow_band} lineup pts "
          f"(from {len(probe['margins'])} observed margins)")
    for pos, d in sorted(corr.items()):
        print(f"  overdispersion {pos}: {d['ratio']} "
              f"(obs {d['observed_var']} vs binom {d['binomial_var']}, "
              f"n={d['windows']})")
    for s in range(1, TEAMS + 1):
        v = slots[str(s)]
        print(f"  slot {s:>2}: {v['nodes']:>3} nodes, "
              f"{v['rendered_forks']} rendered forks "
              f"(+{v['forks_collapsed_by_pruning']} collapsed), "
              f"{v['pruned']['dominated']} dominated pruned, "
              f"{v['pruned']['narrow_kept']} narrow kept, "
              f"{v['pruned']['budget']} over budget")


if __name__ == "__main__":
    main()
