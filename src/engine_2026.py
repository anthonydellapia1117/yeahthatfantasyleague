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

build_model() returns structured data. Three renderers consume it:
out/decision_cards_2026.md (unchanged format), out/engine_2026.json
(for the draft room app), and an in-place injection into
out/draft_room.html between ENGINE-DATA sentinels so the standalone app
reflects a regeneration on reload. The app never parses markdown.

Honesty constraints, per the audit and the null results:
- No champion mimicry. Every recommendation is VOR and tier math.
- The projection feed carries NO variance measure, so "upside tilt" is
  implemented as flagging within-tier ties as coin flips for the owner
  to break toward ceiling - not as a fabricated variance stat.
- K and DEF projections are FLOORS - the feed omits 21 scoring keys this
  league pays. Carried on every surface that shows them.
- Probabilities carry their inputs. Thin priors are named as thin.
- K and DEF in the last two rounds. Not modelled beyond that.

Run (draft morning - projections and ADP move daily):

    python3 src/engine_2026.py                 # all 12 slots
    python3 src/engine_2026.py --slot 7        # one card printed
"""

import argparse
import csv
import json
import math
import os
import re
import sys
import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import draft_board as db

LEAGUE = "1389378429505241088"
DRAFT = "1389378429505241089"
ANTHONY_USER_ID = "345197760305307648"
TEAMS = 12
ROUNDS = 14
SKILL = ("QB", "RB", "WR", "TE")
COMPARABLE_VOR = 8.0        # within one tier for wait-or-reach and coin flips

# Pick-error sd as a SMOOTH function of ADP, fitted to 2,039 league picks 2013-2025
# by log-log OLS over 12 equal-count bins (R^2 = 0.917), capped at the observed max.
#
# This replaced a 4-band step function whose edges were catastrophic: sd jumped 5.46
# to 13.63 across ADP 24/25, so two players one slot apart got survival odds at pick
# 48 differing by 8,284x, and at pick 60 by 2.4e8. Those numbers drove live WAIT and
# TAKE NOW verdicts. A smooth sd removes the cliff entirely.
# FLOOR matters: the lowest observed bin is ADP 7 at sd 3.73. Extrapolating the
# power law below that gives sd 1.30 at ADP 1, which asserts a precision the data
# never showed and reintroduces a cliff at the very top of round 1.
ADP_SD_C, ADP_SD_B = 1.3035, 0.6127
ADP_SD_CAP, ADP_SD_FLOOR = 26.87, 3.73

MD_PATH = "out/decision_cards_2026.md"
JSON_PATH = "out/engine_2026.json"
APP_PATH = "out/draft_room.html"
SENTINEL_OPEN = "<script id=\"engine-data\" type=\"application/json\">"
SENTINEL_CLOSE = "</script><!--engine-data-end-->"


def sd_for(adp):
    return min(max(ADP_SD_C * max(adp, 1.0) ** ADP_SD_B, ADP_SD_FLOOR), ADP_SD_CAP)


def _raw_survival(adp, pick):
    if adp >= 900:
        return 1.0
    # erfc, not 1-erf: the latter loses the whole value to cancellation past z~5 and
    # returns exactly 0.0, which then trips cond_survival's zero guard and reports a
    # certain 0 percent where the truth is small but real.
    z = (pick - adp) / (sd_for(adp) * math.sqrt(2))
    return max(0.0, min(1.0, 0.5 * math.erfc(z)))


def survival(adp, pick):
    """P(player still on the board at overall pick `pick`).

    Normalized so survival(adp, 1) == 1 for every player. The bare normal model puts
    real probability mass BELOW pick 1 - an ADP-5 player loses 14 percent of his mass
    to picks that do not exist - which showed up as the consensus number-one player
    being only 50 percent likely to be available at pick 1, before anyone had drafted
    anything. Dividing by the mass at pick 1 renormalizes that impossible tail away.
    Ratios between two picks are unchanged, so cond_survival is unaffected.
    """
    if adp >= 900:
        return 1.0
    base = _raw_survival(adp, 1)
    if base <= 1e-12:
        return 0.0
    return max(0.0, min(1.0, _raw_survival(adp, pick) / base))


def cond_survival(adp, to_pick, from_pick):
    """P(survives to to_pick GIVEN still available at from_pick).

    The unconditional form charges hazard the player has already survived, and the
    normal model puts real mass before pick 1 for early-ADP players. The ratio
    renormalizes both away. Every wait-or-reach comparison must use this.
    """
    s_from = survival(adp, from_pick)
    if s_from <= 1e-9:
        return 0.0
    return max(0.0, min(1.0, survival(adp, to_pick) / s_from))


def snake_picks(slot):
    return [(r - 1) * TEAMS + (slot if r % 2 == 1 else TEAMS + 1 - slot)
            for r in range(1, ROUNDS + 1)]


def load_opponents():
    priors = {r["franchise"]: r
              for r in csv.DictReader(open("out/opponent_priors.csv"))}
    handle_to_fr = {r["sleeper_display_name"]: r["archive_member_name"]
                    for r in csv.DictReader(open("out/identity_map.csv"))}
    return priors, handle_to_fr


def live_rosters(priors, handle_to_fr):
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


def load_tendency():
    """franchise x round-band x pos -> lift, 1.00 being league average.

    DISPLAY ONLY. This is deliberately NOT folded into survival(). Tested
    2026-08-12: franchise identity does carry positional information (log loss
    1.4590 -> 1.4483, 9 of 10 seasons out-of-sample), but folding it into survival
    probability made the numbers WORSE, not better - pooled Brier 0.23030 -> 0.23050,
    3 of 10 seasons, paired permutation p = 0.9932. See out/tendency_backtest.json.
    The effect is real and about 0.7 percent; spread across 5-12 intervening picks it
    is smaller than the ADP noise it rides on. So the seats and their tendencies are
    shown as context for the owner's judgement, and the probabilities stay honest.
    """
    path = os.path.join("out", "positional_tendency.csv")
    if not os.path.exists(path):
        return {}
    return {(r["franchise"], r["band"], r["pos"]):
            {"lift": float(r["lift"]), "n": int(r["n_picks"]),
             "thin": r["confidence"] == "thin"}
            for r in csv.DictReader(open(path))}


def band_of(rnd):
    for lo, hi, name in ((1, 3, "rd1-3"), (4, 6, "rd4-6"),
                         (7, 10, "rd7-10"), (11, 14, "rd11-14")):
        if lo <= rnd <= hi:
            return name
    return "rd11-14"


def gap_seats(rosters, slot_map, pick, nxt, pos, tend):
    """Who picks between your turn and your next one, and how they lean.

    Returns the seats in pick order with each one's lift at `pos`, plus the mean.
    Context, not a probability input - see load_tendency().
    """
    out = []
    for overall in range(pick + 1, nxt):
        rnd = (overall - 1) // TEAMS + 1
        idx = overall - (rnd - 1) * TEAMS
        slot = idx if rnd % 2 == 1 else TEAMS + 1 - idx
        seat = slot_map.get(slot)
        if not seat:
            continue
        t = tend.get((seat["franchise"], band_of(rnd), pos))
        out.append({"pick": overall, "slot": slot, "handle": seat["handle"],
                    "franchise": seat["franchise"],
                    "lift": round(t["lift"], 2) if t else None,
                    "thin": bool(t and t["thin"])})
    lifts = [s["lift"] for s in out if s["lift"] is not None]
    return out, (round(sum(lifts) / len(lifts), 3) if lifts else None)


def urgency_list(rosters, pos, rnd):
    key = f"first_{pos.lower()}_shrunk"
    out = []
    for r in rosters:
        if not r["prior"]:
            continue
        prior_rnd = float(r["prior"][key])
        if prior_rnd <= rnd + 0.5:
            out.append({"franchise": r["franchise"], "round": prior_rnd,
                        "n_eff": float(r["prior"][f"first_{pos.lower()}_neff"])})
    return sorted(out, key=lambda t: t["round"])


def build_model():
    """Everything the renderers and the app need, as plain data."""
    lg, rows, baseline, repl = db.build(LEAGUE)
    by_pos = defaultdict(list)
    for r in rows:
        by_pos[r["pos"]].append(r)          # already VOR-sorted

    priors, handle_to_fr = load_opponents()
    rosters = live_rosters(priors, handle_to_fr)
    tend = load_tendency()
    # 2026 order is not drawn yet, so seat N is roster N until Sleeper says otherwise.
    slot_map = {r["roster_id"]: r for r in rosters}
    tiers = {p: db.tiers(by_pos[p]) for p in SKILL}
    tier_no = {}
    for p in SKILL:
        for i, t in enumerate(tiers[p], 1):
            for x in t:
                tier_no[x["name"]] = i

    slots = {}
    for slot in range(1, TEAMS + 1):
        picks = snake_picks(slot)
        rounds = []
        for rnd, pick in enumerate(picks, 1):
            nxt = picks[rnd] if rnd < ROUNDS else pick + 2 * TEAMS
            if rnd >= ROUNDS - 1:
                rounds.append({"round": rnd, "pick": pick,
                               "kdef": True, "primary": None})
                continue
            avail = [(r, survival(r["adp"], pick)) for p in SKILL
                     for r in by_pos[p] if r["adp"] < 900]
            likely = sorted([(r, s) for r, s in avail if s >= 0.5],
                            key=lambda t: -t[0]["vor"])
            if not likely:
                rounds.append({"round": rnd, "pick": pick,
                               "kdef": False, "primary": None})
                continue
            prim, ps = likely[0]
            fall = next(((r, s) for r, s in likely[1:]
                         if r["pos"] != prim["pos"]
                         or r["vor"] < prim["vor"] - COMPARABLE_VOR),
                        likely[1] if len(likely) > 1 else (None, 0))
            # WAIT-OR-REACH: best same-position comparable most likely to
            # survive to the NEXT turn. The centrepiece comparison.
            comp = None
            for r, _s in likely[1:]:
                if r["pos"] != prim["pos"]:
                    continue
                if prim["vor"] - r["vor"] > COMPARABLE_VOR:
                    break
                s_next = cond_survival(r["adp"], nxt, pick)
                if comp is None or s_next > comp["p_survives_next"]:
                    comp = {"name": r["name"], "vor": r["vor"],
                            "pts_gap": round(prim["pts"] - r["pts"], 1),
                            "p_survives_next": round(s_next, 3)}
            p_prim_next = cond_survival(prim["adp"], nxt, pick)
            verdict = ("WAIT" if comp and comp["p_survives_next"] >= 0.6
                       else "TAKE NOW")
            tier_of = next((t for t in tiers[prim["pos"]]
                            if any(x["name"] == prim["name"] for x in t)), [])
            cliff = sum(1 for x in tier_of
                        if cond_survival(x["adp"], pick + 2 * TEAMS, pick) >= 0.5)
            coin = [r["name"] for r, s in likely[1:4]
                    if r["pos"] == prim["pos"]
                    and prim["vor"] - r["vor"] <= COMPARABLE_VOR]
            urgent = (urgency_list(rosters, prim["pos"], rnd)
                      if prim["pos"] in ("QB", "TE") else [])
            seats, gap_lift = gap_seats(rosters, slot_map, pick, nxt,
                                        prim["pos"], tend)
            rounds.append({
                "round": rnd, "pick": pick, "next_pick": nxt, "kdef": False,
                "primary": {"name": prim["name"], "pos": prim["pos"],
                            "vor": prim["vor"], "pts": prim["pts"],
                            "adp": prim["adp"], "injury": prim["injury"],
                            "tier": tier_no.get(prim["name"]),
                            "p_available_now": round(ps, 3),
                            "p_gone_by_next": round(1 - p_prim_next, 3)},
                "fallback": ({"name": fall[0]["name"], "pos": fall[0]["pos"],
                              "vor": fall[0]["vor"]} if fall[0] else None),
                "wait_or_reach": {"verdict": verdict, "comparable": comp},
                "tier_cliff": cliff == 0 and bool(tier_of),
                "coin_flips": coin[:2],
                "urgent": urgent[:3],
                "gap_seats": seats,
                "gap_lift": gap_lift,
            })
        slots[slot] = rounds

    players = [{"name": r["name"], "pos": r["pos"], "team": r["team"],
                "pts": r["pts"], "vor": r["vor"], "adp": r["adp"],
                "injury": r["injury"], "tier": tier_no.get(r["name"]),
                "vor_rank": r["vor_rank"],
                "floor": r["pos"] in ("K", "DEF")}
               for r in rows if r["adp"] < 900 or r["vor"] > 0]

    return {
        "generated": datetime.date.today().isoformat(),
        "league": {"id": LEAGUE, "draft_id": DRAFT, "name": lg["name"],
                   "teams": TEAMS, "rounds": ROUNDS,
                   "draft_date": "2026-09-08",
                   "anthony_user_id": ANTHONY_USER_ID,
                   "anthony_roster_id": 7,
                   "scoring": "full PPR, 6-pt pass TD",
                   "starters": " ".join(lg["slots"])},
        "baselines": {p: baseline[p] for p in baseline},
        "replacement_ranks": dict(repl),
        "adp_sd_fit": {"c": ADP_SD_C, "b": ADP_SD_B, "cap": ADP_SD_CAP, "floor": ADP_SD_FLOOR,
                       "form": "sd(adp) = min(max(c * adp**b, floor), cap)"},
        "tendency_note": ("gap_lift is CONTEXT, not a probability input. Folding it into survival made the model worse out-of-sample: Brier 0.23030 to 0.23050, 3 of 10 seasons, paired permutation p=0.9932. See out/tendency_backtest.json."),
        "adp_sd_note": ("normal pick-error model, sd a smooth power law fitted to "
                        "2,039 of this league's own picks 2013-2025"),
        "kdef_note": ("K and DEF projections are FLOORS - the Sleeper feed "
                      "omits 21 scoring keys this league pays, including all "
                      "sub-40 FG brackets and pts_allow brackets"),
        "rosters": [{"roster_id": r["roster_id"], "handle": r["handle"],
                     "franchise": r["franchise"], "thin": r["thin"],
                     "first_qb": (float(r["prior"]["first_qb_shrunk"])
                                  if r["prior"] else None),
                     "first_te": (float(r["prior"]["first_te_shrunk"])
                                  if r["prior"] else None),
                     "n_eff": (float(r["prior"]["first_qb_neff"])
                               if r["prior"] else None)}
                    for r in rosters],
        "players": players,
        "slots": slots,
    }


def render_markdown(m):
    lines = []
    say = lines.append
    say(f"# 2026 Decision Cards - {m['league']['name']}")
    say("")
    say(f"Generated {m['generated']} from live Sleeper projections and ADP. "
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
    for r in m["rosters"]:
        if r["first_qb"] is not None:
            say(f"| {r['roster_id']} | {r['handle']} | {r['franchise']} | "
                f"{r['first_qb']:g} | {r['first_te']:g} | "
                f"{r['n_eff']:g}{' (thin)' if r['thin'] else ''} |")
        else:
            say(f"| {r['roster_id']} | {r['handle']} | (unmapped - league prior) "
                f"| - | - | - |")
    say("")
    for slot in range(1, TEAMS + 1):
        rounds = m["slots"][slot]
        first8 = ", ".join(str(r["pick"]) for r in rounds[:8])
        say(f"## Slot {slot} - picks {first8} ...")
        say("")
        say("| Rd | Pick | Primary (VOR, P surv) | Fallback | Deviation trigger |")
        say("|---|---|---|---|---|")
        for r in rounds:
            if r["kdef"]:
                say(f"| {r['round']} | {r['pick']} | K or DEF, best available "
                    f"| - | none worth modelling |")
                continue
            if not r["primary"]:
                say(f"| {r['round']} | {r['pick']} | best available skill | - "
                    f"| board empty in model - re-run live |")
                continue
            p = r["primary"]
            triggers = []
            if r["tier_cliff"]:
                triggers.append(f"{p['pos']} tier empties before your next "
                                f"turn - take now, do not wait")
            if r["urgent"]:
                names = ", ".join(f"{u['franchise']} (rd {u['round']:.1f}, "
                                  f"n {u['n_eff']:.1f})" for u in r["urgent"])
                triggers.append(f"{p['pos']}-urgent seats: {names}")
            if r["coin_flips"]:
                triggers.append(f"COIN FLIP with "
                                f"{', '.join(r['coin_flips'])} - "
                                f"break toward ceiling")
            if p["injury"]:
                triggers.append(f"{p['name']} is {p['injury']} - "
                                f"re-check draft morning")
            fb = (f"{r['fallback']['name']} {r['fallback']['pos']} "
                  f"{r['fallback']['vor']:.0f}" if r["fallback"] else "-")
            say(f"| {r['round']} | {r['pick']} | {p['name']} {p['pos']} "
                f"{p['vor']:.0f} ({p['p_available_now']:.0%}) | {fb} | "
                f"{'; '.join(triggers) if triggers else 'none'} |")
        say("")
    say("---")
    say("")
    say("Baselines: " + ", ".join(f"{p} {m['baselines'][p]:.1f}"
                                  for p in ("QB", "RB", "WR", "TE")) +
        f". Replacement ranks: QB{m['replacement_ranks']['QB']} "
        f"RB{m['replacement_ranks']['RB']} WR{m['replacement_ranks']['WR']} "
        f"TE{m['replacement_ranks']['TE']}. Scoring verified live: "
        f"6-pt pass TD, full PPR.")
    say("")
    say("Expectation, set in advance: survival numbers are probabilities from "
        "13 drafts of history, not prophecy. The card tells you the price of "
        "waiting; it does not know what eleven humans will do.")
    return "\n".join(lines) + "\n"


def inject_app(m):
    """Replace the JSON between the sentinels in draft_room.html, if present."""
    if not os.path.exists(APP_PATH):
        return False
    html = open(APP_PATH).read()
    if SENTINEL_OPEN not in html or SENTINEL_CLOSE not in html:
        print(f"WARNING: sentinels missing in {APP_PATH}, not injected",
              file=sys.stderr)
        return False
    payload = json.dumps(m, separators=(",", ":"))
    pre, rest = html.split(SENTINEL_OPEN, 1)
    _, post = rest.split(SENTINEL_CLOSE, 1)
    open(APP_PATH, "w").write(pre + SENTINEL_OPEN + payload +
                              SENTINEL_CLOSE + post)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", type=int)
    a = ap.parse_args()

    m = build_model()
    md = render_markdown(m)
    os.makedirs("out", exist_ok=True)
    open(MD_PATH, "w").write(md)
    with open(JSON_PATH, "w") as fh:
        json.dump(m, fh, separators=(",", ":"))
    injected = inject_app(m)

    if a.slot:
        start = md.index(f"## Slot {a.slot} ")
        end = md.index("## Slot", start + 1) if a.slot < TEAMS else md.index("---", start)
        print(md[:md.index("## Slot 1 ")] + md[start:end])
    print(f"wrote {MD_PATH} ({len(md.splitlines())} lines)")
    print(f"wrote {JSON_PATH} ({os.path.getsize(JSON_PATH)//1024} KB)")
    print(f"draft room app {'updated in place' if injected else 'not present'}")


if __name__ == "__main__":
    main()
