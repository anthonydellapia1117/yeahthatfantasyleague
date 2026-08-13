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

# Pick-error sd as a piecewise-linear interpolation of 12 equal-count empirical
# bins over the 2,039 league picks 2013-2025 with recoverable ADP. Adopted after
# the survival audit (docs/AUDIT_SURVIVAL_2026-08-12.md): leave-one-season-out,
# INTERP beat the step function 12 of 13 seasons (two-sided p=0.0034) and the
# power-law refit 10 of 13; it is the only comparison that reached significance.
# It is continuous (no ADP cliff), needs no floor or cap (the ends are the
# observed end bins), and expresses what a monotone power law cannot: the
# empirical sd peaks near ADP 100 and DECLINES toward the end of the draft.
#
# History, because each shape encoded a live bug or a lost backtest:
# - 4-band step: sd jumped 5.46 to 13.63 across ADP 24/25, survival odds for
#   adjacent ADP slots differed by 8,284x at pick 48. Cliff drove verdicts.
# - power law min(max(1.3035*adp^0.6127, 3.73), 26.87): removed the cliff but
#   held sd at the cap across ADP 115-200 where the truth falls to 20, and was
#   a statistical wash against the step out of sample.
PICKS_PATH = "out/picks.csv"
ADP_SD_BINS = 12

MD_PATH = "out/decision_cards_2026.md"
JSON_PATH = "out/engine_2026.json"
APP_PATH = "out/draft_room.html"
SENTINEL_OPEN = "<script id=\"engine-data\" type=\"application/json\">"
SENTINEL_CLOSE = "</script><!--engine-data-end-->"


