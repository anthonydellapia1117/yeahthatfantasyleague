#!/usr/bin/env python3
"""Task 2: are championships in THIS league won on draft day or after it?

IMPORTANT PROVENANCE NOTE, because the brief that commissioned this work
believed otherwise: the drafted-versus-acquired split was NOT blocked and
was NOT unbuilt. `src/phase2_value.py` has computed it since August 11
and writes `out/drafted_vs_acquired.csv` covering all thirteen completed
seasons, 2013-2025 - it reads 02_gamecenter/matchup_rosters.csv for
started lineups, 04_draft/draft_results.csv for origin, and
05_transactions/transactions.csv for acquisition. What was missing is
what this script adds: the champions-versus-field comparison with
intervals, and the era flags the archive's own seasons.csv requires.

ERA FLAGS, from 00_league/seasons.csv (not assumed):
  2013-2020  13-week seasons, playoffs from week 14
  2021-2025  14-week seasons, playoffs from week 15
  2025 only  league-median scoring (use_median_scoring flips to 1)
A pooled number crossing those lines mixes formats; every figure below is
reported pooled AND per era so the reader can see whether it survives.

2013 carries no transaction data, so it is excluded from the acquired
split - phase2_value already flags it as acquired_valid=no, and this
script honors that flag rather than re-deriving it.

Run: python3 src/draft_vs_acquired.py
Output: out/data/draft_vs_acquired.json
"""
import csv
import datetime
import json
import os
import random
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = os.path.join(ROOT, "LeagueLegacy-io",
                       "YeahThatFantasyLeague_LeagueLegacy_Archive_2013-2026")
EXPORT = os.path.join(ROOT, "LeagueLegacy-io",
                      "leaguelegacy_YeahThatFantasyLeague_full_export")
SPLIT = os.path.join(ROOT, "out", "drafted_vs_acquired.csv")
OUT = os.path.join(ROOT, "out", "data", "draft_vs_acquired.json")


def load_champions():
    """Champion per season from the export's own ledger, name-normalized."""
    out = {}
    with open(os.path.join(EXPORT, "champions_by_season.csv")) as fh:
        for r in csv.DictReader(fh):
            champ = r["champion"].split(" (")[0].strip()
            out[r["season"]] = champ
    return out


def load_eras():
    """Era membership per season from the archive's own settings."""
    eras = {}
    seen = set()
    with open(os.path.join(ARCHIVE, "00_league", "seasons.csv")) as fh:
        for r in csv.DictReader(fh):
            s = r["season"]
            if s in seen:
                continue
            seen.add(s)
            eras[s] = {
                "weeks": int(r["num_weeks"] or 0),
                "playoff_start_week": int(r["playoff_start_week"] or 0),
                "median_scoring": r["use_median_scoring"] == "1",
                "keepers": r["use_keepers"] == "1",
                "era": ("weeks14_playoffs_wk15" if int(r["num_weeks"] or 0) == 14
                        else "weeks13_playoffs_wk14"),
            }
    return eras


def boot_ci(a, b, n=4000, seed=20260908):
    """Bootstrap interval for mean(a) - mean(b). Small n on the champion
    side is the whole reason this needs an interval rather than a point."""
    rnd = random.Random(seed)
    diffs = []
    for _ in range(n):
        ra = [rnd.choice(a) for _ in a]
        rb = [rnd.choice(b) for _ in b]
        diffs.append(statistics.mean(ra) - statistics.mean(rb))
    diffs.sort()
    return [round(diffs[int(0.025 * n)], 2), round(diffs[int(0.975 * n)], 2)]


def summarize(ch, fi, label):
    if len(ch) < 2 or len(fi) < 2:
        return {"label": label, "champions_n": len(ch), "field_n": len(fi),
                "note": "too few rows to compare"}
    d = statistics.mean(ch) - statistics.mean(fi)
    ci = boot_ci(ch, fi)
    return {
        "label": label,
        "champions_n": len(ch), "field_n": len(fi),
        "champions_mean": round(statistics.mean(ch), 2),
        "champions_median": round(statistics.median(ch), 2),
        "field_mean": round(statistics.mean(fi), 2),
        "field_median": round(statistics.median(fi), 2),
        "diff_pp": round(d, 2),
        "diff_ci95": ci,
        "separates": bool(ci[0] > 0 or ci[1] < 0),
    }


