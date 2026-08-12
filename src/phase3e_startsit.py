"""Phase 3E - the RB start-sit leak, decision by decision.

Phase 3A found RB start-sit is 80 percent of Anthony's 1.49 pts/wk gap to
Phil Baldino, and that the leak is recent (2022-2025: 5.43 vs 2.47 lost
RB pts/wk). This script characterizes the individual decisions: which
weeks, which benched RB outscored which starter, and whether the right
call was knowable at lock time or only in hindsight.

KNOWABILITY PROXY, stated honestly: the archive carries no historical
weekly projections, so "knowable at lock" is defined as the benched
player entering the week with a season-to-date points-per-game average
at least as high as the starter he should have replaced (minimum 2 prior
games for both). Week 1 and small-sample cases are tagged UNRATED, not
guessed. This is a floor on knowability - a real projection would also
catch injury news and matchup, so the true knowable share is at least
what this reports.

Swap pairing: within each week, players flagged is_optimal-but-benched
are matched to started-but-not-optimal players in descending order of
points (best wrongly-benched player displaces the worst wrongly-started
one), WITHIN slot-eligibility pools - QB with QB, K with K, DEF with
DEF, and RB/WR/TE together because they compete for the same FLEX slot.
A benched RB can never displace a started defense. Only swaps where the
benched player is an RB are kept, since RB is the leak.

Stdlib only, no network. Re-runnable:

    python3 src/phase3e_startsit.py

Writes out/rb_startsit_decisions.csv.

Source A: LeagueLegacy archive, 02_gamecenter/matchup_rosters.csv.
Basis: 2013-2024 rows are bonus-exclusive (G1); every comparison here is
within-week between two players on the same basis, so verdicts are
unaffected.
"""

import csv
import collections
import os

ROSTERS = ("LeagueLegacy-io/YeahThatFantasyLeague_LeagueLegacy_Archive_2013-2026"
           "/02_gamecenter/matchup_rosters.csv")
OUT = "out/rb_startsit_decisions.csv"
ME = "Antdell & Ernie"
RIVAL = "Phil Baldino"
MIN_PRIOR_GAMES = 2
PLAYERS = ("LeagueLegacy-io/YeahThatFantasyLeague_LeagueLegacy_Archive_2013-2026"
           "/06_players/players_all_time.csv")


def eligibility_pool(pos):
    """Which wrongly-started players a benched player could legally displace."""
    return "FLEX" if pos in ("RB", "WR", "TE") else pos


def points(row):
    p = float(row["points"] or 0)
    ppr = float(row["points_ppr"] or 0)
    return ppr if p == 0 and ppr != 0 else p


def flag(v):
    return v == "true"


def load():
    with open(ROSTERS) as fh:
        return list(csv.DictReader(fh))


def prior_ppg(history, player_id, season, week):
    """Season-to-date points per game BEFORE this week. None if under the
    minimum sample - never guessed."""
    games = [p for w, p in history.get((season, player_id), [])
             if int(w) < int(week)]
    if len(games) < MIN_PRIOR_GAMES:
        return None
    return sum(games) / len(games)


def swaps_for(rows, history, who, names):
    """Every wrongly-benched-RB swap for one franchise, with knowability."""
    by_week = collections.defaultdict(lambda: {"bench": [], "start": []})
    for r in rows:
        if r["member_name"] != who:
            continue
        k = (r["season"], r["week"])
        if flag(r["is_optimal"]) and not flag(r["started"]):
            by_week[k]["bench"].append(r)
        elif flag(r["started"]) and not flag(r["is_optimal"]):
            by_week[k]["start"].append(r)

    out = []
    for (season, week), grp in sorted(by_week.items(),
                                      key=lambda t: (t[0][0], int(t[0][1]))):
        pools = collections.defaultdict(lambda: {"bench": [], "start": []})
        for r in grp["bench"]:
            pools[eligibility_pool(r["player_position"])]["bench"].append(r)
        for r in grp["start"]:
            pools[eligibility_pool(r["player_position"])]["start"].append(r)
        pairs = []
        for pool in pools.values():
            bench = sorted(pool["bench"], key=lambda r: -points(r))
            start = sorted(pool["start"], key=lambda r: points(r))
            pairs.extend(zip(bench, start))
        for b, s in pairs:
            if b["player_position"] != "RB":
                continue
            delta = points(b) - points(s)
            if delta <= 0:
                continue
            b_ppg = prior_ppg(history, b["player_id"], season, week)
            s_ppg = prior_ppg(history, s["player_id"], season, week)
            if b_ppg is None or s_ppg is None:
                verdict = "UNRATED"
            elif b_ppg >= s_ppg:
                verdict = "KNOWABLE"
            else:
                verdict = "HINDSIGHT"
            out.append({
                "season": season, "week": week, "franchise": who,
                "benched": b["player_id"],
                "benched_name": names.get(b["player_id"], ""),
                "benched_pts": round(points(b), 2),
                "benched_prior_ppg": round(b_ppg, 2) if b_ppg is not None else "",
                "displaced": s["player_id"],
                "displaced_name": names.get(s["player_id"], ""),
                "displaced_pos": s["player_position"],
                "displaced_pts": round(points(s), 2),
                "displaced_prior_ppg": round(s_ppg, 2) if s_ppg is not None else "",
                "points_lost": round(delta, 2), "verdict": verdict,
            })
    return out


