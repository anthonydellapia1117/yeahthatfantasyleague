#!/usr/bin/env python3
"""Draft Path Tree - VONA (Value Over Next Available), per docs/VONA_TREE_SPEC.md.

VONA(pos) at a node = E[best available at THIS pick] - E[best available at
MY NEXT pick]. The position with the largest expected loss is the one to
take now: the "QB dropoff is shallow so wait, RB dropoff R3 to R5 is
severe so do not" logic as a computed number.

REVIEWED DECISIONS (spec section 7):
  depth 7      display horizon - the tree renders the seven skill-starter
               decisions, but round 7 is valued against the real round-8
               owner pick; the optimization never compares against nothing
  branching    Pareto non-dominance at EVERY slot: preserve every action not
               locally dominated on VONA urgency and expected marginal lineup
               gain. Full-precision local coordinates, no percentile quota and
               no typed epsilon
  no BULLISH   the tree is a decision surface; a marker nudges regardless
               of its label (finding N.1)

MODEL DISCLOSURES, stated here and in the artifact rather than made silently:

  1. The expectation runs over every ABOVE-REPLACEMENT player in the
     positional pool. Replacement is the explicit zero-value state. There
     is no survival cutoff: the displayed state is the modal top-survivor
     outcome from the same distribution. When replacement is modal, the node
     says fallback required instead of assigning an invented player.
  2. Survival is modeled INDEPENDENTLY across players because that is
     what the frozen functions provide. The builder reports descriptive
     same-position adjacency from this league's own 2,339 picks with k,
     n, and Wilson intervals. It does not call that player correlation or
     claim a bias direction. See "correlation" in the output.
  3. Expected decision coordinates integrate every current player state,
     but the visible continuation follows the modal state as a representative
     scenario. It is not a stochastic terminal expectation or a global draft
     optimization, so no terminal-value pruning is performed.

Run: python3 src/build_vona_tree.py
Output: out/data/vona_tree_2026.json
"""
import csv
import datetime
import json
import math
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

# the frozen survival model is CALLED, never reimplemented
from engine_2026 import survival, snake_picks, TEAMS  # noqa: E402
from forward_policy import (phantom_lineup_pts, starter_path_feasible,
                            starter_targets)  # noqa: E402

OUT = os.path.join(ROOT, "out", "data", "vona_tree_2026.json")
SKILL = ("QB", "RB", "WR", "TE")
DEPTH = 7                    # = the seven skill starter slots
MAX_NODES = 120              # render budget per slot, a UI constraint


def best_states(pool, prob):
    """Distribution of the best above-replacement survivor.

    The pool is VOR-descending. Each player state carries
    P(player is available AND every higher-VOR player is gone). The residual
    probability is the replacement state, worth exactly zero. No probability
    cutoff truncates either the expectation or the displayed distribution.
    """
    expected, none, states = 0.0, 1.0, []
    for p in pool:
        if p["vor"] <= 0:
            break
        pr = prob(p)
        p_top = none * pr
        states.append((p, p_top))
        expected += p["vor"] * p_top
        none *= (1 - pr)
    return expected, states, none


def vona_at(pool_by_pos, pick, nxt):
    """VONA per position at a pick, plus its modal top-survivor player."""
    if nxt is None:
        raise ValueError(f"VONA at pick {pick} requires a real next owner pick")
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
        now, states, p_none = best_states(
            pool, lambda p: survival(p["adp"], pick))
        later, _later_states, _later_none = best_states(
            pool, lambda p: survival(p["adp"], nxt))
        assert later <= now + 1e-9, (pos, pick, nxt, now, later)
        player, p_top = (max(states, key=lambda item: (item[1], item[0]["vor"]))
                         if states else (None, 0.0))
        replacement_modal = p_none >= p_top
        e_now = round(now, 2)
        e_next = round(later, 2)
        out[pos] = {"vona_raw": now - later,
                    "e_now_raw": now, "e_next_raw": later,
                    "vona": round(e_now - e_next, 2),
                    "e_now": e_now, "e_next": e_next,
                    "player": None if replacement_modal else player,
                    "states": states,
                    "p_top_survivor": p_top,
                    "p_no_above_replacement": p_none,
                    "p_modal_state": p_none if replacement_modal else p_top,
                    "replacement_modal": replacement_modal}
    return out


