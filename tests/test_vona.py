#!/usr/bin/env python3
"""Adversarial guards for the VONA draft-path tree."""
import csv
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "out", "data")
FAILS = []


def ok(cond, label, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label +
          ("" if cond or not detail else "  -> " + detail))
    if not cond:
        FAILS.append(label)


tree = json.load(open(os.path.join(D, "vona_tree_2026.json")))
eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
flex_usage = json.load(open(os.path.join(D, "flex_usage_2025.json")))
prov, rules = tree["provenance"], tree["decision_rules"]

sys.path.insert(0, os.path.join(ROOT, "src"))
from build_vona_tree import (best_states, derive_display_bands,
                             derive_separation_floor,
                             display_selection_provenance,
                             exact_distinct_forks, iter_decision_groups,
                             normalized_frontier_spread, pareto_front,
                             population_sd, vona_at, wilson)
from engine_2026 import survival, snake_picks
from forward_policy import (phantom_lineup_pts, starter_path_feasible,
                            starter_targets)

POSITIONS = ("QB", "RB", "WR", "TE")
players = [p for p in eng["players"]
           if p["pos"] in POSITIONS and p.get("adp", 999) < 900]
players.sort(key=lambda p: -p["vor"])
flex_positions = tuple(
    pos for pos in POSITIONS if flex_usage.get("counts", {}).get(pos, 0) > 0)
targets = starter_targets(flex_positions)

# Reviewed contracts, not old intent.
ok(prov["depth"] == 7 and prov["value_lookahead_rounds"] == 8,
   "seven rendered rounds carry an eighth-round value lookahead")
ok("display horizon" in prov["depth_rationale"]
   and "round-7" in prov["depth_rationale"]
   and "never compares against nothing" in prov["depth_rationale"],
   "depth rationale labels the display horizon and terminal lookahead")
ok("Pareto" in prov["branch_rule"] and "unrounded" in prov["branch_rule"]
   and "decision_set" in prov["branch_rule"],
   "branching is full-precision Pareto with an auditable candidate ledger")
ok("no survival cutoff" in prov["render_rule"]
   and "fallback-required" in prov["render_rule"],
   "rendering has no probability cutoff and names its honest null")
ok("one shared FLEX" in prov["feasibility"]
   and "including TE" in prov["feasibility"],
   "feasibility represents the shared FLEX and its observed TE use")
ok(prov["flex_positions"] == list(flex_positions)
   and prov["flex_usage_n"] == flex_usage["provenance"]["n"]
   and prov["starter_targets"] == targets,
   "artifact starter targets recompute from observed FLEX counts")
ok("representative scenario" in rules["continuation"].lower()
   and "higher-vor player" in rules["continuation"].lower()
   and "do not use modal terminal values" in rules["continuation"].lower(),
   "modal continuation is disclosed and cannot support terminal pruning")
ok("fails the build" in rules["budget_behavior"],
   "the UI budget fails loudly after the policy is built")
ok("deliberately absent" in prov["bullish_on_nodes"],
   "BULLISH remains absent from the decision surface")

selection = prov["display_selection"]
ok(selection["card_cap"] == 5
   and selection["coverage_bands_considered"] ==
   selection["coverage_band_count"] == 3,
   "artifact declares the approved three-band coverage inside a five-card cap")
ok("recompute exact-distinct fork counts" in selection["band_derivation"]
   and "positive-count rounds" in selection["band_derivation"]
   and "zero-count terminal round" in selection["band_derivation"],
   "artifact discloses data-derived bands and terminal-zero handling")
ok("computed separation floor" in selection["selection_rule"]
   and "no-separable-decision line" in selection["selection_rule"]
   and "cannot re-enter globally" in selection["selection_rule"]
   and "exact spread ties" in selection["selection_rule"],
   "artifact discloses conditional band selection and floor-filtered global fill")
floor_meta = selection["separation_floor"]
ok(floor_meta["classes_n"] == 2
   and "within-class squared error" in floor_meta["method"]
   and "midpoint" in floor_meta["method"]
   and floor_meta["comparison"] ==
   "spread >= floor clears; compare at full precision",
   "artifact derives a two-class presentation floor without typing its value")
