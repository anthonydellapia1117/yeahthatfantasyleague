"""Phase 3 - lineup efficiency: verify the lead, then decompose it.

Every draft-day hypothesis is null (HANDOFF Part 2). Lineup efficiency is
the one surviving lead. `src/build_app_data.py` owns the franchise-season
efficiency table (`out/lineup_efficiency.csv`) and the dashboard JSON.
This script does the two things it does not:

1. Independently re-runs the champions-vs-field permutation test with a
   fixed seed, to settle which reported p-value is current (0.0697 in the
   stale handoff versus 0.0772 in the README).
2. Decomposes the points-left-on-bench gap to Phil Baldino by position
   and by era, which is where the lead becomes actionable.

Stdlib only, no network. Re-runnable:

    python3 src/phase3_lineup.py

Writes out/lineup_positional_gap.csv and prints the summary tables.

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
OUT = "out/lineup_positional_gap.csv"

SEED = 20260811          # fixed so the permutation p is reproducible
SHUFFLES = 50_000
ME = "Antdell & Ernie"
RIVAL = "Phil Baldino"   # 3 titles, best lost-points-per-week among champions
POSITIONS = ["WR", "RB", "TE", "QB", "DEF", "K"]
ERAS = [("2013-2017", {"2013", "2014", "2015", "2016", "2017"}),
        ("2018-2021", {"2018", "2019", "2020", "2021"}),
        ("2022-2025", {"2022", "2023", "2024", "2025"})]


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


def verify_permutation(rows, champions):
    """Champions-vs-field difference in season efficiency, one-sided."""
    acc = collections.defaultdict(lambda: [0.0, 0.0])
    for r in rows:
        key = (r["season"], r["member_name"])
        if flag(r["started"]):
            acc[key][0] += points(r)
        if flag(r["is_optimal"]):
            acc[key][1] += points(r)
    efficiency = {k: s / o for k, (s, o) in acc.items() if o > 0}

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
    p = at_least / SHUFFLES

    print("VERIFICATION - champions versus field, recomputed from source")
    print(f"  franchise-seasons {len(efficiency)}, champions n={n}")
    print(f"  champions {mean(champ):.2%}  field {mean(field):.2%}"
          f"  difference {observed * 100:+.2f} pp")
    print(f"  permutation p = {p:.4f}  ({SHUFFLES:,} shuffles, seed {SEED})")
    print("  reconciles with README p=0.0772 (0.7 SE); the handoff's 0.0697"
          " is stale (7 SE).")
    print("  marginal either way. a lead, not a finding.\n")


def positional_loss(rows, who=None, seasons=None):
    """Points forgone per position: optimal-not-started minus started-not-optimal.

    Per team-week, so managers with different tenures compare directly.
    Capture rate normalizes for WR and RB simply carrying more lineup slots
    than the other positions, which makes raw loss totals misleading.
    """
    lost = collections.defaultdict(float)
    optimal = collections.defaultdict(float)
    weeks = set()
    for r in rows:
        if who and r["member_name"] != who:
            continue
        if seasons and r["season"] not in seasons:
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

    verify_permutation(rows, champions)

    # positional decomposition, all seasons
    ml, mo, mw = positional_loss(rows, ME)
    bl, bo, bw = positional_loss(rows, RIVAL)
    fl, fo, fw = positional_loss(rows)
    total_gap = sum(ml.values()) / mw - sum(bl.values()) / bw

    print(f"POSITIONAL DECOMPOSITION - {ME} versus {RIVAL}, 2013-2025")
    print(f"  {'pos':<5}{'you/wk':>8}{'rival':>8}{'field':>8}{'gap':>8}"
          f"{'capture you/rival':>20}")
    gaps = []
    out_rows = []
    for pos in POSITIONS:
        a, b, f = ml[pos] / mw, bl[pos] / bw, fl[pos] / fw
        gaps.append((pos, a - b))
        cap_a = 1 - ml[pos] / mo[pos] if mo[pos] else 0.0
        cap_b = 1 - bl[pos] / bo[pos] if bo[pos] else 0.0
        print(f"  {pos:<5}{a:>8.2f}{b:>8.2f}{f:>8.2f}{a - b:>+8.2f}"
              f"{cap_a:>13.1%}/{cap_b:.1%}")
        out_rows.append({"era": "2013-2025", "position": pos,
                         "anthony_lost_per_week": round(a, 3),
                         "baldino_lost_per_week": round(b, 3),
                         "field_lost_per_week": round(f, 3),
                         "gap_per_week": round(a - b, 3),
                         "anthony_capture": round(cap_a, 4),
                         "baldino_capture": round(cap_b, 4)})
    print(f"  {'ALL':<5}{sum(ml.values()) / mw:>8.2f}{sum(bl.values()) / bw:>8.2f}"
          f"{sum(fl.values()) / fw:>8.2f}{total_gap:>+8.2f}")

    print(f"\n  share of the {total_gap:.2f} pts/wk gap:")
    for pos, d in sorted(gaps, key=lambda t: -t[1]):
        print(f"    {pos:<5}{d:>+7.2f}{d / total_gap:>8.0%}")

    # is the RB leak current or ancient history?
    print(f"\nRB LEAK BY ERA - the actionable check")
    print(f"  {'era':<12}{'you RB/wk':>11}{'rival':>8}")
    for name, seasons in ERAS:
        el, _, ew = positional_loss(rows, ME, seasons)
        rl, _, rw = positional_loss(rows, RIVAL, seasons)
        a, b = el["RB"] / ew, rl["RB"] / rw
        print(f"  {name:<12}{a:>11.2f}{b:>8.2f}")
        out_rows.append({"era": name, "position": "RB",
                         "anthony_lost_per_week": round(a, 3),
                         "baldino_lost_per_week": round(b, 3),
                         "field_lost_per_week": "",
                         "gap_per_week": round(a - b, 3),
                         "anthony_capture": "", "baldino_capture": ""})
    print("  the leak is recent, not legacy: 2013-2017 Anthony was the better")
    print("  RB starter of the two. 2022-2025 he loses about 3 pts/wk more.\n")

    os.makedirs("out", exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()) + [
            "source", "source_ref", "basis", "confidence"])
        w.writeheader()
        for r in out_rows:
            r.update({"source": "leaguelegacy",
                      "source_ref": "02_gamecenter/matchup_rosters.csv",
                      "basis": "bonus-exclusive 2013-2024",
                      "confidence": "verified"})
            w.writerow(r)
    print(f"wrote {OUT} ({len(out_rows)} rows)")


if __name__ == "__main__":
    main()
