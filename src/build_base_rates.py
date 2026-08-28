#!/usr/bin/env python3
"""C2: hit and bust base rates by ADP band and position, with n and Wilson CIs.

Two independent tables, both computed - nothing imported from any document:

MARKET: for each season 2016-2025, FFC PPR ADP (12-team) gives every player a
positional ADP rank; nflverse weekly stats scored under THIS league's exact
table (6-pt passing TDs, full PPR) give the realized positional finish by
season total. Cells aggregate seasons by position x positional-ADP band.

LEAGUE: the same outcomes joined to this league's own 2,339 archive picks
(out/picks.csv) by round band - what OUR room's draft slots actually returned.

Definitions (stated here and in the artifact; the UI repeats them):
  hit12  = finished top-12 at the position by season total points
  hit24  = finished top-24
  bust36 = finished OUTSIDE the positional top-36 (includes injury wipeouts -
           a drafted season that returns nothing is a bust however it died)
Positions: QB/RB/WR/TE. K/DEF are excluded - their year-to-year finish is
noise this league already treats as floor-projected.

Needs the HISTORY cache (env HISTORY or the scratchpad default). The artifact
is committed, so rebuilds without the cache keep serving the committed table.

Run: python3 src/build_base_rates.py
"""
import csv
import datetime
import json
import math
import os
import re
from collections import defaultdict

from analyze_recency import HISTORY
from player_names import PlayerIdentityResolver

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "data", "base_rates.json")
PICKS = os.path.join(ROOT, "out", "picks.csv")
# LEAGUE-SIDE history runs 2013-2025: the LeagueLegacy archive covers all
# thirteen completed seasons and out/picks.csv carries every one of them.
# The MARKET side is capped at 2016 only where the FFC ADP cache starts;
# both windows are reported per table rather than assumed equal.
SEASONS = range(2013, 2026)
MARKET_SEASONS = range(2016, 2026)
# Era boundaries the archive states in 00_league/seasons.csv - pooling
# across them without a flag would mix formats that are not the same game.
ERAS = {"weeks13_playoffs_wk14": range(2013, 2021),
        "weeks14_playoffs_wk15": range(2021, 2026),
        "median_scoring": range(2025, 2026)}
POSITIONS = ("QB", "RB", "WR", "TE")
BANDS = [(1, 6, "pos1-6"), (7, 12, "pos7-12"), (13, 18, "pos13-18"),
         (19, 24, "pos19-24"), (25, 36, "pos25-36")]
ROUND_BANDS = [(1, 3, "rd1-3"), (4, 6, "rd4-6"), (7, 10, "rd7-10"),
               (11, 14, "rd11-14")]

# League-exact scoring, verified live against both league ids 2026-08-26
# (the same fact table tests/test_vor.py pins). Weekly-stat column -> points.
W = {"passing_yards": 0.04, "passing_tds": 6.0, "passing_interceptions": -1.0,
     "passing_2pt_conversions": 2.0,
     "rushing_yards": 0.1, "rushing_tds": 6.0, "rushing_2pt_conversions": 2.0,
     "receptions": 1.0, "receiving_yards": 0.1, "receiving_tds": 6.0,
     "receiving_2pt_conversions": 2.0,
     "sack_fumbles_lost": -2.0, "rushing_fumbles_lost": -2.0,
     "receiving_fumbles_lost": -2.0,
     "special_teams_tds": 6.0}


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 4), round(c + h, 4))


