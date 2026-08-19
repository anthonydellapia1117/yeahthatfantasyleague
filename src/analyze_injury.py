#!/usr/bin/env python3
"""Item 4: does this league mis-price injury history, relative to outcomes?

TWO QUESTIONS, TWO REGRESSIONS (same sample frame as item 3, plus the
returning-from-injury veterans that frame excluded)

  A. THE LEAGUE'S RESPONSE - does the league discount injury-history
     players beyond the market price?
       ln(pick paid) - ln(FFC ADP) ~ z(burden) + z(full) + pos dummies
     b > 0: the league lets injury-history players fall further than the
     market does. b < 0: the league pays up for them.

  B. THE OUTCOME JUSTIFICATION - does injury history predict the realized
     draft-year season beyond what the price already says?
       z(realized total pts | year x pos) ~ z(burden) + ln(ADP)
                                            + z(full) + pos dummies
     b < 0: injured players really do return less at the same price -
     discounting is justified. b ~ 0: it is not.

  Inefficiency = a gap between A and B: a league discount that outcomes
  do not justify (injured players are value), or no discount where
  outcomes demand one (injury history is a fade).

TWO BURDEN MEASURES, REPORTED SIDE BY SIDE
  inj_desig    weeks of the prior season carrying a game-report status of
               Out or Doubtful (the nflverse designation instrument)
  games_missed scheduled REG weeks minus games played - catches the
               season-long IR players who never appear on weekly reports
Conclusions require the two to agree in direction; disagreement is
reported as such.

SAMPLE
Skill picks with an FFC ADP row. A veteran who missed the ENTIRE prior
season (zero games) stays IN with full = late = 0 and maximal burden -
those are exactly the most injury-discounted players and item 3's
prior-season-exists restriction dropped them. Rookies (no NFL trace in
the prior three seasons and no designations) stay out. K/DEF out of
scope. Realized outcome = draft-year total points under league scoring,
z within year x position, so missed time IS the outcome risk being
priced. 2025 realized outcomes use the completed 2025 season.

Writes out/data/injury_market.json.
"""
import csv
import datetime
import json
import math
import os
import random
from collections import defaultdict

import analyze_recency as base

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "data", "injury_market.json")
SKILL = ("QB", "RB", "WR", "TE")
SEASONS = range(2013, 2026)
SEED = 20260819
DRAWS = 10000


def season_totals(y):
    """Per-player league-scored REG totals + games for season y, and the
    number of scheduled REG weeks."""
    agg = {}
    weeks = set()
    with open(os.path.join(base.HISTORY, f"spw_{y}.csv")) as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        if r["season_type"] != "REG":
            continue
        weeks.add(int(r["week"]))
        if r["position_group"] not in SKILL:
            continue
        try:
            pts = float(r["fantasy_points_ppr"] or 0) + 2 * float(r["passing_tds"] or 0)
        except ValueError:
            continue
        a = agg.setdefault(r["player_id"], {"pts": 0.0, "games": 0})
        a["pts"] += pts
        a["games"] += 1
    return agg, len(weeks)


def designations(y):
    """Per-player count of REG weeks with report_status Out or Doubtful."""
    d = defaultdict(int)
    path = os.path.join(base.HISTORY, f"inj_{y}.csv")
    for r in csv.DictReader(open(path)):
        if r.get("game_type", "REG") not in ("", "REG"):
            continue
        if r["report_status"] in ("Out", "Doubtful") and r["gsis_id"]:
            d[r["gsis_id"]] += 1
    return dict(d)


def build_sample():
    """The shared sample frame: ADP-matched veteran skill picks with burden,
    prior production, and realized outcome. Used here and by the durability
    follow-up (analyze_durability.py). Rows carry pid and prior_games for
    downstream controls; the emitted payload does not change."""
    picks = [r for r in csv.DictReader(open(os.path.join(ROOT, "out", "picks.csv")))
             if r["pos"] in SKILL and (r["player_id"] or "").startswith("00-")]

    totals = {}   # season -> (agg, n_weeks)
    for y in range(2010, 2026):
        if os.path.exists(os.path.join(base.HISTORY, f"spw_{y}.csv")):
            totals[y] = season_totals(y)

    sample = []
    coverage = {}
    for Y in SEASONS:
        prior, n_weeks = totals[Y - 1]
        realized, _ = totals[Y]
        desig = designations(Y - 1)
        ffc = {}
        for p in json.load(open(os.path.join(base.HISTORY, f"ffc_ppr_{Y}.json")))["players"]:
            if p["position"] in SKILL:
                ffc[(base.norm(p["name"]), p["position"])] = float(p["adp"])
        yr = [r for r in picks if int(r["season"]) == Y]
        rookies = no_adp = 0
        rows = []
        for r in yr:
            adp = ffc.get((base.norm(r["player_name"]), r["pos"]))
            if adp is None:
                no_adp += 1
                continue
            pid = r["player_id"]
            pr = prior.get(pid)
            # veteran test: any NFL trace in Y-3..Y-1 or a Y-1 designation
            vet = bool(pr) or pid in desig or any(
                pid in totals[y][0] for y in (Y - 2, Y - 3) if y in totals)
            if not vet:
                rookies += 1
                continue
            full = pr["pts"] if pr else 0.0
            games = pr["games"] if pr else 0
            rl = realized.get(pid)
            rows.append({"season": Y, "pos": r["pos"], "pid": pid,
                         "overall": int(r["overall"]), "adp": adp,
                         "full": full, "prior_games": games,
                         "n_weeks": n_weeks,
                         "inj_desig": desig.get(pid, 0),
                         "games_missed": max(0, n_weeks - games),
                         "realized": rl["pts"] if rl else 0.0})
        # z within year (burden, full) and within year x position (outcome)
        if rows:
            for key in ("inj_desig", "games_missed", "full"):
                zs = base.zscore([x[key] for x in rows])
                for x, z in zip(rows, zs):
                    x["z_" + key] = z
            for pos in SKILL:
                grp = [x for x in rows if x["pos"] == pos]
                if grp:
                    zs = base.zscore([x["realized"] for x in grp])
                    for x, z in zip(grp, zs):
                        x["z_out"] = z
            sample.extend(rows)
        coverage[str(Y)] = {"picks": len(yr), "used": len(rows),
                            "rookies_excluded": rookies, "no_ffc_adp": no_adp,
                            "zero_game_veterans_kept":
                                sum(1 for x in rows if x["games_missed"] >= n_weeks)}
    return sample, coverage


