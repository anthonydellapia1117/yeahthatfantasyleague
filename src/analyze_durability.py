#!/usr/bin/env python3
"""Item 4 follow-up: is the games-missed durability fade real, or a confound?

THE CANDIDATE (from out/data/injury_market.json, approved for
investigation 2026-08-19): players with more prior-season games missed
returned fewer realized points at the SAME market price -
b = -0.084 SD per SD, CI [-0.148, -0.025]. Before that number can mean
anything, it has to survive the obvious alternative explanations.

THE TESTS, PRE-REGISTERED
  base        the original spec, rerun on the shared frame:
                z(realized | yr x pos) ~ z(missed) + ln(adp) + z(full) + pos
  age         + z(age at Sept 1 of draft year) - older players miss more
              games AND decline; if age explains the fade, it is an age
              effect wearing an injury costume
  ppg         + z(prior points per game), zero-game returners carried at
              the year floor - full-season totals conflate talent and
              missed time; ppg separates them. If the fade dies here, it
              was talent mismeasurement, not durability
  full_ctrl   age and ppg together - the spec that has to hold
  returners   returner dummy (zero prior games) + z(missed | partial) -
              does the fade come from the season-long absentees, the
              partial missers, or both?
  eras        full_ctrl split 2013-2018 vs 2019-2025 - signs must agree
  positions   full_ctrl per position - reported, small n, not gating

THE VERDICT RULE (set before looking at the numbers)
  durability_fade_real  requires the full_ctrl interval to exclude zero
                        AND both era coefficients negative
  otherwise             confounded_or_unstable, with the failing test named

All intervals are season-cluster bootstrap (10,000 draws, seeded).
Age comes from nflverse rosters (2013-2025 union of birth dates);
players without a birth date are excluded from age-controlled specs only
and counted. Report-only: nothing here wires anywhere without approval.

Writes out/data/durability_fade.json.
"""
import csv
import datetime
import json
import math
import os
import random

import analyze_recency as base
import analyze_injury as inj

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "data", "durability_fade.json")
SEED = 20260819
DRAWS = 10000


def birth_dates():
    bd = {}
    for y in range(2013, 2026):
        path = os.path.join(base.HISTORY, f"roster_{y}.csv")
        if not os.path.exists(path):
            continue
        for r in csv.DictReader(open(path)):
            g, b = r.get("gsis_id"), r.get("birth_date")
            if g and b and len(b) >= 10 and g not in bd:
                bd[g] = b
    return bd