toy_floor = derive_separation_floor([0.0, 0.0, 1.0, 1.0])
ok(toy_floor["floor"] == 0.5
   and toy_floor["low_class"]["n"] == 2
   and toy_floor["high_class"]["n"] == 2,
   "spread classes never split observations tied at the boundary")
try:
    derive_separation_floor([1.0, 1.0, 1.0])
    degenerate_floor_rejected = False
except ValueError:
    degenerate_floor_rejected = True
ok(degenerate_floor_rejected,
   "an all-tied board fails loudly instead of inventing a card/null boundary")
ok("Candidate supply is the larger observed driver" in
   selection["supply_diagnosis"]
   and "Wider later frontier spreads also contribute" in
   selection["supply_diagnosis"]
   and "presentation selection only" in selection["supply_diagnosis"],
   "artifact records the computed supply-first diagnosis as presentation provenance")

builder = open(os.path.join(ROOT, "src", "build_vona_tree.py")).read()
old_tokens = ("SURV_FLOOR", "branch_eps_by_depth", "narrow_band",
              "narrowly_dominated", "def p25", "terminal_lineup_range",
              "prune_rule")
ok(not any(token in builder for token in old_tokens),
   "builder contains no survival floor, p25 epsilon, or modal terminal pruning")
ok("if nxt is None" in builder and "requires a real next owner pick" in builder,
   "builder rejects a VONA call without a next owner pick")
artifact_text = json.dumps(tree)
ok(not any(token in artifact_text for token in
           ("surv_floor", "branch_eps", "narrow_band", "narrowly_dominated",
            "terminal_lineup_range", "pruned", "p25")),
   "artifact publishes none of the removed threshold or terminal-prune machinery")

try:
    vona_at({"RB": [p for p in players if p["pos"] == "RB"][:2]}, 1, None)
    rejected_missing_next = False
except ValueError:
    rejected_missing_next = True
ok(rejected_missing_next, "runtime refuses the old terminal next-pick null")

# The distribution includes the replacement state and excludes negative VOR.
toy = [{"name": "A", "vor": 10.0}, {"name": "B", "vor": 5.0},
       {"name": "C", "vor": -100.0}]
toy_e, toy_states, toy_none = best_states(toy, lambda _p: 0.5)
ok(math.isclose(sum(q for _, q in toy_states) + toy_none, 1.0, abs_tol=1e-12),
   "top-survivor states plus replacement sum to one")
ok(math.isclose(toy_e, 6.25, abs_tol=1e-12) and len(toy_states) == 2,
   "expected best uses positive VOR states and excludes negative VOR")

# The Pareto rule retains a real tradeoff, rejects a dominated action, is
# order-invariant, and decides on raw rather than rounded display coordinates.
synthetic = [
    {"pos": "RB", "vona_raw": 10.0, "expected_lineup_gain_raw": 1.0},
    {"pos": "WR", "vona_raw": 9.0, "expected_lineup_gain_raw": 2.0},
    {"pos": "TE", "vona_raw": 8.0, "expected_lineup_gain_raw": 0.5},
]
want_front = {"RB", "WR"}
ok({a["pos"] for a in pareto_front(synthetic)} == want_front,
   "Pareto rule keeps the tradeoff and removes the dominated action")
ok({a["pos"] for a in pareto_front(list(reversed(synthetic)))} == want_front,
   "Pareto action set is invariant to iteration order")
near_tie = [
    {"pos": "RB", "vona_raw": 1.00494, "expected_lineup_gain_raw": 1.000094},
    {"pos": "WR", "vona_raw": 1.00491, "expected_lineup_gain_raw": 1.000091},
]
ok({a["pos"] for a in pareto_front(near_tie)} == {"RB"},
   "display-equal near ties are resolved by full-precision coordinates")

# The shared feasibility rule allows every actually observed FLEX position and
# rejects two simultaneous uses of the single shared slot.
ok(starter_path_feasible({"QB": 1, "RB": 3, "WR": 2, "TE": 1}, 0,
                         flex_positions),
   "one RB FLEX composition is feasible")
ok(starter_path_feasible({"QB": 1, "RB": 2, "WR": 3, "TE": 1}, 0,
                         flex_positions),
   "one WR FLEX composition is feasible")
