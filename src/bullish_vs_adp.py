#!/usr/bin/env python3
"""Carryover 3: does the reconciled BULLISH tag beat ADP alone?

Anthony's Phase A conclusion is the reason this test exists: the tag's
candidate pool is gated on fantasy ADP, so by construction the engine can
only re-rank players the market has already surfaced. That makes it a
confirmation device unless it demonstrably adds information ADP does not
carry. This script asks that question the only honest way available -
BACKTEST the criteria, not the 2026 tags (2026 outcomes do not exist).

METHOD, and its limits, stated first:
  For each season 2017-2025 we rebuild the two criteria that CAN be
  reconstructed from the cached history for a prior season and scored
  under league-exact rules - opportunity (prior-season targets or carries
  per game at or above the pool's p75) and efficiency (prior-season
  points per opportunity at or above the pool's p75) - then ask whether a
  player meeting BOTH finishes top-12 / top-24 at his position.
  The comparison is like-for-like: within each preseason ADP band, the
  tagged players' hit rate vs the untagged players' hit rate in the SAME
  band. A tag that only repeats ADP shows no within-band lift.

  This is a PROXY for the shipped 2026 matrix, not the matrix itself.
  The live engine uses route participation, first-read share, inside-5
  equity, implied totals, and line quality - none of which exist as a
  clean per-season history in this cache. What survives the rebuild is
  the OPPORTUNITY + EFFICIENCY spine that every criterion set shares.
  The limitation is printed with the result and carried in the artifact;
  a lift here is evidence for the spine, not proof of the full matrix,
  and a null here is evidence against it.

Run: python3 src/bullish_vs_adp.py
Output: out/data/bullish_vs_adp.json
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
OUT = os.path.join(ROOT, "out", "data", "bullish_vs_adp.json")
YEARS = list(range(2017, 2026))
POSITIONS = ("RB", "WR", "TE")          # the tag's own skill scope
BANDS = [(1, 12, "pos1-12"), (13, 24, "pos13-24"), (25, 48, "pos25-48")]

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


def wilson(k, n):
    if n == 0:
        return None
    z = 1.96
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def two_prop(k1, n1, k2, n2):
    """Two-proportion z-test and the difference's 95% interval."""
    if not n1 or not n2:
        return None
    p1, p2 = k1 / n1, k2 / n2
    pool = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se if se else 0.0
    sed = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    return {"diff": round(p1 - p2, 4),
            "diff_ci95": [round(p1 - p2 - 1.96 * sed, 4),
                          round(p1 - p2 + 1.96 * sed, 4)],
            "z": round(z, 3),
            "p_two_sided": round(math.erfc(abs(z) / math.sqrt(2)), 4)}


def season(year):
    """name|pos -> league-scored totals plus opportunity counts, REG."""
    agg = defaultdict(lambda: defaultdict(float))
    with open(os.path.join(HISTORY, f"spw_{year}.csv")) as fh:
        for r in csv.DictReader(fh):
            if r.get("season_type") != "REG" or r.get("position") not in POSITIONS:
                continue
            a = agg[norm(r["player_display_name"]) + "|" + r["position"]]
            a["games"] += 1
            for col in ("targets", "carries"):
                v = r.get(col)
                if v:
                    try:
                        a[col] += float(v)
                    except ValueError:
                        pass
            for col, w in W.items():
                v = r.get(col)
                if v:
                    try:
                        a["pts"] += float(v) * w
                    except ValueError:
                        pass
    return agg


def pctile(vals, q):
    vals = sorted(vals)
    if not vals:
        return None
    i = max(0, min(len(vals) - 1, int(round(q * (len(vals) - 1)))))
    return vals[i]


