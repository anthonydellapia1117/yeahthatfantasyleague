#!/usr/bin/env python3
"""Item 3: does this league overpay for late-season (recent) performance?

THE QUESTION
Market ADP already embeds market-wide recency bias. The question here is
whether THIS league pays extra for a hot finish beyond what full-season
production and the market price explain. If it does, fading the bias is an
edge; if the effect is not distinguishable from zero, it is not used -
no effect size, no usage.

THE DESIGN
Unit: one league draft pick of a skill player (QB/RB/WR/TE) with at least
one prior-season game and a resolved FantasyFootballCalculator PPR ADP for
that draft year (12-team boards, the league's format). 13 drafts, 2013-2025.

    ln(overall_pick) = a + b_late * z(late4) + b_full * z(full)
                         + b_adp * ln(adp) + position dummies

  late4 = prior-season points over the LAST FOUR scheduled regular-season
          weeks (the recency window - anchored to season end, so 14-17 in
          17-week years and 15-18 in 18-week years)
  full  = prior-season full regular-season points
  Both scored with this league's rules (PPR + 6-pt pass TD = nflverse
  fantasy_points_ppr + 2 x passing_tds), z-scored within draft year.

b_late < 0 means a hotter finish buys an EARLIER league pick than market
price and full-season production justify - recency bias. The 95% interval
comes from a season-cluster bootstrap (draft years resampled with
replacement, 10,000 draws, seeded): picks within one draft are not
independent, draft years nearly are.

SCOPE LIMITS, STATED
Rookies are excluded (no prior season; a different market). Picks with no
FFC ADP row are excluded (no market control) - coverage is reported per
year. K/DEF are out of scope. FFC ADP is an early-September snapshot, the
closest available to the league's draft dates.

Reads out/picks.csv + the fetched history cache (HISTORY env var or the
default scratchpad path). Writes out/data/recency_bias.json.
"""
import csv
import datetime
import json
import math
import os
import random
import re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY = os.environ.get("HISTORY",
    "/tmp/claude-0/-home-user-yeahthatfantasyleague/"
    "3092ab3f-cbec-5ded-8daf-9676b9b6a046/scratchpad/history")
OUT = os.path.join(ROOT, "out", "data", "recency_bias.json")

SKILL = ("QB", "RB", "WR", "TE")
SEASONS = range(2013, 2026)
SEED = 20260819
DRAWS = 10000


def norm(s):
    s = re.sub(r"[.'’]", "", str(s).lower())
    s = re.sub(r"\s+(jr|sr|ii|iii|iv|v)$", "", s.strip())
    return re.sub(r"\s+", " ", s)


def prior_season(y):
    """Per-player league-scored full and last-4-weeks points for season y."""
    agg = {}
    weeks = set()
    with open(os.path.join(HISTORY, f"spw_{y}.csv")) as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        if r["season_type"] == "REG":
            weeks.add(int(r["week"]))
    late_from = max(weeks) - 3
    for r in rows:
        if r["season_type"] != "REG" or r["position_group"] not in SKILL:
            continue
        try:
            pts = float(r["fantasy_points_ppr"] or 0) + 2 * float(r["passing_tds"] or 0)
        except ValueError:
            continue
        a = agg.setdefault(r["player_id"], {"full": 0.0, "late": 0.0, "games": 0})
        a["full"] += pts
        a["games"] += 1
        if int(r["week"]) >= late_from:
            a["late"] += pts
    return agg, late_from


def zscore(vals):
    mu = sum(vals) / len(vals)
    sd = (sum((v - mu) ** 2 for v in vals) / len(vals)) ** 0.5
    return [(v - mu) / sd if sd > 1e-9 else 0.0 for v in vals]


def solve(A, b):
    """Gaussian elimination with partial pivoting. A is n x n, b length n."""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[piv] = M[piv], M[c]
        if abs(M[c][c]) < 1e-12:
            raise ValueError("singular design matrix")
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] for i in range(n)]


def ols(X, y):
    p = len(X[0])
    XtX = [[sum(X[i][a] * X[i][b] for i in range(len(X))) for b in range(p)]
           for a in range(p)]
    Xty = [sum(X[i][a] * y[i] for i in range(len(X))) for a in range(p)]
    return solve(XtX, Xty)


