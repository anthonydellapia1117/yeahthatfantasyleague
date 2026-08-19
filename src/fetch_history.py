#!/usr/bin/env python3
"""Rebuild the historical data cache the analysis layer reads.

The analysis scripts (analyze_recency, analyze_injury, replay_backtest,
analyze_durability) read a local cache of public historical data. The
committed payloads in out/data/ are the results of record; this script
exists so anyone can rebuild that cache from the original sources and
reproduce them byte-for-byte (tests/test_analysis.py reruns every
analysis end-to-end whenever the cache is present, and skips those
reruns - loudly - when it is not).

Cache location: the HISTORY environment variable if set, else the same
default path the analysis scripts use (src/analyze_recency.py HISTORY).

Contents (all public, all versioned by year):
  ffc_ppr_YYYY.json   FantasyFootballCalculator PPR ADP, 12-team boards,
                      2013-2025 (early-September snapshots)
  spw_YYYY.csv        nflverse stats_player_week, 2012-2025 (CC-BY-4.0)
  inj_YYYY.csv        nflverse injury reports, 2012-2025 (CC-BY-4.0);
                      the release stores some years gzipped and some
                      plain, so both are tried
  roster_YYYY.csv     nflverse rosters, 2013-2025 (CC-BY-4.0) - birth
                      dates for the age control in the durability study

Idempotent: files already present (and non-trivial in size) are kept.
Run: python3 src/fetch_history.py            # default cache path
     HISTORY=/somewhere python3 src/fetch_history.py
"""
import gzip
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_recency import HISTORY


def fetch(url, dest, gz=False):
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return "have"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ytfl-hub"})
        raw = urllib.request.urlopen(req, timeout=180).read()
        if gz:
            raw = gzip.decompress(raw)
        open(dest, "wb").write(raw)
        return "ok"
    except Exception as e:
        return f"FAIL {e}"


def main():
    os.makedirs(HISTORY, exist_ok=True)
    results = []
    for y in range(2013, 2026):
        results.append((f"ffc_ppr_{y}.json", fetch(
            f"https://fantasyfootballcalculator.com/api/v1/adp/ppr?teams=12&year={y}",
            os.path.join(HISTORY, f"ffc_ppr_{y}.json"))))
    for y in range(2012, 2026):
        results.append((f"spw_{y}.csv", fetch(
            "https://github.com/nflverse/nflverse-data/releases/download/"
            f"stats_player/stats_player_week_{y}.csv.gz",
            os.path.join(HISTORY, f"spw_{y}.csv"), gz=True)))
    for y in range(2012, 2026):
        dest = os.path.join(HISTORY, f"inj_{y}.csv")
        base_url = ("https://github.com/nflverse/nflverse-data/releases/"
                    f"download/injuries/injuries_{y}.csv")
        r = fetch(base_url + ".gz", dest, gz=True)
        if r.startswith("FAIL"):
            r = fetch(base_url, dest)
        results.append((f"inj_{y}.csv", r))
    for y in range(2013, 2026):
        results.append((f"roster_{y}.csv", fetch(
            "https://github.com/nflverse/nflverse-data/releases/download/"
            f"rosters/roster_{y}.csv",
            os.path.join(HISTORY, f"roster_{y}.csv"))))
    bad = [(f, r) for f, r in results if r.startswith("FAIL")]
    for f, r in results:
        print(f"{r:>5}  {f}" if not r.startswith("FAIL") else f"{f}: {r}")
    print(f"\ncache at {HISTORY}: {len(results) - len(bad)}/{len(results)} present"
          + ("" if not bad else " - FAILURES ABOVE"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