def fit_sd_curve(picks_path=PICKS_PATH, nbins=ADP_SD_BINS):
    """(mean_adp, sd) per equal-count ADP bin - the whole model, no functional form.

    Deterministic from the committed picks table; the same 12 pairs are embedded
    in engine_2026.json so the JS mirror interpolates identical numbers instead
    of re-deriving anything. The two surfaces must never diverge again.
    """
    data = []
    for p in csv.DictReader(open(picks_path)):
        d = p.get("adp_differential")
        if not d:
            continue
        try:
            d = float(d)
        except ValueError:
            continue
        y = float(p["overall"])
        data.append((y - d, y))
    data.sort()
    n = len(data)
    curve = []
    for i in range(nbins):
        chunk = data[i * n // nbins:(i + 1) * n // nbins]
        diffs = [y - adp for adp, y in chunk]
        mu = sum(diffs) / len(diffs)
        sd = math.sqrt(sum((x - mu) ** 2 for x in diffs) / (len(diffs) - 1))
        curve.append((sum(a for a, _ in chunk) / len(chunk), sd))
    return curve


ADP_SD_CURVE = fit_sd_curve()


def sd_for(adp):
    c = ADP_SD_CURVE
    if adp <= c[0][0]:
        return c[0][1]
    if adp >= c[-1][0]:
        return c[-1][1]
    for (a0, s0), (a1, s1) in zip(c, c[1:]):
        if a0 <= adp <= a1:
            return s0 + (adp - a0) / (a1 - a0) * (s1 - s0)
    return c[-1][1]


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


def pick_history():
    """overall pick -> dominant position and share, from 2,339 archive picks."""
    from collections import Counter
    agg = defaultdict(Counter)
    for p in csv.DictReader(open(PICKS_PATH)):
        try:
            agg[int(p["overall"])][p["pos"]] += 1
        except (ValueError, KeyError):
            continue
    out = {}
    for overall, c in agg.items():
        pos, n = c.most_common(1)[0]
        total = sum(c.values())
        out[str(overall)] = {"pos": pos, "share": round(n / total, 2), "n": total}
    return out


def pos_base_rates():
    """League position share per round band, from the 2,339 archive picks.
    The simulator's sampling base - lifts multiply these, display/sim only."""
    from collections import Counter
    bands = {"rd1-3": (1, 3), "rd4-6": (4, 6), "rd7-10": (7, 10), "rd11-14": (11, 14)}
    agg = {b: Counter() for b in bands}
    for p in csv.DictReader(open(PICKS_PATH)):
        try:
            rnd = int(p["round"])
        except (ValueError, KeyError):
            continue
        for b, (lo, hi) in bands.items():
            if lo <= rnd <= hi:
                agg[b][p["pos"]] += 1
                break
    out = {}
    for b, c in agg.items():
        total = sum(c.values()) or 1
        out[b] = {pos: round(n / total, 4) for pos, n in c.items()
                  if pos in ("QB", "RB", "WR", "TE", "K", "DEF")}
    return out


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

    players = [{"name": r["name"], "sleeper_id": r.get("sleeper_id", ""),
                "pos": r["pos"], "team": r["team"],
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
        "adp_sd_curve": [[round(a, 2), round(s, 4)] for a, s in ADP_SD_CURVE],
        "survival_reference": [
            # Python-computed anchors the JS mirror must reproduce (parity test).
            # Includes a deep-tail case that the old 1-erf JS collapsed to 0.
            {"adp": adp, "pick": k, "s": survival(adp, k)}
            for adp in (1, 5, 24, 25, 60, 100, 150)
            for k in (1, 7, 30, 60, 120, 168)
        ],
        "tendency_note": ("gap_lift is CONTEXT, not a probability input. Folding it into survival made the model worse out-of-sample: Brier 0.23030 to 0.23050, 3 of 10 seasons, paired permutation p=0.9932. See out/tendency_backtest.json."),
        "adp_sd_note": ("normal pick-error model, sd piecewise-linear over 12 "
                        "empirical ADP bins from 2,039 of this league's own picks "
                        "2013-2025; adopted over the power law per "
                        "docs/AUDIT_SURVIVAL_2026-08-12.md"),
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
                               if r["prior"] else None),
                     # full dossier: every position's shrunk first-round prior
                     # and n_eff (feature 14 - the payload used to drop these)
                     "priors": ({p: {"round": float(r["prior"][f"first_{p}_shrunk"]),
                                     "n_eff": float(r["prior"][f"first_{p}_neff"])}
                                 for p in ("qb", "rb", "wr", "te", "k", "def")}
                                if r["prior"] else None),
                     "lifts": ([{"band": band, "pos": pos, "lift": v["lift"],
                                 "n": v["n"], "thin": v["thin"]}
                                for (fr, band, pos), v in tend.items()
                                if fr == r["franchise"]] or None)}
                    for r in rosters],
        # feature 15: what this pick slot has historically been, 13 seasons of
        # out/picks.csv aggregated at build time. Descriptive colour only.
        "pick_history": pick_history(),
        "pos_base_rates": pos_base_rates(),
        "players": players,
        "slots": slots,
    }


# ======== OVERLAY-BEGIN (Phase B) ========
# Conviction overlay: data/my_board.csv, applied AFTER build_model as a pure
# transform. Structurally outside the model - the guard test proves the board
# reaches no survival or wait-or-reach arithmetic. Its one decision role is
# the coin-flip tie-break toward bulls; everything else is display. With an
# empty board apply_overlay returns the model untouched, byte for byte.
MY_BOARD_PATH = "data/my_board.csv"


def _norm_name(s):
    # mirrors the JS norm() so both surfaces match calls the same way
    s = re.sub(r"[.']", "", str(s).lower())
    return re.sub(r"\s+(jr|sr|ii|iii|iv|v)$", "", s).strip()


def load_my_board(path=MY_BOARD_PATH):
    if not os.path.exists(path):
        return []
    rows = [ln for ln in open(path) if not ln.lstrip().startswith("#")]
    calls = []
    for row in csv.DictReader(rows):
        player = (row.get("player") or "").strip()
        call = (row.get("call") or "").strip().upper()
        if not player or call not in ("BULL", "BEAR"):
            continue
        calls.append({"player": player, "call": call,
                      "move": (row.get("move") or "").strip(),
                      "reason": (row.get("reason") or "").strip(),
                      "source": (row.get("source") or "").strip(),
                      "confidence": (row.get("confidence") or "").strip(),
                      "date": (row.get("date") or "").strip()})
    return calls