def main():
    stats = {y: season(y) for y in YEARS}
    stats[2016] = season(2016)
    rows = []                       # one per player-season in an ADP band
    for year in YEARS:
        prior = stats[year - 1]
        cur = stats[year]
        ffc = json.load(open(os.path.join(HISTORY, f"ffc_ppr_{year}.json")))
        by_pos = defaultdict(list)
        for p in sorted(ffc["players"], key=lambda x: x["adp"]):
            if p["position"] in POSITIONS:
                by_pos[p["position"]].append(p)
        # finishing ranks under league-exact scoring
        rank = {}
        for pos in POSITIONS:
            pool = sorted(((a["pts"], k) for k, a in cur.items()
                           if k.endswith("|" + pos)), reverse=True)
            for i, (_pts, k) in enumerate(pool, 1):
                rank[k] = i
        for pos, lst in by_pos.items():
            # the criterion thresholds are percentiles of THIS season's own
            # prior-year pool - computed, never carried between seasons
            cand = [prior[norm(p["name"]) + "|" + pos] for p in lst[:48]]
            opp = [(a["targets"] + a["carries"]) / a["games"]
                   for a in cand if a["games"] >= 8]
            eff = [a["pts"] / (a["targets"] + a["carries"])
                   for a in cand if a["games"] >= 8
                   and (a["targets"] + a["carries"]) >= 40]
            t_opp, t_eff = pctile(opp, 0.75), pctile(eff, 0.75)
            if t_opp is None or t_eff is None:
                continue
            for i, p in enumerate(lst[:48], 1):
                band = next((b[2] for b in BANDS if b[0] <= i <= b[1]), None)
                if band is None:
                    continue
                key = norm(p["name"]) + "|" + pos
                a = prior.get(key)
                if not a or a["games"] < 8:
                    continue        # no prior-season sample: criteria unknown
                touches = a["targets"] + a["carries"]
                tagged = (touches / a["games"] >= t_opp and touches >= 40
                          and a["pts"] / touches >= t_eff)
                fr = rank.get(key, 999)
                rows.append({"year": year, "pos": pos, "band": band,
                             "adp_rank": i, "tagged": bool(tagged),
                             "hit12": fr <= 12, "hit24": fr <= 24})

    def agg(sel):
        k12 = sum(1 for r in sel if r["hit12"])
        k24 = sum(1 for r in sel if r["hit24"])
        n = len(sel)
        return {"n": n,
                "hit12": {"k": k12, "rate": round(k12 / n, 4) if n else None,
                          "ci95": wilson(k12, n)},
                "hit24": {"k": k24, "rate": round(k24 / n, 4) if n else None,
                          "ci95": wilson(k24, n)}}

    within = {}
    for _lo, _hi, band in BANDS:
        tg = [r for r in rows if r["band"] == band and r["tagged"]]
        un = [r for r in rows if r["band"] == band and not r["tagged"]]
        a_t, a_u = agg(tg), agg(un)
        within[band] = {
            "tagged": a_t, "untagged": a_u,
            "lift_hit12": two_prop(a_t["hit12"]["k"], a_t["n"],
                                   a_u["hit12"]["k"], a_u["n"]),
            "lift_hit24": two_prop(a_t["hit24"]["k"], a_t["n"],
                                   a_u["hit24"]["k"], a_u["n"])}

    tg_all = [r for r in rows if r["tagged"]]
    un_all = [r for r in rows if not r["tagged"]]
    a_t, a_u = agg(tg_all), agg(un_all)
    pooled = {"tagged": a_t, "untagged": a_u,
              "lift_hit12": two_prop(a_t["hit12"]["k"], a_t["n"],
                                     a_u["hit12"]["k"], a_u["n"]),
              "lift_hit24": two_prop(a_t["hit24"]["k"], a_t["n"],
                                     a_u["hit24"]["k"], a_u["n"])}

    # the verdict is derived, never asserted: a real edge means the
    # within-band difference interval excludes zero somewhere
    sig = [b for b, v in within.items()
           for key in ("lift_hit12", "lift_hit24")
           if v[key] and (v[key]["diff_ci95"][0] > 0 or v[key]["diff_ci95"][1] < 0)]
    verdict = ("BEATS ADP within band" if sig else
               "NULL - no within-band edge over ADP alone")

    out = {
        "provenance": {
            "generated": datetime.date.today().isoformat(),
            "question": ("does the tag add information ADP does not already "
                         "carry? Phase A: the fantasy-ADP gate makes the tag "
                         "a confirmation device by construction unless it "
                         "shows within-band lift"),
            "method": ("per season 2017-2025, rebuild the opportunity + "
                       "efficiency spine from the PRIOR season (per-game "
                       "touches >= pool p75 and points per touch >= pool "
                       "p75, thresholds recomputed per season and position), "
                       "then compare tagged vs untagged hit rates WITHIN "
                       "each preseason ADP band"),
            "scoring": "league-exact (full PPR, 6-pt pass TD)",
            "limitation": ("PROXY for the shipped 2026 matrix: route "
                           "participation, first-read share, inside-5 equity, "
                           "implied totals and line quality have no clean "
                           "per-season history in this cache. What is tested "
                           "is the opportunity+efficiency spine common to "
                           "every criterion set - a lift is evidence for the "
                           "spine, not proof of the full matrix; a null is "
                           "evidence against it"),
            "positions": list(POSITIONS),
            "seasons": f"{YEARS[0]}-{YEARS[-1]}",
        },
        "within_band": within,
        "pooled": pooled,
        "verdict": verdict,
        "significant_cells": sig,
        # the Phase A concern, quantified: if nearly every tag lands on a
        # player ADP already ranks at the top, the tag is confirming the
        # market rather than adding to it, whatever the pooled rates say
        "concentration": {
            "tagged_by_band": {b: within[b]["tagged"]["n"] for _l, _h, b in BANDS},
            "share_in_top12_band": round(
                within["pos1-12"]["tagged"]["n"] / len(tg_all), 4)
            if tg_all else None,
            "note": ("the pooled tagged-vs-untagged gap is dominated by this "
                     "concentration - it measures ADP, not the tag. Only the "
                     "within-band rows above test the tag itself"),
        },
    }
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}")
    print(f"pooled: tagged {a_t['hit12']['k']}/{a_t['n']} "
          f"({a_t['hit12']['rate']}) vs untagged {a_u['hit12']['k']}/{a_u['n']} "
          f"({a_u['hit12']['rate']}) top-12")
    for band, v in within.items():
        l12 = v["lift_hit12"]
        if not l12:
            print(f"  {band:<10} no tagged players in this band "
                  f"(untagged n={v['untagged']['n']}) - no comparison possible")
            continue
        print(f"  {band:<10} top12 tagged {v['tagged']['hit12']['rate']} "
              f"(n={v['tagged']['n']}) vs untagged "
              f"{v['untagged']['hit12']['rate']} (n={v['untagged']['n']}) "
              f"diff {l12['diff']} CI {l12['diff_ci95']} p={l12['p_two_sided']}")
    c = out["concentration"]
    print(f"concentration: {c['share_in_top12_band']} of tags land in the "
          f"pos1-12 ADP band ({c['tagged_by_band']})")
    print("VERDICT:", verdict)


if __name__ == "__main__":
    main()
