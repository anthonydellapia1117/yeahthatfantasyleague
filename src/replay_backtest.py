#!/usr/bin/env python3
"""Item 5: replay the VOR core + survival model against Anthony's actual
picks, honestly scoped.

WHAT CAN AND CANNOT BE REPLAYED, STATED UP FRONT
The 2026 engine's projections come from a live third-party feed that does
not exist historically, and its curated inputs (play-callers, depth
charts) have no archive. Neither is approximated silently. The replay
therefore has two honestly-scoped parts:

  PART 1 - THE VALUE CORE, with a stated proxy projection. At each of
  Anthony's actual skill picks in the 13 drafts, three strategies choose
  from the players ACTUALLY still available (one-step deviation - the
  real board state, no counterfactual opponents):
      actual       the player Anthony took
      adp_best     best available by that year's FFC PPR ADP
      replay_vor   max proxy-VOR: prior-season total points under league
                   scoring minus the positional replacement level
                   (QB12/RB30/WR30/TE12 over that year's draftable pool)
  Scored by realized draft-year league points. THE PROXY IS WEAK AND SAYS
  SO: prior-season points is a far cruder projection than the engine's
  real feed, and it prices every rookie at zero. Beat-or-report.

  PART 2 - THE SURVIVAL MODEL, the frozen functions verbatim. The exact
  committed cond_survival (imported read-only from src/engine_2026.py,
  byte-guarded at every merge) is calibrated against 13 years of observed
  outcomes: for each consecutive pair of Anthony's picks and every
  FFC-listed player still available at the first, predicted
  P(survives to the second) versus what actually happened. Reliability
  by predicted-probability decile plus Brier score against the
  always-predict-base-rate baseline.

K/DEF picks are excluded from Part 1 (team defense has no player-week
scoring rows). Players never drafted survive every pick by definition.

Reads out/picks.csv + the fetched history cache. Writes
out/data/replay_backtest.json.
"""
import csv
import datetime
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import analyze_recency as base           # norm, zscore, HISTORY
import analyze_injury as inj             # season_totals
import engine_2026 as eng                # FROZEN survival - read-only import

OUT = os.path.join(ROOT, "out", "data", "replay_backtest.json")
SKILL = ("QB", "RB", "WR", "TE")
REPLACEMENT = {"QB": 12, "RB": 30, "WR": 30, "TE": 12}
ME = "Antdell & Ernie"
SEASONS = range(2013, 2026)
SEED = 20260819
DRAWS = 10000


