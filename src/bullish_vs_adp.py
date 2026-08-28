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

from analyze_recency import HISTORY
from player_names import nflverse_roster_identity

# THE VERDICT IS REPORTED, NOT COMPUTED. The automated rule this script
# used to carry (BEATS ADP / UNDERPOWERED / NULL, derived from six
# interval checks plus a post-hoc minimum-detectable-effect search) was
# statistically unsound three ways: a post-hoc MDE comparison is not an
# equivalence test and cannot license any verdict about absence; the
# BEATS branch searched six cells (three bands x two hit depths) with no
# multiplicity control; and that branch was sign-blind, so a
# significantly HARMFUL tag would have read "BEATS ADP". The reviewed
# verdict below replaces the automation verbatim. cross_check() ties
# every number the text cites to the freshly computed cells - if the
# data moves, the run fails loudly so a stale verdict is never
# republished; the text itself only changes by review, never by code.
VERDICT = (
    "INCONCLUSIVE — incremental value over ADP remains unresolved in the "
    "RB/WR scope after suspending the non-discriminating TE matrix. Among "
    "positional ADP ranks 1-12, tagged players finished top-12 in 22/35 cases "
    "(62.9%) vs 86/164 (52.4%), +10.4pp, 95% CI [-7.3, +28.2], p=0.261. "
    "Restricting the earlier mixed RB/WR/TE scope to RB/WR reduced the "
    "top-band sample from 300 to 199 players (43 to 35 tagged) and widened "
    "the interval from 31.0pp to 35.5pp. That is the expected direction when "
    "a non-discriminating group is removed: fewer observations mean more "
    "uncertainty. Because the verdict held while uncertainty increased, the "
    "unresolved limitation is the ADP-gated design, not one individual "
    "criterion. The current interval permits harm and useful lift alike. "
    "Only three tags occur "
    "at ranks 13-24 and none at 25-48, so those regions are not identifiable. "
    "Coarse bands do not adjust for exact ADP, position, season, or repeated "
    "players. Tags stay display-only pending continuous-ADP, season-held-out "
    "testing.")

VERDICT_BASIS = (
    "reported, fixed by review 2026-08-28 - not computed. Removing the "
    "non-discriminating TE matrix reduced the point estimate and widened the "
    "interval because the restricted scope has fewer observations; it did not "
    "rescue the result. That points to the ADP gate rather than one criterion. "
    "The prior "
    "three-state automation was removed as unsound: a post-hoc minimum-"
    "detectable-effect comparison is not an equivalence test, the "
    "significance branch searched six cells without multiplicity "
    "control, and its BEATS label was sign-blind. Every figure the "
    "current-scope figure the verdict cites is cross-checked against the "
    "computed cells at build time; the prior-scope comparison is pinned to "
    "the cited pre-suspension artifact. A mismatch fails the build for "
    "re-review instead of regenerating the text")

# the figures the fixed verdict cites, in the artifact's own units -
# cross_check() recomputes each from the cells and refuses to publish on
# any mismatch
VERDICT_CITES = {
    "pos1-12 tagged k/n": (22, 35),
    "pos1-12 tagged rate pct": 62.9,
    "pos1-12 untagged k/n": (86, 164),
    "pos1-12 untagged rate pct": 52.4,
    "pos1-12 diff pp": 10.4,
    "pos1-12 diff ci95 pp": (-7.3, 28.2),
    "pos1-12 p two-sided": 0.261,
    "pos1-12 total n": 199,
    "pos1-12 diff ci95 width pp": 35.5,
    "pos13-24 tagged n": 3,
    "pos25-48 tagged n": 0,
}

PRIOR_SCOPE_REFERENCE = {
    "scope": ["RB", "WR", "TE"],
    "top_band_total_n": 300,
    "top_band_tagged_n": 43,
    "diff_ci95_width_pp": 31.0,
    "source_commit": "242ae6b284a82e81f575eb42805bcf638a65ebbf",
    "source_artifact": "out/data/bullish_vs_adp.json",
    "source_content_sha256":
        "405cac582f5b953d9ba46a53b670123c8870892b37dc79bdfb2e5ffe2ee172b4",
}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "data", "bullish_vs_adp.json")
YEARS = list(range(2017, 2026))
POSITIONS = ("RB", "WR")                # live tag scope after TE suspension
BANDS = [(1, 12, "pos1-12"), (13, 24, "pos13-24"), (25, 48, "pos25-48")]

W = {"passing_yards": 0.04, "passing_tds": 6.0, "passing_interceptions": -1.0,
     "passing_2pt_conversions": 2.0,
     "rushing_yards": 0.1, "rushing_tds": 6.0, "rushing_2pt_conversions": 2.0,
     "receptions": 1.0, "receiving_yards": 0.1, "receiving_tds": 6.0,
     "receiving_2pt_conversions": 2.0,
     "sack_fumbles_lost": -2.0, "rushing_fumbles_lost": -2.0,
     "receiving_fumbles_lost": -2.0, "special_teams_tds": 6.0}


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
    """gsis id -> identity plus league-scored totals/opportunities, REG."""
    agg = defaultdict(lambda: defaultdict(float))
    with open(os.path.join(HISTORY, f"spw_{year}.csv")) as fh:
        for r in csv.DictReader(fh):
            if r.get("season_type") != "REG" or r.get("position") not in POSITIONS:
                continue
            a = agg[r["player_id"]]
            a["name"] = r["player_display_name"]
            a["pos"] = r["position"]
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


