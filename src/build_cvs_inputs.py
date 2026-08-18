#!/usr/bin/env python3
"""CVS input shards - volatility, TD rates, and 2026 SOS from literal columns.

Fetches two nflverse assets (stdlib only, no pandas) and writes three
provenance-stamped shards to out/data/. Nothing here is modelled: every
number is a literal column or a documented arithmetic combination of
literal columns, per the house rule.

  volatility_2025.json  weekly PPR distribution per player: mean, sd,
                        boom/bust rates, p90/p25 - the third CVS output
  td_rates_2025.json    2025 TD per opportunity + positional outlier flags -
                        feeds the Regression Cross-Map against Walter
  sos_2026.json         2026 schedule x 2025 PPR points allowed by each
                        defense vs each position; season and weeks 15-17
                        slices - the schedule factor and the playoff lens

Run after the engine on draft morning:
    python3 src/build_cvs_inputs.py
"""
import csv
import datetime
import gzip
import io
import json
import os
import statistics
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "data")

SPW_URL = ("https://github.com/nflverse/nflverse-data/releases/download/"
           "stats_player/stats_player_week_2025.csv.gz")
SCHED_URL = ("https://github.com/nflverse/nflverse-data/releases/download/"
             "schedules/games.csv")

# nflverse team codes -> this repo's adp.json codes
ALIAS = {"LA": "LAR"}


def canon(team):
    return ALIAS.get(team, team)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ytfl-hub"})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
    if url.endswith(".gz"):
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", errors="replace")


def pctl(sorted_vals, q):
    if not sorted_vals:
        return None
    i = (len(sorted_vals) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(sorted_vals) - 1)
    return round(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (i - lo), 2)


