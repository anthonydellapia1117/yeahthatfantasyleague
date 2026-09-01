#!/usr/bin/env python3
"""Build the Python-canonical parity corpus for the RxR browser policy.

The fixture is intentionally a contract artifact, not a production input.  It
mixes fixed edge cases with the current slot-4 geometry so the JavaScript mirror
cannot drift from Python while still passing only toy examples.
"""
import json
import os

from forward_policy import roster_caps, score_candidates

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "out", "engine_2026.json")
OUT = os.path.join(ROOT, "out", "data", "rxr_policy_reference.json")


def player(pid, name, pos, pts, vor):
    return {"sleeper_id": str(pid), "name": name, "pos": pos,
            "pts": float(pts), "vor": float(vor)}


def case(name, pool, roster, baselines, caps):
    return {
        "name": name,
        "pool": pool,
        "roster": roster,
        "baselines": baselines,
        "caps": caps,
        "expected": score_candidates(pool, roster, baselines, caps),
    }


def compact(p):
    return {"sleeper_id": p["sleeper_id"], "name": p["name"],
            "pos": p["pos"], "pts": p["pts"], "vor": p["vor"]}


def main():
    with open(ENGINE) as fh:
        eng = json.load(fh)
    baselines = eng["baselines"]
    caps = roster_caps(eng["flex_allocation"])
    by_name = {p["name"]: compact(p) for p in eng["players"]}
    top = [compact(p) for p in eng["players"][:10]]
    floor = next(compact(p) for p in eng["players"] if p["pos"] == "DEF")

    cases = [
        case("observed_slot4_empty", top + [floor], [], baselines, caps),
        case("observed_slot4_puka", [by_name[n] for n in (
            "Brock Bowers", "Derrick Henry", "Kenneth Walker",
            "Nico Collins", "Javonte Williams")] + [floor],
             [by_name["Puka Nacua"]], baselines, caps),
        case("observed_slot4_puka_bowers", [by_name[n] for n in (
            "Derrick Henry", "Kenneth Walker", "Nico Collins",
            "Javonte Williams", "Trey McBride")] + [floor],
             [by_name["Puka Nacua"], by_name["Brock Bowers"]],
             baselines, caps),
    ]

    zero = {pos: 0.0 for pos in ("QB", "RB", "WR", "TE", "K", "DEF")}
    roomy = {"QB": 2, "RB": 4, "WR": 4, "TE": 2, "K": 1, "DEF": 1}
    cases += [
        case("rounding_and_vor_tiebreak", [
            player("r1", "Round A", "QB", 10.00005, 1),
            player("r2", "Round B", "QB", 10.000049, 99),
            player("r3", "Round C", "QB", 10.00005, 1),
        ], [], zero, roomy),
        case("same_display_name_distinct_ids", [
            player("same-b", "Same Name", "WR", 11, 4),
        ], [player("same-a", "Same Name", "WR", 12, 5)], zero, roomy),
        case("flex_filled_and_projection_floors", [
            player("rb4", "Fourth RB", "RB", 8, 8),
            player("wr4", "Fourth WR", "WR", 7, 7),
            player("k1", "K Floor", "K", 99, 99),
            player("d1", "DEF Floor", "DEF", 99, 99),
        ], [
            player("rb1", "RB One", "RB", 15, 15),
            player("rb2", "RB Two", "RB", 14, 14),
            player("rb3", "RB Three", "RB", 13, 13),
            player("wr1", "WR One", "WR", 12, 12),
            player("wr2", "WR Two", "WR", 11, 11),
            player("te1", "TE One", "TE", 10, 10),
        ], zero, roomy),
        case("cap_and_over_cap", [
            player("rb-new", "RB Capped", "RB", 20, 20),
            player("wr-new", "WR Live", "WR", 9, 9),
        ], [
            player("rb-a", "RB A", "RB", 5, 5),
            player("rb-b", "RB B", "RB", 4, 4),
        ], zero, {**roomy, "RB": 2}),
        case("cap_minus_one", [
            player("rb-live", "RB Still Live", "RB", 20, 20),
        ], [player("rb-held", "RB Held", "RB", 4, 4)],
             zero, {**roomy, "RB": 2}),
        case("over_cap_is_still_ineligible", [
            player("rb-over-new", "RB Over", "RB", 20, 20),
        ], [
            player("rb-over-a", "RB Over A", "RB", 5, 5),
            player("rb-over-b", "RB Over B", "RB", 4, 4),
            player("rb-over-c", "RB Over C", "RB", 3, 3),
        ], zero, {**roomy, "RB": 2}),
        case("bench_heavy_roster", [
            player("bench-rb", "Bench RB", "RB", 8, 2),
            player("bench-te", "Bench TE", "TE", 7, 1),
        ], [
            player("bench-qb-a", "Bench QB A", "QB", 20, 20),
            player("bench-qb-b", "Bench QB B", "QB", 19, 19),
            player("bench-wr-a", "Bench WR A", "WR", 18, 18),
            player("bench-wr-b", "Bench WR B", "WR", 17, 17),
            player("bench-wr-c", "Bench WR C", "WR", 16, 16),
            player("bench-wr-d", "Bench WR D", "WR", 15, 15),
        ], zero, roomy),
        case("all_candidates_outside_domain", [
            player("full-qb-new", "Full QB", "QB", 20, 20),
            player("full-rb-new", "Full RB", "RB", 20, 20),
            player("full-wr-new", "Full WR", "WR", 20, 20),
            player("full-te-new", "Full TE", "TE", 20, 20),
            player("full-k-new", "Full K", "K", 20, 20),
        ], [
            player("full-qb", "Full QB Held", "QB", 5, 5),
            player("full-rb", "Full RB Held", "RB", 5, 5),
            player("full-wr", "Full WR Held", "WR", 5, 5),
            player("full-te", "Full TE Held", "TE", 5, 5),
        ], zero, {**roomy, "QB": 1, "RB": 1, "WR": 1, "TE": 1}),
        case("mutation_bite", [
            player("mut-qb", "High VOR Duplicate QB", "QB", 19, 100),
            player("mut-rb", "Lineup Improving RB", "RB", 18, 5),
        ], [player("mut-held", "Held QB", "QB", 20, 20)], zero, roomy),
    ]

    error_inputs = [
        {"name": "duplicate_pool_id",
         "pool": [player("dup", "Dup A", "RB", 1, 1),
                  player("dup", "Dup B", "WR", 1, 1)],
         "roster": [], "baselines": zero, "caps": roomy,
         "error": "duplicate player id"},
        {"name": "pool_roster_overlap",
         "pool": [player("overlap", "Overlap", "RB", 1, 1)],
         "roster": [player("overlap", "Overlap", "RB", 1, 1)],
         "baselines": zero, "caps": roomy, "error": "overlaps roster"},
        {"name": "missing_cap",
         "pool": [player("cap", "Cap", "RB", 1, 1)], "roster": [],
         "baselines": zero,
         "caps": {k: v for k, v in roomy.items() if k != "TE"},
         "error": "caps incomplete"},
        {"name": "unknown_position",
         "pool": [player("unk", "Unknown", "LS", 1, 1)], "roster": [],
         "baselines": zero, "caps": roomy, "error": "unknown policy position"},
        {"name": "numeric_string_is_not_a_score",
         "pool": [{"sleeper_id": "str-pts", "name": "String Points",
                   "pos": "RB", "pts": "1", "vor": 1.0}],
         "roster": [], "baselines": zero, "caps": roomy,
         "error": "non-finite pts"},
        {"name": "boolean_is_not_a_cap",
         "pool": [player("bool-cap", "Boolean Cap", "RB", 1, 1)],
         "roster": [], "baselines": zero,
         "caps": {**roomy, "RB": True}, "error": "caps invalid"},
    ]
    for item in error_inputs:
        try:
            score_candidates(item["pool"], item["roster"],
                             item["baselines"], item["caps"])
        except ValueError as exc:
            if item["error"] not in str(exc):
                raise AssertionError(f"{item['name']}: wrong error {exc}")
        else:
            raise AssertionError(f"{item['name']}: expected failure")

    out = {
        "contract": "src/forward_policy.py::score_candidates",
        "browser_mirror": "out/rxr_policy.js::RxRPolicy.scoreCandidates",
        "engine_content_sha256": eng["content_sha256"],
        "primary_slot": eng["draft_order_context"]["primary_slot"],
        "round4": [{"input": x, "expected": round(x, 4)} for x in (
            1.23444, 1.23445, 1.23455, 2.67505, -1.23445, 10.00005,
            10.000049, 0.00005, -0.00005)],
        "cases": cases,
        "error_cases": error_inputs,
        "mutation_case": "mutation_bite",
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    print(f"wrote {OUT}: {len(cases)} cases")


if __name__ == "__main__":
    main()