ok(starter_path_feasible({"QB": 1, "RB": 2, "WR": 2, "TE": 2}, 0,
                         flex_positions),
   "observed TE FLEX composition is feasible")
ok(not starter_path_feasible({"QB": 1, "RB": 3, "WR": 3, "TE": 1}, 0,
                             flex_positions),
   "RB3 plus WR3 cannot consume two shared FLEX slots")


def independent_states(pool, pick):
    expected, none, states = 0.0, 1.0, []
    for p in pool:
        if p["vor"] <= 0:
            break
        available = survival(p["adp"], pick)
        p_top = none * available
        states.append((p, p_top))
        expected += p["vor"] * p_top
        none *= 1 - available
    return expected, states, none


def independent_dominates(left, right):
    return (left["vona_raw"] >= right["vona_raw"]
            and left["gain_raw"] >= right["gain_raw"]
            and (left["vona_raw"] > right["vona_raw"]
                 or left["gain_raw"] > right["gain_raw"]))


all_nodes = []
all_leaves = []
round7 = []
total_forks = 0

for slot, slot_tree in tree["slots"].items():
    full_picks = snake_picks(int(slot))
    ok(slot_tree["picks"] == full_picks[:7], f"slot {slot}: seven display picks")
    ok(slot_tree["next_picks"] == full_picks[1:8],
       f"slot {slot}: every display pick has its real next owner pick")
    ok(slot_tree["nodes"] <= rules["max_nodes_per_slot"],
       f"slot {slot}: rendered tree clears the UI budget")

    observed = {"forks": 0, "groups": 0, "actions": 0}

    def check_siblings(nodes, unavailable, roster, counts, depth):
        observed["groups"] += 1
        if len(nodes) > 1:
            observed["forks"] += 1
        pick, nxt = full_picks[depth - 1], full_picks[depth]
        actions = []
        for pos in POSITIONS:
            pool = [p for p in players
                    if p["pos"] == pos and p["name"] not in unavailable]
            if not pool:
                continue
            now, states, p_none = independent_states(pool, pick)
            later, _later_states, _later_none = independent_states(pool, nxt)
            proposed = Counter(counts)
            proposed[pos] += 1
            if not starter_path_feasible(proposed, 7 - depth, flex_positions):
                continue
            base = phantom_lineup_pts(roster, eng["baselines"])
            gain = sum(
                q * (phantom_lineup_pts(
                    roster + [{"name": p["name"], "pos": p["pos"],
                               "pts": p["pts"]}], eng["baselines"]) - base)
                for p, q in states)
            actions.append({"pos": pos, "pool": pool, "now": now, "later": later,
                            "states": states, "p_none": p_none,
                            "vona_raw": now - later, "gain_raw": gain})
        observed["actions"] += len(actions)
        ok(all(not ({p["name"] for p in action["pool"]} & unavailable)
               for action in actions),
           f"slot {slot} round {depth}: no modal-state absence is resurrected")

        independently_front = {
            action["pos"] for action in actions
            if not any(independent_dominates(other, action)
                       for other in actions if other is not action)
        }
        rendered_positions = {node["pos"] for node in nodes}
        ok(rendered_positions == independently_front,
           f"slot {slot} round {depth}: rendered siblings equal the real-board Pareto set",
           f"rendered={sorted(rendered_positions)} expected={sorted(independently_front)}")
        ledgers = [node["decision_set"] for node in nodes]
        ok(all(ledger == ledgers[0] for ledger in ledgers),
           f"slot {slot} round {depth}: siblings share one decision ledger")
        ledger_by_pos = {entry["pos"]: entry for entry in ledgers[0]}
        ok(set(ledger_by_pos) == {action["pos"] for action in actions},
           f"slot {slot} round {depth}: ledger contains every feasible action")
        for action in actions:
            entry = ledger_by_pos[action["pos"]]
            witnesses = sorted(other["pos"] for other in actions
                               if other is not action
                               and independent_dominates(other, action))
            ok(entry["pareto"] == (action["pos"] in independently_front)
               and entry["dominated_by"] == witnesses,
               f"slot {slot} round {depth}: Pareto flag and witnesses recompute")
            ok(math.isclose(entry["vona_raw"], action["vona_raw"], abs_tol=1e-12)
               and math.isclose(entry["expected_lineup_gain_raw"],
                                action["gain_raw"], abs_tol=1e-12),
               f"slot {slot} round {depth}: raw ledger coordinates recompute")
            ok(entry["expected_lineup_gain"] == round(action["gain_raw"], 4),
               f"slot {slot} round {depth}: display ledger gain derives from raw")

        by_pos_action = {action["pos"]: action for action in actions}
        for node in nodes:
            all_nodes.append((slot, node))
            action = by_pos_action[node["pos"]]
            ok(node["forced"] == (len(nodes) == 1),
               f"slot {slot}: forced flag matches rendered siblings")
            expected_force_basis = (None if len(nodes) > 1 else
                                    "feasibility" if len(actions) == 1 else
                                    "pareto-dominance")
            ok(node["force_basis"] == expected_force_basis,
               f"slot {slot}: forced reason distinguishes feasibility from dominance")
            ok((expected_force_basis != "feasibility" or
                "Feasibility-forced" in node["why"])
               and (expected_force_basis != "pareto-dominance" or
                    "Pareto-dominant" in node["why"])
               and (expected_force_basis is not None or
                    "Pareto tradeoff" in node["why"]),
               f"slot {slot}: displayed reason matches the actual branch mechanism")
            ok(node["round"] == depth, f"slot {slot}: node round matches depth")
            ok(node["pick"] == pick and node["next_pick"] == nxt,
               f"slot {slot}: node uses real current and next owner picks")
            ok(node["vona"] == round(node["e_now"] - node["e_next"], 2),
               f"slot {slot}: published VONA is published E[now] minus E[next]")
            ok(node["vona"] >= 0 and node["e_next"] <= node["e_now"] + 1e-9,
               f"slot {slot}: expected availability is monotone")
            ok(math.isclose(node["decision_vona_raw"], action["vona_raw"],
                            abs_tol=1e-12)
               and math.isclose(node["decision_expected_lineup_gain_raw"],
                                action["gain_raw"], abs_tol=1e-12),
               f"slot {slot}: node decision uses unrounded coordinates")
            ok(node["e_now"] == round(action["now"], 2)
               and node["e_next"] == round(action["later"], 2),
               f"slot {slot}: both expectations independently recompute")
            ok(node["expected_lineup_gain"] == round(action["gain_raw"], 4),
               f"slot {slot}: expected lineup gain uses every current state")
            ok(node["continuation_basis"] ==
               "coherent modal-state representative path"
               and "terminal_lineup_range" not in node,
               f"slot {slot}: continuation is representative, never terminal proof")
            ok("bullish" not in json.dumps(node).lower(),
               f"slot {slot}: no BULLISH marker on any node")

            states, p_none = action["states"], action["p_none"]
            ok(math.isclose(sum(q for _, q in states) + p_none, 1.0,
                            abs_tol=1e-9),
               f"slot {slot}: player and replacement state probabilities sum to one")
            player, p_top = (max(states, key=lambda item: (item[1], item[0]["vor"]))
                             if states else (None, 0.0))
            replacement_modal = p_none >= p_top
            ok(node["fallback_required"] == replacement_modal,
               f"slot {slot}: fallback follows the modal distribution")
            ok(node["p_top_survivor"] == round(p_top, 3)
               and node["p_no_above_replacement"] == round(p_none, 3)
               and node["p_modal_state"] == round(max(p_none, p_top), 3),
               f"slot {slot}: modal and replacement probabilities recompute")

            if replacement_modal:
                ok(node["name"] is None and node["adp"] is None
                   and node["p_available"] is None,
                   f"slot {slot}: fallback null invents no player or market number")
                picked = {"name": f"replacement:{node['pos']}:round{depth}",
                          "pos": node["pos"],
                          "pts": eng["baselines"][node["pos"]]}
                modal_gone = [p["name"] for p, _q in states]
                continuation_removed = modal_gone
            else:
                ok(node["name"] == player["name"],
                   f"slot {slot}: displayed player is the modal top-survivor")
                ok(node["p_available"] == round(survival(player["adp"], pick), 3),
                   f"slot {slot}: displayed player availability recomputes")
                tier_pool = [p for p in action["pool"] if p["vor"] > 0
                             and p.get("tier") == player.get("tier")]
                tier_expected = sum(survival(p["adp"], pick) for p in tier_pool)
                tier_none = math.prod(1 - survival(p["adp"], pick)
                                      for p in tier_pool)
                ok(node["tier_expected_available"] == round(tier_expected, 2)
                   and node["tier_p_any"] == round(1 - tier_none, 3),
                   f"slot {slot}: tier availability fields recompute")
                picked = {"name": player["name"], "pos": player["pos"],
                          "pts": player["pts"]}
                state_players = [p for p, _q in states]
                selected_index = next(
                    i for i, p in enumerate(state_players)
                    if p["name"] == player["name"])
                modal_gone = [p["name"]
                              for p in state_players[:selected_index]]
                continuation_removed = modal_gone + [player["name"]]

            ok(node["modal_state_gone"] == modal_gone
               and node["continuation_removed"] == continuation_removed,
               f"slot {slot}: continuation preserves the complete modal event")
            next_unavailable = unavailable | set(continuation_removed)

            next_counts = Counter(counts)
            next_counts[node["pos"]] += 1
            ok(starter_path_feasible(next_counts, 7 - depth, flex_positions),
               f"slot {slot}: partial path can complete one exact starter target")
            next_roster = roster + [picked]
            if depth == 7:
                round7.append((slot, node))
                ok(not node["children"], f"slot {slot}: no round-8 child is rendered")
                all_leaves.append((slot, next_counts, depth))
            else:
                ok(bool(node["children"]),
                   f"slot {slot}: every pre-terminal node continues to round 7")
                check_siblings(node["children"], next_unavailable, next_roster,
                               next_counts, depth + 1)

    check_siblings(slot_tree["roots"], set(), [], Counter(), 1)
    ok(observed["forks"] == slot_tree["rendered_forks"],
       f"slot {slot}: rendered fork count matches the actual tree")
    ok(observed["groups"] == slot_tree["decision_groups"],
       f"slot {slot}: decision-group count matches the actual tree")
    ok(observed["actions"] == slot_tree["evaluated_actions"],
       f"slot {slot}: evaluated-action count matches every candidate ledger")
    total_forks += observed["forks"]

