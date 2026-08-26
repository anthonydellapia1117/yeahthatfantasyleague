#!/usr/bin/env python3
"""Post-merge item 1: mock-draft validation - does the VOR board produce
sensible DRAFTS, not just sensible rankings?

Three deterministic 12-team, 14-round snake simulations from the committed
engine payload, one per review-named slot (1, 6, 12). Our seat drafts by
the board's MARGINAL policy: each candidate is scored by the improvement
to the optimal starting lineup where every empty slot holds a
replacement-level phantom (the engine's own baselines), VOR as the bench
tie-break. The other eleven seats draft by Sleeper ADP with the league's
observed K/DEF timing (window start = max round minus the median
first-K/DEF rounds-from-end in the 2024-2025 Sleeper drafts, computed
from out/picks.csv at build time). Two comparison runs per slot: our seat
on naive max-VOR, and our seat on ADP chalk.

WHY MARGINAL AND NOT NAIVE MAX-VOR: the first run of this validation
caught naive max-VOR drafting two elite TEs in rounds 2-3 from slots 6
and 12 - raw VOR prices a duplicate at starter value even though the
league's own derived flex allocation (WR 8 / RB 4 / TE 0, n=216) says a
second TE never starts here. The live room already guards this with its
roster-need line (it flags when max-VOR duplicates a filled slot); the
marginal policy is the autopilot form of the same economics. Both
policies are reported so the divergence stays visible.

Deliberately deterministic: no RNG, no sampled opponents. This validates
the board's economics (does the board build a legal, coherent roster and
beat chalk at the same slot?), not the live room's survival model, which
has its own calibration artifact and backtest.

Roster: QB RB RB WR WR TE FLEX K DEF + 5 bench (engine league config).
Feasibility: a seat may never draft a position that would make the
remaining starter slots unfillable with its remaining picks, never a
second K or DEF, and our seat leaves K/DEF to the feasibility forcing -
if the board's VOR ever ranked a K above the marginal bench skill player
it could take it early, and the artifact would show it.

Run: python3 src/mock_draft.py
Output: out/data/mock_drafts_2026.json
"""
import csv
import datetime
import json
import os
import statistics
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "out", "data")
OUT = os.path.join(D, "mock_drafts_2026.json")

STARTERS = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF"]
FLEX_OK = ("RB", "WR", "TE")
OUR_SLOTS = (1, 6, 12)


def kdef_window(rounds_total):
    """Opponents' K/DEF window start, from observed league behavior."""
    rows = [r for r in csv.DictReader(open(os.path.join(ROOT, "out", "picks.csv")))
            if r["season"] in ("2024", "2025")]
    max_round = defaultdict(int)
    first = defaultdict(dict)
    for r in rows:
        max_round[r["season"]] = max(max_round[r["season"]], int(r["round"]))
        if r["pos"] in ("K", "DEF"):
            key = (r["season"], r["member_name"])
            first[key].setdefault(r["pos"], int(r["round"]))
    from_end = [max_round[s] - d[p] for (s, _m), d in first.items()
                for p in d]
    med = statistics.median(from_end)
    return int(rounds_total - med), {"observed_n": len(from_end),
                                     "median_rounds_from_end": med}


class Team:
    def __init__(self, slot):
        self.slot = slot
        self.players = []

    def counts(self):
        return Counter(p["pos"] for p in self.players)

    def unfilled_starters(self):
        """Starter slots not yet coverable by the current roster."""
        c = self.counts()
        need = []
        base = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "K": 1, "DEF": 1}
        used_for_base = {}
        for pos, k in base.items():
            used_for_base[pos] = min(c.get(pos, 0), k)
            need += [pos] * (k - used_for_base[pos])
        flex_spare = sum(c.get(p, 0) - used_for_base[p] for p in FLEX_OK)
        if flex_spare < 1:
            need.append("FLEX")
        return need

    def feasible(self, pos, picks_left, caps=None):
        """Would drafting pos keep the remaining starters fillable?"""
        if pos in ("K", "DEF") and self.counts().get(pos, 0) >= 1:
            return False
        if caps and self.counts().get(pos, 0) >= caps.get(pos, 99):
            return False
        need = self.unfilled_starters()
        # drafting pos satisfies at most one needed slot
        if pos in need:
            need.remove(pos)
        elif "FLEX" in need and pos in FLEX_OK:
            need.remove("FLEX")
        return len(need) <= picks_left - 1


