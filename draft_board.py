#!/usr/bin/env python3
"""Draft board for a Sleeper league: projections + ADP -> VOR, tiers, and wait/reach math.

Data comes from Sleeper's public API only. No credentials, no scraping, no third party.
Run:  python3 draft_board.py <league_id> [--pick N] [--pos RB]
"""
import json, os, sys, urllib.request, argparse
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
            # injury_status is undated Sleeper preseason/player metadata, not an
            # official practice/game designation. It is displayed, never priced.
            rows.append({
                "name": f"{pl.get('first_name','')} {pl.get('last_name','')}".strip(),
                "sleeper_id": str(r.get("player_id") or ""),
                "pos": pos, "team": r.get("team") or "FA",
                "pts": pts,
                "injury": pl.get("injury_status") or "",
                "sleeper_generic": st.get(f"pts_{key}"),
                "adp": float(adp) if adp else 999.0,
            })
    return rows


def flex_slot_count(slots):
    base = defaultdict(int)
    flex = 0
    for s in slots:
        if s in ("FLEX", "WRRB_FLEX", "REC_FLEX", "SUPER_FLEX"):
            flex += 1
        elif s in POSITIONS:
            base[s] += 1
    return base, flex


def greedy_flex_alloc(by_pos, base, flex, teams):
    """Projection-optimal flex fill: each of the flex*teams slots goes to the
    best remaining RB/WR/TE by projected points. The theoretical bound; the
    observed-behavior artifact supersedes it when present."""
    taken = {"RB": 0, "WR": 0, "TE": 0}
    for _ in range(flex * teams):
        best_pos, best_pts = None, float("-inf")
        for p in ("RB", "WR", "TE"):
            i = base[p] * teams + taken[p]
            if i < len(by_pos[p]) and by_pos[p][i]["pts"] > best_pts:
                best_pos, best_pts = p, by_pos[p][i]["pts"]
        if best_pos is None:
            break
        taken[best_pos] += 1
    return taken


def load_flex_usage():
    """The observed-behavior artifact: how this league ACTUALLY filled its flex
    slot (2025 season, every matchup week, starters array is slot-ordered).
    Written by src/derive_flex.py; None when absent so the caller can fall back
    to the projection-greedy derivation - never to an assumed split."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "out", "data", "flex_usage_2025.json")
    if not os.path.exists(path):
        return None
    d = json.load(open(path))
    return d.get("allocation")


def replacement_ranks(slots, teams, flex_alloc):
    """How deep each position is drafted for starters. The flex share is a
    DERIVED input (observed league behavior, or projection-greedy fallback),
    never an assumed constant - the old 50/50 RB/WR split mispriced both
    positions against how this league actually starts its flex."""
    base, flex = flex_slot_count(slots)
    out = {p: base[p] * teams for p in POSITIONS}
    for p, n in (flex_alloc or {}).items():
        out[p] = out.get(p, 0) + int(n)
    return out


def build(league_id):
    lg = league(league_id)
    rows = projections(lg)

    by_pos = defaultdict(list)
    for r in rows:
        by_pos[r["pos"]].append(r)
    for pos in by_pos:
        by_pos[pos].sort(key=lambda x: -x["pts"])

    base, flex = flex_slot_count(lg["slots"])
    flex_alloc = load_flex_usage()
    lg["flex_source"] = "observed_2025" if flex_alloc else "projection_greedy"
    if not flex_alloc:
        flex_alloc = greedy_flex_alloc(by_pos, base, flex, lg["teams"])
    lg["flex_alloc"] = dict(flex_alloc)
    repl_rank = replacement_ranks(lg["slots"], lg["teams"], flex_alloc)

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


def tier_gap(players):
    """Derived per-position tier threshold: the 90th percentile of successive
    VOR drops among draftable players. A single absolute constant cannot serve
    positions whose VOR scales differ - a fixed 12.0 cut QB nine times and WR
    once in the same forty players. p90 is the stated convention; the threshold
    VALUE is computed from the position's own distribution."""
    ps = draftable(players)
    drops = [ps[i]["vor"] - ps[i + 1]["vor"] for i in range(len(ps) - 1)]
    if len(drops) < 8:
        return float("inf")             # too few players to claim tier structure
    drops_sorted = sorted(drops)
    idx = max(0, min(len(drops) - 1, int(round(0.9 * (len(drops) - 1)))))
    return drops_sorted[idx]


def tiers(players, gap=None):
    """Split a position list into tiers wherever VOR drops by more than `gap`.
    gap=None derives the threshold from the position's own drop distribution."""
    if gap is None:
        gap = tier_gap(players)
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