def main():
    sample, _ = inj.build_sample()
    bd = birth_dates()

    # age at Sept 1 of the draft year; ppg with returners at the year floor
    no_bd = 0
    for x in sample:
        b = bd.get(x["pid"])
        if b:
            x["age"] = (x["season"] - int(b[:4])
                        - (1 if (int(b[5:7]), int(b[8:10])) > (9, 1) else 0))
        else:
            x["age"] = None
            no_bd += 1
        x["ppg"] = x["full"] / x["prior_games"] if x["prior_games"] else 0.0
        x["returner"] = 1.0 if x["prior_games"] == 0 else 0.0
    for season in sorted({x["season"] for x in sample}):
        yr = [x for x in sample if x["season"] == season]
        zs = base.zscore([x["ppg"] for x in yr])
        for x, z in zip(yr, zs):
            x["z_ppg"] = z
        aged = [x for x in yr if x["age"] is not None]
        if aged:
            zs = base.zscore([x["age"] for x in aged])
            for x, z in zip(aged, zs):
                x["z_age"] = z
        part = [x for x in yr if not x["returner"]]
        if part:
            zs = base.zscore([x["games_missed"] for x in part])
            for x, z in zip(part, zs):
                x["z_missed_partial"] = z
        for x in yr:
            x.setdefault("z_missed_partial", 0.0)

    POSD = lambda x: [1.0 if x["pos"] == "RB" else 0.0,
                      1.0 if x["pos"] == "WR" else 0.0,
                      1.0 if x["pos"] == "TE" else 0.0]

    SPECS = {
        "base": (lambda x: x["z_age"] is not None or True,
                 lambda x: [1.0, x["z_games_missed"], math.log(x["adp"]),
                            x["z_full"]] + POSD(x), 1),
        "age": (lambda x: x["z_age"] is not None if x["age"] is not None else False,
                lambda x: [1.0, x["z_games_missed"], math.log(x["adp"]),
                           x["z_full"], x["z_age"]] + POSD(x), 1),
        "ppg": (lambda x: True,
                lambda x: [1.0, x["z_games_missed"], math.log(x["adp"]),
                           x["z_full"], x["z_ppg"]] + POSD(x), 1),
        "full_ctrl": (lambda x: x["age"] is not None,
                      lambda x: [1.0, x["z_games_missed"], math.log(x["adp"]),
                                 x["z_full"], x["z_age"], x["z_ppg"]] + POSD(x), 1),
        "returners": (lambda x: x["age"] is not None,
                      lambda x: [1.0, x["returner"], x["z_missed_partial"],
                                 math.log(x["adp"]), x["z_full"], x["z_age"],
                                 x["z_ppg"]] + POSD(x), (1, 2)),
    }

    rng = random.Random(SEED)
    seasons = sorted({x["season"] for x in sample})

    def fit(rows, design, coef_ix):
        X = [design(x) for x in rows]
        y = [x["z_out"] for x in rows]
        beta = base.ols(X, y)
        by = {s: [x for x in rows if x["season"] == s] for s in seasons}
        keys = [s for s in seasons if by[s]]
        idxs = coef_ix if isinstance(coef_ix, tuple) else (coef_ix,)
        boots = {i: [] for i in idxs}
        for _ in range(DRAWS):
            rs = []
            for _ in keys:
                rs.extend(by[rng.choice(keys)])
            try:
                bb = base.ols([design(x) for x in rs], [x["z_out"] for x in rs])
                for i in idxs:
                    boots[i].append(bb[i])
            except ValueError:
                continue
        out = {}
        for i in idxs:
            bs = sorted(boots[i])
            ci = [round(bs[int(len(bs) * .025)], 5), round(bs[int(len(bs) * .975)], 5)]
            out[i] = {"b": round(beta[i], 5), "ci95": ci,
                      "distinguishable": bool(ci[1] < 0 or ci[0] > 0)}
        return out, len(rows)

    results = {}
    for name, (keep, design, coef_ix) in SPECS.items():
        rows = [x for x in sample if keep(x)]
        est, n = fit(rows, design, coef_ix)
        if isinstance(coef_ix, tuple):
            results[name] = {"n": n,
                             "returner_dummy": est[coef_ix[0]],
                             "missed_partial": est[coef_ix[1]]}
        else:
            results[name] = dict(est[coef_ix], n=n)

    eras = {}
    keepf, designf, _ = SPECS["full_ctrl"]
    for label, lo, hi in (("2013-2018", 2013, 2018), ("2019-2025", 2019, 2025)):
        rows = [x for x in sample if keepf(x) and lo <= x["season"] <= hi]
        era_seasons = sorted({x["season"] for x in rows})
        X = [designf(x) for x in rows]
        beta = base.ols(X, [x["z_out"] for x in rows])
        by = {s: [x for x in rows if x["season"] == s] for s in era_seasons}
        boots = []
        for _ in range(DRAWS):
            rs = []
            for _ in era_seasons:
                rs.extend(by[rng.choice(era_seasons)])
            try:
                boots.append(base.ols([designf(x) for x in rs],
                                      [x["z_out"] for x in rs])[1])
            except ValueError:
                continue
        boots.sort()
        eras[label] = {"n": len(rows), "b": round(beta[1], 5),
                       "ci95": [round(boots[int(len(boots) * .025)], 5),
                                round(boots[int(len(boots) * .975)], 5)]}

    positions = {}
    for pos in ("QB", "RB", "WR", "TE"):
        rows = [x for x in sample if keepf(x) and x["pos"] == pos]
        if len(rows) < 60:
            positions[pos] = {"n": len(rows), "note": "too thin to estimate"}
            continue
        design_p = lambda x: [1.0, x["z_games_missed"], math.log(x["adp"]),
                              x["z_full"], x["z_age"], x["z_ppg"]]
        est, n = fit(rows, design_p, 1)
        positions[pos] = dict(est[1], n=n)

    fc = results["full_ctrl"]
    era_signs_agree = eras["2013-2018"]["b"] < 0 and eras["2019-2025"]["b"] < 0
    verdict = ("durability_fade_real"
               if fc["distinguishable"] and fc["b"] < 0 and era_signs_agree
               else "confounded_or_unstable")
    failing = []
    if not fc["distinguishable"]:
        failing.append("full_ctrl interval spans zero")
    if not era_signs_agree:
        failing.append("era signs disagree")

    payload = {
        "generated": datetime.date.today().isoformat(),
        "candidate": "games-missed durability fade from injury_market.json "
                     "(b=-0.084, CI [-0.148,-0.025], approved for investigation)",
        "specs": results,
        "eras_full_ctrl": eras,
        "positions_full_ctrl": positions,
        "players_without_birth_date": no_bd,
        "verdict": verdict,
        "verdict_basis": ("pre-registered: full_ctrl (age + ppg controls) must "
                          "exclude zero AND both era signs negative"
                          + ("" if not failing else " - FAILED: " + "; ".join(failing))),
        "recommendation": ("candidate for a gated decision (wire as CVS factor "
                           "or display-only flag - Anthony's call)"
                           if verdict == "durability_fade_real"
                           else "drop - the signal does not survive its controls"),
        "provenance": {"frame": "analyze_injury.build_sample() (shared, guarded)",
                       "ages": "nflverse rosters 2013-2025 birth dates",
                       "seed": SEED, "bootstrap_draws": DRAWS},
    }
    json.dump(payload, open(OUT, "w"), indent=1)
    for k, v in results.items():
        if k == "returners":
            print(f"{k:>10}: returner b={v['returner_dummy']['b']:+.4f} "
                  f"CI{v['returner_dummy']['ci95']} | partial-missed "
                  f"b={v['missed_partial']['b']:+.4f} CI{v['missed_partial']['ci95']} "
                  f"(n={v['n']})")
        else:
            print(f"{k:>10}: b={v['b']:+.4f} CI{v['ci95']} "
                  f"dist={v['distinguishable']} (n={v['n']})")
    for e, v in eras.items():
        print(f"{e:>10}: b={v['b']:+.4f} CI{v['ci95']} (n={v['n']})")
    print("verdict:", verdict)


if __name__ == "__main__":
    main()