def main():
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    spw = list(csv.DictReader(io.StringIO(fetch(SPW_URL))))
    sched = list(csv.DictReader(io.StringIO(fetch(SCHED_URL))))
    reg = [r for r in spw if r["season_type"] == "REG"]

    # ---- volatility: weekly PPR distribution per player
    weekly = {}
    for r in reg:
        if r["position_group"] not in ("QB", "RB", "WR", "TE"):
            continue
        key = (r["player_id"], r["player_display_name"], r["position_group"])
        try:
            pts = float(r["fantasy_points_ppr"] or 0)
        except ValueError:
            continue
        weekly.setdefault(key, []).append(pts)
    vol = []
    for (gsis, name, pos), pts in weekly.items():
        if len(pts) < 4:
            continue
        s = sorted(pts)
        vol.append({
            "gsis_id": gsis, "name": name, "pos": pos, "games": len(pts),
            "ppr_mean": round(statistics.mean(pts), 2),
            "ppr_sd": round(statistics.stdev(pts), 2),
            "boom_rate": round(sum(1 for x in pts if x >= 20) / len(pts), 3),
            "bust_rate": round(sum(1 for x in pts if x < 5) / len(pts), 3),
            "p90": pctl(s, 0.90), "p25": pctl(s, 0.25),
        })
    json.dump({"players": sorted(vol, key=lambda x: -x["ppr_mean"]),
               "provenance": {
                   "source": "nflverse stats_player_week 2025 (CC-BY-4.0)",
                   "url": SPW_URL, "fetched_at": now,
                   "basis": ("weekly fantasy_points_ppr, REG season, min 4 "
                             "games; boom >=20, bust <5, p90/p25 by linear "
                             "interpolation; literal column arithmetic only")}},
              open(os.path.join(OUT, "volatility_2025.json"), "w"), indent=1)

    # ---- TD rates: TD per opportunity, positional outlier deciles
    agg = {}
    for r in reg:
        pos = r["position_group"]
        if pos not in ("QB", "RB", "WR", "TE"):
            continue
        key = (r["player_id"], r["player_display_name"], pos)
        a = agg.setdefault(key, {"tds": 0, "opps": 0})
        try:
            if pos == "QB":
                a["tds"] += int(float(r["passing_tds"] or 0))
                a["opps"] += int(float(r["attempts"] or 0))
            else:
                a["tds"] += (int(float(r["rushing_tds"] or 0))
                             + int(float(r["receiving_tds"] or 0)))
                a["opps"] += (int(float(r["carries"] or 0))
                              + int(float(r["targets"] or 0)))
        except ValueError:
            continue
    MIN_OPPS = {"QB": 150, "RB": 100, "WR": 60, "TE": 50}
    rates = []
    for (gsis, name, pos), a in agg.items():
        if a["opps"] < MIN_OPPS[pos]:
            continue
        rates.append({"gsis_id": gsis, "name": name, "pos": pos,
                      "tds": a["tds"], "opportunities": a["opps"],
                      "td_rate": round(a["tds"] / a["opps"], 4)})
    for pos in ("QB", "RB", "WR", "TE"):
        grp = sorted([x for x in rates if x["pos"] == pos],
                     key=lambda x: x["td_rate"])
        n = len(grp)
        for i, x in enumerate(grp):
            x["pos_percentile"] = round(i / max(1, n - 1), 3)
            x["outlier"] = ("high" if x["pos_percentile"] >= 0.9 else
                            "low" if x["pos_percentile"] <= 0.1 else None)
    json.dump({"players": sorted(rates, key=lambda x: -x["td_rate"]),
               "provenance": {
                   "source": "nflverse stats_player_week 2025 (CC-BY-4.0)",
                   "url": SPW_URL, "fetched_at": now,
                   "basis": ("2025 REG TDs per opportunity: QB = passing TDs / "
                             "attempts; RB/WR/TE = (rush+rec TDs) / (carries + "
                             "targets); outliers = top/bottom decile within "
                             "position at minimum-opportunity thresholds")}},
              open(os.path.join(OUT, "td_rates_2025.json"), "w"), indent=1)

    # ---- SOS 2026: 2025 PPR allowed per game by defense vs position,
    # mapped onto each team's 2026 schedule; season + weeks 15-17 slices
    allowed = {}
    def_games = {}
    for r in reg:
        pos = r["position_group"]
        if pos not in ("QB", "RB", "WR", "TE"):
            continue
        d = canon(r["opponent_team"])
        try:
            allowed[(d, pos)] = allowed.get((d, pos), 0.0) + float(
                r["fantasy_points_ppr"] or 0)
        except ValueError:
            continue
        def_games.setdefault(d, set()).add(r["game_id"])
    per_game = {k: v / max(1, len(def_games.get(k[0], set())))
                for k, v in allowed.items()}

    opps_2026 = {}
    for g in sched:
        if g["season"] != "2026" or g["game_type"] != "REG":
            continue
        wk = int(g["week"])
        home, away = canon(g["home_team"]), canon(g["away_team"])
        opps_2026.setdefault(home, []).append((wk, away))
        opps_2026.setdefault(away, []).append((wk, home))
    teams = sorted(opps_2026)
    sos = []
    for t in teams:
        row = {"team": t, "opponents": sorted(opps_2026[t])}
        for pos in ("QB", "RB", "WR", "TE"):
            season = [per_game.get((o, pos)) for _, o in opps_2026[t]]
            season = [x for x in season if x is not None]
            playoff = [per_game.get((o, pos)) for wk, o in opps_2026[t]
                       if wk in (15, 16, 17)]
            playoff = [x for x in playoff if x is not None]
            row[f"sos_{pos.lower()}"] = round(statistics.mean(season), 2) if season else None
            row[f"sos_{pos.lower()}_wk15_17"] = (round(statistics.mean(playoff), 2)
                                                 if playoff else None)
        sos.append(row)
    # ranks: 1 = easiest schedule (most points allowed to that position)
    for pos in ("qb", "rb", "wr", "te"):
        for key in (f"sos_{pos}", f"sos_{pos}_wk15_17"):
            vals = sorted([r[key] for r in sos if r[key] is not None], reverse=True)
            for r in sos:
                r[key + "_rank"] = (vals.index(r[key]) + 1) if r[key] in vals else None
    json.dump({"teams": sos,
               "provenance": {
                   "source": ("nflverse schedules (2026) x nflverse "
                              "stats_player_week 2025 (CC-BY-4.0)"),
                   "url": SCHED_URL, "fetched_at": now,
                   "basis": ("2025 REG PPR points allowed per game by each "
                             "defense to each position, averaged over each "
                             "team's 2026 opponents; weeks 15-17 slice "
                             "separate; rank 1 = most points allowed = "
                             "easiest. Prior-season defense predicts weakly - "
                             "this factor carries a low default weight and "
                             "says so")}},
              open(os.path.join(OUT, "sos_2026.json"), "w"), indent=1)

    print(f"volatility: {len(vol)} players | td_rates: {len(rates)} players | "
          f"sos: {len(sos)} teams")


if __name__ == "__main__":
    main()