ok(round7 and all(node["next_pick"] is not None for _, node in round7),
   "every round-7 node carries a real round-8 owner pick")
ok(all(depth == 7 and dict(counts) in targets
       for _slot, counts, depth in all_leaves),
   "every leaf fills exactly one supported seven-starter composition",
   str([(s, dict(c), d) for s, c, d in all_leaves
        if d != 7 or dict(c) not in targets][:3]))
ok(sum(v["nodes"] for v in tree["slots"].values()) == len(all_nodes),
   "reported rendered-node counts equal artifact values")
ok(total_forks == sum(v["rendered_forks"] for v in tree["slots"].values()),
   "fork ledger reconciles without requiring a quota")

# Presentation bands come from the committed artifact's exact-distinct fork
# supply. They never alter or truncate the raw occurrence tree above.
distinct_by_slot = {
    slot: exact_distinct_forks(payload)
    for slot, payload in tree["slots"].items()
}
fork_counts = Counter(
    nodes[0]["round"]
    for groups in distinct_by_slot.values() for nodes in groups)
expected_counts = {str(r): fork_counts[r] for r in range(1, prov["depth"] + 1)}
expected_bands = derive_display_bands(fork_counts, depth=prov["depth"],
                                      band_count=selection["coverage_band_count"])
ok(selection["fork_counts_by_round"] == expected_counts
   and selection["distinct_forks_n"] == sum(fork_counts.values()),
   "display provenance recomputes exact-distinct fork supply by round")
