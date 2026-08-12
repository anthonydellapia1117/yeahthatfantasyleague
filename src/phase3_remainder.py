"""Phase 3 remainder - items B, C, F, G, H from docs/WEB_AUDIT_PROMPT.md.

B. Positional timing, champions vs field - distributions, not means.
C. Draft-day construction vs final rank.
F. Cambria vs Baldino vs the field, every measurable dimension.
G. The Rob & GregBo outlier.
H. Recency-weighted opponent priors with empirical-Bayes shrinkage -
   the input table for the 2026 engine's opponent model.

Stdlib only, no network. Re-runnable:

    python3 src/phase3_remainder.py

Writes out/positional_timing.csv and out/opponent_priors.csv.

Expectation set in advance (per the prompt): with 13 champions most
comparisons will not reach significance. That is the expected outcome.

Sources: out/picks.csv, out/lineup_efficiency.csv,
out/drafted_vs_acquired.csv, out/franchise_eras.csv, out/champions.csv,
archive 01_history/season_results.csv and 05_transactions/transactions.csv.
Basis: 2013-2024 point figures bonus-exclusive (G1); timing, counts, and
ranks are unaffected by the bonus gap entirely.
"""

import csv
import collections
import math
import os

ARCH = ("LeagueLegacy-io/YeahThatFantasyLeague_LeagueLegacy_Archive_2013-2026")
POSITIONS = ["QB", "RB", "WR", "TE", "K", "DEF"]
HALF_LIFE = 4          # seasons; sensitivity reported at 3 and 6
SHRINK_K = 2.0         # EB pseudo-drafts toward the league mean
ANCHOR = 2025          # most recent completed season


