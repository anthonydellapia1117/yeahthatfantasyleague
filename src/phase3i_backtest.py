#!/usr/bin/env python3
"""Does opponent conditioning actually beat the opponent-agnostic model?

This is the gate. A model that is theoretically nicer but empirically worse does not
ship. Walk-forward backtest on this league's own drafts:

  For each season S from 2016 on, build the tendency table from seasons BEFORE S
  only, then predict, for every real pick in S, whether each still-available player
  survives to that team's next pick. Score both models against what actually
  happened.

Strictly out-of-sample: the tendency table for 2020 never sees a 2020-2025 pick.
That is what makes the comparison honest rather than a restatement of the fit.

Metrics: Brier score (mean squared error on the 0/1 outcome, lower is better) and
log loss. Reported with a paired permutation test over seasons, because 10 seasons
of paired differences is a small sample and the direction alone proves nothing.

Run: python3 src/phase3i_backtest.py
"""
import csv
import json
import math
import os
import random
import statistics
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PICKS = os.path.join(ROOT, "out", "picks.csv")
OUT = os.path.join(ROOT, "out", "tendency_backtest.json")

POS = ("QB", "RB", "WR", "TE", "K", "DEF")
BANDS = [(1, 3, "rd1-3"), (4, 6, "rd4-6"), (7, 10, "rd7-10"), (11, 14, "rd11-14")]
ADP_SD = [(24, 5.46), (60, 13.63), (120, 24.01), (10 ** 9, 23.81)]
HALF_LIFE = 6.0
SEED = 20260812
TEAMS = 12
EPS = 1e-6


def band_of(rnd):
    for lo, hi, name in BANDS:
        if lo <= rnd <= hi:
            return name
    return BANDS[-1][2]


def sd_for(adp):
    for hi, sd in ADP_SD:
        if adp <= hi:
            return sd
    return ADP_SD[-1][1]


def survival(adp, pick):
    if adp >= 900:
        return 1.0
    z = (pick - adp) / (sd_for(adp) * math.sqrt(2))
    return max(0.0, min(1.0, 0.5 * (1 - math.erf(z))))


def cond_survival(adp, to_pick, from_pick):
    """P(survives to to_pick | still available at from_pick)."""
    s_from = survival(adp, from_pick)
    if s_from <= EPS:
        return 0.0
    return max(0.0, min(1.0, survival(adp, to_pick) / s_from))


def build_lift(rows, before_season):
    """Tendency lift from seasons strictly before `before_season`. Never leaks."""
    latest = before_season - 1
    fr, fr_tot = defaultdict(float), defaultdict(float)
    lg, lg_tot = defaultdict(float), defaultdict(float)
    raw_n = defaultdict(int)
    for r in rows:
        s = int(r["season"])
        if s >= before_season or r["pos"] not in POS:
            continue
        b = band_of(int(r["round"]))
        w = 0.5 ** ((latest - s) / HALF_LIFE)
        f = r["member_name"]
        fr[(f, b, r["pos"])] += w
        fr_tot[(f, b)] += w
        lg[(b, r["pos"])] += w
        lg_tot[b] += w
        raw_n[(f, b)] += 1

    franchises = {f for f, _ in fr_tot}
    lift = {}
    for _, _, b in BANDS:
        if not lg_tot[b]:
            continue
        for p in POS:
            league_p = lg[(b, p)] / lg_tot[b]
            pts = [(raw_n[(f, b)], fr[(f, b, p)] / max(fr_tot[(f, b)], 1e-9))
                   for f in franchises if raw_n[(f, b)] >= 5]
            k = 50.0
            if len(pts) >= 3 and 0 < league_p < 1:
                n_bar = statistics.mean(n for n, _ in pts)
                between = statistics.pvariance([q for _, q in pts]) - \
                    league_p * (1 - league_p) / n_bar
                k = 200.0 if between <= 1e-9 else \
                    max(1.0, min(200.0, league_p * (1 - league_p) / between))
            for f in franchises:
                n = raw_n[(f, b)]
                if not n:
                    continue
                q_obs = fr[(f, b, p)] / fr_tot[(f, b)]
                q = (n * q_obs + k * league_p) / (n + k)
                lift[(f, b, p)] = q / league_p if league_p > 1e-6 else 1.0
    return lift