def season_finishes(year):
    """Return positional ranks by gsis id plus a fail-closed name resolver."""
    totals = defaultdict(float)
    pos_of = {}
    name_of = {}
    with open(os.path.join(HISTORY, f"spw_{year}.csv")) as fh:
        for r in csv.DictReader(fh):
            if r.get("season_type") != "REG" or r.get("position") not in POSITIONS:
                continue
            key = r["player_id"]
            pos_of[key] = r["position"]
            name_of[key] = r["player_display_name"]
            for col, w in W.items():
                v = r.get(col)
                if v:
                    try:
                        totals[key] += float(v) * w
                    except ValueError:
                        pass
    ranks = {}
    by_pos = defaultdict(list)
    for key, pts in totals.items():
        by_pos[pos_of[key]].append((pts, key))
    for pos, lst in by_pos.items():
        lst.sort(reverse=True)
        for i, (_, key) in enumerate(lst, 1):
            ranks[key] = i
    resolver = PlayerIdentityResolver([
        {"name": name_of[key], "pos": pos_of[key], "gsis_id": key}
        for key in totals])
    return ranks, resolver


def band_of(rank, bands):
    for lo, hi, name in bands:
        if lo <= rank <= hi:
            return name
    return None


def main():
    cells = {p: {b[2]: {"n": 0, "hit12": 0, "hit24": 0, "bust36": 0}
                 for b in BANDS} for p in POSITIONS}
    lg_cells = {p: {b[2]: {"n": 0, "hit12": 0, "hit24": 0, "bust36": 0}
                    for b in ROUND_BANDS} for p in POSITIONS}
    joined = unjoined = lg_joined = lg_unjoined = 0

    league_picks = defaultdict(list)   # season -> [(name, pos, round)]
    coverage = defaultdict(lambda: {"picks": 0, "franchises": set()})
    for r in csv.DictReader(open(PICKS)):
        try:
            season, rnd = int(r["season"]), int(r["round"])
        except (KeyError, ValueError):
            continue
        if season in SEASONS:
            coverage[season]["picks"] += 1
            coverage[season]["franchises"].add(r.get("member_name"))
        if season in SEASONS and r.get("pos") in POSITIONS:
            league_picks[season].append((r["player_name"], r["pos"], rnd))

    for year in MARKET_SEASONS:
        finishes, identity = season_finishes(year)
        ffc = json.load(open(os.path.join(HISTORY, f"ffc_ppr_{year}.json")))
        players = ffc["players"] if isinstance(ffc, dict) else ffc
        by_pos = defaultdict(list)
        for p in players:
            if p.get("position") in POSITIONS:
                by_pos[p["position"]].append(p)
        for pos, lst in by_pos.items():
            lst.sort(key=lambda x: x["adp"])
            for i, p in enumerate(lst, 1):
                band = band_of(i, BANDS)
                if band is None:
                    continue
                resolved = identity.resolve(p["name"], position=pos)
                fin = finishes.get(resolved.record["gsis_id"]) \
                    if resolved.record is not None else None
                if fin is None:
                    unjoined += 1     # drafted, produced zero recorded points
                    fin = 10 ** 6     # counts as the deepest possible bust
                else:
                    joined += 1
                c = cells[pos][band]
                c["n"] += 1
                c["hit12"] += fin <= 12
                c["hit24"] += fin <= 24
                c["bust36"] += fin > 36


    # LEAGUE table, its own loop over its own window. This used to be nested
    # inside the market loop, which silently capped the league history at
    # the market cache's 2016 start and discarded 2013-2015 - three seasons
    # of this league's own drafts that the archive has always carried.
    era_cells = {e: {"n": 0, "hit12": 0, "hit24": 0, "bust36": 0} for e in ERAS}
    for year in SEASONS:
        picks = league_picks.get(year, [])
        if not picks:
            continue
        finishes, identity = season_finishes(year)
        eras_of = [e for e, yrs in ERAS.items() if year in yrs]
        for name, pos, rnd in picks:
            band = band_of(rnd, ROUND_BANDS)
            if band is None:
                continue
            resolved = identity.resolve(name, position=pos)
            fin = finishes.get(resolved.record["gsis_id"]) \
                if resolved.record is not None else None
            if fin is None:
                lg_unjoined += 1
                fin = 10 ** 6
            else:
                lg_joined += 1
            for c in [lg_cells[pos][band]] + [era_cells[e] for e in eras_of]:
                c["n"] += 1
                c["hit12"] += fin <= 12
                c["hit24"] += fin <= 24
                c["bust36"] += fin > 36

    def finish(table):
        out = {}
        for pos, bands in table.items():
            out[pos] = {}
            for band, c in bands.items():
                if c["n"] == 0:
                    continue
                out[pos][band] = {"n": c["n"]}
                for m in ("hit12", "hit24", "bust36"):
                    k = c[m]
                    out[pos][band][m] = {
                        "k": k, "rate": round(k / c["n"], 4),
                        "ci95": wilson(k, c["n"]),
                    }
        return out

    artifact = {
        "provenance": {
            "generated": datetime.date.today().isoformat(),
            "league_seasons": "2013-2025 (all thirteen completed)",
            "market_seasons": "2016-2025 (FFC ADP cache starts 2016)",
            "market_adp": "FFC PPR 12-team (history cache)",
            "outcomes": ("nflverse weekly REG totals scored under the exact "
                         "league table (6-pt pass TD, full PPR), positional "
                         "rank by season total"),
            "league_picks": "out/picks.csv archive, joined by name|pos+season",
            "join": {"market_joined": joined, "market_unjoined_as_bust": unjoined,
                     "league_joined": lg_joined,
                     "league_unjoined_as_bust": lg_unjoined},
            "league_history_coverage": {
                "per_season": {str(y): {"picks": coverage[y]["picks"],
                                        "franchises":
                                        len(coverage[y]["franchises"])}
                               for y in sorted(coverage)},
                "survivorship_label": (
                    "LABELED, not restricted: a review note reports 2016-2021 "
                    "as survivorship-filtered (1-3 departed managers per "
                    "season). The archive itself shows all 12 franchises with "
                    "full drafts in every season used here, departed-manager "
                    "franchises included, so no manager-level gap is "
                    "detectable at the picks level; the counts above are the "
                    "computed evidence. The label stands, and converts to a "
                    "2022-2025 restriction, if the Yahoo 2014-2024 history "
                    "pull shows the archive was reconstructed incompletely."),
            },
        },
        "eras": {e: {"seasons": f"{min(y)}-{max(y)}",
                     "n": c["n"],
                     "hit12": {"k": c["hit12"],
                               "rate": round(c["hit12"] / c["n"], 4) if c["n"] else None,
                               "ci95": list(wilson(c["hit12"], c["n"]))},
                     "bust36": {"k": c["bust36"],
                                "rate": round(c["bust36"] / c["n"], 4) if c["n"] else None,
                                "ci95": list(wilson(c["bust36"], c["n"]))}}
                 for e, c, y in ((e, era_cells[e], ERAS[e]) for e in ERAS)},
        "era_note": ("league eras from the archive's own 00_league/seasons.csv: "
                     "13-week seasons with playoffs in week 14 through 2020, "
                     "14-week with playoffs in week 15 from 2021, and league-"
                     "median scoring only from 2025. Pooled league rates cross "
                     "these boundaries - the per-era rows are the honest cut"),
        "definitions": {
            "hit12": "finished top-12 at the position by season total points",
            "hit24": "finished top-24 at the position",
            "bust36": ("finished outside the positional top-36; a drafted "
                       "player with no recorded points counts as a bust"),
        },
        "market": finish(cells),
        "league": finish(lg_cells),
    }
    json.dump(artifact, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}: market joins {joined} (+{unjoined} zero-point busts), "
          f"league joins {lg_joined} (+{lg_unjoined})")
    for pos in POSITIONS:
        row = artifact["market"][pos].get("pos1-6")
        if row:
            print(f"  {pos} pos1-6: hit12 {row['hit12']['rate']:.0%} "
                  f"{row['hit12']['ci95']} n={row['n']}")


if __name__ == "__main__":
    main()
