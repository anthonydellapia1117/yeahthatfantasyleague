#!/usr/bin/env python3
"""Item 2 backtest: do per-franchise positional profiles beat league priors?

THE QUESTION
The simulator samples each opponent seat's positional choice from its shrunk
franchise tendency (lift x league band base rate). That is only defensible if
the franchise-specific component actually predicts held-out picks better than
the league-wide band rates alone. This script answers that question and
nothing else - it changes no rank, no verdict, no UI.

THE DESIGN (walk-forward, never any future data)
For each evaluation season S (2016-2025, so every train window holds >= 3
drafts), train BOTH models on seasons strictly before S using the exact
committed methodology from src/phase3i_tendencies.py - recency half-life 6
anchored at S-1, empirical-Bayes shrinkage k by method of moments per
band x position - then score every pick of season S:

  baseline  P(pos | band)              league band shares, train window only
  profile   P(pos | franchise, band)   shrunk franchise shares, train window

Coverage rule (the spec): a franchise with fewer than 2 drafts in the train
window falls back to the baseline and is counted as low-confidence.

METRICS
Mean log-loss (natural log; lower is better) and top-1 hit rate, per model,
paired per pick. The headline delta carries a season-cluster bootstrap 95%
interval (evaluation seasons resampled with replacement, 10,000 draws,
seeded) - picks within a draft are not independent, seasons nearly are.

Writes out/data/manager_profiles_backtest.json. Beat-or-report: if the
profile model does not beat the baseline, that is the finding.
"""
import csv
import datetime
import json
import math
import os
import random
import statistics
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PICKS = os.path.join(ROOT, "out", "picks.csv")
OUT = os.path.join(ROOT, "out", "data", "manager_profiles_backtest.json")

POS = ("QB", "RB", "WR", "TE", "K", "DEF")
BANDS = [(1, 3, "rd1-3"), (4, 6, "rd4-6"), (7, 10, "rd7-10"), (11, 14, "rd11-14")]
HALF_LIFE = 6.0
SEED = 20260819
EVAL_START = 2016
FLOOR = 1e-4          # probability floor so a never-seen position never scores -inf


def band_of(rnd):
    for lo, hi, name in BANDS:
        if lo <= rnd <= hi:
            return name
    return BANDS[-1][2]


def shrinkage_k(obs, league_p):
    """Method-of-moments pseudo-count, verbatim logic from phase3i_tendencies."""
    pts = [(n, x / n) for n, x in obs if n >= 5]
    if len(pts) < 3 or not (0 < league_p < 1):
        return 50.0
    n_bar = statistics.mean(n for n, _ in pts)
    total_var = statistics.pvariance([p for _, p in pts])
    within = league_p * (1 - league_p) / n_bar
    between = total_var - within
    if between <= 1e-9:
        return 200.0
    return max(1.0, min(200.0, league_p * (1 - league_p) / between))


def train(rows, upto_season):
    """League band shares + shrunk franchise shares from seasons < upto_season,
    recency-weighted with the committed half-life anchored at upto_season-1."""
    def w(season):
        return 0.5 ** ((upto_season - 1 - int(season)) / HALF_LIFE)
    lg = defaultdict(float)      # (band, pos) -> weighted count
    lg_tot = defaultdict(float)  # band -> weighted count
    fr = defaultdict(float)      # (franchise, band, pos) -> weighted count
    fr_tot = defaultdict(float)  # (franchise, band) -> weighted count
    raw = defaultdict(int)       # (franchise, band) -> raw pick count (for k)
    drafts = defaultdict(set)    # franchise -> seasons seen
    for r in rows:
        s = int(r["season"])
        if s >= upto_season or r["pos"] not in POS:
            continue
        b = band_of(int(r["round"]))
        wt = w(s)
        f = r["member_name"]
        lg[(b, r["pos"])] += wt
        lg_tot[b] += wt
        fr[(f, b, r["pos"])] += wt
        fr_tot[(f, b)] += wt
        raw[(f, b)] += 1
        drafts[f].add(s)
    league = {}
    for _, _, b in BANDS:
        for p in POS:
            league[(b, p)] = lg[(b, p)] / lg_tot[b] if lg_tot[b] else 1 / len(POS)
    ks = {}
    franchises = sorted({f for f, _, _ in fr})
    for _, _, b in BANDS:
        for p in POS:
            obs = [(raw[(f, b)], fr[(f, b, p)] / fr_tot[(f, b)] * raw[(f, b)])
                   for f in franchises if raw[(f, b)]]
            ks[(b, p)] = shrinkage_k(obs, league[(b, p)])
    return league, fr, fr_tot, raw, ks, drafts


def predict(model, f, b):
    """Return (probs dict, used_profile flag) for a franchise x band."""
    league, fr, fr_tot, raw, ks, drafts = model
    base = {p: league[(b, p)] for p in POS}
    if len(drafts.get(f, ())) < 2 or not fr_tot.get((f, b)):
        return base, False
    n = raw[(f, b)]
    probs = {}
    for p in POS:
        q_obs = fr[(f, b, p)] / fr_tot[(f, b)]
        k = ks[(b, p)]
        probs[p] = (n * q_obs + k * base[p]) / (n + k)
    tot = sum(probs.values())
    return {p: v / tot for p, v in probs.items()}, True