def snake(teams, rounds_total):
    for rnd in range(1, rounds_total + 1):
        order = range(1, teams + 1) if rnd % 2 else range(teams, 0, -1)
        for slot in order:
            yield rnd, slot


def roster_caps(flex_alloc):
    """Bench sanity for the marginal autopilot, derived from the league's
    own observed flex allocation: a position may hold at most its maximum
    simultaneous starters (base slots, plus the flex slot only where the
    league has ever actually flexed the position) plus ONE injury spare -
    a stated convention, like the p75/p90 choices elsewhere."""
    base = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "K": 1, "DEF": 1}
    caps = {}
    for pos, k in base.items():
        flexes = 1 if flex_alloc.get(pos, 0) > 0 and pos in FLEX_OK else 0
        caps[pos] = k + flexes + (1 if pos not in ("K", "DEF") else 0)
    return caps


def run_sim(players, rounds_total, teams_n, our_slot, our_policy,
            window_start, baselines, caps):
    taken = set()
    teams = {s: Team(s) for s in range(1, teams_n + 1)}
    log = []
    for rnd, slot in snake(teams_n, rounds_total):
        t = teams[slot]
        picks_left = rounds_total - len(t.players)
        avail = [p for p in players if p["name"] + "|" + p["pos"] not in taken]
        ours = slot == our_slot and our_policy != "adp"
        pool = [p for p in avail
                if t.feasible(p["pos"], picks_left,
                              caps if ours and our_policy == "marginal"
                              else None)]
        if not ours:
            # ADP seat: inside the observed window, fill a missing K/DEF
            # first; otherwise best available ADP among feasible skill
            c = t.counts()
            missing_kdef = [p for p in ("K", "DEF") if c.get(p, 0) == 0]
            if rnd >= window_start and missing_kdef:
                cand = [p for p in pool if p["pos"] in missing_kdef]
            else:
                cand = [p for p in pool if p["pos"] not in ("K", "DEF")] or pool
            pick = min(cand, key=lambda p: p["adp"])
        elif our_policy == "naive_vor":
            pick = max(pool, key=lambda p: p["vor"])
        else:
            # marginal policy: lineup improvement over phantoms, VOR
            # tie-break for bench depth once the lineup is beaten
            base = phantom_lineup_pts(t.players, baselines)
            pick = max(pool, key=lambda p: (
                round(phantom_lineup_pts(t.players + [p], baselines) - base, 4),
                p["vor"]))
        taken.add(pick["name"] + "|" + pick["pos"])
        t.players.append(pick)
        if slot == our_slot:
            log.append({"round": rnd,
                        "overall": (rnd - 1) * teams_n +
                        (slot if rnd % 2 else teams_n - slot + 1),
                        "name": pick["name"], "pos": pick["pos"],
                        "adp": pick["adp"], "vor": pick.get("vor"),
                        "pts": pick["pts"], "tier": pick.get("tier")})
    return teams[our_slot], log


def phantom_lineup_pts(players, baselines):
    """Optimal starter points with replacement-level phantoms in empty
    slots - the lineup value function the marginal policy maximizes."""
    by_pos = defaultdict(list)
    for p in sorted(players, key=lambda x: -x["pts"]):
        by_pos[p["pos"]].append(p)
    total = 0.0
    used = set()

    def take(pos, n):
        nonlocal total
        got = 0
        for p in by_pos.get(pos, []):
            if got == n:
                break
            k = p["name"] + "|" + p["pos"]
            if k not in used:
                used.add(k)
                total += max(p["pts"], baselines[pos])
                got += 1
        while got < n:
            total += baselines[pos]
            got += 1

    take("QB", 1), take("RB", 2), take("WR", 2), take("TE", 1)
    flex = [p for pos in FLEX_OK for p in by_pos.get(pos, [])
            if p["name"] + "|" + p["pos"] not in used]
    flex_phantom = max(baselines[p] for p in FLEX_OK)
    total += max([p["pts"] for p in flex] + [flex_phantom])
    take("K", 1), take("DEF", 1)
    return total


