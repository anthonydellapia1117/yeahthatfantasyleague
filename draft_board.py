#!/usr/bin/env python3
"""Draft board for a Sleeper league: projections + ADP -> VOR, tiers, and wait/reach math.

Data comes from Sleeper's public API only. No credentials, no scraping, no third party.
Run:  python3 draft_board.py <league_id> [--pick N] [--pos RB]
"""
import json, sys, urllib.request, argparse
from collections import defaultdict

SEASON = "2026"
POSITIONS = ["QB", "RB", "WR", "TE", "K", "DEF"]


def get(url):
    # Sleeper 403s the default urllib user agent
    req = urllib.request.Request(url, headers={"User-Agent": "ff-hub/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def league(league_id):
    d = get(f"https://api.sleeper.app/v1/league/{league_id}")
    slots = [s for s in d["roster_positions"] if s != "BN"]
    scoring = d.get("scoring_settings", {}) or {}
    ppr = float(scoring.get("rec", 0))
    # key selects which ADP column to read; points are computed from `scoring`, not this
    key = "ppr" if ppr >= 1 else ("half_ppr" if ppr >= 0.5 else "std")
    return {"name": d["name"], "teams": d["total_rosters"], "slots": slots,
            "key": key, "scoring": scoring}


def score(stats, scoring):
    """Points from raw projected stats under THIS league's scoring settings.

    Sleeper's precomputed pts_ppr hardcodes 4-point passing TDs. Leagues paying 6
    were under-projecting every QB by 40 to 66 points. Never read pts_* again.
    """
    total = 0.0
    for stat, value in stats.items():
        # Exclude exactly Sleeper's precomputed fantasy points, not the pts_
        # prefix: pts_allow_* are REAL defensive scoring stats (pts_allow_0
        # pays 10.0 in this league) and a prefix filter silently dropped them,
        # under-scoring every DEF by the shutout bonus.
        if stat in ("pts_ppr", "pts_half_ppr", "pts_std") \
                or stat.startswith(("adp_", "rank_")):
            continue
        mult = scoring.get(stat)
        if mult is None:
            continue
        try:
            total += float(value) * float(mult)
        except (TypeError, ValueError):
            continue
    return round(total, 1)


def projections(lg):
    """Every position's projected points, scored under this league's settings."""
    key, scoring = lg["key"], lg["scoring"]
    rows = []
    for pos in POSITIONS:
        url = (f"https://api.sleeper.com/projections/nfl/{SEASON}"
               f"?season_type=regular&position[]={pos}&order_by=pts_{key}")
        try:
            data = get(url)
        except Exception as e:          # K and DEF are not always published
            print(f"  (skipped {pos}: {e})", file=sys.stderr)
            continue
        for r in data:
            st, pl = r.get("stats") or {}, r.get("player") or {}
            pts = score(st, scoring)
            if pts <= 0:
                continue
            adp = st.get(f"adp_{key}")
            # gp is a hardcoded 18.0 placeholder for every drafted offensive player,
            # so any per-game rate derived from it is pts/18 and carries no information.
            # injury_status is the only availability signal Sleeper actually supplies.
            rows.append({
                "name": f"{pl.get('first_name','')} {pl.get('last_name','')}".strip(),
                "pos": pos, "team": r.get("team") or "FA",
                "pts": pts,
                "injury": pl.get("injury_status") or "",
                "sleeper_generic": st.get(f"pts_{key}"),
                "adp": float(adp) if adp else 999.0,
            })
    return rows


def replacement_ranks(slots, teams):
    """How deep each position is drafted for starters, flex shared by RB/WR/TE."""
    base = defaultdict(int)
    flex = 0
    for s in slots:
        if s in ("FLEX", "WRRB_FLEX", "REC_FLEX", "SUPER_FLEX"):
            flex += 1
        elif s in POSITIONS:
            base[s] += 1
    # flex splits roughly half RB, half WR in PPR; TE rarely
    out = {p: base[p] * teams for p in POSITIONS}
    out["RB"] += int(flex * teams * 0.5)
    out["WR"] += int(flex * teams * 0.5)
    return out


def build(league_id):
    lg = league(league_id)
    rows = projections(lg)
    repl_rank = replacement_ranks(lg["slots"], lg["teams"])

    by_pos = defaultdict(list)
    for r in rows:
        by_pos[r["pos"]].append(r)
    for pos in by_pos:
        by_pos[pos].sort(key=lambda x: -x["pts"])

    # replacement baseline = the projected points of the last startable player
    baseline = {}
    for pos, players in by_pos.items():
        i = min(max(repl_rank.get(pos, 12) - 1, 0), len(players) - 1)
        baseline[pos] = players[i]["pts"]

    for r in rows:
        r["vor"] = round(r["pts"] - baseline[r["pos"]], 1)
    rows.sort(key=lambda x: -x["vor"])
    for i, r in enumerate(rows, 1):
        r["vor_rank"] = i
    return lg, rows, baseline, repl_rank


def draftable(players, limit=40):
    """Only players actually being drafted. ADP 999 means unranked, and below
    replacement the VOR curve flattens so everything collapses into one tier."""
    return [p for p in players if p["adp"] < 999][:limit]


def tiers(players, gap=12.0):
    """Split a position list into tiers wherever VOR drops by more than `gap`."""
    out, cur = [], []
    for p in draftable(players):
        if cur and (cur[-1]["vor"] - p["vor"]) > gap:
            out.append(cur); cur = []
        cur.append(p)
    if cur:
        out.append(cur)
    return out


def wait_cost(players, pick, teams):
    """Points lost at this position between your next pick and the one after."""
    nxt = [p for p in players if p["adp"] >= pick]
    later = [p for p in players if p["adp"] >= pick + 2 * teams]
    if not nxt or not later:
        return None
    return round(nxt[0]["pts"] - later[0]["pts"], 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("league_id")
    ap.add_argument("--pick", type=int, default=1, help="your next overall pick")
    ap.add_argument("--pos", help="show one position's tiers")
    ap.add_argument("--top", type=int, default=25)
    a = ap.parse_args()

    lg, rows, baseline, repl = build(a.league_id)
    by_pos = defaultdict(list)
    for r in rows:
        by_pos[r["pos"]].append(r)

    print(f"\n{lg['name']}  |  {lg['teams']} teams  |  scoring: {lg['key']}")
    print(f"starters: {' '.join(lg['slots'])}\n")

    if a.pos:
        pos = a.pos.upper()
        print(f"{pos} TIERS  (replacement = {pos}{repl[pos]}, {baseline[pos]:.1f} pts)\n")
        for n, t in enumerate(tiers(by_pos[pos])[:6], 1):
            print(f"  Tier {n}")
            for p in t:
                print(f"    {p['name'][:24]:24} {p['team']:3} proj {p['pts']:6.1f}  VOR {p['vor']:6.1f}  ADP {p['adp']:5.1f}")
            print()
        return

    print(f"TOP {a.top} BY VALUE OVER REPLACEMENT\n")
    print(f"  {'#':>3} {'PLAYER':24} {'POS':4} {'PROJ':>6} {'VOR':>7} {'ADP':>6} {'EDGE':>6}  INJ")
    for r in rows[:a.top]:
        edge = r["adp"] - r["vor_rank"]          # positive = falls later than value says
        print(f"  {r['vor_rank']:>3} {r['name'][:24]:24} {r['pos']:4} {r['pts']:6.1f} {r['vor']:7.1f} {r['adp']:6.1f} {edge:+6.1f}  {r['injury']}")

    print(f"\nWAIT COST from pick {a.pick} (points lost if you skip a full turn)\n")
    print(f"  {'POS':5} {'BEST NOW':24} {'COST':>7}  READ")
    for pos in POSITIONS:
        c = wait_cost(by_pos[pos], a.pick, lg["teams"])
        if c is None:
            continue
        nxt = [p for p in by_pos[pos] if p["adp"] >= a.pick]
        read = "WAIT" if c < 15 else ("reach" if c > 35 else "soft")
        print(f"  {pos:5} {nxt[0]['name'][:24]:24} {c:7.1f}  {read}")
    print("\n  low cost = the curve is flat, you can wait. high cost = cliff, take it now.\n")


if __name__ == "__main__":
    main()