def dominates(left, right):
    """Exact internal dominance; display rounding never enters decisions."""
    return (left["vona_raw"] >= right["vona_raw"]
            and left["expected_lineup_gain_raw"] >=
            right["expected_lineup_gain_raw"]
            and (left["vona_raw"] > right["vona_raw"]
                 or left["expected_lineup_gain_raw"] >
                 right["expected_lineup_gain_raw"]))


def pareto_front(actions):
    """Return actions not dominated on both urgency and lineup gain."""
    front = []
    for action in actions:
        if not any(dominates(other, action)
                   for other in actions if other is not action):
            front.append(action)
    return sorted(front, key=lambda a: (-a["vona_raw"],
                                       -a["expected_lineup_gain_raw"], a["pos"]))


def wilson(k, n, z=1.96):
    """Wilson interval for a computed proportion."""
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(center - half, 4), round(center + half, 4)]


def correlation_diagnostic(picks_path):
    """Descriptive same-position adjacency, never a correlation estimate.

    For each position, compare P(next pick has the same position | current
    pick has that position) with that position's marginal share among all
    within-season next picks. Counts and Wilson intervals are published.
    Adjacent pairs are not independent and this cannot identify joint player
    survival, so the result is a disclosure, not an adjustment or verdict.
    """
    seq = defaultdict(list)
    for r in csv.DictReader(open(picks_path)):
        try:
            seq[r["season"]].append(r["pos"])
        except KeyError:
            continue
    out = {}
    for pos in SKILL:
        contexts = repeats = base_n = base_k = 0
        for positions in seq.values():
            for current, nxt in zip(positions, positions[1:]):
                base_n += 1
                base_k += nxt == pos
                if current == pos:
                    contexts += 1
                    repeats += nxt == pos
        repeat_rate = repeats / contexts if contexts else None
        base_rate = base_k / base_n if base_n else None
        out[pos] = {
            "seasons": len(seq),
            "repeat_contexts_n": contexts,
            "same_position_next_k": repeats,
            "repeat_rate": round(repeat_rate, 4) if repeat_rate is not None else None,
            "repeat_wilson95": wilson(repeats, contexts),
            "marginal_next_n": base_n,
            "marginal_next_k": base_k,
            "marginal_rate": round(base_rate, 4) if base_rate is not None else None,
            "marginal_wilson95": wilson(base_k, base_n),
            "repeat_vs_marginal_ratio": (
                round(repeat_rate / base_rate, 3)
                if repeat_rate is not None and base_rate else None),
        }
    return out