def summarize(swaps, who, seasons=None):
    sel = [s for s in swaps
           if seasons is None or s["season"] in seasons]
    by_v = collections.defaultdict(lambda: [0, 0.0])
    for s in sel:
        by_v[s["verdict"]][0] += 1
        by_v[s["verdict"]][1] += s["points_lost"]
    total_pts = sum(v[1] for v in by_v.values()) or 1.0
    label = f"{who}" + (f" {min(seasons)}-{max(seasons)}" if seasons else " 2013-2025")
    print(f"  {label}")
    for v in ("KNOWABLE", "HINDSIGHT", "UNRATED"):
        n, pts = by_v[v]
        print(f"    {v:<10} {n:>4} swaps  {pts:>8.1f} pts  {pts / total_pts:>5.1%}")
    return by_v


def main():
    rows = load()

    # per-player weekly scoring history, for the prior-PPG proxy.
    # A player's week counts as a game if he was on ANY roster that week.
    history = collections.defaultdict(list)
    for r in rows:
        history[(r["season"], r["player_id"])].append((r["week"], points(r)))

    with open(PLAYERS) as fh:
        names = {r["gsis_id"]: r["name"] for r in csv.DictReader(fh)}

    me = swaps_for(rows, history, ME, names)
    rival = swaps_for(rows, history, RIVAL, names)

    print("RB START-SIT SWAPS - wrongly benched RB, points lost, knowability")
    print("verdict = benched player's season-to-date PPG vs the displaced")
    print(f"starter's, minimum {MIN_PRIOR_GAMES} prior games each. UNRATED = too early")
    print("in the season to rate. Knowable share is a floor, not a ceiling.\n")

    summarize(me, ME)
    summarize(me, ME, {"2022", "2023", "2024", "2025"})
    summarize(rival, RIVAL)
    summarize(rival, RIVAL, {"2022", "2023", "2024", "2025"})

    # the worst individual decisions, recent era
    recent = [s for s in me if s["season"] >= "2022"]
    recent.sort(key=lambda s: -s["points_lost"])
    print(f"\n  {ME}: ten costliest RB benchings, 2022-2025")
    print(f"  {'season':<7}{'wk':>3}  {'benched':<12}{'pts':>6}  "
          f"{'over':<12}{'pts':>6}{'lost':>7}  verdict")
    for s in recent[:10]:
        b = names.get(s["benched"], s["benched"])[:18]
        d = names.get(s["displaced"], s["displaced"])[:18]
        print(f"  {s['season']:<7}{s['week']:>3}  {b:<19}"
              f"{s['benched_pts']:>6.1f}  {d:<19}"
              f"{s['displaced_pts']:>6.1f}{s['points_lost']:>7.1f}  {s['verdict']}")

    os.makedirs("out", exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(me[0].keys()) + [
            "source", "source_ref", "basis", "confidence"])
        w.writeheader()
        for s in me + rival:
            s.update({"source": "leaguelegacy",
                      "source_ref": "02_gamecenter/matchup_rosters.csv",
                      "basis": "bonus-exclusive 2013-2024",
                      "confidence": "verified"})
            w.writerow(s)
    print(f"\nwrote {OUT} ({len(me) + len(rival)} swaps, both franchises)")


if __name__ == "__main__":
    main()