def main():
    picks = [r for r in csv.DictReader(open(os.path.join(ROOT, "out", "picks.csv")))
             if r["pos"] in SKILL and (r["player_id"] or "").startswith("00-")]

    sample = []           # dicts: season, overall, late, full, adp, pos
    coverage = {}
    for Y in SEASONS:
        prior, late_from = prior_season(Y - 1)
        ffc = {}
        for p in json.load(open(os.path.join(HISTORY, f"ffc_ppr_{Y}.json")))["players"]:
            if p["position"] in SKILL:
                ffc[(norm(p["name"]), p["position"])] = float(p["adp"])
        yr = [r for r in picks if int(r["season"]) == Y]
        rookies = no_adp = 0
        rows = []
        for r in yr:
            pr = prior.get(r["player_id"])
            if not pr or pr["games"] < 1:
                rookies += 1
                continue
            adp = ffc.get((norm(r["player_name"]), r["pos"]))
            if adp is None:
                no_adp += 1
                continue
            rows.append({"season": Y, "overall": int(r["overall"]),
                         "late": pr["late"], "full": pr["full"],
                         "adp": adp, "pos": r["pos"]})
        # z within draft year so scoring drift never masquerades as signal
        if rows:
            zl = zscore([x["late"] for x in rows])
            zf = zscore([x["full"] for x in rows])
            for x, a, b in zip(rows, zl, zf):
                x["z_late"], x["z_full"] = a, b
            sample.extend(rows)
        coverage[str(Y)] = {"picks": len(yr), "used": len(rows),
                            "rookies_excluded": rookies,
                            "no_ffc_adp": no_adp, "late_window_from_wk": late_from}

    def design(rows):
        X, y = [], []
        for x in rows:
            X.append([1.0, x["z_late"], x["z_full"], math.log(x["adp"]),
                      1.0 if x["pos"] == "RB" else 0.0,
                      1.0 if x["pos"] == "WR" else 0.0,
                      1.0 if x["pos"] == "TE" else 0.0])
            y.append(math.log(x["overall"]))
        return X, y

    X, y = design(sample)
    beta = ols(X, y)
    b_late = beta[1]

    rng = random.Random(SEED)
    seasons = sorted({x["season"] for x in sample})
    by = {s: [x for x in sample if x["season"] == s] for s in seasons}
    boots = []
    for _ in range(DRAWS):
        rows = []
        for _ in seasons:
            rows.extend(by[rng.choice(seasons)])
        try:
            Xb, yb = design(rows)
            boots.append(ols(Xb, yb)[1])
        except ValueError:
            continue
    boots.sort()
    ci = (boots[int(len(boots) * .025)], boots[int(len(boots) * .975)])
    distinguishable = ci[1] < 0 or ci[0] > 0

    # readability: picks moved at the median selection by +1 SD of late4
    med = sorted(x["overall"] for x in sample)[len(sample) // 2]
    picks_moved = med * (math.exp(b_late) - 1)

    payload = {
        "generated": datetime.date.today().isoformat(),
        "model": "ln(overall) ~ z(late4) + z(full) + ln(ffc_adp) + pos dummies",
        "n": len(sample), "seasons": [int(s) for s in seasons],
        "b_late": round(b_late, 5),
        "b_late_ci95_season_bootstrap": [round(ci[0], 5), round(ci[1], 5)],
        "b_full": round(beta[2], 5), "b_ln_adp": round(beta[3], 5),
        "distinguishable_from_zero": distinguishable,
        "direction": ("league_overpays_hot_finishes" if distinguishable and b_late < 0
                      else "league_underpays_hot_finishes" if distinguishable
                      else "none_established"),
        "picks_moved_at_median_selection_per_sd": round(picks_moved, 2),
        "usage_rule": ("USE only if distinguishable_from_zero is true - "
                       "no effect size, no usage (commission)"),
        "coverage_by_year": coverage,
        "scope_limits": ["rookies excluded (no prior season)",
                         "picks without an FFC ADP row excluded (no market control)",
                         "K/DEF out of scope",
                         "FFC ADP is an early-September 12-team PPR snapshot",
                         "late window anchored to each season's final 4 REG weeks"],
        "provenance": {"picks": "out/picks.csv (13 league drafts)",
                       "stats": "nflverse stats_player_week 2012-2024 (CC-BY-4.0), "
                                "league scoring = fantasy_points_ppr + 2 x passing_tds",
                       "adp": "FantasyFootballCalculator historical PPR ADP API, "
                              "12-team, by draft year",
                       "seed": SEED, "bootstrap_draws": DRAWS},
    }
    json.dump(payload, open(OUT, "w"), indent=1)
    used = sum(c["used"] for c in coverage.values())
    tot = sum(c["picks"] for c in coverage.values())
    print(f"sample {len(sample)} of {tot} skill picks ({used/tot:.0%} coverage)")
    print(f"b_late {b_late:+.5f}  CI95 [{ci[0]:+.5f}, {ci[1]:+.5f}]  "
          f"distinguishable={distinguishable}")
    print(f"at the median selection (pick {med}) +1 SD late-window moves the "
          f"league {picks_moved:+.2f} picks")


if __name__ == "__main__":
    main()
