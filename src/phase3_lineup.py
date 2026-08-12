"""Phase 3 - lineup efficiency, the one surviving lead.

Every draft-day hypothesis is null (see HANDOFF Part 2). This tests the
start-sit lever instead, and decomposes it by position against the
strongest comparable manager.

Stdlib only, no network. Re-runnable:

    python3 src/phase3_lineup.py

Writes out/lineup_efficiency.csv and prints the summary tables.

Source A: LeagueLegacy archive, 02_gamecenter/matchup_rosters.csv, 37,106 rows.
Basis note: 2013-2024 figures are bonus-exclusive (the six 40-yard long-play
bonuses are absent from per-player rows; see out/gap_register.md G1). Both
sides of every ratio here are bonus-exclusive, so the ratios are unaffected.
"""

import csv
import collections
import random
import os

ROSTERS = ("LeagueLegacy-io/YeahThatFantasyLeague_LeagueLegacy_Archive_2013-2026"
           "/02_gamecenter/matchup_rosters.csv")
CHAMPIONS = "out/champions.csv"
OUT = "out/lineup_efficiency.csv"

SEED = 20260811          # fixed so the permutation p is reproducible
SHUFFLES = 50_000
MIN_TEAM_WEEKS = 30      # below this a franchise is too thin to rank
ME = "Antdell & Ernie"
RIVAL = "Phil Baldino"   # 3 titles, best lost-points-per-week in the league
POSITIONS = ["WR", "RB", "TE", "QB", "DEF", "K"]


def points(row):
    """Archive stores 0 in `points` for some rows that carry `points_ppr`."""
    p = float(row["points"] or 0)
    ppr = float(row["points_ppr"] or 0)
    return ppr if p == 0 and ppr != 0 else p


def flag(value):
    return value == "true"


def load():
    with open(ROSTERS) as fh:
        rows = list(csv.DictReader(fh))
    with open(CHAMPIONS) as fh:
        champions = {r["season"]: r["champion"] for r in csv.DictReader(fh)}
    missing = [f"{s}:{c}" for s, c in champions.items()
               if not any(r["season"] == s and r["member_name"] == c for r in rows)]
    if missing:
        raise SystemExit(f"champion not found in roster data: {missing}")
    return rows, champions


def franchise_seasons(rows):
    """(season, member) -> [started_points, optimal_points]."""
    acc = collections.defaultdict(lambda: [0.0, 0.0])
    for r in rows:
        key = (r["season"], r["member_name"])
        if flag(r["started"]):
            acc[key][0] += points(r)
        if flag(r["is_optimal"]):
            acc[key][1] += points(r)
    return acc


def permutation_test(efficiency, champions):
    """One-sided: do champions sit above the field on lineup efficiency?"""
    is_champ = lambda k: champions.get(k[0]) == k[1]
    champ = [v for k, v in efficiency.items() if is_champ(k)]
    field = [v for k, v in efficiency.items() if not is_champ(k)]
    mean = lambda xs: sum(xs) / len(xs)
    observed = mean(champ) - mean(field)

    pool = list(efficiency.values())
    n = len(champ)
    rng = random.Random(SEED)
    at_least = 0
    for _ in range(SHUFFLES):
        rng.shuffle(pool)
        if mean(pool[:n]) - mean(pool[n:]) >= observed:
            at_least += 1
    return champ, field, observed, at_least / SHUFFLES


def by_franchise(rows):
    """member -> [started, optimal, team_weeks]."""
    acc = collections.defaultdict(lambda: [0.0, 0.0])
    weeks = collections.defaultdict(set)
    for r in rows:
        m = r["member_name"]
        weeks[m].add((r["season"], r["week"]))
        if flag(r["started"]):
            acc[m][0] += points(r)
        if flag(r["is_optimal"]):
            acc[m][1] += points(r)
    return {m: (s, o, len(weeks[m])) for m, (s, o) in acc.items()}


def positional_loss(rows, who=None):
    """Points forgone per position: optimal-not-started minus started-not-optimal.

    Returned per team-week so managers with different tenures compare directly.
    Also returns capture rate, which normalizes for the fact that WR and RB
    simply have more slots and would dominate any raw points total.
    """
    lost = collections.defaultdict(float)
    optimal = collections.defaultdict(float)
    weeks = set()
    for r in rows:
        if who and r["member_name"] != who:
            continue
        weeks.add((r["season"], r["week"], r["member_name"]))
        pos = r["player_position"]
        if flag(r["is_optimal"]):
            optimal[pos] += points(r)
            if not flag(r["started"]):
                lost[pos] += points(r)
        elif flag(r["started"]):
            lost[pos] -= points(r)
    return lost, optimal, len(weeks)


