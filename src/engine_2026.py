"""The 2026 draft engine - per-slot decision cards, opponent-aware.

Built only after the Phase 3B audit passed. Combines:

- VALUE: the audited draft_board.py - VOR from raw-stat projections x this
  league's actual scoring, tiers from VOR gaps, live from Sleeper.
- SURVIVAL: P(player survives to pick k), from a normal model of pick
  error whose sd is EMPIRICAL - fitted per ADP band to 2,039 of this
  league's own historical picks (out/picks.csv adp_differential), not an
  assumed constant.
- OPPONENTS: out/opponent_priors.csv (Phase 3H) - recency-weighted,
  shrunk first-round priors per 2025 franchise era, joined to 2026
  Sleeper rosters through out/identity_map.csv. Unmapped rosters get the
  league prior, labelled.

Honesty constraints, per the audit and the null results:
- No champion mimicry. Every recommendation is VOR and tier math.
- The projection feed carries NO variance measure, so "upside tilt" is
  implemented as flagging within-tier ties as coin flips for the owner
  to break toward ceiling - not as a fabricated variance stat.
- Probabilities carry their inputs. Thin priors are named as thin.
- K and DEF in the last two rounds. Not modelled beyond that.

Run (draft morning - projections and ADP move daily):

    python3 src/engine_2026.py                 # all 12 slots
    python3 src/engine_2026.py --slot 7        # one card

Writes out/decision_cards_2026.md.
"""

import argparse
import csv
import math
import os
import sys
import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import draft_board as db

LEAGUE = "1389378429505241088"
TEAMS = 12
ROUNDS = 14
SKILL = ("QB", "RB", "WR", "TE")

# Empirical pick-error sd by ADP band, fitted to 2,039 league picks
# 2013-2025 (see commit for the fit). (band_hi, sd)
ADP_SD = [(24, 5.46), (60, 13.63), (120, 24.01), (10 ** 9, 23.81)]


def sd_for(adp):
    for hi, sd in ADP_SD:
        if adp <= hi:
            return sd
    return ADP_SD[-1][1]


def survival(adp, pick):
    """P(player still on the board at overall pick `pick`)."""
    if adp >= 900:
        return 1.0
    z = (pick - adp) / (sd_for(adp) * math.sqrt(2))
    return max(0.0, min(1.0, 0.5 * (1 - math.erf(z))))


def snake_picks(slot):
    return [(r - 1) * TEAMS + (slot if r % 2 == 1 else TEAMS + 1 - slot)
            for r in range(1, ROUNDS + 1)]


def load_opponents():
    """franchise -> priors row, plus sleeper handle -> franchise."""
    priors = {r["franchise"]: r
              for r in csv.DictReader(open("out/opponent_priors.csv"))}
    handle_to_fr = {r["sleeper_display_name"]: r["archive_member_name"]
                    for r in csv.DictReader(open("out/identity_map.csv"))}
    return priors, handle_to_fr


def live_rosters(priors, handle_to_fr):
    """2026 roster slots -> franchise prior (or league prior, labelled)."""
    users = {u["user_id"]: u.get("display_name", "?")
             for u in db.get(f"https://api.sleeper.app/v1/league/{LEAGUE}/users")}
    rosters = db.get(f"https://api.sleeper.app/v1/league/{LEAGUE}/rosters")
    out = []
    for r in sorted(rosters, key=lambda x: x["roster_id"]):
        handle = users.get(r.get("owner_id"), "?")
        fr = handle_to_fr.get(handle)
        row = priors.get(fr) if fr else None
        out.append({"roster_id": r["roster_id"], "handle": handle,
                    "franchise": fr or "(unmapped)",
                    "prior": row,
                    "thin": (row is None) or row["confidence"].startswith("thin")})
    return out


def urgency_list(rosters, pos, rnd):
    """Franchises whose shrunk first-{pos} prior says they act by this round."""
    key = f"first_{pos.lower()}_shrunk"
    out = []
    for r in rosters:
        if not r["prior"]:
            continue
        prior_rnd = float(r["prior"][key])
        if prior_rnd <= rnd + 0.5:
            out.append((r["franchise"], prior_rnd,
                        float(r["prior"][f"first_{pos.lower()}_neff"])))
    return sorted(out, key=lambda t: t[1])


