#!/usr/bin/env python3
"""Derive the FLEX allocation from this league's own observed starting behavior.

The VOR replacement level for RB/WR/TE depends on how the league's single FLEX
slot actually gets filled. draft_board.py assumed a 50/50 RB/WR split for years;
the projection-greedy fill says 12/12 WR. Neither is observed behavior. This
script computes the real thing: every FLEX start from the 2025 season (the one
real Sleeper season - the 2024 shell 1092592577628426240 is excluded from all
analysis by standing rule), read straight from the matchup starters arrays,
which Sleeper orders by roster_positions so the FLEX index is exact.

Writes out/data/flex_usage_2025.json: counts, shares with Wilson 95% intervals,
and the largest-remainder allocation of the 12 flex slots. The season is over,
so the artifact is a permanent snapshot; rebuilds are deterministic from it.

Run: python3 src/derive_flex.py
"""
import datetime
import json
import math
import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "data", "flex_usage_2025.json")
LEAGUE_2025 = "1245905122328846336"
EXCLUDED_SHELL = "1092592577628426240"
FLEX_POS = ("RB", "WR", "TE")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ff-hub/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 4), round(c + h, 4))


def main():
    lg = get(f"https://api.sleeper.app/v1/league/{LEAGUE_2025}")
    rp = lg["roster_positions"]
    flex_idx = rp.index("FLEX")
    n_flex_slots = rp.count("FLEX") * lg["total_rosters"]
    players = get("https://api.sleeper.app/v1/players/nfl")

    counts, total, weeks = {p: 0 for p in FLEX_POS}, 0, 0
    for wk in range(1, 19):
        try:
            ms = get(f"https://api.sleeper.app/v1/league/{LEAGUE_2025}/matchups/{wk}")
        except Exception:
            break
        if not ms:
            break
        weeks += 1
        for m in ms:
            st = m.get("starters") or []
            if len(st) > flex_idx and st[flex_idx] and st[flex_idx] != "0":
                pos = (players.get(st[flex_idx]) or {}).get("position")
                if pos in counts:
                    counts[pos] += 1
                    total += 1

    shares = {p: round(counts[p] / total, 4) for p in FLEX_POS}
    # largest-remainder rounding of shares over the league's flex slots
    raw = {p: shares[p] * n_flex_slots for p in FLEX_POS}
    alloc = {p: int(raw[p]) for p in FLEX_POS}
    rem = n_flex_slots - sum(alloc.values())
    for p in sorted(FLEX_POS, key=lambda q: raw[q] - int(raw[q]), reverse=True)[:rem]:
        alloc[p] += 1

    out = {
        "provenance": {
            "source": f"sleeper matchups, league {LEAGUE_2025} (2025 season)",
            "excluded": f"2024 shell {EXCLUDED_SHELL} excluded from all analysis",
            "method": ("starters array is roster_positions-ordered; index "
                       f"{flex_idx} is FLEX; every non-empty flex start counted"),
            "generated": datetime.date.today().isoformat(),
            "weeks": weeks,
            "n": total,
        },
        "counts": counts,
        "shares": shares,
        "wilson95": {p: wilson(counts[p], total) for p in FLEX_POS},
        "flex_slots": n_flex_slots,
        "allocation": alloc,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}: n={total} over {weeks} weeks -> allocation {alloc}")


if __name__ == "__main__":
    main()