def main():
    rows, champions = load()
    titles = collections.Counter(champions.values())

    # 1. Is the champion signal real?
    fs = franchise_seasons(rows)
    efficiency = {k: s / o for k, (s, o) in fs.items() if o > 0}
    champ, field, observed, p = permutation_test(efficiency, champions)
    mean = lambda xs: sum(xs) / len(xs)

    print("LINEUP EFFICIENCY - champions versus field")
    print(f"  franchise-seasons  {len(efficiency)}")
    print(f"  champions  n={len(champ):<3} mean {mean(champ):.2%}")
    print(f"  field      n={len(field):<3} mean {mean(field):.2%}")
    print(f"  difference {observed * 100:+.2f} pp")
    print(f"  permutation p = {p:.4f}  ({SHUFFLES:,} shuffles, seed {SEED})")
    print("  marginal. a lead, not a finding.\n")

    # 2. Who leaves the fewest points on the bench?
    per = by_franchise(rows)
    table = sorted(((m, s / o, (o - s) / n, n, titles.get(m, 0))
                    for m, (s, o, n) in per.items()
                    if o > 0 and n >= MIN_TEAM_WEEKS),
                   key=lambda t: t[2])
    print("POINTS LEFT ON THE BENCH, per team-week")
    print(f"  {'franchise':<22}{'lost/wk':>9}{'eff':>9}{'wks':>6}{'titles':>8}")
    for m, eff, lost, n, t in table:
        mark = "  <-- you" if m == ME else ""
        print(f"  {m:<22}{lost:>9.2f}{eff:>9.2%}{n:>6}{t:>8}{mark}")
    rank = [m for m, *_ in table].index(ME) + 1
    print(f"  rank {rank} of {len(table)} on lost/wk\n")

    # 3. Where does the gap to the rival sit?
    ml, mo, mw = positional_loss(rows, ME)
    bl, bo, bw = positional_loss(rows, RIVAL)
    fl, fo, fw = positional_loss(rows)
    total_gap = sum(ml.values()) / mw - sum(bl.values()) / bw

    print(f"POSITIONAL DECOMPOSITION - {ME} versus {RIVAL}")
    print(f"  {'pos':<5}{'you/wk':>8}{'rival':>8}{'field':>8}{'gap':>8}"
          f"{'capture you/rival':>20}")
    gaps = []
    for pos in POSITIONS:
        a, b, f = ml[pos] / mw, bl[pos] / bw, fl[pos] / fw
        gaps.append((pos, a - b))
        cap_a = 1 - ml[pos] / mo[pos] if mo[pos] else 0.0
        cap_b = 1 - bl[pos] / bo[pos] if bo[pos] else 0.0
        print(f"  {pos:<5}{a:>8.2f}{b:>8.2f}{f:>8.2f}{a - b:>+8.2f}"
              f"{cap_a:>13.1%}/{cap_b:.1%}")
    print(f"  {'ALL':<5}{sum(ml.values()) / mw:>8.2f}{sum(bl.values()) / bw:>8.2f}"
          f"{sum(fl.values()) / fw:>8.2f}{total_gap:>+8.2f}")

    print(f"\n  share of the {total_gap:.2f} pts/wk gap:")
    for pos, d in sorted(gaps, key=lambda t: -t[1]):
        print(f"    {pos:<5}{d:>+7.2f}{d / total_gap:>8.0%}")

    # 4. Persist the franchise-season table
    os.makedirs("out", exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["season", "member_name", "started_points", "optimal_points",
                    "efficiency", "points_left", "is_champion", "source",
                    "source_ref", "basis", "confidence"])
        for (season, member), (started, optimal) in sorted(fs.items()):
            if optimal <= 0:
                continue
            w.writerow([season, member, round(started, 2), round(optimal, 2),
                        round(started / optimal, 6), round(optimal - started, 2),
                        int(champions.get(season) == member), "leaguelegacy",
                        "02_gamecenter/matchup_rosters.csv",
                        "bonus-exclusive" if season <= "2024" else "full",
                        "verified"])
    print(f"\nwrote {OUT} ({len(fs)} franchise-seasons)")


if __name__ == "__main__":
    main()