def build_cards(slot_filter=None):
    lg, rows, baseline, repl = db.build(LEAGUE)
    by_pos = defaultdict(list)
    for r in rows:
        by_pos[r["pos"]].append(r)          # already VOR-sorted

    priors, handle_to_fr = load_opponents()
    rosters = live_rosters(priors, handle_to_fr)
    tiers = {p: db.tiers(by_pos[p]) for p in SKILL}
    today = datetime.date.today().isoformat()

    lines = []
    say = lines.append
    say(f"# 2026 Decision Cards - {lg['name']}")
    say("")
    say(f"Generated {today} from live Sleeper projections and ADP. "
        f"**Regenerate the morning of 2026-09-08** - both move daily, and "
        f"injury statuses churn.")
    say("")
    say("Survival = P(available), normal pick-error model, sd fitted per ADP "
        "band to 2,039 of this league's own picks. Opponent urgency from "
        "Phase 3H priors (recency-weighted, shrunk; thin eras labelled). "
        "No champion mimicry - every call is VOR and tier math. Where two "
        "candidates sit in one tier the card says COIN FLIP: the projection "
        "feed has no variance measure, so break ties toward ceiling yourself.")
    say("")
    say("## The table, as mapped today")
    say("")
    say("| Roster | Handle | Franchise era | 1st QB prior | 1st TE prior | n_eff |")
    say("|---|---|---|---|---|---|")
    for r in rosters:
        if r["prior"]:
            p = r["prior"]
            say(f"| {r['roster_id']} | {r['handle']} | {r['franchise']} | "
                f"{p['first_qb_shrunk']} | {p['first_te_shrunk']} | "
                f"{p['first_qb_neff']}{' (thin)' if r['thin'] else ''} |")
        else:
            say(f"| {r['roster_id']} | {r['handle']} | (unmapped - league prior) "
                f"| - | - | - |")
    say("")

    for slot in range(1, TEAMS + 1):
        if slot_filter and slot != slot_filter:
            continue
        picks = snake_picks(slot)
        say(f"## Slot {slot} - picks {', '.join(map(str, picks[:8]))} ...")
        say("")
        say("| Rd | Pick | Primary (VOR, P surv) | Fallback | Deviation trigger |")
        say("|---|---|---|---|---|")
        for rnd, pick in enumerate(picks, 1):
            if rnd >= ROUNDS - 1:
                say(f"| {rnd} | {pick} | K or DEF, best available | - | "
                    f"none worth modelling |")
                continue
            # expected-available skill players at this pick
            avail = [(r, survival(r["adp"], pick)) for p in SKILL
                     for r in by_pos[p] if r["adp"] < 900]
            likely = [(r, s) for r, s in avail if s >= 0.5]
            likely.sort(key=lambda t: -t[0]["vor"])
            if not likely:
                say(f"| {rnd} | {pick} | best available skill | - | board empty "
                    f"in model - re-run live |")
                continue
            prim, ps = likely[0]
            # fallback: best likely-available from a different tier or position
            fall = next(((r, s) for r, s in likely[1:]
                         if r["pos"] != prim["pos"] or r["vor"] < prim["vor"] - 8),
                        likely[1] if len(likely) > 1 else (None, 0))
            # tier cliff: does the primary's tier survive a full turn?
            tier_of = next((t for t in tiers[prim["pos"]]
                            if any(x["name"] == prim["name"] for x in t)), [])
            cliff = sum(1 for x in tier_of if survival(x["adp"], pick + 2 * TEAMS) >= 0.5)
            triggers = []
            if cliff == 0 and tier_of:
                triggers.append(f"{prim['pos']} tier empties before your next "
                                f"turn - take now, do not wait")
            urgent = urgency_list(rosters, prim["pos"], rnd)
            if prim["pos"] in ("QB", "TE") and urgent:
                names = ", ".join(f"{f} (rd {pr:.1f}, n {ne:.1f})"
                                  for f, pr, ne in urgent[:3])
                triggers.append(f"{prim['pos']}-urgent seats: {names}")
            coin = [r["name"] for r, s in likely[1:4]
                    if r["pos"] == prim["pos"] and prim["vor"] - r["vor"] <= 8]
            if coin:
                triggers.append(f"COIN FLIP with {', '.join(coin[:2])} - "
                                f"break toward ceiling")
            if prim.get("injury"):
                triggers.append(f"{prim['name']} is {prim['injury']} - "
                                f"re-check draft morning")
            fb = (f"{fall[0]['name']} {fall[0]['pos']} {fall[0]['vor']:.0f}"
                  if fall[0] else "-")
            say(f"| {rnd} | {pick} | {prim['name']} {prim['pos']} "
                f"{prim['vor']:.0f} ({ps:.0%}) | {fb} | "
                f"{'; '.join(triggers) if triggers else 'none'} |")
        say("")

    say("---")
    say("")
    say(f"Baselines: " + ", ".join(f"{p} {baseline[p]:.1f}" for p in
                                   ("QB", "RB", "WR", "TE")) +
        f". Replacement ranks: QB{repl['QB']} RB{repl['RB']} WR{repl['WR']} "
        f"TE{repl['TE']}. Scoring verified live: 6-pt pass TD, full PPR.")
    say("")
    say("Expectation, set in advance: survival numbers are probabilities from "
        "13 drafts of history, not prophecy. The card tells you the price of "
        "waiting; it does not know what eleven humans will do.")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", type=int)
    a = ap.parse_args()
    text = build_cards(a.slot)
    os.makedirs("out", exist_ok=True)
    with open("out/decision_cards_2026.md", "w") as fh:
        fh.write(text + "\n")
    print(text[:3000])
    print(f"\n... wrote out/decision_cards_2026.md "
          f"({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()