ok(selection["raw_fork_occurrences_n"] == total_forks
   and selection["distinct_forks_n"] <= total_forks,
   "display provenance distinguishes raw fork occurrences from exact deduplication")
ok(selection["bands"] == expected_bands,
   "display bands are the deterministic minimum-error contiguous partition")
ok(selection["occupied_rounds"] ==
   [r for r in range(1, prov["depth"] + 1) if fork_counts[r] > 0]
   and selection["zero_fork_rounds"] ==
   [r for r in range(1, prov["depth"] + 1) if fork_counts[r] == 0],
   "band provenance publishes positive support and genuine zero-fork rounds")
ok(expected_bands[0]["start_round"] == 1
   and expected_bands[-1]["end_round"] == prov["depth"]
   and all(left["end_round"] + 1 == right["start_round"]
           for left, right in zip(expected_bands, expected_bands[1:])),
   "derived bands cover the full display horizon without gaps")

expected_support = {}
for slot, groups in distinct_by_slot.items():
    expected_support[slot] = {
        band["label"]: sum(
            band["start_round"] <= nodes[0]["round"] <= band["end_round"]
            for nodes in groups)
        for band in expected_bands
    }
ok(selection["slot_band_fork_counts"] == expected_support
   and all(count > 0 for row in expected_support.values()
           for count in row.values()),
   "every slot has an exact-distinct fork in every derived band before gating")

