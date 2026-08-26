#!/usr/bin/env python3
"""P2 cron audit: is the LIVE site actually receiving daily data?

The third silent-cron incident taught the lesson this script encodes:
alert on missing successful PUBLICATION, not on workflow execution. The
pages-data cron failed 8 of its first 14 scheduled runs - the last four
consecutively - and nothing noticed, because every prior alert idea
watched the workflow. This watches the deliverable: the deployed
provenance.json on the live site, whose freshest fetched_at timestamp
moves if and only if a green run committed and Pages deployed it.

Prints exactly one status line for the alert Routine to act on:
  PAGES DATA FRESH - published <timestamp> (<N>h ago)
  PAGES DATA STALE - last successful publication <timestamp> (<N>h ago)
  PAGES DATA UNREADABLE - <why> (treat as an alert: the site is the product)

Threshold: 48 hours. The cron runs daily at 12:00 UTC, so 48h means a
full scheduled publication was missed - one late or delayed run never
alerts, two missed days always does.

Run: python3 src/check_publication.py
"""
import datetime
import json
import urllib.request

PAGES = ("https://anthonydellapia1117.github.io/yeahthatfantasyleague"
         "/out/data/provenance.json")
STALE_HOURS = 48


def main():
    try:
        req = urllib.request.Request(PAGES, headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=30) as r:
            prov = json.load(r)
        stamps = [s["fetched_at"] for s in prov.get("shards", {}).values()
                  if s.get("fetched_at")]
        if not stamps:
            print("PAGES DATA UNREADABLE - provenance.json has no "
                  "fetched_at stamps (treat as an alert: the site is the "
                  "product)")
            return
        latest = max(datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
                     for s in stamps)
    except Exception as e:  # noqa: BLE001 - one line out, whatever broke
        print(f"PAGES DATA UNREADABLE - {type(e).__name__}: {e} (treat as "
              "an alert: the site is the product)")
        return

    age = datetime.datetime.now(datetime.timezone.utc) - latest
    hours = age.total_seconds() / 3600
    stamp = latest.strftime("%Y-%m-%dT%H:%MZ")
    if hours <= STALE_HOURS:
        print(f"PAGES DATA FRESH - published {stamp} ({hours:.0f}h ago)")
    else:
        print(f"PAGES DATA STALE - last successful publication {stamp} "
              f"({hours:.0f}h ago)")


if __name__ == "__main__":
    main()