def main():
    sample, coverage = build_sample()

    def run(burden_key):
        def dA(rows):
            X = [[1.0, x["z_" + burden_key], x["z_full"],
                  1.0 if x["pos"] == "RB" else 0.0,
                  1.0 if x["pos"] == "WR" else 0.0,
                  1.0 if x["pos"] == "TE" else 0.0] for x in rows]
            y = [math.log(x["overall"]) - math.log(x["adp"]) for x in rows]
            return X, y

        def dB(rows):
            X = [[1.0, x["z_" + burden_key], math.log(x["adp"]), x["z_full"],
                  1.0 if x["pos"] == "RB" else 0.0,
                  1.0 if x["pos"] == "WR" else 0.0,
                  1.0 if x["pos"] == "TE" else 0.0] for x in rows]
            y = [x["z_out"] for x in rows]
            return X, y

        res = {}
        rng = random.Random(SEED)
        seasons = sorted({x["season"] for x in sample})
        by = {s: [x for x in sample if x["season"] == s] for s in seasons}
        for name, dfn in (("league_response", dA), ("outcome_justification", dB)):
            X, y = dfn(sample)
            b = base.ols(X, y)[1]
            boots = []
            for _ in range(DRAWS):
                rows = []
                for _ in seasons:
                    rows.extend(by[rng.choice(seasons)])
                try:
                    Xb, yb = dfn(rows)
                    boots.append(base.ols(Xb, yb)[1])
                except ValueError:
                    continue
            boots.sort()
            ci = (boots[int(len(boots) * .025)], boots[int(len(boots) * .975)])
            res[name] = {"b": round(b, 5),
                         "ci95": [round(ci[0], 5), round(ci[1], 5)],
                         "distinguishable": bool(ci[1] < 0 or ci[0] > 0)}
        return res

    results = {"inj_desig": run("inj_desig"), "games_missed": run("games_missed")}

    def direction(r):
        A, B = r["league_response"], r["outcome_justification"]
        a = "fades" if A["distinguishable"] and A["b"] > 0 else \
            "pays_up" if A["distinguishable"] else "follows_market"
        b = "justified" if B["distinguishable"] and B["b"] < 0 else \
            "outperform_at_price" if B["distinguishable"] else "no_outcome_signal"
        return a, b

    d1, d2 = direction(results["inj_desig"]), direction(results["games_missed"])
    agree = d1 == d2
    verdict = ("no_inefficiency_established" if not agree
               or (d1[0] == "follows_market" and d1[1] == "no_outcome_signal")
               else f"league_{d1[0]}__outcomes_{d1[1]}")

    payload = {
        "generated": datetime.date.today().isoformat(),
        "n": len(sample),
        "models": {
            "A_league_response": "ln(pick) - ln(adp) ~ z(burden) + z(full) + pos",
            "B_outcome_justification": "z(realized | yr x pos) ~ z(burden) + "
                                       "ln(adp) + z(full) + pos"},
        "results": results,
        "burden_measures_agree": agree,
        "verdict": verdict,
        "usage_rule": "USE nothing unless both burden measures agree and the "
                      "relevant interval excludes zero",
        "coverage_by_year": coverage,
        "scope_limits": [
            "designation reporting is sparser and less standardized pre-2016",
            "season-long IR players carry zero designations - the games_missed "
            "measure exists exactly for them",
            "rookies excluded (no injury history to price)",
            "picks without an FFC ADP row excluded (no market benchmark)",
            "realized outcome is total season points - missed time counts "
            "against the player, which is the risk being priced"],
        "provenance": {"injuries": "nflverse injuries 2012-2024 (CC-BY-4.0)",
                       "stats": "nflverse stats_player_week, league scoring",
                       "adp": "FantasyFootballCalculator PPR 12-team by year",
                       "picks": "out/picks.csv", "seed": SEED,
                       "bootstrap_draws": DRAWS},
    }
    json.dump(payload, open(OUT, "w"), indent=1)
    print(f"sample {len(sample)}")
    for k, r in results.items():
        A, B = r["league_response"], r["outcome_justification"]
        print(f"{k:>13}: A(league) b={A['b']:+.4f} CI{A['ci95']} "
              f"dist={A['distinguishable']} | B(outcome) b={B['b']:+.4f} "
              f"CI{B['ci95']} dist={B['distinguishable']}")
    print("verdict:", verdict)


if __name__ == "__main__":
    main()