raw_fork_groups = [
    nodes for payload in tree["slots"].values()
    for nodes in iter_decision_groups(payload["roots"]) if len(nodes) > 1
]
raw_fork_nodes = [node for nodes in raw_fork_groups for node in nodes]
expected_vona_sd = population_sd(
    [node["decision_vona_raw"] for node in raw_fork_nodes])
expected_gain_sd = population_sd(
    [node["decision_expected_lineup_gain_raw"] for node in raw_fork_nodes])
spread_evidence = selection["spread_evidence"]
norm = spread_evidence["normalization"]
ok(norm["alternatives_n"] == len(raw_fork_nodes)
   and math.isclose(norm["vona_population_sd"], expected_vona_sd,
                    abs_tol=1e-12)
   and math.isclose(norm["lineup_gain_population_sd"], expected_gain_sd,
                    abs_tol=1e-12),
   "spread evidence normalizes over every raw frontier alternative")
raw_fork_spreads = [
    normalized_frontier_spread(nodes, expected_vona_sd, expected_gain_sd)
    for nodes in raw_fork_groups
]
alternative_weighted_spreads = [
    spread for spread, nodes in zip(raw_fork_spreads, raw_fork_groups)
    for _node in nodes
]
expected_floor = derive_separation_floor(alternative_weighted_spreads)
for key in ("classes_n", "method", "floor", "comparison", "low_class",
            "high_class", "variance_explained"):
    ok(floor_meta[key] == expected_floor[key],
       f"separation floor {key} recomputes from all raw alternatives")
ok(floor_meta["alternatives_n"] == len(raw_fork_nodes)
   and floor_meta["fork_occurrences_n"] == len(raw_fork_groups)
   and floor_meta["distinct_forks_n"] == selection["distinct_forks_n"]
   and "every alternative carries" in floor_meta["sample_unit"],
   "separation-floor provenance names and reconciles its sample units")
distinct_spreads = [
    normalized_frontier_spread(nodes, expected_vona_sd, expected_gain_sd)
    for groups in distinct_by_slot.values() for nodes in groups
]
distinct_floor = derive_separation_floor(distinct_spreads)
distinct_check = floor_meta["distinct_candidate_check"]
ok(distinct_check["n"] == len(distinct_spreads)
   and distinct_check["floor"] == distinct_floor["floor"]
   and distinct_check["matches_alternative_weighted_boundary"] ==
   math.isclose(distinct_floor["floor"], expected_floor["floor"],
                abs_tol=1e-12),
   "floor provenance reports the exact-distinct robustness check honestly")
ok(floor_meta["low_class"]["max"] < floor_meta["floor"] <
   floor_meta["high_class"]["min"]
   and floor_meta["low_class"]["n"] + floor_meta["high_class"]["n"] ==
   len(raw_fork_nodes),
   "computed floor lies strictly inside the observed class boundary")

expected_outcomes = {}
expected_eligible = {}
expected_cleared = expected_fallback = 0
for slot, groups in distinct_by_slot.items():
    scored = [(normalized_frontier_spread(nodes, expected_vona_sd,
                                           expected_gain_sd), nodes)
              for nodes in groups]
    expected_eligible[slot] = sum(
        spread >= expected_floor["floor"] for spread, _nodes in scored)
    row = {}
    for band in expected_bands:
        candidates = [(spread, nodes) for spread, nodes in scored
                      if band["start_round"] <= nodes[0]["round"] <=
                      band["end_round"]]
        spread = max(value for value, _nodes in candidates)
        clears = spread >= expected_floor["floor"]
        expected_cleared += clears
        expected_fallback += not clears
        row[band["label"]] = {
            "winner_spread": spread,
            "clears": clears,
        }
    expected_outcomes[slot] = row
