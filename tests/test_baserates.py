#!/usr/bin/env python3
"""C2 guards: base-rate artifact integrity and board wiring.

Runs WITHOUT network on the committed artifact and pages.
Run: python3 tests/test_baserates.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []


def ok(cond, name, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "  -> " + detail))
    if not cond:
        fails.append(name)


path = os.path.join(ROOT, "out", "data", "base_rates.json")
ok(os.path.exists(path), "base_rates.json exists")
d = json.load(open(path))

# 1. Structure: definitions, provenance with join counts, both tables
for k in ("hit12", "hit24", "bust36"):
    ok(k in d["definitions"] and len(d["definitions"][k]) > 20,
       f"definition stated for {k}")
prov = d["provenance"]
ok(prov.get("seasons") == "2016-2025", "season window stated", str(prov.get("seasons")))
ok("6-pt pass TD" in prov.get("outcomes", ""),
   "outcomes declare league-exact scoring")
j = prov.get("join", {})
ok(all(k in j for k in ("market_joined", "market_unjoined_as_bust",
                        "league_joined", "league_unjoined_as_bust")),
   "join accounting present (nothing silently dropped)")
ok(j.get("market_joined", 0) > 1000 and j.get("league_joined", 0) > 1000,
   "joins cover real samples", str(j))
unj_rate = j["market_unjoined_as_bust"] / max(1, j["market_joined"])
ok(unj_rate < 0.05, "market unjoined rate under 5%", f"{unj_rate:.3f}")

# 2. Every cell internally consistent: k <= n, rate = k/n, CI brackets rate,
#    interval bounds ordered and inside [0,1] (Wilson can graze the edges)
cells = 0
for table in ("market", "league"):
    for pos, bands in d[table].items():
        ok(pos in ("QB", "RB", "WR", "TE"), f"{table} position {pos} expected")
        for band, c in bands.items():
            cells += 1
            n = c["n"]
            ok(n > 0, f"{table} {pos} {band} has n>0")
            for m in ("hit12", "hit24", "bust36"):
                cell = c[m]
                good = (0 <= cell["k"] <= n
                        and abs(cell["rate"] - cell["k"] / n) < 1e-3
                        and cell["ci95"][0] <= cell["rate"] <= cell["ci95"][1]
                        and -0.01 <= cell["ci95"][0] <= cell["ci95"][1] <= 1.01)
                if not good:
                    ok(False, f"{table} {pos} {band} {m} internally consistent",
                       str(cell))
ok(cells >= 30, "both tables populated across bands", str(cells))
print(f"PASS  every populated cell internally consistent ({cells} cells)")

# 3. hit24 >= hit12 in every cell (a top-12 finish IS a top-24 finish)
bad = [f"{t}/{p}/{b}" for t in ("market", "league") for p, bs in d[t].items()
       for b, c in bs.items() if c["hit24"]["k"] < c["hit12"]["k"]]
ok(not bad, "hit24 dominates hit12 in every cell", "; ".join(bad[:3]))

# 4. Board wiring: fetch, chip, reference table, honesty line, display-only
bp = open(os.path.join(ROOT, "out", "big_board.html")).read()
ok('get("data/base_rates.json")' in bp, "board fetches the artifact")
ok("never gates boot" in bp, "board renders without the artifact (stated)")
ok("baseRateChip" in bp and "baseRateTable" in bp, "chip and table wired")
ok("History, not a projection" in bp, "honesty line present")
ok("n=${cell.n}" in bp, "chip renders n beside every rate")
_chip = bp[bp.index("function baseRateChip"):bp.index("function baseRateTable")]
ok("cvs_rank" not in _chip and "signal" not in _chip and "score" not in _chip,
   "chip is display-only - reads adp_pos_rank and the artifact, nothing else")

print()
if fails:
    print(f"{len(fails)} FAILURES")
    sys.exit(1)
print("ALL PASS")