def optimal_starters(team):
    """Best legal lineup by projected points; returns (points, lineup)."""
    by_pos = defaultdict(list)
    for p in sorted(team.players, key=lambda x: -x["pts"]):
        by_pos[p["pos"]].append(p)
    lineup, used = [], set()

    def take(pos, n):
        got = 0
        for p in by_pos.get(pos, []):
            if got == n:
                break
            k = p["name"] + "|" + p["pos"]
            if k not in used:
                used.add(k)
                lineup.append((pos, p))
                got += 1

    take("QB", 1), take("RB", 2), take("WR", 2), take("TE", 1)
    flex = [p for pos in FLEX_OK for p in by_pos.get(pos, [])
            if p["name"] + "|" + p["pos"] not in used]
    if flex:
        p = max(flex, key=lambda x: x["pts"])
        used.add(p["name"] + "|" + p["pos"])
        lineup.append(("FLEX", p))
    take("K", 1), take("DEF", 1)
    return round(sum(p["pts"] for _, p in lineup), 1), [
        {"slot": s, "name": p["name"], "pos": p["pos"], "pts": p["pts"]}
        for s, p in lineup]


def sanity(team, rounds_total):
    c = team.counts()
    names = [p["name"] + "|" + p["pos"] for p in team.players]
    return {
        "picks": len(team.players) == rounds_total,
        "no_duplicates": len(set(names)) == len(names),
        "one_k_one_def": c.get("K", 0) == 1 and c.get("DEF", 0) == 1,
        "starters_fillable": len(team.unfilled_starters()) == 0,
    }


def main():
    eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
    lg = eng["league"]
    rounds_total, teams_n = lg["rounds"], lg["teams"]
    players = [p for p in eng["players"] if p.get("adp") is not None]
    window_start, window_prov = kdef_window(rounds_total)

    baselines = eng["baselines"]
    caps = roster_caps(eng.get("flex_allocation", {}))
    sims = {}
    for slot in OUR_SLOTS:
        board_team, board_log = run_sim(players, rounds_total, teams_n, slot,
                                        "marginal", window_start, baselines,
                                        caps)
        naive_team, naive_log = run_sim(players, rounds_total, teams_n, slot,
                                        "naive_vor", window_start, baselines,
                                        caps)
        adp_team, _ = run_sim(players, rounds_total, teams_n, slot,
                              "adp", window_start, baselines, caps)
        b_pts, b_lineup = optimal_starters(board_team)
        n_pts, _ = optimal_starters(naive_team)
        a_pts, _ = optimal_starters(adp_team)
        sims[str(slot)] = {
            "picks": board_log,
            "starters": b_lineup,
            "starter_pts_board": b_pts,
            "starter_pts_naive_vor": n_pts,
            "starter_pts_adp_chalk": a_pts,
            "board_minus_chalk": round(b_pts - a_pts, 1),
            "board_minus_naive": round(b_pts - n_pts, 1),
            "naive_vor_picks": [{"round": p["round"], "name": p["name"],
                                 "pos": p["pos"]} for p in naive_log],
            "position_counts": dict(board_team.counts()),
            "sanity": sanity(board_team, rounds_total),
        }

    out = {
        "provenance": {
            "generated": datetime.date.today().isoformat(),
            "engine_generated": eng["generated"],
            "method": ("deterministic snake sim from the committed engine "
                       "payload; our seat scores candidates by optimal-"
                       "lineup improvement over replacement-level phantoms "
                       "(engine baselines), VOR tie-break; eleven ADP seats; "
                       "comparison runs: naive max-VOR and ADP chalk"),
            "finding": ("naive max-VOR drafts duplicate elite TEs early "
                        "(slots 6 and 12) because raw VOR prices a duplicate "
                        "at starter value; the marginal policy corrects it "
                        "and the live room's roster-need line is the same "
                        "guard in interactive form"),
            "kdef_window": {"opponents_start_round": window_start,
                            **window_prov,
                            "source": "out/picks.csv 2024-2025 observed"},
            "scope": ("validates board economics only - no survival model, "
                      "no RNG; the live room adds survival and need logic "
                      "on top of this same VOR core"),
        },
        "slots": sims,
    }
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}")
    for slot, s in sims.items():
        top3 = ", ".join(f"{p['name']} ({p['pos']})" for p in s["picks"][:3])
        print(f"slot {slot}: {top3}")
        print(f"  board {s['starter_pts_board']} | naive "
              f"{s['starter_pts_naive_vor']} | chalk "
              f"{s['starter_pts_adp_chalk']} | board-chalk "
              f"{s['board_minus_chalk']} | board-naive "
              f"{s['board_minus_naive']} | sanity "
              f"{all(s['sanity'].values())}")


if __name__ == "__main__":
    main()