ok(selection["slot_band_outcomes"] == expected_outcomes
   and selection["bands_cleared_n"] == expected_cleared
   and selection["bands_fallback_n"] == expected_fallback,
   "every slot-band clearance and honest fallback recomputes at full precision")
ok(selection["eligible_distinct_forks_by_slot"] == expected_eligible
   and all(count >= selection["card_cap"] for count in expected_eligible.values()),
   "floor-filtered global refill can fill the current cap without a below-floor card")
for band in expected_bands:
    values = [
        normalized_frontier_spread(nodes, expected_vona_sd, expected_gain_sd)
        for groups in distinct_by_slot.values() for nodes in groups
        if band["start_round"] <= nodes[0]["round"] <= band["end_round"]
    ]
    reported = spread_evidence["by_band"][band["label"]]
    ok(reported["n"] == len(values)
       and math.isclose(reported["mean"], sum(values) / len(values),
                        abs_tol=1e-12)
       and math.isclose(reported["max"], max(values), abs_tol=1e-12),
       f"spread evidence {band['label']}: n, mean, and max recompute")

recomputed_selection = display_selection_provenance(tree["slots"])
ok(recomputed_selection == selection,
   "complete display-selection provenance deterministically rebuilds")

terminal_groups = [
    nodes for payload in tree["slots"].values()
    for nodes in iter_decision_groups(payload["roots"])
    if nodes and nodes[0]["round"] == prov["depth"]
]
terminal_check = selection["terminal_round_check"]
ok(terminal_check["round"] == prov["depth"]
   and terminal_check["lookahead_round"] == prov["value_lookahead_rounds"]
   and terminal_check["decision_groups_n"] == len(terminal_groups)
   and terminal_check["forks_n"] == sum(len(nodes) > 1
                                         for nodes in terminal_groups)
   and terminal_check["multi_action_ledgers_n"] == sum(
       len(nodes[0]["decision_set"]) > 1 for nodes in terminal_groups)
   and "genuine Pareto result" in terminal_check["result"],
   "terminal zero-fork result is reconciled after real round-8 lookahead")

# Correlation disclosure reports descriptive counts and Wilson intervals without
# pretending adjacency identifies player-level survival or a bias direction.
corr = tree["correlation"]
seq = defaultdict(list)
for row in csv.DictReader(open(os.path.join(ROOT, "out", "picks.csv"))):
    seq[row["season"]].append(row["pos"])
for pos in POSITIONS:
    contexts = repeats = base_n = base_k = 0
    for positions in seq.values():
        for current, nxt in zip(positions, positions[1:]):
            base_n += 1
            base_k += nxt == pos
            if current == pos:
                contexts += 1
                repeats += nxt == pos
    d = corr["by_pos"][pos]
    ok(d["repeat_contexts_n"] == contexts
       and d["same_position_next_k"] == repeats
       and d["marginal_next_n"] == base_n
       and d["marginal_next_k"] == base_k,
       f"correlation disclosure {pos}: every within-season adjacency is counted")
    ok(d["repeat_wilson95"] == wilson(repeats, contexts)
       and d["marginal_wilson95"] == wilson(base_k, base_n),
       f"correlation disclosure {pos}: Wilson intervals recompute")
ok(corr["bias_direction"].startswith("UNKNOWN")
   and "joint distribution" in corr["what_breaks"],
   "correlation limitation states what breaks without inventing a bias sign")

page = open(os.path.join(ROOT, "out", "paths.html")).read()
ok('data-active="paths"' in page and "vona_tree_2026.json" in page,
   "paths page joins the nav and reads the artifact")
ok("decision_groups" in page and "evaluated_actions" in page
   and "distinct tradeoffs shown" in page and "decision_set" in page
   and "dominated_by" in page and "Decision ledger" in page,
   "paths page renders grouped candidate ledgers plus initial and full counts")
ok("rules.continuation" in page and "what_breaks" in page
   and "repeat_rate" in page and "repeat_wilson95" in page
   and "marginal_wilson95" in page and "Wilson 95%" in page,
   "paths page surfaces modal and correlation limitations")
