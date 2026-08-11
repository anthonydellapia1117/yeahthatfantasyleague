#!/usr/bin/env python3
"""Phase 2 - value layer.

Joins every draft pick to that player's realized starter production in this league's
own scoring, then splits each franchise-season's starter points into DRAFTED versus
ACQUIRED. That split decides whether this league is won on draft day or after it.

BASIS, stated once and carried into every output:
  Yahoo seasons 2013-2024 are BONUS-EXCLUSIVE. Six 40-yard long-play bonuses worth
  6.14 points per team-week (4.99 percent) are present in official team totals but
  absent from per-player rows. See out/gap_register.md G1. The drafted-vs-acquired
  RATIO is unaffected because both sides are bonus-exclusive. Absolute per-pick point
  totals for 2013-2024 are understated by roughly 5 percent, concentrated on
  deep-threat receivers, explosive backs, and vertical quarterbacks.

  2013 has no transaction data, so it is excluded from the acquired split only.

Run:  python3 src/phase2_value.py
"""
import csv, json, os, statistics
from collections import defaultdict, Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "made-resources",
                 "YeahThatFantasyLeague_LeagueLegacy_Archive_2013-2026")
OUT = os.path.join(ROOT, "out")
NO_TX = {"2013"}          # transactions start 2014


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def load(rel):
    with open(os.path.join(A, rel), errors="replace") as f:
        return list(csv.DictReader(f))


def main():
    picks = load("04_draft/draft_results.csv")
    rosters = load("02_gamecenter/matchup_rosters.csv")

    # ---- draft ownership: (season, member, player) -> pick metadata
    drafted = {}
    for p in picks:
        for pid in (p.get("service_player_id"), p.get("player_id")):
            if pid:
                drafted[(p["season"], p["member_name"], str(pid))] = p

    # ---- starter production per player-week, tagged drafted or acquired
    prod = defaultdict(float)                      # pick key -> starter points
    weeks = Counter()                              # pick key -> starter weeks
    fs = defaultdict(lambda: {"drafted": 0.0, "acquired": 0.0, "n": 0})
    unmatched = 0

    for r in rosters:
        if r.get("started") != "true":
            continue
        pts = num(r.get("points")) or num(r.get("points_ppr"))
        season, member = r["season"], r["member_name"]
        key = None
        for pid in (r.get("service_player_id"), r.get("player_id")):
            if pid and (season, member, str(pid)) in drafted:
                key = (season, member, str(pid))
                break
        bucket = "drafted" if key else "acquired"
        fs[(season, member)][bucket] += pts
        fs[(season, member)]["n"] += 1
        if key:
            prod[key] += pts
            weeks[key] += 1
        else:
            unmatched += 1

    # ---- per-pick rows
    rows = []
    for p in picks:
        key = None
        for pid in (p.get("service_player_id"), p.get("player_id")):
            if pid and (p["season"], p["member_name"], str(pid)) in drafted:
                key = (p["season"], p["member_name"], str(pid))
                break
        rows.append({
            "season": p["season"], "franchise": p["member_name"],
            "round": int(p["draft_round"]), "overall": int(p["draft_pick"]),
            "player": p["player_name"], "pos": p["player_position"],
            "starter_points": round(prod.get(key, 0.0), 2),
            "starter_weeks": weeks.get(key, 0),
            "adp_differential": p.get("adp_differential", ""),
            "basis": "bonus_exclusive" if p["season"] < "2025" else "complete",
        })

    # ---- positional replacement WITHIN season, then VOR per pick
    by_sp = defaultdict(list)
    for r in rows:
        by_sp[(r["season"], r["pos"])].append(r["starter_points"])
    baseline = {}
    for k, v in by_sp.items():
        v = sorted(v, reverse=True)
        # replacement = the 12th best at that position that season (1 per team)
        i = min(11, len(v) - 1)
        baseline[k] = v[i] if v else 0.0
    for r in rows:
        r["vor"] = round(r["starter_points"] - baseline.get((r["season"], r["pos"]), 0.0), 2)

    # ---- expected value by round, then realized minus expected
    by_round = defaultdict(list)
    for r in rows:
        by_round[r["round"]].append(r["starter_points"])
    exp = {rd: statistics.median(v) for rd, v in by_round.items()}
    for r in rows:
        r["expected_for_round"] = round(exp.get(r["round"], 0.0), 2)
        r["vs_expected"] = round(r["starter_points"] - r["expected_for_round"], 2)
        r["hit"] = 1 if r["starter_points"] >= 1.5 * r["expected_for_round"] and r["expected_for_round"] > 0 else 0
        r["bust"] = 1 if r["starter_points"] <= 0.5 * r["expected_for_round"] and r["expected_for_round"] > 0 else 0

    with open(os.path.join(OUT, "pick_value.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ---- THE central number
    split = []
    for (season, member), d in sorted(fs.items()):
        tot = d["drafted"] + d["acquired"]
        if tot <= 0:
            continue
        split.append({
            "season": season, "franchise": member,
            "starter_points": round(tot, 2),
            "drafted_points": round(d["drafted"], 2),
            "acquired_points": round(d["acquired"], 2),
            "drafted_share": round(100 * d["drafted"] / tot, 1),
            "starter_weeks": d["n"],
            "acquired_valid": "no" if season in NO_TX else "yes",
            "basis": "bonus_exclusive" if season < "2025" else "complete",
        })
    with open(os.path.join(OUT, "drafted_vs_acquired.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(split[0].keys()))
        w.writeheader()
        w.writerows(split)

    # ---- report
    print(f"picks {len(rows)} | starter rows matched to a draft pick "
          f"{sum(weeks.values())} | unmatched starter weeks {unmatched}")
    print(f"\n{'SEASON':7} {'DRAFTED SHARE':>14} {'teams':>6}")
    byseason = defaultdict(list)
    for s in split:
        byseason[s["season"]].append(s["drafted_share"])
    for s in sorted(byseason):
        v = byseason[s]
        flag = "  (no tx data)" if s in NO_TX else ""
        print(f"{s:7} {statistics.mean(v):13.1f}% {len(v):6d}{flag}")
    allv = [x for s, v in byseason.items() if s not in NO_TX for x in v]
    print(f"\nLEAGUE-WIDE DRAFTED SHARE, 2014-2025: {statistics.mean(allv):.1f}% "
          f"(median {statistics.median(allv):.1f}, min {min(allv):.1f}, max {max(allv):.1f})")

    print(f"\n{'FRANCHISE':20} {'DRAFTED SHARE':>14} {'seasons':>8}")
    byfr = defaultdict(list)
    for s in split:
        if s["season"] not in NO_TX:
            byfr[s["franchise"]].append(s["drafted_share"])
    for fr, v in sorted(byfr.items(), key=lambda x: -statistics.mean(x[1])):
        print(f"{fr[:20]:20} {statistics.mean(v):13.1f}% {len(v):8d}")


if __name__ == "__main__":
    main()
