#!/usr/bin/env python3
"""Compute lineup efficiency and emit a single JSON the HTML app embeds.

Efficiency = points actually started / points the optimal lineup would have scored,
per team-week, from `started` and `is_optimal` in the weekly roster table.

BASIS: Yahoo seasons 2013-2024 are bonus-exclusive (six 40-yard bonuses, 6.14 pts per
team-week). Efficiency is a RATIO of two bonus-exclusive sums, so it is unaffected.

Run:  python3 src/build_app_data.py
"""
import csv, json, os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "made-resources",
                 "YeahThatFantasyLeague_LeagueLegacy_Archive_2013-2026")
OUT = os.path.join(ROOT, "out")


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def main():
    rosters = list(csv.DictReader(
        open(os.path.join(A, "02_gamecenter/matchup_rosters.csv"), errors="replace")))
    champs = {c["season"]: c["champion"]
              for c in csv.DictReader(open(os.path.join(OUT, "champions.csv")))}

    started = defaultdict(float)
    optimal = defaultdict(float)
    tw = set()
    for r in rosters:
        k = (r["season"], r["member_name"], r["week"])
        p = num(r.get("points")) or num(r.get("points_ppr"))
        if r.get("started") == "true":
            started[k] += p
        if r.get("is_optimal") == "true":
            optimal[k] += p
        tw.add(k)

    # per franchise-season
    fs = defaultdict(lambda: {"s": 0.0, "o": 0.0, "w": 0})
    for k in tw:
        if optimal[k] <= 0:
            continue
        f = fs[(k[0], k[1])]
        f["s"] += started[k]
        f["o"] += optimal[k]
        f["w"] += 1

    rows = []
    for (season, fr), d in sorted(fs.items()):
        if d["o"] <= 0:
            continue
        is_champ = 1 if champs.get(season) == fr else 0
        rows.append({
            "season": season, "franchise": fr,
            "efficiency": round(100 * d["s"] / d["o"], 2),
            "points_left_per_week": round((d["o"] - d["s"]) / max(d["w"], 1), 2),
            "points_left_season": round(d["o"] - d["s"], 1),
            "weeks": d["w"],
            "champion": is_champ,
        })
    # out/lineup_efficiency.csv is owned by src/phase3_lineup.py, which writes the same
    # 156 rows with started/optimal and provenance columns. Writing it here too would
    # silently downgrade that file every time the app is rebuilt.

    # The permutation test runs ONCE, in src/phase3_lineup.py, which writes
    # the canonical result. Reading it here makes dashboard-vs-docs drift
    # structurally impossible. Run phase3_lineup.py first (see README).
    test_path = os.path.join(OUT, "efficiency_test.json")
    if not os.path.exists(test_path):
        raise SystemExit("out/efficiency_test.json missing - run "
                         "python3 src/phase3_lineup.py first (README rebuild order)")
    with open(test_path) as f:
        eff_test = json.load(f)

    # per franchise, career
    byfr = defaultdict(lambda: {"s": 0.0, "o": 0.0, "w": 0, "t": 0})
    for (season, fr), d in fs.items():
        b = byfr[fr]
        b["s"] += d["s"]; b["o"] += d["o"]; b["w"] += d["w"]
        if champs.get(season) == fr:
            b["t"] += 1
    fr_rows = []
    for fr, b in byfr.items():
        if b["o"] <= 0:
            continue
        fr_rows.append({
            "franchise": fr,
            "efficiency": round(100 * b["s"] / b["o"], 2),
            "points_left_per_week": round((b["o"] - b["s"]) / max(b["w"], 1), 2),
            "points_left_per_season": round((b["o"] - b["s"]) / max(b["w"], 1) * 14, 0),
            "titles": b["t"],
        })
    fr_rows.sort(key=lambda x: -x["efficiency"])

    # supporting tables the app renders
    def read(name):
        return list(csv.DictReader(open(os.path.join(OUT, name))))

    picks = read("picks.csv")
    seq = defaultdict(list)
    for p in picks:
        if int(p["round"]) <= 5:
            seq[(p["season"], p["member_name"])].append((int(p["round"]), p["pos"]))
    champ_seq = []
    for s in sorted(champs):
        k = (s, champs[s])
        if k in seq:
            champ_seq.append({"season": s, "franchise": champs[s],
                              "seq": [x[1] for x in sorted(seq[k])]})

    data = {
        "generated": "2026-08-11",
        "basis": ("Yahoo 2013-2024 bonus-exclusive: six 40-yard bonuses worth 6.14 pts "
                  "per team-week sit in team totals but not per-player rows. Efficiency "
                  "is a ratio of two bonus-exclusive sums and is unaffected."),
        "league": {"teams": 12, "seasons": 13, "span": "2013-2025",
                   "draft_date": "2026-09-08", "scoring": "full PPR, 6-pt passing TD",
                   "starters": "QB RB RB WR WR TE FLEX K DEF + 5 bench"},
        "efficiency_test": eff_test,
        "franchise_efficiency": fr_rows,
        "season_efficiency": rows,
        "champions": [{"season": s, "franchise": champs[s]} for s in sorted(champs)],
        "champion_sequences": champ_seq,
        "dead_hypotheses": [
            {"h": "Champions wait on QB", "stat": "6.46 vs 5.92 rounds", "p": 0.252},
            {"h": "Champions avoid QB in rounds 1-5", "stat": "62% vs 48%", "p": 0.266},
            {"h": "Champions load RB early", "stat": "2.15 vs 2.01", "p": None},
            {"h": "Champions load WR early", "stat": "2.00 vs 2.03", "p": None},
            {"h": "Draft slot matters", "stat": "mean 7.5 vs 6.5 expected", "p": None},
            {"h": "Drafted share predicts winning", "stat": "corr +0.043", "p": None},
            {"h": "FAAB aggression", "stat": "46.8 vs 35.7", "p": 0.197},
            {"h": "Champions draft the #1 board player", "stat": "0 of 13", "p": 0.323},
        ],
        "drafted_share": read("drafted_vs_acquired.csv"),
    }
    with open(os.path.join(OUT, "app_data.json"), "w") as f:
        json.dump(data, f)

    print(f"efficiency: {len(rows)} franchise-seasons")
    print(f"  champions {eff_test['champions_mean']:.2f}%  "
          f"field {eff_test['field_mean']:.2f}%  "
          f"p={eff_test['p_value']:.3f}  "
          f"n={eff_test['n_champions']}/{eff_test['n_total']}  (canonical)")
    print(f"app_data.json: {os.path.getsize(os.path.join(OUT,'app_data.json'))//1024} KB")
    print(f"\n{'FRANCHISE':20} {'EFF':>7} {'LEFT/WK':>8} {'/SEASON':>8} {'TITLES':>7}")
    for r in fr_rows:
        print(f"{r['franchise'][:20]:20} {r['efficiency']:6.2f}% {r['points_left_per_week']:8.2f} "
              f"{r['points_left_per_season']:8.0f} {r['titles']:7d}")


if __name__ == "__main__":
    main()