def main():
    random.seed(SEED)
    rows = [r for r in csv.DictReader(open(PICKS))]
    seasons = sorted({int(r["season"]) for r in rows})

    per_season = []
    for season in [s for s in seasons if s >= 2016]:
        lift = build_lift(rows, season)
        sp = sorted([r for r in rows if int(r["season"]) == season],
                    key=lambda r: int(r["overall"]))
        if not sp:
            continue
        # who owns each overall pick, and each team's ordered pick list
        owner = {int(r["overall"]): r["member_name"] for r in sp}
        team_picks = defaultdict(list)
        for r in sp:
            team_picks[r["member_name"]].append(int(r["overall"]))
        taken_at = {}
        for r in sp:
            if r["player_name"]:
                taken_at.setdefault(r["player_name"], int(r["overall"]))

        # ADP proxy: this league's own realised pick for that player-season.
        # Using realised overall as ADP would be circular, so use the LEAGUE-WIDE
        # mean pick of that player across OTHER seasons where available; fall back
        # to skipping. Players drafted in only one season carry no usable prior.
        by_player = defaultdict(list)
        for r in rows:
            if r["player_name"] and int(r["season"]) != season:
                by_player[r["player_name"]].append(int(r["overall"]))
        adp = {p: statistics.mean(v) for p, v in by_player.items() if len(v) >= 2}

        base_b, adj_b, base_l, adj_l, n = 0.0, 0.0, 0.0, 0.0, 0
        for r in sp:
            cur = int(r["overall"])
            me = r["member_name"]
            later = [p for p in team_picks[me] if p > cur]
            if not later:
                continue
            nxt = later[0]
            gap = [p for p in range(cur + 1, nxt)]
            if not gap:
                continue
            # candidates: players with a usable prior, still on the board at cur
            for name, a in adp.items():
                if abs(a - cur) > 40:
                    continue
                t = taken_at.get(name)
                if t is not None and t <= cur:
                    continue                      # already gone
                pos = next((x["pos"] for x in sp if x["player_name"] == name), None)
                if pos not in POS:
                    continue
                actual = 1 if (t is None or t >= nxt) else 0
                s_base = cond_survival(a, nxt, cur)
                lifts = [lift.get((owner.get(g, ""), band_of((g - 1) // TEAMS + 1), pos), 1.0)
                         for g in gap]
                lbar = statistics.mean(lifts) if lifts else 1.0
                sb = min(1 - 1e-9, max(EPS, s_base))
                s_adj = math.exp(-(-math.log(sb)) * lbar)
                base_b += (s_base - actual) ** 2
                adj_b += (s_adj - actual) ** 2
                base_l += -math.log(max(EPS, s_base if actual else 1 - s_base))
                adj_l += -math.log(max(EPS, s_adj if actual else 1 - s_adj))
                n += 1
        if n:
            per_season.append({"season": season, "n": n,
                               "brier_base": base_b / n, "brier_adj": adj_b / n,
                               "logloss_base": base_l / n, "logloss_adj": adj_l / n})

    if not per_season:
        print("no evaluable seasons")
        return

    d = [s["brier_base"] - s["brier_adj"] for s in per_season]   # >0 means adj better
    obs = statistics.mean(d)
    n_shuf, hits = 50000, 0
    for _ in range(n_shuf):
        flipped = [x if random.random() < 0.5 else -x for x in d]
        if statistics.mean(flipped) >= obs:
            hits += 1
    p = hits / n_shuf

    tot = sum(s["n"] for s in per_season)
    bb = sum(s["brier_base"] * s["n"] for s in per_season) / tot
    ba = sum(s["brier_adj"] * s["n"] for s in per_season) / tot
    lb = sum(s["logloss_base"] * s["n"] for s in per_season) / tot
    la = sum(s["logloss_adj"] * s["n"] for s in per_season) / tot

    better = sum(1 for s in per_season if s["brier_adj"] < s["brier_base"])
    ships = p < 0.05 and ba < bb

    print(f"walk-forward backtest, {len(per_season)} seasons, {tot:,} predictions\n")
    print(f"{'season':<8}{'n':>7}{'Brier base':>12}{'Brier adj':>12}{'delta':>10}")
    for s in per_season:
        dd = s["brier_base"] - s["brier_adj"]
        print(f"{s['season']:<8}{s['n']:>7}{s['brier_base']:>12.5f}"
              f"{s['brier_adj']:>12.5f}{dd:>+10.5f}")
    print(f"\n{'POOLED':<8}{tot:>7}{bb:>12.5f}{ba:>12.5f}{bb-ba:>+10.5f}")
    print(f"log loss   base {lb:.5f}   adjusted {la:.5f}   delta {lb-la:+.5f}")
    print(f"\nseasons improved: {better}/{len(per_season)}")
    print(f"paired permutation p = {p:.4f} ({n_shuf:,} sign flips, seed {SEED})")
    print(f"\nVERDICT: {'SHIP - conditioning beats the agnostic model' if ships else 'DO NOT SHIP - no reliable improvement'}")

    with open(OUT, "w") as fh:
        json.dump({"per_season": per_season, "pooled_brier_base": bb,
                   "pooled_brier_adj": ba, "pooled_logloss_base": lb,
                   "pooled_logloss_adj": la, "seasons_improved": better,
                   "seasons": len(per_season), "n_predictions": tot,
                   "p_value": p, "shuffles": n_shuf, "seed": SEED,
                   "ship": ships}, fh, indent=1)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