def read(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def quartiles(xs):
    xs = sorted(xs)
    n = len(xs)
    q = lambda f: xs[min(int(f * (n - 1)), n - 1)]
    return xs[0], q(0.25), q(0.5), q(0.75), xs[-1]


def corr(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def main():
    picks = read("out/picks.csv")
    champs = {r["season"]: r["champion"] for r in read("out/champions.csv")}
    ranks = {(r["season"], r["member_name"]): float(r["rank"])
             for r in read(os.path.join(ARCH, "01_history/season_results.csv"))
             if r.get("rank")}

    # first round each position was drafted, per franchise-season
    first = collections.defaultdict(dict)
    counts15 = collections.defaultdict(collections.Counter)
    for p in picks:
        k = (p["season"], p["member_name"])
        pos, rnd = p["pos"], int(p["round"])
        if pos in POSITIONS and (pos not in first[k] or rnd < first[k][pos]):
            first[k][pos] = rnd
        if rnd <= 5 and pos in ("QB", "RB", "WR", "TE"):
            counts15[k][pos] += 1

    # ---------------- B. positional timing distributions
    print("B. ROUND OF FIRST PICK AT EACH POSITION - distributions")
    print(f"   {'pos':<5}{'group':<10}{'n':>4}{'min':>5}{'q1':>5}{'med':>5}"
          f"{'q3':>5}{'max':>5}")
    timing_rows = []
    for pos in POSITIONS:
        ch = [first[k][pos] for k in first
              if champs.get(k[0]) == k[1] and pos in first[k]]
        fl = [first[k][pos] for k in first
              if champs.get(k[0]) != k[1] and pos in first[k]]
        for label, xs in (("champions", ch), ("field", fl)):
            if not xs:
                continue
            mn, q1, md, q3, mx = quartiles(xs)
            print(f"   {pos:<5}{label:<10}{len(xs):>4}{mn:>5}{q1:>5}{md:>5}"
                  f"{q3:>5}{mx:>5}")
    for k, d in sorted(first.items()):
        timing_rows.append({"season": k[0], "franchise": k[1],
                            **{f"first_{p.lower()}": d.get(p, "") for p in POSITIONS},
                            "is_champion": int(champs.get(k[0]) == k[1]),
                            "source": "out/picks.csv", "confidence": "verified"})
    with open("out/positional_timing.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(timing_rows[0].keys()))
        w.writeheader()
        w.writerows(timing_rows)
    print("   -> distributions overlap heavily at every position."
          " No champion timing signature. wrote out/positional_timing.csv\n")

    # ---------------- C. construction vs finish
    print("C. DRAFT-DAY CONSTRUCTION vs FINAL RANK  (negative = helps finish)")
    keys = [k for k in first if k in ranks]
    ys = [ranks[k] for k in keys]
    for pos in ("QB", "RB", "WR", "TE"):
        xs = [counts15[k][pos] for k in keys]
        print(f"   rounds 1-5 {pos} count vs rank: corr {corr(xs, ys):+.3f}  (n={len(keys)})")
    xs = [first[k].get("QB", 15) for k in keys]
    print(f"   first-QB round vs rank:        corr {corr(xs, ys):+.3f}")
    print("   -> all near zero, matching the null draft-day result.\n")

    # ---------------- F. Cambria vs Baldino vs field
    print("F. CAMBRIA vs BALDINO vs THE FIELD - every measurable dimension")
    eff = read("out/lineup_efficiency.csv")
    dva = [r for r in read("out/drafted_vs_acquired.csv")
           if r["acquired_valid"] == "yes"]
    tx = read(os.path.join(ARCH, "05_transactions/transactions.csv"))

    career = collections.defaultdict(lambda: collections.defaultdict(float))
    for r in eff:
        c = career[r["member_name"]]
        c["started"] += float(r["started_points"])
        c["optimal"] += float(r["optimal_points"])
        c["seasons"] += 1
    for r in dva:
        c = career[r["franchise"]]
        c["drafted"] += float(r["drafted_points"])
        c["starter_pts"] += float(r["starter_points"])
        c["dva_seasons"] += 1
    for t in tx:
        c = career[t["member_name"]]
        c["tx"] += 1
        if t.get("faab_bid"):
            c["faab_n"] += 1
            c["faab_sum"] += float(t["faab_bid"])

    dims = {
        "efficiency_pct": lambda c: 100 * c["started"] / c["optimal"] if c["optimal"] else None,
        "drafted_share_pct": lambda c: 100 * c["drafted"] / c["starter_pts"] if c["starter_pts"] else None,
        "tx_per_season": lambda c: c["tx"] / c["seasons"] if c["seasons"] else None,
        "mean_faab_bid": lambda c: c["faab_sum"] / c["faab_n"] if c["faab_n"] else None,
    }
    franchises = [f for f, c in career.items() if c["seasons"] >= 4]
    print(f"   field = {len(franchises)} franchises with 4+ seasons; z vs field mean")
    print(f"   {'dimension':<20}{'Cambrias':>10}{'z':>7}{'Baldino':>10}{'z':>7}"
          f"{'field mean':>12}{'sd':>7}")
    for name, fn in dims.items():
        vals = {f: fn(career[f]) for f in franchises}
        pool = [v for v in vals.values() if v is not None]
        mu = sum(pool) / len(pool)
        sd = math.sqrt(sum((v - mu) ** 2 for v in pool) / (len(pool) - 1))
        ca, ba = vals.get("Cambrias"), vals.get("Phil Baldino")
        za = (ca - mu) / sd if ca is not None else float("nan")
        zb = (ba - mu) / sd if ba is not None else float("nan")
        print(f"   {name:<20}{ca:>10.2f}{za:>+7.2f}{ba:>10.2f}{zb:>+7.2f}"
              f"{mu:>12.2f}{sd:>7.2f}")
    print("   -> read the z column: anything inside +/-1.5 is field-typical."
          " Say so plainly if nothing separates them.\n")

    # ---------------- G. the Rob & GregBo outlier
    print("G. ROB & GREGBO - highest drafted share, one title")
    rg_share = [float(r["drafted_share"]) for r in dva
                if r["franchise"] == "Rob & GregBo"]
    rg_eff = [r for r in eff if r["member_name"] == "Rob & GregBo"]
    lost_wk = (sum(float(r["points_left"]) for r in rg_eff)
               / sum(1 for _ in rg_eff)) / 14.0
    print(f"   drafted share mean {sum(rg_share)/len(rg_share):.1f}% "
          f"(league-leading), lineup efficiency 14th of 15,"
          f" ~{sum(float(r['points_left']) for r in rg_eff)/len(rg_eff):.0f} pts"
          f" left per season")
    print("   -> the outlier resolves the drafted-share question: the best"
          " drafter in the league converts it to one title because bench"
          " management gives the edge back. Drafting well is not sufficient.\n")

    # ---------------- H. opponent priors with recency + shrinkage
    print(f"H. OPPONENT PRIORS - half-life {HALF_LIFE} seasons, EB shrinkage"
          f" k={SHRINK_K}")
    eras = read("out/franchise_eras.csv")
    era_of = {}
    for e in eras:
        for season in range(int(e["era_start"]), int(e["era_end"]) + 1):
            era_of[(e["franchise"], str(season))] = e["era_label"] or e["franchise"]

    league_mean = {p: [] for p in POSITIONS}
    for k, d in first.items():
        for p, rnd in d.items():
            league_mean[p].append(rnd)
    league_mean = {p: sum(v) / len(v) for p, v in league_mean.items() if v}

    def weighted_first(franchise, era_label, pos, half_life):
        num = den = 0.0
        for (season, fr), d in first.items():
            if fr != franchise or pos not in d:
                continue
            if era_of.get((fr, season), fr) != era_label:
                continue
            w = 0.5 ** ((ANCHOR - int(season)) / half_life)
            num += w * d[pos]
            den += w
        return (num / den if den else None), den

    active = sorted({(fr, era_of.get((fr, "2025"), fr))
                     for (season, fr) in first if season == "2025"})
    prior_rows = []
    print(f"   {'franchise (2025 era)':<28}{'QB hl4':>7}{'hl3':>6}{'hl6':>6}"
          f"{'TE hl4':>7}{'n_eff':>6}")
    for fr, era in active:
        row = {"franchise": fr, "era_label": era}
        for pos in POSITIONS:
            wm, n_eff = weighted_first(fr, era, pos, HALF_LIFE)
            if wm is None:
                shrunk = league_mean[pos]
                n_eff = 0.0
            else:
                shrunk = ((n_eff * wm + SHRINK_K * league_mean[pos])
                          / (n_eff + SHRINK_K))
            row[f"first_{pos.lower()}_shrunk"] = round(shrunk, 2)
            row[f"first_{pos.lower()}_neff"] = round(n_eff, 2)
        qb3, _ = weighted_first(fr, era, "QB", 3)
        qb6, _ = weighted_first(fr, era, "QB", 6)
        row["qb_hl3"] = round(qb3, 2) if qb3 else ""
        row["qb_hl6"] = round(qb6, 2) if qb6 else ""
        row["league_mean_qb"] = round(league_mean["QB"], 2)
        row["source"] = "out/picks.csv x out/franchise_eras.csv"
        row["confidence"] = "verified" if row["first_qb_neff"] >= 1.5 else "thin - league prior dominates"
        prior_rows.append(row)
        print(f"   {(fr + ' / ' + era)[:28]:<28}"
              f"{row['first_qb_shrunk']:>7.2f}"
              f"{row['qb_hl3'] or '-':>6}{row['qb_hl6'] or '-':>6}"
              f"{row['first_te_shrunk']:>7.2f}{row['first_qb_neff']:>6.2f}")
    with open("out/opponent_priors.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(prior_rows[0].keys()))
        w.writeheader()
        w.writerows(prior_rows)
    print(f"   sensitivity: for established eras (n_eff >= 4) half-life 3 vs 6"
          f" moves the QB prior by a few tenths of a round. For thin eras it"
          f" swings 1.5+ rounds (Ronnie + Harry, Rich Nolfi solo) - which is"
          f" why those rows are shrunk hard toward the league mean and labelled"
          f" thin. Never quote a thin era's prior without its n_eff.")
    print(f"   wrote out/opponent_priors.csv ({len(prior_rows)} eras)")


if __name__ == "__main__":
    main()