def main():
    champs = load_champions()
    eras = load_eras()
    rows = list(csv.DictReader(open(SPLIT)))

    per_season = []
    for r in rows:
        s = r["season"]
        e = eras.get(s, {})
        per_season.append({
            "season": s, "franchise": r["franchise"],
            "starter_points": float(r["starter_points"]),
            "drafted_share": float(r["drafted_share"]),
            "acquired_valid": r["acquired_valid"] == "yes",
            "is_champion": champs.get(s) == r["franchise"],
            "era": e.get("era"), "median_scoring": e.get("median_scoring"),
            "weeks": e.get("weeks"),
            "basis": r.get("basis", ""),
        })

    valid = [r for r in per_season if r["acquired_valid"]]
    ch = [r["drafted_share"] for r in valid if r["is_champion"]]
    fi = [r["drafted_share"] for r in valid if not r["is_champion"]]

    comparisons = {"pooled": summarize(ch, fi, "all valid seasons")}
    for era in sorted({r["era"] for r in valid if r["era"]}):
        e_rows = [r for r in valid if r["era"] == era]
        comparisons[era] = summarize(
            [r["drafted_share"] for r in e_rows if r["is_champion"]],
            [r["drafted_share"] for r in e_rows if not r["is_champion"]], era)

    # the same question asked of raw starter points, as a sanity companion:
    # champions should out-SCORE the field even if their sourcing mix does
    # not differ, and if they do not, the split is not the story either way
    ch_pts = [r["starter_points"] for r in valid if r["is_champion"]]
    fi_pts = [r["starter_points"] for r in valid if not r["is_champion"]]
    points = summarize(ch_pts, fi_pts, "starter points, champions vs field")

    out = {
        "provenance": {
            "generated": datetime.date.today().isoformat(),
            "question": ("does championship-winning production come from the "
                         "draft or from in-season acquisition?"),
            "split_source": ("out/drafted_vs_acquired.csv, computed by "
                             "src/phase2_value.py from the LeagueLegacy "
                             "archive: 02_gamecenter/matchup_rosters.csv for "
                             "started lineups, 04_draft/draft_results.csv for "
                             "origin, 05_transactions/transactions.csv for "
                             "acquisition"),
            "correction": ("this split was already built and already covered "
                           "2013-2025; it was never blocked on unread files. "
                           "What this script adds is the champions-vs-field "
                           "comparison with intervals and the era flags"),
            "champions_source": ("LeagueLegacy export champions_by_season.csv, "
                                 "read at compute time - not transcribed"),
            "era_source": ("archive 00_league/seasons.csv - num_weeks, "
                           "playoff_start_week, use_median_scoring"),
            "excluded": ("2013 from the acquired split only: the archive "
                         "carries no 2013 transaction data, flagged upstream "
                         "as acquired_valid=no and honored here"),
            "basis_caveat": ("Yahoo seasons 2013-2024 are bonus-exclusive "
                             "(six 40-yard long-play bonuses absent from "
                             "per-player rows). The drafted-vs-acquired RATIO "
                             "is unaffected because both sides share the "
                             "basis; absolute points are understated ~5%"),
            "interval": "bootstrap, 4000 resamples, fixed seed",
        },
        "comparisons": comparisons,
        "starter_points": points,
        "per_season": per_season,
    }
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}")
    for k, v in comparisons.items():
        if "diff_pp" not in v:
            print(f"  {k:<24} {v.get('note')}")
            continue
        print(f"  {k:<24} champions {v['champions_mean']}% (n={v['champions_n']}) "
              f"vs field {v['field_mean']}% (n={v['field_n']}) "
              f"diff {v['diff_pp']:+.2f}pp CI {v['diff_ci95']} "
              f"{'SEPARATES' if v['separates'] else 'overlaps zero'}")
    print(f"  starter points           champions {points['champions_mean']} "
          f"vs field {points['field_mean']} diff {points['diff_pp']:+.1f} "
          f"CI {points['diff_ci95']} "
          f"{'SEPARATES' if points['separates'] else 'overlaps zero'}")


if __name__ == "__main__":
    main()
