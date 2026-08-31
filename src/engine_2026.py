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
- K and DEF projections are FLOORS - 21 configured scoring keys (19 nonzero)
  are absent verbatim, and DEF touchdown components use four unaliased feed
  names. Carried on every surface that shows them.
- Probabilities carry their inputs. Thin priors are named as thin.
- K and DEF in the last two rounds. Not modelled beyond that.

Run (draft morning - projections and ADP move daily):

    python3 src/engine_2026.py                 # all 12 slots
    python3 src/engine_2026.py --slot 4        # primary card printed
"""

import argparse
import csv
import hashlib
import io
import json
import math
import os
import sys
import datetime
import statistics

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from forward_policy import pick_marginal, roster_caps  # noqa: E402
from engine_lineage import stamp as stamp_engine  # noqa: E402
from player_names import PlayerIdentityResolver, comparison_key  # noqa: E402
from draft_order import (DraftOrderResolutionError, load_reported_order,
                         reconcile_owner_slot, reported_order_basis,
                         resolve_owner_slot)  # noqa: E402
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import draft_board as db

LEAGUE = "1389378429505241088"
DRAFT = "1389378429505241089"
ANTHONY_USER_ID = "345197760305307648"
ANTHONY_ROSTER_ID = 7
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
REPORTED_ORDER_PATH = "data/draft_order_2026.json"
POSITIONAL_TIMING_PATH = "out/positional_timing.csv"
POSITIONAL_TIMING_COLUMNS = (
    "season", "franchise", "first_qb", "first_rb", "first_wr", "first_te",
    "first_k", "first_def", "is_champion", "source", "confidence")
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


# ---- survival calibration layer (ADOPTED 2026-08-19, Anthony, scope ii).
# The five frozen functions above are UNTOUCHED - this is a monotone 20-bin
# lookup applied AFTER them, correcting the normal model's thin late tail
# (fallers keep falling; the frozen model says "gone" too confidently below
# 50 percent predicted survival). Table = the 2019-2025 era fit, chosen over
# the all-years blend by a pre-registered rule (the eras differ by up to
# 0.111 per bin and straddle the 0.6 verdict threshold; the modern fit is
# not worse on the 2023-2025 holdout). Full evidence, the fallback table,
# and both flip intervals: out/data/survival_recalibration.json and the
# MODEL.md ADR. Kill switches: this flag (rebuild-level) and the room's
# one-tap CALIBRATED SURVIVAL toggle (display-level).
SURVIVAL_CALIBRATION = [0.2749, 0.2749, 0.2749, 0.3559, 0.431, 0.431,
                        0.4632, 0.5484, 0.5484, 0.6448, 0.6448, 0.6929,
                        0.7487, 0.7487, 0.8062, 0.8834, 0.9182, 0.946,
                        0.9795, 0.9974]
SURVIVAL_CALIBRATION_ENABLED = True


def calibrated_cond_survival(adp, to_pick, from_pick):
    """cond_survival, then the calibration lookup. Monotone by construction,
    so it can rescale confidence but never reorder two players."""
    p = cond_survival(adp, to_pick, from_pick)
    if not SURVIVAL_CALIBRATION_ENABLED:
        return p
    return SURVIVAL_CALIBRATION[min(len(SURVIVAL_CALIBRATION) - 1,
                                    int(p * len(SURVIVAL_CALIBRATION)))]


def snake_picks(slot):
    return [(r - 1) * TEAMS + (slot if r % 2 == 1 else TEAMS + 1 - slot)
            for r in range(1, ROUNDS + 1)]


def load_first_position_history(path=POSITIONAL_TIMING_PATH,
                                with_provenance=False):
    """Raw descriptive first-position medians and n by franchise.

    These are deliberately separate from the recency-weighted, shrunk priors.
    The user-facing drawn-order table asks what each known seat did, with raw
    sample size; this evidence never enters survival or a verdict.
    """
    raw = open(path, "rb").read()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if tuple(reader.fieldnames or ()) != POSITIONAL_TIMING_COLUMNS:
        raise RuntimeError(
            "positional timing schema moved; raw manager-history table blocked")
    rows = list(reader)
    if not rows:
        raise RuntimeError("positional timing is empty")
    grouped = defaultdict(lambda: defaultdict(list))
    seasons = defaultdict(set)
    seen = set()
    all_seasons = set()
    for row in rows:
        if None in row or any(value is None for value in row.values()):
            raise RuntimeError("positional timing row disagrees with its schema")
        franchise = row["franchise"].strip()
        try:
            season = int(row["season"])
        except (TypeError, ValueError) as exc:
            raise RuntimeError("positional timing has a non-integer season") from exc
        key = (season, franchise)
        if (not franchise or franchise != row["franchise"] or
                str(season) != row["season"] or key in seen):
            raise RuntimeError(
                "positional timing has a noncanonical or duplicate "
                "season/franchise row")
        if row["source"] != "out/picks.csv" or row["confidence"] != "verified":
            raise RuntimeError(
                "positional timing lost its verified out/picks.csv provenance")
        seen.add(key)
        all_seasons.add(season)
        seasons[franchise].add(season)
        if row["is_champion"] not in ("0", "1"):
            raise RuntimeError("positional timing has invalid champion status")
        for pos in ("qb", "rb", "wr", "te", "k", "def"):
            value = row.get(f"first_{pos}")
            if value in (None, ""):
                continue
            try:
                observed = float(value)
            except (TypeError, ValueError) as exc:
                raise RuntimeError(
                    f"positional timing has a non-numeric first_{pos}") from exc
            if not math.isfinite(observed) or not observed.is_integer() or observed < 1:
                raise RuntimeError(
                    f"positional timing first_{pos} is not a positive round")
            if pos in ("qb", "rb", "wr", "te"):
                grouped[franchise][pos].append(observed)
    out = {}
    for franchise in set(grouped) | set(seasons):
        out[franchise] = {
            "seasons": len(seasons[franchise]),
            "positions": {
                pos: ({"median_round": statistics.median(values),
                       "min_round": min(values),
                       "max_round": max(values),
                       "n": len(values)} if values else None)
                for pos in ("qb", "rb", "wr", "te")
                for values in [grouped[franchise][pos]]
            },
        }
    provenance = {
        "path": path,
        "source_content_sha256": hashlib.sha256(raw).hexdigest(),
        "schema": list(POSITIONAL_TIMING_COLUMNS),
        "key": ["season", "franchise"],
        "rows": len(rows),
        "franchises": len(seasons),
        "seasons": len(all_seasons),
        "season_min": min(all_seasons),
        "season_max": max(all_seasons),
        "duplicate_keys": 0,
        "source": "out/picks.csv",
        "confidence": "verified",
    }
    return (out, provenance) if with_provenance else out


def derive_overlay_pick_basis(draft, reported_order=None):
    """Provenance for conviction-overlay pick windows from one draft payload."""
    if reported_order is not None:
        return reconcile_owner_slot(
            draft, reported_order, ANTHONY_USER_ID, ANTHONY_ROSTER_ID,
            TEAMS)
    resolved = resolve_owner_slot(
        draft, ANTHONY_USER_ID, ANTHONY_ROSTER_ID, TEAMS)
    if resolved["drawn"] and resolved["slot"] is None:
        raise DraftOrderResolutionError(
            resolved["source"],
            "draft order is drawn but Anthony's slot is not resolvable: "
            f"{resolved['source']}")
    return {
        "status": "drawn" if resolved["drawn"] else "undrawn",
        "slot": resolved["slot"], "source": resolved["source"],
        # All slots stay in the populated overlay even after the draw. The
        # selected alias is convenience, not the only surviving evidence.
        "coverage": "all_slots",
    }


def reconcile_draft_start(draft, reported_order):
    """Return the verified epoch, rejecting present malformed/live conflicts."""
    verified = reported_order["draft_start"]["epoch_ms"]
    live = (draft if isinstance(draft, dict) else {}).get("start_time")
    if live is None:
        return verified
    if type(live) is not int or live <= 0:
        raise RuntimeError("Sleeper draft start is present but malformed")
    if live != verified:
        raise RuntimeError(
            "Sleeper draft start disagrees with the committed verified "
            f"snapshot: {live} vs {verified}")
    return live


def reported_slot_context(reported_order, rosters, first_position_history):
    """Partial display map for the externally drawn manager order.

    This deliberately is not a Sleeper roster-id permutation. Slots 3 and 7
    have unresolved 2026 identities and remain unresolved; known franchises
    contribute description-only history and never enter survival arithmetic.
    """
    by_franchise = {r["franchise"]: r for r in rosters}
    owner_rosters = [r for r in rosters
                     if str(r.get("owner_id")) == ANTHONY_USER_ID]
    if len(owner_rosters) != 1:
        raise RuntimeError(
            "live rosters do not identify Anthony's user exactly once")
    owner_franchise = owner_rosters[0]["franchise"]
    slots, lookup = [], {}
    for raw in reported_order["slots"]:
        row = dict(raw)
        franchise = row.get("history_franchise")
        historical = by_franchise.get(franchise) if franchise else None
        if franchise and historical is None:
            raise RuntimeError(
                f"reported slot {row['slot']} history franchise is unmapped: "
                f"{franchise}")
        if franchise and franchise not in first_position_history:
            raise RuntimeError(
                f"reported slot {row['slot']} lacks raw positional history: "
                f"{franchise}")
        if (row["history_status"] == "owner" and
                (historical is None or
                 historical.get("roster_id") != ANTHONY_ROSTER_ID or
                 franchise != owner_franchise)):
            raise RuntimeError(
                "reported owner history does not map to Anthony's user and "
                f"stable roster id {ANTHONY_ROSTER_ID}")
        row["history_available"] = historical is not None
        slots.append(row)
        lookup[row["slot"]] = {
            "handle": row["reported_label"],
            "reported_label": row["reported_label"],
            "franchise": franchise,
            "history_franchise": franchise,
            "history_status": row["history_status"],
            "thin": bool(historical and historical["thin"]),
            "prior": historical["prior"] if historical else None,
        }
    return slots, lookup


def load_opponents():
    prior_rows = list(csv.DictReader(open("out/opponent_priors.csv")))
    identity_rows = list(csv.DictReader(open("out/identity_map.csv")))
    for rows, key, label in (
            (prior_rows, "franchise", "opponent prior franchise"),
            (identity_rows, "sleeper_display_name", "Sleeper display name"),
            (identity_rows, "archive_member_name", "archive franchise")):
        values = [r.get(key, "").strip() for r in rows]
        if any(not value for value in values) or len(set(values)) != len(values):
            raise RuntimeError(f"duplicate or blank {label} in identity inputs")
    priors = {r["franchise"]: r for r in prior_rows}
    handle_to_fr = {r["sleeper_display_name"]: r["archive_member_name"]
                    for r in identity_rows}
    return priors, handle_to_fr


def live_rosters(priors, handle_to_fr):
    users = {u["user_id"]: u
             for u in db.get(f"https://api.sleeper.app/v1/league/{LEAGUE}/users")}
    rosters = db.get(f"https://api.sleeper.app/v1/league/{LEAGUE}/rosters")
    out = []
    for r in sorted(rosters, key=lambda x: x["roster_id"]):
        u = users.get(r.get("owner_id")) or {}
        handle = u.get("display_name", "?")
        # The Sleeper team name is what Anthony sees on the draft board
        # ("Taylor Made" for antdell); most managers leave it unset. It is
        # DISPLAY ONLY and deliberately separate from `franchise`, which is
        # the archive member name that joins 13 seasons of history and must
        # never move.
        team = ((u.get("metadata") or {}).get("team_name") or "").strip() or None
        fr = handle_to_fr.get(handle)
        row = priors.get(fr) if fr else None
        out.append({"roster_id": r["roster_id"], "handle": handle,
                    "owner_id": r.get("owner_id"),
                    "team_name": team,
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
        franchise = seat.get("history_franchise", seat.get("franchise"))
        t = (tend.get((franchise, band_of(rnd), pos))
             if franchise else None)
        out.append({"pick": overall, "slot": slot,
                    "handle": seat.get("handle"),
                    "label": seat.get("reported_label", seat.get("handle")),
                    "franchise": franchise,
                    "history_status": seat.get("history_status", "known"),
                    "lift": round(t["lift"], 2) if t else None,
                    "n": int(t["n"]) if t else None,
                    "thin": bool(t and t["thin"])})
    lifts = [s["lift"] for s in out if s["lift"] is not None]
    return out, (round(sum(lifts) / len(lifts), 3) if lifts else None)


def tier_survivors_at_next(tier, pick, nxt):
    """Count median-or-better tier survivors at the owner's actual next pick."""
    return sum(1 for player in tier
               if cond_survival(player["adp"], nxt, pick) >= 0.5)


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
    The simulator's sampling base. Manager lifts remain display only after
    their probability fold failed out of sample (p=0.9932)."""
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
    first_position_history, first_position_provenance = \
        load_first_position_history(with_provenance=True)
    reported_order = load_reported_order(
        REPORTED_ORDER_PATH, DRAFT, ANTHONY_USER_ID, TEAMS, ROUNDS)
    reported_slots, slot_map = reported_slot_context(
        reported_order, rosters, first_position_history)
    tiers = {p: db.tiers(by_pos[p]) for p in SKILL}
    tier_no = {}
    for p in SKILL:
        for i, t in enumerate(tiers[p], 1):
            for x in t:
                tier_no[x["name"]] = i

    slots = {}
    caps = roster_caps(lg.get("flex_alloc", {}))
    for slot in range(1, TEAMS + 1):
        picks = snake_picks(slot)
        rounds = []
        # FORWARD-PICK LAW (shared with the mock simulator via
        # forward_policy): a multi-pick projection consumes its own prior
        # selections. Each round's primary leaves the pool, and the next
        # round is solved with the marginal-lineup policy against what
        # remains - never the same player at consecutive picks, never a
        # duplicate elite position priced at starter value.
        consumed = set()
        proj_roster = []
        for rnd, pick in enumerate(picks, 1):
            if rnd >= ROUNDS - 1:
                rounds.append({"round": rnd, "pick": pick,
                               "kdef": True, "primary": None})
                continue
            nxt = picks[rnd]
            avail = [(r, survival(r["adp"], pick)) for p in SKILL
                     for r in by_pos[p] if r["adp"] < 900
                     and r["name"] not in consumed]
            likely = sorted([(r, s) for r, s in avail if s >= 0.5],
                            key=lambda t: -t[0]["vor"])
            if not likely:
                rounds.append({"round": rnd, "pick": pick,
                               "kdef": False, "primary": None})
                continue
            prim = pick_marginal([r for r, _s in likely], proj_roster,
                                 baseline, caps)
            if prim is None:      # every position capped: relax the caps
                prim = pick_marginal([r for r, _s in likely], proj_roster,
                                     baseline, None)
            ps = next(s for r, s in likely if r is prim)
            others = [(r, s) for r, s in likely if r is not prim]
            consumed.add(prim["name"])
            proj_roster.append({"name": prim["name"], "pos": prim["pos"],
                                "pts": prim["pts"]})
            fall = next(((r, s) for r, s in others
                         if r["pos"] != prim["pos"]
                         or r["vor"] < prim["vor"] - COMPARABLE_VOR),
                        others[0] if others else (None, 0))
            # WAIT-OR-REACH: best same-position comparable most likely to
            # survive to the NEXT turn. The centrepiece comparison.
            comp = None
            for r, _s in others:
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
            # The snake gap is seat-specific. ``pick + 2*teams`` is only the
            # same seat two rounds later; at slot 4 it turns a 4->21 question
            # into 4->28 and can invent a cliff in the seven-pick difference.
            cliff = tier_survivors_at_next(tier_of, pick, nxt)
            coin = [r["name"] for r, s in others[:3]
                    if r["pos"] == prim["pos"]
                    and prim["vor"] - r["vor"] <= COMPARABLE_VOR]
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
                # Tendency prediction was rejected out of sample (p=0.9932).
                # Raw, n-labelled history stays in gap_seats and the order
                # table, but it creates no thresholded urgency trigger.
                "urgent": [],
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

    # Seat provenance for the conviction overlay. Before the draw, Sleeper's
    # slot map is the identity placeholder; roster_id 7 is identity, not seat.
    # Preserve every slot hypothesis rather than silently treating those two
    # integers as interchangeable. A drawn but unresolvable order is fatal: a
    # wrong selected slot would produce plausible, incorrect survival numbers.
    try:
        draft = db.get(f"https://api.sleeper.app/v1/draft/{DRAFT}")
    except Exception as exc:  # preserve all hypotheses, but never hide the outage
        print(f"WARNING: draft-order endpoint unavailable: {exc}",
              file=sys.stderr)
        overlay_pick_basis = reported_order_basis(
            reported_order, "unavailable",
            sleeper_source="draft_endpoint_unavailable")
    else:
        reconcile_draft_start(draft, reported_order)
        overlay_pick_basis = derive_overlay_pick_basis(draft, reported_order)

    draft_order_context = {
        "status": "externally_drawn",
        "primary_slot": reported_order["owner"]["slot"],
        "primary_picks": reported_order["owner"]["picks"],
        "source": reported_order["source"],
        "sleeper_confirmation": overlay_pick_basis["official_check"],
        "coverage": "all_slots",
        "slots": reported_slots,
        "description_only": ("manager history never enters survival, VOR, "
                             "or a verdict; slots 3 and 7 remain unresolved"),
        "manager_history_provenance": first_position_provenance,
    }

    return {
        "generated": datetime.date.today().isoformat(),
        "league": {"id": LEAGUE, "draft_id": DRAFT, "name": lg["name"],
                   "teams": TEAMS, "rounds": ROUNDS,
                   "draft_date": "2026-09-08",
                   "draft_start_time": reported_order["draft_start"]["epoch_ms"],
                   "draft_start_source": reported_order["draft_start"],
                   "anthony_user_id": ANTHONY_USER_ID,
                   "anthony_roster_id": ANTHONY_ROSTER_ID,
                   "scoring": "full PPR, 6-pt pass TD",
                   "starters": " ".join(lg["slots"])},
        "baselines": {p: baseline[p] for p in baseline},
        "replacement_ranks": dict(repl),
        # flex allocation is DERIVED - observed league behavior (2025 matchup
        # starters, out/data/flex_usage_2025.json) or projection-greedy fallback;
        # the old assumed 50/50 RB/WR split is gone
        "flex_allocation": lg.get("flex_alloc", {}),
        "flex_source": lg.get("flex_source", ""),
        "overlay_pick_basis": overlay_pick_basis,
        "draft_order_context": draft_order_context,
        "adp_sd_curve": [[round(a, 2), round(s, 4)] for a, s in ADP_SD_CURVE],
        "survival_calibration": SURVIVAL_CALIBRATION,
        "survival_calibration_enabled": SURVIVAL_CALIBRATION_ENABLED,
        "calibration_reference": [
            # Python-computed calibrated anchors the JS wrapper must
            # reproduce - the same cross-language parity pattern as
            # survival_reference, so the smoke check is not circular
            {"adp": adp, "from_pick": c, "to_pick": k,
             "cal": calibrated_cond_survival(adp, k, c)}
            for adp, k, c in ((24, 18, 7), (60, 40, 10), (5, 18, 7),
                              (100, 120, 60), (1.7, 70, 60))
        ],
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
        "kdef_note": ("K and DEF projections are FLOORS - 21 configured "
                      "league keys (19 nonzero) are absent verbatim; DEF TD "
                      "components use unaliased feed keys def_fum_td, "
                      "def_kr_td, pass_int_td, and pr_td"),
        "rosters": [{"roster_id": r["roster_id"], "handle": r["handle"],
                     # Sleeper team name, display only; null when the manager
                     # never set one. `franchise` stays the history join key.
                     "team_name": r["team_name"],
                     "franchise": r["franchise"], "thin": r["thin"],
                     "history_first": first_position_history.get(
                         r["franchise"]),
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
    to every slot's picks, computed WITH the frozen survival(), never into it)
    and stamps coin_break on rounds where a bull sits in an existing coin flip.
    Verdicts, primaries, and every survival number are never rewritten.
    """
    if not calls:
        return m
    resolver = PlayerIdentityResolver(m["players"])
    basis = m.get("overlay_pick_basis") or {}
    selected_slot = basis.get("slot")
    slot_picks = {
        str(slot): [r["pick"] for r in
                    (m["slots"].get(slot) or
                     m["slots"].get(str(slot)) or [])][:4]
        for slot in range(1, int(m["league"]["teams"]) + 1)
    }
    board = []
    bulls = set()
    for c in calls:
        p = resolver.resolve(c["player"]).record
        entry = dict(c)
        entry["matched"] = bool(p)
        if p:
            entry.update({"sleeper_id": p["sleeper_id"], "pos": p["pos"],
                          "adp": p["adp"], "vor": p["vor"],
                          "tier": p["tier"]})
            if c["call"] == "BULL":
                bulls.add(p["name"])
                entry["survival_to_slots"] = {
                    slot: [[k, round(survival(p["adp"], k), 3)]
                           for k in picks]
                    for slot, picks in slot_picks.items()
                }
                if selected_slot is not None:
                    entry["survival_to_my_picks"] = entry[
                        "survival_to_slots"][str(selected_slot)]
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
                                        if comparison_key(pl) == comparison_key(toward)),
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
    say(f"Engine content SHA-256: `{m['content_sha256']}`.")
    say("")
    say("Survival = P(available), normal pick-error model, sd fitted per ADP "
        "band to 2,039 of this league's own picks. Live-seat dossiers use "
        "recency-weighted, current-era shrunk history with n_eff; the order "
        "table separately reports raw full-franchise medians and n. Both are "
        "description only: "
        "the tendency probability fold was rejected (p=0.9932), so history "
        "creates no urgency trigger. "
        "No champion mimicry - every call is VOR and tier math. Where two "
        "candidates sit in one tier the card says COIN FLIP: the projection "
        "feed has no variance measure, so break ties toward ceiling yourself.")
    say("")
    order_ctx = m.get("draft_order_context") or {}
    primary_slot = order_ctx.get("primary_slot")
    if primary_slot is not None:
        say(f"**Primary planning seat: slot {primary_slot}** - externally "
            f"reported draw, Sleeper confirmation "
            f"{order_ctx.get('sleeper_confirmation')}. The other "
            f"{m['league']['teams'] - 1} slot calculations remain below as "
            "references; manager history is description only and never "
            "enters a probability or verdict.")
        say("")
    say("## Historical first-position timing, as mapped today")
    say("")
    say("Description only; raw median round with n observed seasons. The "
        "tendency backtest remains null (p=0.9932), so none of this enters "
        "survival or a verdict.")
    say("")
    say("| Slot | Drawn seat | History franchise | Seasons | 1st RB | 1st WR | 1st QB | 1st TE |")
    say("|---|---|---|---|---|---|---|---|")
    by_franchise = {r["franchise"]: r for r in m["rosters"]}
    for seat in order_ctx.get("slots", []):
        r = by_franchise.get(seat.get("history_franchise"))
        history = r.get("history_first") if r else None
        if history:
            cells = []
            for pos in ("rb", "wr", "qb", "te"):
                observed = history["positions"].get(pos)
                cells.append((f"{observed['median_round']:g} "
                              f"(range {observed['min_round']:g}-"
                              f"{observed['max_round']:g}; n {observed['n']})")
                             if observed else "-")
            say(f"| {seat['slot']} | {seat['reported_label']} | "
                f"{r['franchise']} | {history['seasons']} | " +
                " | ".join(cells) + " |")
        else:
            say(f"| {seat['slot']} | {seat['reported_label']} | "
                "history unresolved | - | - | - | - | - |")
    say("")
    slot_order = ([primary_slot] if primary_slot is not None else []) + [
        slot for slot in range(1, TEAMS + 1) if slot != primary_slot]
    for slot in slot_order:
        rounds = m["slots"].get(slot) or m["slots"][str(slot)]
        first8 = ", ".join(str(r["pick"]) for r in rounds[:8])
        primary_mark = " - PRIMARY" if slot == primary_slot else " - reference"
        say(f"## Slot {slot}{primary_mark} - picks {first8} ...")
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
        basis = m.get("overlay_pick_basis") or {}
        selected_slot = basis.get("slot")
        if basis.get("official_check") == "unavailable":
            say(f"Draft-order endpoint was unavailable at build time; the "
                f"externally reported owner slot {selected_slot} remains the "
                "planning basis, with confirmation visibly unavailable. "
                "Survival windows for all twelve slots are retained in the "
                "JSON artifact.")
        elif selected_slot is None:
            say("Draft order is not resolved; no seat is assumed. Survival "
                "windows for all twelve slots are retained in the JSON artifact.")
        else:
            say(f"Draft-order source: {basis.get('source')}; owner slot "
                f"{selected_slot}; Sleeper check "
                f"{basis.get('official_check', 'not recorded')}. All twelve "
                "slot windows remain in the JSON.")
        say("")
        survival_head = (f"Survival to picks (slot {selected_slot})"
                         if selected_slot is not None
                         else "Survival coverage")
        say(f"| Player | Call | Move | {survival_head} | Reason (source, date) |")
        say("|---|---|---|---|---|")
        for c in m["my_board"]:
            if not c["matched"]:
                say(f"| {c['player']} | {c['call']} | {c['move'] or '-'} | "
                    f"UNMATCHED - not in the projection feed | "
                    f"{c['reason']} ({c['source']}, {c['date']}) |")
                continue
            if c.get("survival_to_my_picks"):
                sv = ", ".join(f"{k}: {s:.0%}"
                               for k, s in c["survival_to_my_picks"])
            elif c.get("survival_to_slots"):
                sv = "all 12 slots precomputed; no owner slot assumed"
            else:
                sv = "-"
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
    """Replace the draft-room payload; absence is fatal in this repository."""
    if not os.path.exists(APP_PATH):
        raise RuntimeError(f"draft-room app missing at {APP_PATH}")
    html = open(APP_PATH).read()
    if SENTINEL_OPEN not in html or SENTINEL_CLOSE not in html:
        raise RuntimeError(f"engine sentinels missing in {APP_PATH}")
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
    stamp_engine(m)
    md = render_markdown(m)
    os.makedirs("out", exist_ok=True)
    open(MD_PATH, "w").write(md)
    with open(JSON_PATH, "w") as fh:
        json.dump(m, fh, separators=(",", ":"))
    injected = inject_app(m)

    if a.slot:
        start = md.index(f"## Slot {a.slot} ")
        next_heading = md.find("## Slot", start + 1)
        end = next_heading if next_heading >= 0 else md.index("---", start)
        print(md[:md.index("## Slot")] + md[start:end])
    print(f"wrote {MD_PATH} ({len(md.splitlines())} lines)")
    print(f"wrote {JSON_PATH} ({os.path.getsize(JSON_PATH)//1024} KB)")
    print(f"draft room app {'updated in place' if injected else 'not present'}")


if __name__ == "__main__":
    main()