def build_slot(slot, players, baselines, flex_positions):
    """Build a local expected-value policy with auditable candidate sets."""
    full_picks = snake_picks(slot)
    if len(full_picks) <= DEPTH:
        raise ValueError(f"slot {slot} has no round-{DEPTH + 1} lookahead pick")
    picks = full_picks[:DEPTH]
    next_picks = full_picks[1:DEPTH + 1]
    metrics = {"decision_groups": 0, "evaluated_actions": 0}

    def pool_for(unavailable):
        by_pos = defaultdict(list)
        for p in players:
            if p["name"] in unavailable:
                continue
            by_pos[p["pos"]].append(p)
        for pos in by_pos:
            by_pos[pos].sort(key=lambda x: -x["vor"])
        return by_pos

    def expected_gain(states, roster):
        base = phantom_lineup_pts(roster, baselines)
        return sum(
            p_top * (phantom_lineup_pts(
                roster + [{"name": p["name"], "pos": p["pos"],
                           "pts": p["pts"]}], baselines) - base)
            for p, p_top in states)

    def walk(depth, unavailable, roster):
        if depth >= DEPTH:
            return []
        pick, nxt = picks[depth], next_picks[depth]
        pool = pool_for(unavailable)
        v = vona_at(pool, pick, nxt)
        counts = defaultdict(int)
        for player in roster:
            counts[player["pos"]] += 1
        metrics["decision_groups"] += 1

        actions = []
        for pos, d in v.items():
            proposed = dict(counts)
            proposed[pos] = proposed.get(pos, 0) + 1
            remaining = DEPTH - depth - 1
            if not starter_path_feasible(proposed, remaining, flex_positions):
                continue
            actions.append({"pos": pos, "vona_raw": d["vona_raw"],
                            "expected_lineup_gain_raw": expected_gain(
                                d["states"], roster),
                            "detail": d})
        metrics["evaluated_actions"] += len(actions)
        chosen = pareto_front(actions)
        if not chosen:
            raise RuntimeError(
                f"slot {slot} round {depth + 1}: no feasible modal action; "
                f"roster={dict(counts)}, modal_positions={sorted(v)}")

        front_positions = {a["pos"] for a in chosen}
        decision_set = []
        for candidate in sorted(actions, key=lambda a: a["pos"]):
            decision_set.append({
                "pos": candidate["pos"],
                "vona": candidate["detail"]["vona"],
                "vona_raw": candidate["vona_raw"],
                "expected_lineup_gain": round(
                    candidate["expected_lineup_gain_raw"], 4),
                "expected_lineup_gain_raw":
                    candidate["expected_lineup_gain_raw"],
                "pareto": candidate["pos"] in front_positions,
                "dominated_by": sorted(
                    other["pos"] for other in actions
                    if other is not candidate and dominates(other, candidate)),
            })

        made = []
        for action in chosen:
            pos, d = action["pos"], action["detail"]
            p = d["player"]
            fallback = p is None
            s_now = None if fallback else survival(p["adp"], pick)
            tier_pool = ([] if fallback else
                         [q for q in pool[pos]
                          if q["vor"] > 0 and q.get("tier") == p.get("tier")])
            tier_expected = sum(survival(q["adp"], pick) for q in tier_pool)
            tier_none = 1.0
            for q in tier_pool:
                tier_none *= 1 - survival(q["adp"], pick)
            display_name = None if fallback else p["name"]
            roster_name = (f"replacement:{pos}:round{depth + 1}"
                           if fallback else p["name"])
            picked = {"name": roster_name, "pos": pos,
                      "pts": baselines[pos] if fallback else p["pts"]}
            next_roster = roster + [picked]
            state_players = [q for q, _prob in d["states"]]
            if fallback:
                # The replacement state means every positive-VOR player at
                # this position was already gone at the current pick.
                modal_gone = [q["name"] for q in state_players]
                continuation_removed = modal_gone
            else:
                selected_index = next(
                    i for i, q in enumerate(state_players)
                    if q["name"] == p["name"])
                # "p is top survivor" jointly means p is available and every
                # higher-VOR state is gone. Preserve that whole event in the
                # representative continuation, then also remove our drafted p.
                modal_gone = [q["name"] for q in state_players[:selected_index]]
                continuation_removed = modal_gone + [p["name"]]
            next_unavailable = unavailable | set(continuation_removed)
            children = walk(depth + 1, next_unavailable, next_roster)
            fork = len(chosen) > 1
            if fork:
                decision_reason = (
                    f"Pareto tradeoff: {d['vona']:.1f} VONA pts and "
                    f"{action['expected_lineup_gain_raw']:.1f} expected lineup pts")
                force_basis = None
            elif len(actions) == 1:
                decision_reason = (
                    "Feasibility-forced: the only action that can complete one "
                    "supported seven-starter composition")
                force_basis = "feasibility"
            else:
                decision_reason = (
                    "Pareto-dominant on VONA urgency and expected lineup gain")
                force_basis = "pareto-dominance"
            if fallback:
                decision_reason = (
                    "Replacement is the modal state - fallback required; " +
                    decision_reason)
            node = {
                "round": depth + 1, "pick": pick, "next_pick": nxt,
                "pos": pos, "name": display_name,
                "fallback_required": fallback,
                "vor": 0.0 if fallback else p["vor"],
                "adp": None if fallback else p["adp"],
                "pts": baselines[pos] if fallback else p["pts"],
                "p_available": None if fallback else round(s_now, 3),
                "p_top_survivor": round(d["p_top_survivor"], 3),
                "p_no_above_replacement": round(d["p_no_above_replacement"], 3),
                "p_modal_state": round(d["p_modal_state"], 3),
                "vona": d["vona"], "e_now": d["e_now"],
                "e_next": d["e_next"],
                "decision_vona_raw": action["vona_raw"],
                "expected_lineup_gain": round(
                    action["expected_lineup_gain_raw"], 4),
                "decision_expected_lineup_gain_raw":
                    action["expected_lineup_gain_raw"],
                "tier": None if fallback else p.get("tier"),
                "tier_expected_available": round(tier_expected, 2),
                "tier_p_any": round(1 - tier_none, 3),
                "forced": not fork,
                "force_basis": force_basis,
                "why": decision_reason,
                "modal_state_gone": modal_gone,
                "continuation_removed": continuation_removed,
                "continuation_basis": (
                    "coherent modal-state representative path"),
                "decision_set": decision_set,
                "children": children,
            }
            made.append(node)
        return made

    roots = walk(0, frozenset(), [])

    def count_nodes(nodes):
        return sum(1 + count_nodes(node["children"]) for node in nodes)

    def count_forks(nodes):
        return ((1 if len(nodes) > 1 else 0) +
                sum(count_forks(node["children"]) for node in nodes))

    rendered = count_nodes(roots)
    if rendered > MAX_NODES:
        raise RuntimeError(
            f"slot {slot} needs {rendered} rendered nodes, above UI budget {MAX_NODES}")
    return {"slot": slot, "roots": roots, "nodes": rendered,
            "decision_groups": metrics["decision_groups"],
            "evaluated_actions": metrics["evaluated_actions"],
            "rendered_forks": count_forks(roots),
            "picks": picks, "next_picks": next_picks}


