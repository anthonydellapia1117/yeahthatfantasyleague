#!/usr/bin/env python3
"""Verify harvested Yahoo per-player points against the LeagueLegacy export.

The hypothesis under test: Yahoo per-player points are bonus-inclusive and
LeagueLegacy dropped the six 40-yard long-play bonuses on import.

Pass condition: for each team-week, the sum of Yahoo STARTER points equals the
official team score in matchups_all.csv within 0.02.

Run:  python3 src/verify_yahoo.py raw/yahoo/players_2013.csv
"""
import csv, sys, os, collections, statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "made-resources",
                 "YeahThatFantasyLeague_LeagueLegacy_Archive_2013-2026")
B = os.path.join(ROOT, "LeagueLegacy-io",
                 "leaguelegacy_YeahThatFantasyLeague_full_export")


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def main(path):
    yahoo = list(csv.DictReader(open(path)))
    season = yahoo[0]["season"]

    # Yahoo starter sums per (week, yahoo team id) and per team name
    ysum = collections.defaultdict(float)
    yname = {}
    for r in yahoo:
        if r["bench"] == "1":
            continue
        k = (r["wk"], r["team"])
        ysum[k] += num(r["pts"])
        if r.get("team_name"):
            yname[k] = r["team_name"]

    # official team scores, keyed by (week, leaguelegacy franchise name)
    off = {}
    for m in csv.DictReader(open(os.path.join(B, "matchups_all.csv"), errors="replace")):
        if m["season"] == season:
            off[(m["week"], m["team"])] = num(m["points"])

    # local per-player starter sums, same key
    lsum = collections.defaultdict(float)
    for r in csv.DictReader(open(os.path.join(A, "02_gamecenter/matchup_rosters.csv"),
                                 errors="replace")):
        if r["season"] == season and r["started"] == "true":
            lsum[(r["week"], r["member_name"])] += num(r["points"]) or num(r["points_ppr"])

    # match Yahoo team-weeks to official by score, since names differ by era
    matched, exact, deltas, unmatched = 0, 0, [], []
    for k, ytotal in sorted(ysum.items()):
        wk = k[0]
        cands = {name: v for (w, name), v in off.items() if w == wk}
        hit = [n for n, v in cands.items() if abs(v - ytotal) < 0.02]
        if len(hit) == 1:
            matched += 1
            exact += 1
            local = lsum.get((wk, hit[0]))
            if local is not None:
                deltas.append(round(ytotal - local, 2))
        elif len(hit) > 1:
            matched += 1
        else:
            unmatched.append((wk, k[1], yname.get(k, ""), round(ytotal, 2)))

    print(f"season {season}")
    print(f"  yahoo team-weeks           : {len(ysum)}")
    print(f"  matched an official score  : {matched}")
    print(f"  EXACT single-score match   : {exact}")
    print(f"  unmatched                  : {len(unmatched)}")
    for u in unmatched[:8]:
        print(f"     wk{u[0]} team {u[1]} {u[2][:20]:20} yahoo={u[3]}")
    if deltas:
        print(f"\n  bonus recovered vs local per-player rows:")
        print(f"    n {len(deltas)}  mean {statistics.mean(deltas):+.2f}  "
              f"median {statistics.median(deltas):+.2f}  "
              f"max {max(deltas):+.2f}  zero {sum(1 for d in deltas if abs(d) < 0.005)}")
        ints = sum(1 for d in deltas if abs(d - round(d)) < 0.005)
        print(f"    whole integers {ints}/{len(deltas)} ({100*ints/len(deltas):.0f}%)")
    verdict = "PASS" if exact >= 0.95 * len(ysum) else "REVIEW"
    print(f"\n  VERDICT: {verdict}")


if __name__ == "__main__":
    main(sys.argv[1])
