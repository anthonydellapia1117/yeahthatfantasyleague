#!/usr/bin/env python3
"""C4: ceiling lens for the median-game format, ENABLED (confirmed setting).

This league scores every week twice - H2H plus the league median
(league_average_match=1, verified live) - so weekly ceiling is worth more than
in pure H2H. This artifact computes, per draftable player, the DIRECT
empirical ceiling stats under league-exact scoring:

  boom_rate  share of 2025 weeks at top-12-week level for the position, where
             each week's cutoff is that week's actual 12th-best positional
             score (computed, never a constant)
  p90_week   90th-percentile weekly score
  weekly_sd  weekly scoring volatility

plus the zero-IR availability penalty the settings correction requires:

  gp_rate    games played / games possible over 2024-2025
  exp_missed 17 x (1 - gp_rate)
  avail_adj  projection x gp_rate - exp_missed x weekly replacement points at
             the position (C1 baselines / 17): his missed weeks return nothing
             AND the roster slot he blocks (no IR, 5 bench) could have held a
             replacement-level fill - both costs are stated, both computed.

DELIBERATE LIMITATION, stated: no synthetic variance-premium coefficient is
applied. Deriving one honestly needs multi-season weekly team scores (the
yfpy 2014-2024 backlog); a lambda invented from one 12-team season would be
noise wearing a formula. The lens ranks by boom_rate - the thing the median
format actually pays for - and shows the stats. When the historical module
lands, the premium can be estimated and this note replaced.

Run: python3 src/build_ceiling.py
"""
import csv
import datetime
import json
import math
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY = os.environ.get(
    "HISTORY",
    "/tmp/claude-0/-home-user-yeahthatfantasyleague/"
    "3092ab3f-cbec-5ded-8daf-9676b9b6a046/scratchpad/history")
D = os.path.join(ROOT, "out", "data")
OUT = os.path.join(D, "ceiling_2026.json")
POSITIONS = ("QB", "RB", "WR", "TE")

W = {"passing_yards": 0.04, "passing_tds": 6.0, "passing_interceptions": -1.0,
     "passing_2pt_conversions": 2.0,
     "rushing_yards": 0.1, "rushing_tds": 6.0, "rushing_2pt_conversions": 2.0,
     "receptions": 1.0, "receiving_yards": 0.1, "receiving_tds": 6.0,
     "receiving_2pt_conversions": 2.0,
     "sack_fumbles_lost": -2.0, "rushing_fumbles_lost": -2.0,
     "receiving_fumbles_lost": -2.0, "special_teams_tds": 6.0}


def norm(n):
    n = n.lower().replace(".", "").replace("'", "")
    return " ".join(w for w in n.split()
                    if w not in ("jr", "sr", "ii", "iii", "iv", "v"))


def weekly_points(year):
    """(name|pos, week) -> league-scored points, REG."""
    pts = defaultdict(float)
    with open(os.path.join(HISTORY, f"spw_{year}.csv")) as fh:
        for r in csv.DictReader(fh):
            if r.get("season_type") != "REG" or r.get("position") not in POSITIONS:
                continue
            key = (norm(r["player_display_name"]) + "|" + r["position"],
                   int(r["week"]))
            for col, w in W.items():
                v = r.get(col)
                if v:
                    try:
                        pts[key] += float(v) * w
                    except ValueError:
                        pass
    return pts


def main():
    eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
    baselines = eng["baselines"]
    draftable = [p for p in eng["players"]
                 if p["adp"] <= 14 * 12 and p["pos"] in POSITIONS]

    wp25 = weekly_points(2025)
    wp24 = weekly_points(2024)

    # per-week positional top-12 cutoffs, computed from the week itself
    by_week = defaultdict(list)          # (pos, week) -> scores
    for (key, week), v in wp25.items():
        by_week[(key.split("|")[1], week)].append(v)
    cutoff = {}
    for (pos, week), scores in by_week.items():
        scores.sort(reverse=True)
        if len(scores) >= 12:
            cutoff[(pos, week)] = scores[11]

    # per-player weekly series
    series25 = defaultdict(list)
    for (key, week), v in wp25.items():
        series25[key].append((week, v))
    games24 = defaultdict(int)
    for (key, _w), _v in wp24.items():
        games24[key] += 1

    players = []
    for p in draftable:
        key = norm(p["name"]) + "|" + p["pos"]
        weeks = sorted(series25.get(key, []))
        g25 = len(weeks)
        g24 = games24.get(key, 0)
        entry = {"name": p["name"], "pos": p["pos"], "adp": p["adp"],
                 "proj": p["pts"]}
        if weeks:
            vals = [v for _, v in weeks]
            mean = sum(vals) / len(vals)
            sd = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
            booms = sum(1 for wk, v in weeks
                        if (p["pos"], wk) in cutoff and v >= cutoff[(p["pos"], wk)])
            vs = sorted(vals)
            p90 = vs[max(0, min(len(vs) - 1, int(round(0.9 * (len(vs) - 1)))))]
            entry.update({
                "weeks_2025": g25,
                "weekly_mean": round(mean, 2), "weekly_sd": round(sd, 2),
                "p90_week": round(p90, 2),
                "boom": {"k": booms, "n": g25, "rate": round(booms / g25, 4)},
            })
        # availability: two-season games-played rate; rookies have no sample
        possible = (17 if g25 or True else 0) + (17 if g24 or g25 else 0)
        if g24 + g25 > 0:
            gp_rate = (g24 + g25) / 34 if g24 else g25 / 17
            gp_rate = min(1.0, gp_rate)
            exp_missed = round(17 * (1 - gp_rate), 2)
            repl_weekly = baselines[p["pos"]] / 17
            avail_adj = round(p["pts"] * gp_rate - exp_missed * repl_weekly, 1)
            entry.update({
                "gp_rate_2yr": round(gp_rate, 4),
                "exp_missed": exp_missed,
                "avail_adj_proj": avail_adj,
                "avail_note": ("missed weeks return nothing and block a bench "
                               "slot (no IR); penalty = expected missed weeks "
                               "x weekly replacement points"),
            })
        else:
            entry["avail_note"] = "no NFL sample - availability unadjusted"
        players.append(entry)

    out = {
        "provenance": {
            "generated": datetime.date.today().isoformat(),
            "format": ("H2H + league median, league_average_match=1 verified "
                       "live on both league ids - every week scores twice"),
            "scoring": "league-exact (6-pt pass TD, full PPR)",
            "boom_cutoffs": "per-week positional top-12 scores, computed",
            "limitation": ("no synthetic variance-premium coefficient: deriving "
                           "one needs multi-season weekly team data (yfpy "
                           "backlog); the lens ranks by boom_rate directly"),
        },
        "weekly_replacement": {p: round(baselines[p] / 17, 2) for p in POSITIONS},
        "players": players,
    }
    json.dump(out, open(OUT, "w"), indent=1)
    with_boom = [p for p in players if "boom" in p]
    with_boom.sort(key=lambda x: -x["boom"]["rate"])
    print(f"wrote {OUT}: {len(players)} draftable, {len(with_boom)} with 2025 series")
    for p in with_boom[:6]:
        print(f"  {p['name']:<22} {p['pos']} boom {p['boom']['k']}/{p['boom']['n']}"
              f" p90 {p['p90_week']} sd {p['weekly_sd']}")


if __name__ == "__main__":
    main()