ok("branch_eps" not in page and "narrow_band" not in page
   and "surv_floor" not in page and "COIN FLIP" not in page
   and "prune_rule" not in page,
   "paths page contains none of the removed floor, epsilon, or prune language")
ok("BULLISH" not in page.upper().replace("BULLISH_ON_NODES", ""),
   "paths page renders no BULLISH marker")
ok("Fallback required" in page and "Model disclosure" in page,
   "paths page renders the honest null and model disclosures")
ok("DISPLAY_SELECTION.card_cap" in page and "priority-grid" in page
   and "distinct tradeoffs shown" in page and "fork occurrences represented" in page
   and "tree nodes shown initially" in page,
   "paths page reads its initial card cap from artifact provenance")
ok("populationSd" in page and "frontierSpread" in page
   and "decision_vona_raw" in page
   and "decision_expected_lineup_gain_raw" in page
   and "maximum pairwise distance" in page
   and "Downstream decision reach breaks" in page,
   "priority cards rank objective-symmetric normalized frontier spread")
ok("selectPriorityForks" in page and "DISPLAY_SELECTION.bands" in page
   and "bandForRound" in page and "Draft-depth coverage" in page
   and "Coverage selection" in page and 'data-band="' in page,
   "paths page applies and labels artifact-derived draft-depth coverage")
ok("separation_floor.floor" in page and "frontierSpread >= floor" in page
   and "No separable " in page and "board floor " in page
   and 'data-best-spread="' in page and 'data-floor="' in page,
   "paths page gates every initial card and renders an auditable band null")
ok("var eligible = ordered.filter" in page
   and "eligible.forEach" in page
   and "ordered.forEach" not in page,
   "global refill cannot reintroduce a fork that failed the separation floor")
ok("start_round" in page and "end_round" in page
   and not re.search(r"(?:round|R)\s*1\s*[-–]\s*3\s*/\s*4", page, re.I),
   "paths page consumes computed band boundaries instead of typing them")
ok("localDecisionSignature" in page and "aggregateExactDecisions" in page
   and "presentationOccurrences" in page and "modeled tree paths" in page,
   "five-card cap aggregates only exact repeated local payloads and discloses paths")
ok('role="group" aria-label="Draft slot"' in page
   and 'aria-pressed="' in page and '<h3 class="decision-title">' in page,
   "paths priority surface exposes accessible controls and card headings")
ok('aria-expanded="false"' in page and 'id="fullTree"></div>' in page
   and "full.innerHTML = fullGroupHtml(root)" in page
   and 'full.innerHTML = ""' in page,
   "complete tree is absent initially, created on disclosure, and removed on hide")
ok(page.count("ledgerHtml(g.nodes[0])") == 2
   and "g.nodes.map(alternativeHtml)" in page,
   "initial and disclosed groups each render one shared ledger, not one per sibling")
ok('data-availability="' in page and "avail-fill" in page
   and "literal probability" in page and "linear from 0% to 100%" in page
   and "never filters, ranks, branches, or changes the model" in page,
   "every named alternative gets an exact continuous availability scale")
ok("LOW AVAILABILITY" not in page.upper()
   and "SURVIVAL FLOOR" not in page.upper()
   and not re.search(r"(?:below|under|less than)\s+40%", page, re.I),
   "availability presentation contains no binary threshold or recycled floor")
avail_color = re.search(r"--avail:\s*(#[0-9a-fA-F]{6})", page)
reserved = {"#34d399", "#f87171", "#fbbf24", "#60a5fa",
            "#047857", "#b91c1c", "#b45309", "#0f766e"}
ok(bool(avail_color) and avail_color.group(1).lower() not in reserved,
   "continuous availability scale uses none of the reserved verdict colors")
null_rule = re.search(r"\.band-null\{([^}]*)\}", page)
ok(bool(null_rule)
   and not any(color in null_rule.group(1).lower() for color in reserved)
   and "var(--ink2)" in null_rule.group(1),
   "no-separable-decision treatment is neutral and uses no verdict color")

if FAILS:
    print(f"\n{len(FAILS)} FAILURES")
    sys.exit(1)
print("\nALL PASS")