def apply_overlay(m, calls):
    """Pure transform. Empty board -> m returned untouched (guarded byte-identity).

    Populated board -> adds m["my_board"] (display data + survival of each bull
    to each slot-7 pick, computed WITH the frozen survival(), never into it)
    and stamps coin_break on rounds where a bull sits in an existing coin flip.
    Verdicts, primaries, and every survival number are never rewritten.
    """
    if not calls:
        return m
    by_norm = {_norm_name(p["name"]): p for p in m["players"]}
    my_picks = [r["pick"] for r in
                (m["slots"].get(7) or m["slots"].get("7") or [])][:4]
    board = []
    bulls = set()
    for c in calls:
        p = by_norm.get(_norm_name(c["player"]))
        entry = dict(c)
        entry["matched"] = bool(p)
        if p:
            entry.update({"pos": p["pos"], "adp": p["adp"], "vor": p["vor"],
                          "tier": p["tier"]})
            if c["call"] == "BULL":
                bulls.add(p["name"])
                entry["survival_to_my_picks"] = [
                    [k, round(survival(p["adp"], k), 3)] for k in my_picks]
        board.append(entry)
    m["my_board"] = board
    date_of = {c["player"]: c["date"] for c in calls if c["call"] == "BULL"}
    for rounds in m["slots"].values():
        for r in rounds:
            if r.get("kdef") or not r.get("primary"):
                continue
            flip_names = list(r.get("coin_flips") or [])
            if not flip_names:
                continue
            # tie-break toward bulls - the overlay's ONE decision role.
            # The primary (the wait-or-reach subject) is never replaced.
            toward = next((n for n in [r["primary"]["name"]] + flip_names
                           if n in bulls), None)
            if toward:
                r["coin_break"] = {"toward": toward,
                                   "call_date": next(
                                       (d for pl, d in date_of.items()
                                        if _norm_name(pl) == _norm_name(toward)),
                                       "")}
    return m
# ======== OVERLAY-END ========


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
        rounds = m["slots"].get(slot) or m["slots"][str(slot)]
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
                cb = r.get("coin_break")
                triggers.append(f"COIN FLIP with "
                                f"{', '.join(r['coin_flips'])} - "
                                + (f"break toward your call - {cb['toward']}"
                                   if cb else "break toward ceiling"))
            if p["injury"]:
                triggers.append(f"{p['name']} is {p['injury']} - "
                                f"re-check draft morning")
            fb = (f"{r['fallback']['name']} {r['fallback']['pos']} "
                  f"{r['fallback']['vor']:.0f}" if r["fallback"] else "-")
            say(f"| {r['round']} | {r['pick']} | {p['name']} {p['pos']} "
                f"{p['vor']:.0f} ({p['p_available_now']:.0%}) | {fb} | "
                f"{'; '.join(triggers) if triggers else 'none'} |")
        say("")
    if m.get("my_board"):
        say("## MY BOARD - conviction overlay (display; one decision role)")
        say("")
        say("Calls from data/my_board.csv, scored by the pre-registered rule "
            "in its header. The model's primary stays the wait-or-reach "
            "subject; the only decision the overlay touches is the coin-flip "
            "tie-break toward bulls.")
        say("")
        say("| Player | Call | Move | Survival to picks (slot 7) | Reason (source, date) |")
        say("|---|---|---|---|---|")
        for c in m["my_board"]:
            if not c["matched"]:
                say(f"| {c['player']} | {c['call']} | {c['move'] or '-'} | "
                    f"UNMATCHED - not in the projection feed | "
                    f"{c['reason']} ({c['source']}, {c['date']}) |")
                continue
            sv = (", ".join(f"{k}: {s:.0%}" for k, s in c["survival_to_my_picks"])
                  if c.get("survival_to_my_picks") else "-")
            say(f"| {c['player']} | {c['call']} | {c['move'] or '-'} | {sv} | "
                f"{c['reason']} ({c['source']}, {c['date']}) |")
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

    m = apply_overlay(build_model(), load_my_board())
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