def main():
    eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
    players = [p for p in eng["players"]
               if p["pos"] in SKILL and p.get("adp", 999) < 900]
    players.sort(key=lambda p: -p["vor"])

    flex_usage = json.load(open(os.path.join(
        ROOT, "out", "data", "flex_usage_2025.json")))
    flex_positions = tuple(
        pos for pos in SKILL if flex_usage.get("counts", {}).get(pos, 0) > 0)
    targets = starter_targets(flex_positions)
    if not targets:
        raise RuntimeError("league flex data supports no seven-starter composition")

    slots = {}
    for slot in range(1, TEAMS + 1):
        slots[str(slot)] = build_slot(
            slot, players, eng["baselines"], flex_positions)

    corr = correlation_diagnostic(os.path.join(ROOT, "out", "picks.csv"))

    out = {
        "provenance": {
            "generated": datetime.date.today().isoformat(),
            "engine_generated": eng["generated"],
            "objective": ("VONA(pos) = E[best available at this pick] - "
                          "E[best available at my next pick], both survival-"
                          "weighted over the above-replacement positional pool; "
                          "replacement is the explicit zero-value state"),
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
            "feasibility": ("exact seven-skill-starter compositions from the "
                            "shared forward_policy layer: six fixed skill "
                            "slots plus exactly one shared FLEX. Eligible "
                            "positions come from nonzero observed 2025 FLEX "
                            "starts, including TE; counts and Wilson intervals "
                            "live in out/data/flex_usage_2025.json"),
            "starter_targets": targets,
            "flex_positions": list(flex_positions),
            "flex_usage_n": flex_usage["provenance"]["n"],
            "depth": DEPTH,
            "value_lookahead_rounds": DEPTH + 1,
            "depth_rationale": ("display horizon: render the seven skill-"
                                "starter decisions, but value every node "
                                "against the owner's real next pick. The "
                                "round-7 node therefore looks to round 8; it "
                                "never compares against nothing"),
            "branch_rule": ("at any slot, render the Pareto frontier on two "
                            "computed objectives: VONA urgency and expected "
                            "marginal lineup gain over the same top-survivor "
                            "distribution. Decisions use unrounded coordinates "
                            "and every feasible sibling is published in the "
                            "node's decision_set ledger. A fork is a local "
                            "model tradeoff, not a percentile quota or a "
                            "statistical coin flip"),
            "render_rule": ("no survival cutoff: display the modal player "
                            "state from the full above-replacement top-survivor "
                            "distribution; if replacement is modal, show a "
                            "fallback-required honest null instead of naming "
                            "an invented player"),
            "bullish_on_nodes": ("deliberately absent - the tree is a "
                                 "decision surface and a marker nudges "
                                 "regardless of its label (finding N.1)"),
            "deviations": [
                ("the expectation runs over every above-replacement player "
                 "with replacement as the zero-value residual state; no "
                 "survival floor truncates the expectation or display"),
                ("survival is independent across players because that is what "
                 "the frozen model provides; the correlation block below is "
                 "a descriptive adjacency diagnostic, not an adjustment"),
                ("each visible continuation follows the modal player state as "
                 "a representative scenario. Expected coordinates integrate "
                 "all current player states, but the visible path is not an "
                 "expectation over future chance branches and is not a global "
                 "draft optimization"),
                ("depth seven intentionally constructs the seven skill "
                 "starters. Legal early-bench or delayed-starter strategies "
                 "exist in the 14-round draft but are outside this surface"),
            ],
        },
        "decision_rules": {
            "render": ("modal top-survivor identity among all positive-VOR "
                       "player states, with replacement/no-player competing "
                       "as an explicit fallback state; no probability threshold"),
            "branch": ("Pareto non-dominance on VONA and expected marginal "
                       "lineup gain using full-precision internal coordinates; "
                       "every candidate and exact dominance witness is "
                       "serialized in decision_set; no epsilon, percentile, "
                       "or forced quota"),
            "continuation": ("roll the modal top-survivor identity into the "
                             "next visible node as a representative scenario, "
                             "also removing every higher-VOR player whose "
                             "absence defines that state; a replacement state "
                             "removes every positive-VOR player at the position. "
                             "Do not use modal terminal values to prune or claim "
                             "global optimality"),
            "max_nodes_per_slot": MAX_NODES,
            "budget_behavior": ("finish the complete local Pareto policy "
                                "before checking the UI budget; exceedance "
                                "fails the build instead of silently dropping "
                                "a path"),
        },
        "correlation": {
            "method": ("within each season, compare the computed same-position "
                       "next-pick rate with that position's marginal share "
                       "among all next picks; publish k, n, and Wilson 95% "
                       "intervals for both proportions"),
            "by_pos": corr,
            "what_breaks": ("the product used for top-survivor states is no "
                            "longer the joint distribution when player "
                            "availabilities are correlated, so state "
                            "probabilities, E[now], E[next], and VONA are not "
                            "jointly calibrated"),
            "bias_direction": (
                "UNKNOWN. Positive or negative player-level dependence can "
                "move the expected maximum in either direction. The adjacency "
                "rates are descriptive evidence of draft runs, but they do "
                "not identify player-level survival correlations or the sign "
                "of VONA bias; overlapping pairs also make Wilson intervals "
                "descriptive rather than a formal test."),
        },
        "slots": slots,
    }
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}")
    print("branch rule: local Pareto(VONA, expected lineup gain), full precision")
    for pos, d in sorted(corr.items()):
        print(f"  adjacency {pos}: {d['repeat_rate']:.3f} repeat vs "
              f"{d['marginal_rate']:.3f} marginal "
              f"(k/n={d['same_position_next_k']}/"
              f"{d['repeat_contexts_n']})")
    for s in range(1, TEAMS + 1):
        v = slots[str(s)]
        print(f"  slot {s:>2}: {v['nodes']:>3} nodes, "
              f"{v['decision_groups']} decision groups, "
              f"{v['evaluated_actions']} actions evaluated, "
              f"{v['rendered_forks']} rendered forks")


if __name__ == "__main__":
    main()
