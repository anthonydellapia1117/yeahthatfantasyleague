#!/usr/bin/env python3
"""Per-franchise positional draft tendency, for opponent-conditional survival.

WHY THIS EXISTS
The survival model in engine_2026.py is opponent-agnostic: it knows a player's ADP
and the pick number, nothing about WHO picks in between. But the seats ahead of you
are not interchangeable. RB share in rounds 1-3 runs from 0.31 to 0.62 across
franchises against a 0.45 league mean.

THE LICENCE TO USE IT
Tendencies have to PERSIST or conditioning on them is fitting noise. Tested by
splitting 2013-2019 against 2020-2025 and correlating each franchise's positional
share across the two eras: r = +0.813, permutation p < 0.00002 (50,000 shuffles,
seed 20260812), n = 168 franchise x band x position pairs. They persist.

THE TRAP THIS FILE AVOIDS
ADP already encodes average drafting behaviour - ADP IS the aggregate of how teams
draft. Multiplying ADP-based survival by each opponent's positional probability
double counts. What this table emits is therefore a LIFT, q_franchise / q_league,
centred on 1.0. A perfectly average seat contributes exactly 1.0 and changes
nothing. The consumer redistributes hazard by the lift; it never adds hazard.

Writes out/positional_tendency.csv.
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
OUT = os.path.join(ROOT, "out", "positional_tendency.csv")
TEST_OUT = os.path.join(ROOT, "out", "tendency_persistence.json")

POS = ("QB", "RB", "WR", "TE", "K", "DEF")
BANDS = [(1, 3, "rd1-3"), (4, 6, "rd4-6"), (7, 10, "rd7-10"), (11, 14, "rd11-14")]
HALF_LIFE = 6.0          # seasons; a 2020 pick counts half as much as a 2026 one
LATEST = 2025
SEED = 20260812


def band_of(rnd):
    for lo, hi, name in BANDS:
        if lo <= rnd <= hi:
            return name
    return BANDS[-1][2]


def weight(season):
    """Recency weight. Half-life in seasons, so old eras fade rather than vanish."""
    return 0.5 ** ((LATEST - int(season)) / HALF_LIFE)


def load():
    return list(csv.DictReader(open(PICKS)))


def shrinkage_k(obs, league_p):
    """Empirical-Bayes prior weight by method of moments.

    Returns the pseudo-count k such that q = (n*q_obs + k*q_league) / (n + k).
    Large k means the franchise signal is weak relative to sampling noise and the
    estimate collapses toward the league mean, which is the safe failure.
    """
    pts = [(n, x / n) for n, x in obs if n >= 5]
    if len(pts) < 3 or not (0 < league_p < 1):
        return 50.0
    n_bar = statistics.mean(n for n, _ in pts)
    total_var = statistics.pvariance([p for _, p in pts])
    within = league_p * (1 - league_p) / n_bar      # expected sampling variance
    between = total_var - within
    if between <= 1e-9:
        return 200.0                                 # no real signal; shrink hard
    return max(1.0, min(200.0, league_p * (1 - league_p) / between))


def persistence_test(rows):
    """Do tendencies persist across eras? The licence for this whole feature."""
    random.seed(SEED)

    def shares(lo, hi):
        d = defaultdict(lambda: [0, 0])
        for r in rows:
            s = int(r["season"])
            if not (lo <= s <= hi):
                continue
            key_band = band_of(int(r["round"]))
            for p in POS[:4]:                        # skill positions only
                d[(r["member_name"], key_band, p)][1] += 1
                if r["pos"] == p:
                    d[(r["member_name"], key_band, p)][0] += 1
        return d

    early, late = shares(2013, 2019), shares(2020, 2025)
    pairs = [(a[0] / a[1], late[k][0] / late[k][1])
             for k, a in early.items()
             if k in late and a[1] >= 8 and late[k][1] >= 8]

    def corr(xy):
        xs = [p[0] for p in xy]
        ys = [p[1] for p in xy]
        mx, my = statistics.mean(xs), statistics.mean(ys)
        num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
        return num / den if den else 0.0

    obs = corr(pairs)
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    n_shuf, hits = 50000, 0
    for _ in range(n_shuf):
        sh = ys[:]
        random.shuffle(sh)
        if corr(list(zip(xs, sh))) >= obs:
            hits += 1
    return {"r": round(obs, 4), "p_value": hits / n_shuf, "n_pairs": len(pairs),
            "shuffles": n_shuf, "seed": SEED, "eras": "2013-2019 vs 2020-2025",
            "verdict": "persists" if hits / n_shuf < 0.05 else "not significant"}


def main():
    rows = load()

    test = persistence_test(rows)
    with open(TEST_OUT, "w") as fh:
        json.dump(test, fh, indent=1)
    print(f"persistence: r={test['r']:+.3f} p={test['p_value']:.5f} "
          f"n={test['n_pairs']} -> {test['verdict'].upper()}")
    if test["verdict"] != "persists":
        print("STOPPING: tendencies do not persist, so a lift table would be noise.")
        return

    # weighted counts per franchise x band x position, and the league baseline
    fr = defaultdict(float)
    fr_tot = defaultdict(float)
    lg = defaultdict(float)
    lg_tot = defaultdict(float)
    raw_n = defaultdict(int)
    for r in rows:
        if r["pos"] not in POS:
            continue
        b = band_of(int(r["round"]))
        w = weight(r["season"])
        f = r["member_name"]
        fr[(f, b, r["pos"])] += w
        fr_tot[(f, b)] += w
        lg[(b, r["pos"])] += w
        lg_tot[b] += w
        raw_n[(f, b)] += 1

    franchises = sorted({f for f, _ in fr_tot})
    out = []
    for b in [n for _, _, n in BANDS]:
        for p in POS:
            league_p = lg[(b, p)] / lg_tot[b] if lg_tot[b] else 0.0
            obs = [(raw_n[(f, b)], fr[(f, b, p)] / max(fr_tot[(f, b)], 1e-9) * raw_n[(f, b)])
                   for f in franchises if raw_n[(f, b)]]
            k = shrinkage_k(obs, league_p)
            for f in franchises:
                n = raw_n[(f, b)]
                if not n:
                    continue
                q_obs = fr[(f, b, p)] / fr_tot[(f, b)] if fr_tot[(f, b)] else league_p
                q = (n * q_obs + k * league_p) / (n + k)
                lift = q / league_p if league_p > 1e-6 else 1.0
                out.append({
                    "franchise": f, "band": b, "pos": p,
                    "q_observed": round(q_obs, 4),
                    "q_league": round(league_p, 4),
                    "q_shrunk": round(q, 4),
                    "lift": round(lift, 4),
                    "n_picks": n, "shrink_k": round(k, 1),
                    "source": "out/picks.csv",
                    "basis": f"recency half-life {HALF_LIFE:g} seasons, empirical-Bayes shrunk",
                    "confidence": "verified" if n >= 20 else "thin",
                })

    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"wrote {OUT} ({len(out)} rows, {len(franchises)} franchises)")

    print("\nRB lift by franchise, rounds 1-3 (1.00 = league average):")
    rb = sorted([r for r in out if r["band"] == "rd1-3" and r["pos"] == "RB"],
                key=lambda r: -r["lift"])
    for r in rb:
        flag = " thin" if r["confidence"] == "thin" else ""
        print(f"  {r['franchise']:<22} lift {r['lift']:.2f}  "
              f"(raw {r['q_observed']:.2f} -> shrunk {r['q_shrunk']:.2f}, "
              f"n={r['n_picks']}, k={r['shrink_k']:g}){flag}")


if __name__ == "__main__":
    main()