def main():
    picks = list(csv.DictReader(open(os.path.join(ROOT, "out", "picks.csv"))))
    totals = {y: inj.season_totals(y) for y in range(2012, 2026)}

    value_rows = []          # one per Anthony skill pick: realized pts per strategy
    surv_pairs = []          # (predicted, observed) for the frozen cond_survival
    coverage = {}

    for Y in SEASONS:
        prior, _ = totals[Y - 1]
        realized, _ = totals[Y]
        # prior-season points by normalized name+pos, for FFC rows without gsis
        prior_by_name = {}
        with open(os.path.join(base.HISTORY, f"spw_{Y-1}.csv")) as fh:
            for r in csv.DictReader(fh):
                if r["season_type"] == "REG" and r["position_group"] in SKILL:
                    prior_by_name[(base.norm(r["player_display_name"]),
                                   r["position_group"])] = r["player_id"]
        realized_by_name = {}
        with open(os.path.join(base.HISTORY, f"spw_{Y}.csv")) as fh:
            for r in csv.DictReader(fh):
                if r["season_type"] == "REG" and r["position_group"] in SKILL:
                    realized_by_name[(base.norm(r["player_display_name"]),
                                      r["position_group"])] = r["player_id"]

        yr = sorted([r for r in picks if int(r["season"]) == Y],
                    key=lambda r: int(r["overall"]))
        taken_by = {}                       # norm name+pos -> overall taken
        for r in yr:
            taken_by[(base.norm(r["player_name"]), r["pos"])] = int(r["overall"])

        # the draft universe: FFC list + everyone actually drafted
        universe = {}                       # (nname, pos) -> {adp, proj, realized}
        for p in json.load(open(os.path.join(base.HISTORY, f"ffc_ppr_{Y}.json")))["players"]:
            if p["position"] not in SKILL:
                continue
            key = (base.norm(p["name"]), p["position"])
            pid = prior_by_name.get(key)
            rid = realized_by_name.get(key)
            universe[key] = {
                "adp": float(p["adp"]),
                "proj": prior[pid]["pts"] if pid and pid in prior else 0.0,
                "realized": realized[rid]["pts"] if rid and rid in realized else 0.0,
            }
        for r in yr:
            if r["pos"] not in SKILL:
                continue
            key = (base.norm(r["player_name"]), r["pos"])
            if key not in universe:
                pid = r["player_id"]
                universe[key] = {
                    "adp": 999.0,
                    "proj": prior[pid]["pts"] if pid in prior else 0.0,
                    "realized": realized[pid]["pts"] if pid in realized else 0.0,
                }

        # replacement level per position over this year's universe
        vor_base = {}
        for pos in SKILL:
            pool = sorted((v["proj"] for (n, p), v in universe.items() if p == pos),
                          reverse=True)
            n = REPLACEMENT[pos]
            vor_base[pos] = pool[n - 1] if len(pool) >= n else 0.0

        my = [r for r in yr if r["member_name"] == ME]
        my_skill = [r for r in my if r["pos"] in SKILL]

        # PART 1: one-step deviation at each of my skill picks
        for r in my_skill:
            k = int(r["overall"])
            avail = {key: v for key, v in universe.items()
                     if taken_by.get(key, 10**9) >= k}
            akey = (base.norm(r["player_name"]), r["pos"])
            if akey not in avail:
                continue                     # attribution mismatch; skip, counted
            adp_best = min(avail.items(), key=lambda kv: kv[1]["adp"])
            vor_best = max(avail.items(),
                           key=lambda kv: kv[1]["proj"] - vor_base[kv[0][1]])
            value_rows.append({
                "season": Y, "overall": k, "player": r["player_name"],
                "actual": universe[akey]["realized"],
                "adp_best": adp_best[1]["realized"],
                "replay_vor": vor_best[1]["realized"],
            })

        # PART 2: frozen cond_survival calibration on consecutive my-picks
        mine = sorted(int(r["overall"]) for r in my)
        for k0, k1 in zip(mine, mine[1:]):
            for key, v in universe.items():
                if v["adp"] >= 900 or taken_by.get(key, 10**9) < k0:
                    continue
                pred = eng.cond_survival(v["adp"], k1, k0)
                surv_pairs.append((Y, pred, 1 if taken_by.get(key, 10**9) >= k1 else 0))

        coverage[str(Y)] = {"my_picks": len(my), "my_skill_picks": len(my_skill),
                            "value_rows": sum(1 for x in value_rows if x["season"] == Y),
                            "universe": len(universe)}

    # ---- Part 1 aggregation: paired deltas, season-cluster bootstrap
    n = len(value_rows)
    mean = lambda k: sum(x[k] for x in value_rows) / n
    rng = random.Random(SEED)
    seasons = sorted({x["season"] for x in value_rows})
    by = {s: [x for x in value_rows if x["season"] == s] for s in seasons}

    def boot_delta(a, b):
        ds = []
        for _ in range(DRAWS):
            rows = []
            for _ in seasons:
                rows.extend(by[rng.choice(seasons)])
            ds.append(sum(x[a] - x[b] for x in rows) / len(rows))
        ds.sort()
        return [round(ds[int(len(ds) * .025)], 2), round(ds[int(len(ds) * .975)], 2)]

    part1 = {
        "n_picks": n,
        "mean_realized_pts": {k: round(mean(k), 2)
                              for k in ("actual", "adp_best", "replay_vor")},
        "deltas_per_pick": {
            "actual_minus_adp_best": {"mean": round(mean("actual") - mean("adp_best"), 2),
                                      "ci95": boot_delta("actual", "adp_best")},
            "actual_minus_replay_vor": {"mean": round(mean("actual") - mean("replay_vor"), 2),
                                        "ci95": boot_delta("actual", "replay_vor")},
            "replay_vor_minus_adp_best": {"mean": round(mean("replay_vor") - mean("adp_best"), 2),
                                          "ci95": boot_delta("replay_vor", "adp_best")},
        },
        "proxy_caveat": ("replay_vor prices players by PRIOR-SEASON points only - "
                         "a far weaker projection than the engine's live feed, and "
                         "it values every rookie at zero. This bounds the replay "
                         "from below; it does not measure the 2026 engine."),
    }

    # ---- Part 2 aggregation: reliability by decile + Brier vs base rate,
    # overall and per era (the sd curve is fitted on the current era - if the
    # low-bucket miscalibration is an old-era artifact, the split shows it)
    def calib(pairs):
        m = len(pairs)
        br = sum(o for _, p, o in pairs) / m
        brier = sum((p - o) ** 2 for _, p, o in pairs) / m
        brier_base = sum((br - o) ** 2 for _, p, o in pairs) / m
        deciles = []
        for d in range(10):
            lo, hi = d / 10, (d + 1) / 10
            grp = [(p, o) for _, p, o in pairs
                   if lo <= p < hi or (d == 9 and p == 1.0)]
            if grp:
                deciles.append({"bucket": f"{lo:.1f}-{hi:.1f}", "n": len(grp),
                                "predicted_mean": round(sum(p for p, _ in grp) / len(grp), 3),
                                "observed": round(sum(o for _, o in grp) / len(grp), 3)})
        low = [(p, o) for _, p, o in pairs if p < 0.5]
        return {"n_pairs": m, "base_rate": round(br, 4),
                "brier": round(brier, 4),
                "brier_always_base_rate": round(brier_base, 4),
                "skill_vs_base_rate": round(1 - brier / brier_base, 4),
                "low_bucket_lt50": {"n": len(low),
                                    "predicted_mean": round(sum(p for p, _ in low) / len(low), 3) if low else None,
                                    "observed": round(sum(o for _, o in low) / len(low), 3) if low else None},
                "reliability_by_decile": deciles}

    part2 = calib(surv_pairs)
    part2["by_era"] = {
        "2013-2018": calib([x for x in surv_pairs if x[0] <= 2018]),
        "2019-2022": calib([x for x in surv_pairs if 2019 <= x[0] <= 2022]),
        "2023-2025": calib([x for x in surv_pairs if x[0] >= 2023]),
    }
    for era in part2["by_era"].values():
        era.pop("reliability_by_decile")
    part2["basis"] = ("frozen cond_survival verbatim (current committed sd "
                      "curve) applied to each year's FFC ADP, evaluated between "
                      "each consecutive pair of Anthony's actual picks against "
                      "observed availability")

    payload = {
        "generated": datetime.date.today().isoformat(),
        "design": "one-step deviation at actual board states; no counterfactual "
                  "opponents simulated; K/DEF excluded from value scoring",
        "not_replayable_stated": ["engine's live projection feed (no archive)",
                                  "walter layer (no historical guides)",
                                  "curated play-callers and depth charts"],
        "part1_value_core": part1,
        "part2_survival_calibration": part2,
        "coverage_by_year": coverage,
        "provenance": {"picks": "out/picks.csv", "adp": "FFC PPR 12-team by year",
                       "stats": "nflverse stats_player_week, league scoring",
                       "survival": "src/engine_2026.py frozen functions, read-only",
                       "seed": SEED, "bootstrap_draws": DRAWS},
    }
    json.dump(payload, open(OUT, "w"), indent=1)
    print(f"part1: {n} picks | actual {part1['mean_realized_pts']['actual']} vs "
          f"adp_best {part1['mean_realized_pts']['adp_best']} vs "
          f"replay_vor {part1['mean_realized_pts']['replay_vor']} pts/pick")
    for k, v in part1["deltas_per_pick"].items():
        print(f"  {k}: {v['mean']:+.2f} CI {v['ci95']}")
    print(f"part2: {part2['n_pairs']} pairs | Brier {part2['brier']:.4f} vs "
          f"base-rate {part2['brier_always_base_rate']:.4f} "
          f"(skill {part2['skill_vs_base_rate']:+.2%})")


if __name__ == "__main__":
    main()