def season_identity(year):
    """Resolve that season's market names against nflverse roster identity.

    Roster snapshots retain players who produced no stats, so a drafted
    injury/holdout still enters the outcome ledger as a bust.  Stable GSIS ids
    also carry an actual player across a recorded position change without
    transferring a father's history to his son.
    """
    with open(os.path.join(HISTORY, f"roster_{year}.csv")) as roster_fh, \
         open(os.path.join(HISTORY, f"spw_{year}.csv")) as stats_fh:
        return nflverse_roster_identity(
            csv.DictReader(roster_fh), positions=POSITIONS,
            stat_rows=csv.DictReader(stats_fh))


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
        current_identity = season_identity(year)
        ffc = json.load(open(os.path.join(HISTORY, f"ffc_ppr_{year}.json")))
        by_pos = defaultdict(list)
        for p in sorted(ffc["players"], key=lambda x: x["adp"]):
            if p["position"] in POSITIONS:
                by_pos[p["position"]].append(p)
        # finishing ranks under league-exact scoring
        rank = {}
        for pos in POSITIONS:
            pool = sorted(((a["pts"], k) for k, a in cur.items()
                           if a["pos"] == pos), reverse=True)
            for i, (_pts, k) in enumerate(pool, 1):
                rank[k] = i
        for pos, lst in by_pos.items():
            # the criterion thresholds are percentiles of THIS season's own
            # prior-year pool - computed, never carried between seasons
            resolved = [current_identity.resolve(
                            p["name"], position=pos,
                            prefer_latest_draft_year=True).record
                        for p in lst[:48]]
            cand = [prior[r["gsis_id"]] for r in resolved
                    if r is not None and r["gsis_id"] in prior
                    and prior[r["gsis_id"]]["pos"] == pos]
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
                current = current_identity.resolve(
                    p["name"], position=pos,
                    prefer_latest_draft_year=True).record
                gsis_id = current["gsis_id"] if current is not None else None
                a = prior.get(gsis_id)
                if not a or a["pos"] != pos or a["games"] < 8:
                    continue        # no prior-season sample: criteria unknown
                touches = a["targets"] + a["carries"]
                tagged = (touches / a["games"] >= t_opp and touches >= 40
                          and a["pts"] / touches >= t_eff)
                # Positional hit rates require the outcome and ADP cohorts to
                # agree. Stable identity alone must not turn a finish at one
                # position into a hit at another.
                fr = rank.get(gsis_id, 999) \
                    if gsis_id in cur and cur[gsis_id]["pos"] == pos else 999
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

    # the cross-check: every figure the fixed verdict cites, recomputed
    # from the cells this run just produced. A mismatch means the data
    # moved under the reviewed text - fail the build for re-review, never
    # regenerate the verdict in code.
    top = within["pos1-12"]
    l12 = top["lift_hit12"]
    tk, tn = top["tagged"]["hit12"]["k"], top["tagged"]["n"]
    uk, un = top["untagged"]["hit12"]["k"], top["untagged"]["n"]
    computed = {
        "pos1-12 tagged k/n": (tk, tn),
        "pos1-12 tagged rate pct": round(100.0 * tk / tn, 1) if tn else None,
        "pos1-12 untagged k/n": (uk, un),
        "pos1-12 untagged rate pct": round(100.0 * uk / un, 1) if un else None,
        "pos1-12 diff pp": round(l12["diff"] * 100, 1) if l12 else None,
        "pos1-12 diff ci95 pp": (round(l12["diff_ci95"][0] * 100, 1),
                                 round(l12["diff_ci95"][1] * 100, 1))
        if l12 else None,
        "pos1-12 p two-sided": round(l12["p_two_sided"], 3) if l12 else None,
        "pos1-12 total n": tn + un,
        "pos1-12 diff ci95 width pp": round(
            (l12["diff_ci95"][1] - l12["diff_ci95"][0]) * 100, 1)
        if l12 else None,
        "pos13-24 tagged n": within["pos13-24"]["tagged"]["n"],
        "pos25-48 tagged n": within["pos25-48"]["tagged"]["n"],
    }
    drift = [(k, VERDICT_CITES[k], computed[k])
             for k in VERDICT_CITES if computed[k] != VERDICT_CITES[k]]
    if drift:
        print("VERDICT CROSS-CHECK FAILED - the data no longer matches the "
              "reviewed verdict text. NOT publishing. Re-review the verdict; "
              "do not regenerate it in code.")
        for k, want, got in drift:
            print(f"  {k}: verdict cites {want}, computed {got}")
        raise SystemExit(1)

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
        "verdict": VERDICT,
        "verdict_basis": VERDICT_BASIS,
        "verdict_cites": {k: list(v) if isinstance(v, tuple) else v
                          for k, v in VERDICT_CITES.items()},
        "scope_change": {
            "prior": PRIOR_SCOPE_REFERENCE,
            "current": {
                "scope": list(POSITIONS),
                "top_band_total_n": tn + un,
                "top_band_tagged_n": tn,
                "diff_ci95_width_pp": computed[
                    "pos1-12 diff ci95 width pp"],
            },
            "interpretation": (
                "Removing the non-discriminating TE group left fewer observations "
                "and therefore widened uncertainty. The INCONCLUSIVE verdict "
                "holding under that expected widening points to the ADP-gated "
                "design rather than one individual tag criterion."),
        },
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
    print("verdict cross-check: all cited figures match the computed cells")
    print("VERDICT (reported, fixed by review):", VERDICT)


if __name__ == "__main__":
    main()