def main():
    rows = [r for r in csv.DictReader(open(PICKS)) if r["pos"] in POS]
    seasons = sorted({int(r["season"]) for r in rows})
    eval_seasons = [s for s in seasons if s >= EVAL_START]

    per_pick = []      # (season, band, ll_base, ll_prof, hit_base, hit_prof, used)
    for S in eval_seasons:
        model = train(rows, S)
        for r in rows:
            if int(r["season"]) != S:
                continue
            b = band_of(int(r["round"]))
            base, _ = predict(model, "\x00nobody", b)     # forces league fallback
            prof, used = predict(model, r["member_name"], b)
            y = r["pos"]
            per_pick.append({
                "season": S, "band": b, "used_profile": used,
                "ll_base": -math.log(max(base[y], FLOOR)),
                "ll_prof": -math.log(max(prof[y], FLOOR)),
                "hit_base": int(max(base, key=base.get) == y),
                "hit_prof": int(max(prof, key=prof.get) == y),
            })

    n = len(per_pick)
    mean = lambda k: sum(p[k] for p in per_pick) / n
    ll_b, ll_p = mean("ll_base"), mean("ll_prof")
    hit_b, hit_p = mean("hit_base"), mean("hit_prof")

    # season-cluster bootstrap on the log-loss delta (baseline - profile;
    # positive = profiles better)
    rng = random.Random(SEED)
    by_season = defaultdict(list)
    for p in per_pick:
        by_season[p["season"]].append(p["ll_base"] - p["ll_prof"])
    keys = sorted(by_season)
    deltas = []
    for _ in range(10000):
        sample = [by_season[rng.choice(keys)] for _ in keys]
        flat = [x for grp in sample for x in grp]
        deltas.append(sum(flat) / len(flat))
    deltas.sort()
    ci = (deltas[249], deltas[9749])
    delta = ll_b - ll_p

    by_band = {}
    for _, _, b in BANDS:
        grp = [p for p in per_pick if p["band"] == b]
        if grp:
            by_band[b] = {
                "n": len(grp),
                "logloss_delta": round(sum(p["ll_base"] - p["ll_prof"] for p in grp) / len(grp), 4),
                "hit_base": round(sum(p["hit_base"] for p in grp) / len(grp), 4),
                "hit_prof": round(sum(p["hit_prof"] for p in grp) / len(grp), 4),
            }
    by_season_out = {}
    for s in eval_seasons:
        grp = [p for p in per_pick if p["season"] == s]
        by_season_out[str(s)] = {
            "n": len(grp),
            "logloss_delta": round(sum(p["ll_base"] - p["ll_prof"] for p in grp) / len(grp), 4),
        }

    verdict = ("profiles_beat_priors" if ci[0] > 0 else
               "priors_beat_profiles" if ci[1] < 0 else
               "not_distinguishable")
    payload = {
        "generated": datetime.date.today().isoformat(),
        "design": ("walk-forward: for each season S in "
                   f"{eval_seasons[0]}-{eval_seasons[-1]}, both models train on "
                   "seasons < S only (recency half-life 6 anchored at S-1, "
                   "method-of-moments shrinkage per band x position, verbatim "
                   "phase3i methodology); <2 prior drafts falls back to league "
                   "priors and counts as low-confidence"),
        "n_picks_scored": n,
        "pct_low_confidence_fallback": round(
            sum(1 for p in per_pick if not p["used_profile"]) / n, 4),
        "logloss": {"league_baseline": round(ll_b, 4), "profiles": round(ll_p, 4),
                    "delta": round(delta, 4),
                    "delta_ci95_season_bootstrap": [round(ci[0], 4), round(ci[1], 4)],
                    "note": "delta = baseline - profiles; positive means the "
                            "franchise component adds real predictive information"},
        "hit_rate_top1": {"league_baseline": round(hit_b, 4),
                          "profiles": round(hit_p, 4),
                          "note": "top-1 is a blunt metric here - both models "
                                  "usually name the modal position (RB/WR); "
                                  "log-loss is the honest headline"},
        "by_band": by_band,
        "by_season": by_season_out,
        "verdict": verdict,
        "provenance": {"source": "out/picks.csv (13 league drafts) via the "
                                 "committed phase3i methodology",
                       "seed": SEED, "bootstrap_draws": 10000},
    }
    json.dump(payload, open(OUT, "w"), indent=1)
    print(f"scored {n} picks over {len(eval_seasons)} walk-forward seasons")
    print(f"log-loss  baseline {ll_b:.4f}  profiles {ll_p:.4f}  "
          f"delta {delta:+.4f}  CI95 [{ci[0]:+.4f}, {ci[1]:+.4f}]")
    print(f"hit rate  baseline {hit_b:.4f}  profiles {hit_p:.4f}")
    print(f"verdict: {verdict}")


if __name__ == "__main__":
    main()
