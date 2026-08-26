#!/usr/bin/env python3
"""Guards for the drafted-vs-acquired champions analysis.

The guards exist so the headline cannot drift: the sourcing-mix result
must stay reported with its interval, the era cuts must stay present, and
the separating result (total production) must not be confused with the
non-separating one (where the points came from).
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS = []


def ok(cond, label):
    print(("PASS  " if cond else "FAIL  ") + label)
    if not cond:
        FAILS.append(label)


a = json.load(open(os.path.join(ROOT, "out", "data", "draft_vs_acquired.json")))
prov = a["provenance"]

ok("champions_by_season.csv" in prov["champions_source"],
   "champions read from the export ledger at compute time, not transcribed")
ok("seasons.csv" in prov["era_source"], "eras read from the archive settings")
ok("never blocked" in prov["correction"],
   "the artifact records that the split already existed")
ok("bonus-exclusive" in prov["basis_caveat"],
   "the Yahoo bonus-exclusive basis caveat is carried")
ok("2013" in prov["excluded"], "the 2013 transaction gap is stated")

# every comparison carries n on both sides and an interval
comps = a["comparisons"]
ok("pooled" in comps, "the pooled comparison is present")
ok(any(k.startswith("weeks") for k in comps), "per-era cuts are present")
for k, c in comps.items():
    if "diff_pp" not in c:
        continue
    ok(c["champions_n"] > 0 and c["field_n"] > 0, f"{k}: both sides carry n")
    lo, hi = c["diff_ci95"]
    ok(lo <= c["diff_pp"] <= hi, f"{k}: the interval brackets its own estimate")
    ok(c["separates"] == bool(lo > 0 or hi < 0),
       f"{k}: the separates flag is exactly what the interval says")

# the two results must stay distinguishable: sourcing mix does NOT separate,
# total production does. Collapsing them would invert the finding.
ok(not comps["pooled"]["separates"],
   "sourcing mix does not separate champions from the field")
ok(a["starter_points"]["separates"],
   "total starter production DOES separate champions from the field")

# per-season rows carry their era and validity flags
rows = a["per_season"]
ok(len(rows) >= 150, "every franchise-season is carried")
ok({r["season"] for r in rows} >= {str(y) for y in range(2013, 2026)},
   "all thirteen completed seasons are present")
ok(all(r["era"] for r in rows), "every row carries an era flag")
ok(any(r["median_scoring"] for r in rows)
   and not all(r["median_scoring"] for r in rows),
   "median scoring is flagged on some seasons and not others")
ok(all(not r["acquired_valid"] for r in rows if r["season"] == "2013"),
   "2013 rows are marked invalid for the acquired split")

if FAILS:
    print(f"\n{len(FAILS)} FAILURES")
    sys.exit(1)
print("\nALL PASS")
