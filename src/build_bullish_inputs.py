#!/usr/bin/env python3
"""C5 stage 1: every computed input the BULLISH matrices consume.

No analyzed figure is imported from a narrative document or R export. The one
path under ``docs/ffopportunity`` is a machine-refreshed 2026 schedule snapshot;
this module independently validates and prices it from literal game lines.
Proportions carry k and n so the tag engine can put Wilson intervals on them;
continuous metrics carry weekly SEs. Team state resolves from current depth
charts; role stats (inside-5 share, receiving market share) are 2025-role priors
and say so.

Blocks:
  players   per-player computed metrics by position group
  teams     Week-1 2026 implied totals (dated), td-per-point rate (computed
            from 2025 actuals), 2025 team YBC/att (current-team line quality)
  thresholds  percentile thresholds with the distributions behind them
  qb_gap    the settings-correction derivation: rushing-vs-pocket QB value
            under EXACT league scoring (6-pt) vs the 4-pt counterfactual,
            2016-2025, n and CI

Sources: cached nflverse files in the history dir (participation, ftn, pbp,
advrush, games.csv, spw weekly), repo shards, live Sleeper depth state via
the committed depth_charts.json.

Run: python3 src/build_bullish_inputs.py
"""
import csv
import datetime
import hashlib
import inspect
import json
import math
import os
from collections import defaultdict

from analyze_recency import HISTORY
from engine_lineage import (file_content_sha256, json_content_sha256,
                            require as require_engine_digest)
from player_names import PlayerIdentityResolver
from team_codes import CANONICAL_NFL_TEAMS, canonical_team

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "out", "data")
OUT = os.path.join(D, "bullish_inputs_2026.json")
FORWARD_SCHEDULE_REL = "docs/ffopportunity/schedule_2026.csv"
FORWARD_SCHEDULE = os.path.join(ROOT, FORWARD_SCHEDULE_REL)
FORWARD_META_REL = "docs/ffopportunity/schedule_2026.meta.json"
FORWARD_META = os.path.join(ROOT, FORWARD_META_REL)
NFL_REGULAR_SEASON_GAMES_PER_TEAM = 17

W = {"passing_yards": 0.04, "passing_tds": 6.0, "passing_interceptions": -1.0,
     "passing_2pt_conversions": 2.0,
     "rushing_yards": 0.1, "rushing_tds": 6.0, "rushing_2pt_conversions": 2.0,
     "receptions": 1.0, "receiving_yards": 0.1, "receiving_tds": 6.0,
     "receiving_2pt_conversions": 2.0,
     "sack_fumbles_lost": -2.0, "rushing_fumbles_lost": -2.0,
     "receiving_fumbles_lost": -2.0, "special_teams_tds": 6.0}
W4 = dict(W, passing_tds=4.0)            # the counterfactual for the QB gap


def pctile(vals, q):
    vals = sorted(vals)
    if not vals:
        return None
    i = max(0, min(len(vals) - 1, int(round(q * (len(vals) - 1)))))
    return vals[i]


def observed_share(observations, player_id, minimum_total=100):
    """Return an observed share; absence is null while observed zero is valid."""
    if not player_id or player_id not in observations:
        return None
    vals = list(observations.values())
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
           not math.isfinite(v) or v < 0 for v in vals):
        raise ValueError("share observations must be finite non-negative numbers")
    total = sum(vals)
    if total < minimum_total:
        return None
    return {"value": round(observations[player_id] / total, 4),
            "player": observations[player_id], "total": total}


def _validated_rb_usage(usage_rows):
    """Return canonical 2025 RB usage rows keyed by player identity.

    `usage_2025.json` is already one season row per player. Rejecting duplicate
    identities here keeps a future producer change from silently assigning one
    player's carries to two denominators.
    """
    canonical = set(CANONICAL_NFL_TEAMS)
    rows = {}
    for row in usage_rows:
        if row.get("pos") != "RB":
            continue
        player_id = str(row.get("gsis_id") or "").strip()
        team = canonical_team(row.get("team"))
        carries = row.get("carries")
        if not player_id or player_id in rows:
            raise ValueError(
                "2025 RB usage contains a blank or duplicate player identity")
        if team not in canonical:
            raise ValueError(
                f"2025 RB usage contains an unresolved historical team: {team}")
        if (isinstance(carries, bool) or not isinstance(carries, (int, float)) or
                not math.isfinite(carries) or carries < 0):
            raise ValueError(
                f"2025 RB usage contains invalid carries for {player_id}")
        rows[player_id] = {"team": team, "carries": carries}
    return rows


def _rb_backfield_samples(usage_rows, assigned_teams, minimum_total=100):
    """Build player shares after assigning every observed row to one team."""
    usage_by_player = _validated_rb_usage(usage_rows)
    canonical = set(CANONICAL_NFL_TEAMS)
    by_team = defaultdict(dict)
    for player_id, usage_row in usage_by_player.items():
        team = assigned_teams.get(player_id)
        if team is None:
            continue
        team = canonical_team(team)
        if team not in canonical:
            raise ValueError(
                f"RB denominator assignment has an unresolved team: {team}")
        by_team[team][player_id] = usage_row["carries"]

    samples = {}
    for team, observations in by_team.items():
        for player_id in observations:
            share = observed_share(observations, player_id, minimum_total)
            if share is not None:
                samples[player_id] = {
                    "value": share["value"],
                    "season": 2025,
                    "team": team,
                    "player_carries": share["player"],
                    "team_rb_carries": share["total"],
                }
    return samples


def historical_rb_backfield_samples(carry_ledger, minimum_total=100):
    """Build exact historical-team shares from player-team carry rows.

    Every row contributes to its historical team's denominator. A player with
    positive carries for multiple teams has no single share and is therefore
    null rather than assigned by row order; his split rows still remain in both
    team denominators.
    """
    canonical = set(CANONICAL_NFL_TEAMS)
    by_team = defaultdict(dict)
    player_rows = defaultdict(list)
    seen = set()
    for row in carry_ledger:
        player_id = str(row.get("gsis_id") or "").strip()
        team = canonical_team(row.get("team"))
        carries = row.get("carries")
        key = (player_id, team)
        if not player_id or key in seen:
            raise ValueError(
                "RB player-team carry ledger has a blank or duplicate identity/team")
        if team not in canonical:
            raise ValueError(
                f"RB player-team carry ledger has an unresolved team: {team}")
        if (isinstance(carries, bool) or not isinstance(carries, (int, float)) or
                not math.isfinite(carries) or carries < 0):
            raise ValueError(
                f"RB player-team carry ledger has invalid carries for {player_id}")
        seen.add(key)
        by_team[team][player_id] = carries
        player_rows[player_id].append((team, carries))

    samples = {}
    for player_id, rows in player_rows.items():
        positive_teams = [team for team, carries in rows if carries > 0]
        if len(positive_teams) == 1:
            team = positive_teams[0]
        elif not positive_teams and len(rows) == 1:
            team = rows[0][0]
        else:
            continue
        share = observed_share(by_team[team], player_id, minimum_total)
        if share is not None:
            samples[player_id] = {
                "value": share["value"],
                "season": 2025,
                "team": team,
                "player_carries": share["player"],
                "team_rb_carries": share["total"],
            }
    return samples


def current_roster_rb_backfield_counterfactual(usage_rows, depth_rows,
                                               minimum_total=100):
    """Reproduce the retired bug: group 2025 usage by the 2026 depth team."""
    assigned = {}
    for row in depth_rows:
        if row.get("pos") != "RB":
            continue
        player_id = str(row.get("gsis_id") or "").strip()
        if player_id.lower() in ("", "none", "null", "nan"):
            continue
        if player_id in assigned:
            raise ValueError(
                "2026 RB depth chart contains a duplicate identity")
        assigned[player_id] = canonical_team(row.get("team"))
    return _rb_backfield_samples(usage_rows, assigned, minimum_total)


def distribution(vals, name, qs=(0.5, 0.75, 0.8), *,
                 excluded_unobserved_n=0, observation_rule="finite observed values"):
    """Describe a percentile population without converting absence to zero."""
    if excluded_unobserved_n < 0:
        raise ValueError("excluded_unobserved_n cannot be negative")
    clean = []
    for value in vals:
        if (isinstance(value, bool) or not isinstance(value, (int, float)) or
                not math.isfinite(value)):
            raise ValueError(f"{name} contains a non-finite observation")
        clean.append(value)
    return {
        "n": len(clean),
        "zero_n": sum(value == 0 for value in clean),
        "excluded_unobserved_n": excluded_unobserved_n,
        "observation_rule": observation_rule,
        "percentile_method": "nearest index: round(q * (n - 1))",
        **{f"p{int(q * 100)}": (round(pctile(clean, q), 4)
                                  if clean else None) for q in qs},
    }


def derive_forward_vegas(rows):
    """Derive the maximal fully priced 2026 REG prefix from schedule rows.

    The returned team totals are canonical and averaged only across the
    contiguous complete horizon. A partial week ends the horizon; it never
    contributes a partially observed team sample.
    """
    by_week = defaultdict(list)
    game_ids = set()
    canonical = set(CANONICAL_NFL_TEAMS)
    for row in rows:
        if str(row.get("season") or "") != "2026" or row.get("game_type") != "REG":
            continue
        try:
            week = int(row["week"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("forward schedule contains an invalid week")
        game_id = str(row.get("game_id") or "").strip()
        if not game_id or game_id in game_ids:
            raise ValueError("forward schedule contains a blank or duplicate game_id")
        game_ids.add(game_id)
        home = canonical_team(row.get("home_team"))
        away = canonical_team(row.get("away_team"))
        if home not in canonical or away not in canonical or home == away:
            raise ValueError(
                f"forward schedule has unresolved teams in {game_id}: {home}/{away}")

        raw_total = str(row.get("total_line") or "").strip()
        raw_spread = str(row.get("spread_line") or "").strip()
        total = spread = None
        line_state = "unpriced"
        if raw_total and raw_spread:
            try:
                total, spread = float(raw_total), float(raw_spread)
            except ValueError:
                raise ValueError(f"forward schedule has non-numeric lines: {game_id}")
            if not math.isfinite(total) or not math.isfinite(spread):
                raise ValueError(f"forward schedule has non-finite lines: {game_id}")
            line_state = "priced"
        elif raw_total or raw_spread:
            # Sportsbooks can post one side of the pair first. That makes the
            # game unpriced for horizon purposes; it must not invalidate an
            # earlier contiguous, fully priced prefix.
            line_state = "partial"
        by_week[week].append({"game_id": game_id, "home": home, "away": away,
                              "total": total, "spread": spread,
                              "line_state": line_state})

    weeks = sorted(by_week)
    if not weeks or weeks != list(range(1, weeks[-1] + 1)):
        raise ValueError("forward schedule weeks must be contiguous from week 1")
    for week, games in by_week.items():
        seen = set()
        for game in games:
            pair = {game["home"], game["away"]}
            if seen & pair:
                raise ValueError(f"team appears twice in forward schedule week {week}")
            seen |= pair

    # Reconcile the input as a complete NFL regular-season schedule before
    # judging pricing coverage. Otherwise a missing row can make a week look
    # fully priced relative only to the rows that survived the omission.
    season_team_games = defaultdict(int)
    for games in by_week.values():
        for game in games:
            season_team_games[game["home"]] += 1
            season_team_games[game["away"]] += 1
    expected_games = (len(CANONICAL_NFL_TEAMS) *
                      NFL_REGULAR_SEASON_GAMES_PER_TEAM // 2)
    if (set(season_team_games) != canonical or
            set(season_team_games.values()) !=
            {NFL_REGULAR_SEASON_GAMES_PER_TEAM} or
            len(game_ids) != expected_games):
        raise ValueError(
            "forward schedule is not a complete 32-team regular season: "
            f"games={len(game_ids)}/{expected_games}, "
            f"team_games={dict(sorted(season_team_games.items()))}")

    coverage = []
    selected_weeks = []
    for week in weeks:
        games = by_week[week]
        priced = sum(g["total"] is not None and g["spread"] is not None
                     for g in games)
        partial = sum(g["line_state"] == "partial" for g in games)
        coverage.append({"week": week, "priced_games": priced,
                         "scheduled_games": len(games),
                         "partial_line_games": partial,
                         "complete": priced == len(games)})
        if len(selected_weeks) == week - 1 and priced == len(games):
            selected_weeks.append(week)
    if not selected_weeks:
        raise ValueError("forward schedule has no fully priced opening week")

    team_values = defaultdict(list)
    game_count = 0
    for week in selected_weeks:
        for game in by_week[week]:
            total, spread = game["total"], game["spread"]
            home_total = total / 2 + spread / 2
            away_total = total / 2 - spread / 2
            if (not math.isclose(home_total + away_total, total) or
                    not math.isclose(home_total - away_total, spread)):
                raise ValueError("forward implied-total sign invariant failed")
            team_values[game["home"]].append(home_total)
            team_values[game["away"]].append(away_total)
            game_count += 1

    if set(team_values) != canonical:
        missing = sorted(canonical - set(team_values))
        extra = sorted(set(team_values) - canonical)
        raise ValueError(f"forward horizon team coverage mismatch: missing={missing}, extra={extra}")
    if sum(map(len, team_values.values())) != 2 * game_count:
        raise ValueError("forward horizon team-game reconciliation failed")

    totals = {team: round(sum(team_values[team]) / len(team_values[team]), 2)
              for team in CANONICAL_NFL_TEAMS}
    team_game_counts = {team: len(team_values[team])
                        for team in CANONICAL_NFL_TEAMS}
    boundary = next((x for x in coverage if x["week"] == selected_weeks[-1] + 1),
                    None)

    def pricing_digest(weeks_to_hash):
        decision_rows = [
            {
                "game_id": game["game_id"],
                "week": week,
                "home": game["home"],
                "away": game["away"],
                "total": game["total"],
                "spread": game["spread"],
            }
            for week in weeks_to_hash
            for game in by_week[week]
        ]
        decision_rows.sort(key=lambda row: (row["week"], row["game_id"]))
        payload = json.dumps(
            decision_rows, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    return {
        "implied_total": totals,
        "weeks": selected_weeks,
        "game_count": game_count,
        "team_game_count": 2 * game_count,
        "team_game_counts": team_game_counts,
        "full_schedule_games": len(game_ids),
        "regular_season_games_per_team": NFL_REGULAR_SEASON_GAMES_PER_TEAM,
        "coverage": coverage,
        "boundary": boundary,
        "decision_input_sha256": pricing_digest(selected_weeks),
        "pricing_by_week_sha256": {
            str(week): pricing_digest([week]) for week in selected_weeks
        },
    }


def forward_model_logic_sha256():
    """Digest the derivation itself, separately from changing schedule data."""
    return hashlib.sha256(
        inspect.getsource(derive_forward_vegas).encode("utf-8")
    ).hexdigest()


def classify_forward_transition(previous_provenance, previous_totals,
                                current_provenance, current_totals):
    """Classify the schedule-driven decision-input change between builds.

    Event priority follows the decision window, not raw source bytes. A source
    can change outside the selected horizon while the actual QB/WR input stays
    identical; that is UNCHANGED with source_changed=true, not REPRICED.
    """
    previous_provenance = previous_provenance or current_provenance
    previous_totals = previous_totals or current_totals

    def state(provenance):
        weeks = list(provenance.get("weeks") or [])
        games = provenance.get("games_priced", provenance.get("games"))
        team_games = provenance.get(
            "team_games_priced", provenance.get("team_games"))
        return {
            "source_content_sha256": provenance.get(
                "snapshot_content_sha256",
                provenance.get("source_content_sha256")),
            "upstream_content_sha256": provenance.get(
                "upstream_content_sha256"),
            "model_logic_sha256": provenance.get("model_logic_sha256"),
            "decision_input_sha256": provenance.get("decision_input_sha256"),
            "pricing_by_week_sha256": dict(
                provenance.get("pricing_by_week_sha256") or {}),
            "weeks": weeks,
            "first_week": weeks[0] if weeks else None,
            "last_week": weeks[-1] if weeks else None,
            "games_priced": games,
            "team_games_priced": team_games,
            "next_partial_week": provenance.get("next_partial_week"),
        }

    prior = state(previous_provenance)
    current = state(current_provenance)
    prior_last = prior["last_week"] or 0
    current_last = current["last_week"] or 0
    prior_games = prior["games_priced"] or 0
    current_games = current["games_priced"] or 0
    horizon_contracted = (current_last < prior_last or
                          (current_last == prior_last and
                           current_games < prior_games))
    horizon_extended = (current_last > prior_last or
                        (current_last == prior_last and
                         current_games > prior_games))
    totals_changed = previous_totals != current_totals
    prior_decision_digest = prior.get("decision_input_sha256")
    current_decision_digest = current.get("decision_input_sha256")
    pricing_changed = (
        prior_decision_digest != current_decision_digest
        if prior_decision_digest is not None and current_decision_digest is not None
        else totals_changed
    )
    if horizon_contracted:
        event = "CONTRACTED"
    elif horizon_extended:
        event = "HORIZON_EXTENDED"
    elif pricing_changed or totals_changed:
        event = "REPRICED"
    else:
        event = "UNCHANGED"

    prior_model = prior.get("model_logic_sha256")
    current_model = current.get("model_logic_sha256")
    model_changed = (prior_model != current_model
                     if prior_model is not None and current_model is not None
                     else None)
    source_changed = (
        prior.get("source_content_sha256") !=
        current.get("source_content_sha256") or
        (prior.get("upstream_content_sha256") is not None and
         current.get("upstream_content_sha256") is not None and
         prior.get("upstream_content_sha256") !=
         current.get("upstream_content_sha256")))
    prior_week_hashes = prior.get("pricing_by_week_sha256") or {}
    current_week_hashes = current.get("pricing_by_week_sha256") or {}
    common_weeks = set(prior_week_hashes) & set(current_week_hashes)
    prior_horizon_repriced = any(
        prior_week_hashes[week] != current_week_hashes[week]
        for week in common_weeks
    )
    if event == "UNCHANGED":
        attribution = "NO_FORWARD_DECISION_INPUT_CHANGE"
    elif model_changed is False and pricing_changed:
        attribution = "SCHEDULE_INPUT"
    elif model_changed is True and not pricing_changed:
        attribution = "MODEL_LOGIC"
    elif model_changed is True and pricing_changed:
        attribution = "MIXED_SOURCE_AND_MODEL"
    else:
        attribution = "SAME_BUILD_COUNTERFACTUAL_REQUIRED"

    return {
        "event": event,
        "attribution": attribution,
        "prior": prior,
        "current": current,
        "flags": {
            "source_changed": source_changed,
            "coverage_changed": (
                prior["weeks"] != current["weeks"] or
                prior["games_priced"] != current["games_priced"] or
                prior["team_games_priced"] != current["team_games_priced"] or
                prior["next_partial_week"] != current["next_partial_week"]),
            "horizon_changed": prior["weeks"] != current["weeks"],
            "implied_totals_changed": totals_changed,
            "decision_pricing_changed": pricing_changed,
            "model_logic_changed": model_changed,
            "prior_horizon_repriced": prior_horizon_repriced,
        },
        "contracted_response": (
            "FAIL CLOSED: do not overwrite the last verified snapshot or tags; "
            "a shorter priced horizon can reflect an unpriced game or source "
            "hiccup and must be reviewed before changing the decision window."),
    }


def enforce_forward_transition(transition):
    """Refuse a narrower live decision window; the prior verified build stays."""
    if transition.get("event") == "CONTRACTED":
        prior = transition["prior"]
        current = transition["current"]
        raise ValueError(
            "forward Vegas horizon CONTRACTED; refusing to publish "
            f"W1-{prior['last_week']} / {prior['games_priced']} games -> "
            f"W1-{current['last_week']} / {current['games_priced']} games. "
            + transition["contracted_response"])


def require_implied_total_map(values, label):
    """Require one finite implied-total value for every canonical NFL team."""
    if not isinstance(values, dict) or set(values) != set(CANONICAL_NFL_TEAMS):
        raise ValueError(
            f"{label} does not cover exactly 32 canonical NFL teams")
    invalid = {
        team: value for team, value in values.items()
        if isinstance(value, bool) or not isinstance(value, (int, float)) or
        not math.isfinite(value)
    }
    if invalid:
        raise ValueError(f"{label} has non-finite/non-numeric values: {invalid}")
    return values


def validate_sync_transition(sync_transition, prior_totals,
                             current_provenance, current_totals):
    """Rederive producer metadata before trusting its event or counterfactual."""
    if not isinstance(sync_transition, dict):
        raise ValueError("forward schedule metadata has no sync transition")
    require_implied_total_map(prior_totals, "forward prior implied totals")
    require_implied_total_map(current_totals, "forward current implied totals")
    expected = classify_forward_transition(
        sync_transition.get("prior"), prior_totals,
        current_provenance, current_totals)
    if sync_transition != expected:
        raise ValueError(
            "forward schedule sync transition is not self-consistent with its "
            f"prior/current inputs: expected {expected}, got {sync_transition}")
    enforce_forward_transition(expected)
    return expected


def select_forward_transition(sync_transition, build_transition,
                              sync_prior_totals, previous_output_totals,
                              current_totals):
    """Select an honest event and a current-code schedule counterfactual.

    The sync producer rederives both its prior snapshot and current snapshot with
    the current code, so its prior totals are the preferred schedule-only frame.
    A previous artifact is usable only to recover a schedule change that landed
    without a paired output, and only when both artifacts carry identical model
    logic. Mixed model/schedule movement fails instead of being misattributed.
    """
    require_implied_total_map(sync_prior_totals,
                              "forward sync-prior implied totals")
    require_implied_total_map(current_totals,
                              "forward current implied totals")
    sync_material = sync_transition["event"] != "UNCHANGED"
    build_material = build_transition["event"] != "UNCHANGED"

    if sync_material and build_material:
        decision_fields = (
            "model_logic_sha256", "decision_input_sha256",
            "pricing_by_week_sha256", "weeks", "games_priced",
            "team_games_priced", "next_partial_week")
        same_prior_frame = all(
            sync_transition["prior"].get(field) ==
            build_transition["prior"].get(field)
            for field in decision_fields)
        same_event = (
            sync_transition["event"] == build_transition["event"] and
            sync_transition["attribution"] == build_transition["attribution"])
        same_prior_totals = (
            isinstance(previous_output_totals, dict) and
            previous_output_totals == sync_prior_totals)
        if not (same_prior_frame and same_event and same_prior_totals):
            raise ValueError(
                "forward schedule sync and prior-artifact transitions are both "
                "material but disagree; refusing to publish ambiguous attribution")
        return sync_transition, sync_prior_totals

    if sync_material:
        # A deterministic rerun after the output was already rebuilt still
        # carries the producer's material event and current-code prior frame.
        return sync_transition, sync_prior_totals

    if build_material:
        attribution = build_transition.get("attribution")
        if attribution == "MODEL_LOGIC":
            # Schedule did not move. Comparing the sync producer's two
            # current-code frames correctly yields a zero schedule-only delta.
            return build_transition, sync_prior_totals
        if attribution == "SCHEDULE_INPUT":
            require_implied_total_map(
                previous_output_totals,
                "forward prior-artifact implied totals")
            prior_model = build_transition["prior"].get("model_logic_sha256")
            current_model = build_transition["current"].get("model_logic_sha256")
            if not prior_model or prior_model != current_model:
                raise ValueError(
                    "cannot recover a schedule-only counterfactual across "
                    "different or missing model-logic digests")
            return build_transition, previous_output_totals
        raise ValueError(
            "forward model and schedule changed without one current-code prior "
            "schedule frame; refusing to label a same-build counterfactual")

    return sync_transition, sync_prior_totals


def main():
    # Keep the pure parsing/contract helpers importable in the Pages gate, whose
    # Python environment intentionally does not carry the analysis-only package.
    import pyarrow.parquet as pq

    previous_output = None
    if os.path.exists(OUT):
        with open(OUT) as fh:
            previous_output = json.load(fh)

    games_path = os.path.join(HISTORY, "games.csv")
    games_pulled = datetime.datetime.fromtimestamp(
        os.path.getmtime(games_path), tz=datetime.timezone.utc).date().isoformat()

    # ---- pbp: dropbacks, targets, receiving yards, receiver ids, TDs/points
    pbp = pq.read_table(
        os.path.join(HISTORY, "pbp_2025.parquet"),
        columns=["nflverse_game_id" if False else "game_id", "play_id",
                 "season_type", "posteam", "qb_dropback", "pass_attempt",
                 "receiver_player_id", "receiver_player_name",
                 "receiving_yards", "pass_touchdown", "rush_touchdown",
                 "week"]).to_pydict()
    n_plays = len(pbp["play_id"])

    team_dropbacks = defaultdict(int)
    tgt = defaultdict(int)               # receiver id -> targets
    rec_yds = defaultdict(float)
    rcv_team = {}
    rcv_name = {}
    off_tds = defaultdict(int)
    dropback_keys = {}                   # (game_id, play_id) -> posteam
    for i in range(n_plays):
        if pbp["season_type"][i] != "REG":
            continue
        team = pbp["posteam"][i]
        if pbp["qb_dropback"][i] == 1 and team:
            team_dropbacks[team] += 1
            dropback_keys[(pbp["game_id"][i], pbp["play_id"][i])] = team
        rid = pbp["receiver_player_id"][i]
        if rid and pbp["pass_attempt"][i] == 1:
            tgt[rid] += 1
            rcv_team[rid] = team
            rcv_name[rid] = pbp["receiver_player_name"][i] or ""
            v = pbp["receiving_yards"][i]
            if v is not None:
                rec_yds[rid] += v
        if pbp["pass_touchdown"][i] == 1 or pbp["rush_touchdown"][i] == 1:
            if team:
                off_tds[team] += 1

    # ---- participation: routes proxy = on-field membership on dropbacks
    part = pq.read_table(
        os.path.join(HISTORY, "participation_2025.parquet"),
        columns=["nflverse_game_id", "play_id", "offense_players"]).to_pydict()
    routes = defaultdict(int)            # gsis id -> dropbacks on field
    for i in range(len(part["play_id"])):
        key = (part["nflverse_game_id"][i], part["play_id"][i])
        team = dropback_keys.get(key)
        if not team:
            continue
        for pid in (part["offense_players"][i] or "").split(";"):
            if pid:
                routes[pid] += 1

    # ---- ftn: first-read targets
    ftn = pq.read_table(
        os.path.join(HISTORY, "ftn_2025.parquet"),
        columns=["nflverse_game_id", "nflverse_play_id", "read_thrown"]).to_pydict()
    first_read_plays = set()
    for i in range(len(ftn["nflverse_play_id"])):
        if str(ftn["read_thrown"][i]).strip() == "1":
            first_read_plays.add((ftn["nflverse_game_id"][i],
                                  ftn["nflverse_play_id"][i]))
    fr_tgt = defaultdict(int)
    fr_team_n = defaultdict(int)
    for i in range(n_plays):
        if pbp["season_type"][i] != "REG":
            continue
        key = (pbp["game_id"][i], pbp["play_id"][i])
        if key in first_read_plays:
            team = pbp["posteam"][i]
            if team:
                fr_team_n[team] += 1
            rid = pbp["receiver_player_id"][i]
            if rid:
                fr_tgt[rid] += 1

    # ---- team line quality: 2025 team YBC per attempt (current-team basis)
    adv = pq.read_table(os.path.join(HISTORY, "advrush_2025.parquet")).to_pydict()
    team_ybc = defaultdict(float)
    team_car = defaultdict(int)
    for i in range(len(adv["team"])):
        if adv["game_type"][i] != "REG":
            continue
        t = adv["team"][i]
        team_ybc[t] += adv["rushing_yards_before_contact"][i] or 0
        team_car[t] += adv["carries"][i] or 0
    team_line = {t: round(team_ybc[t] / team_car[t], 3)
                 for t in team_ybc if team_car[t] >= 200}

    # ---- Week-1 2026 implied totals (the clean 16/16 coverage window)
    implied = {}
    with open(games_path) as fh:
        for r in csv.DictReader(fh):
            if r["season"] == "2026" and r["week"] == "1" and r.get("total_line"):
                tl, sp = float(r["total_line"]), float(r["spread_line"] or 0)
                # spread_line is home-relative in nflverse
                implied[r["home_team"]] = round(tl / 2 + sp / 2, 2)
                implied[r["away_team"]] = round(tl / 2 - sp / 2, 2)

    # Forward schedule is a separate source and a separate decision input.
    # It changes QB environment and WR opportunity only; RB expected-TD equity
    # remains on the Week-1 lines above so a schedule-window change cannot move
    # a different criterion through hidden dictionary reuse.
    with open(FORWARD_SCHEDULE) as fh:
        forward = derive_forward_vegas(csv.DictReader(fh))
    forward_implied = forward["implied_total"]
    forward_schedule_digest = file_content_sha256(FORWARD_SCHEDULE)
    with open(FORWARD_META) as fh:
        forward_meta = json.load(fh)
    forward_meta_digest = file_content_sha256(FORWARD_META)
    forward_model_digest = forward_model_logic_sha256()
    try:
        pulled_at = datetime.datetime.fromisoformat(
            forward_meta["pulled_at"].replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("forward schedule metadata has no valid pull time") from exc
    if pulled_at.utcoffset() != datetime.timedelta(0):
        raise ValueError("forward schedule pull time is not UTC")
    expected_meta = {
        "season": 2026,
        "snapshot_content_sha256": forward_schedule_digest,
        "decision_input_sha256": forward["decision_input_sha256"],
        "pricing_by_week_sha256": forward["pricing_by_week_sha256"],
        "model_logic_sha256": forward_model_digest,
        "games_priced": forward["game_count"],
        "team_games_priced": forward["team_game_count"],
        "weeks": forward["weeks"],
        "next_partial_week": forward["boundary"],
        "current_implied_total": forward_implied,
    }
    meta_mismatch = {
        key: {"expected": value, "actual": forward_meta.get(key)}
        for key, value in expected_meta.items()
        if forward_meta.get(key) != value
    }
    upstream_digest = forward_meta.get("upstream_content_sha256", "")
    if len(upstream_digest) != 64 or any(
            char not in "0123456789abcdef" for char in upstream_digest):
        meta_mismatch["upstream_content_sha256"] = {
            "expected": "64 lowercase hex characters",
            "actual": upstream_digest,
        }
    if meta_mismatch:
        raise ValueError(
            "forward schedule snapshot/metadata mismatch; run "
            f"src/sync_forward_schedule.py first: {meta_mismatch}")

    forward_provenance = {
        "source": FORWARD_SCHEDULE_REL,
        "metadata_source": FORWARD_META_REL,
        "upstream_source": forward_meta.get("upstream_source"),
        "pulled_at": forward_meta["pulled_at"],
        "source_content_sha256": forward_schedule_digest,
        "snapshot_content_sha256": forward_schedule_digest,
        "upstream_content_sha256": upstream_digest,
        "decision_input_sha256": forward["decision_input_sha256"],
        "pricing_by_week_sha256": forward["pricing_by_week_sha256"],
        "model_logic_sha256": forward_model_digest,
        "season": 2026,
        "derivation": ("maximal contiguous prefix from week 1 where every "
                       "scheduled game has total_line and spread_line"),
        "spread_convention": ("positive spread_line means home favored; "
                              "home=total/2+spread/2, "
                              "away=total/2-spread/2"),
        "weeks": forward["weeks"],
        "first_week": forward["weeks"][0],
        "last_week": forward["weeks"][-1],
        "games": forward["game_count"],
        "games_priced": forward["game_count"],
        "team_games": forward["team_game_count"],
        "team_games_priced": forward["team_game_count"],
        "teams": len(forward_implied),
        "full_schedule_games": forward["full_schedule_games"],
        "regular_season_games_per_team": forward[
            "regular_season_games_per_team"],
        "team_game_counts": forward["team_game_counts"],
        "coverage": forward["coverage"],
        "next_partial_week": forward["boundary"],
        "top_five_teams": sorted(
            forward_implied,
            key=lambda team: (-forward_implied[team], team))[:5],
        "top_five_tie_policy": "higher mean, then canonical team code",
        "consumers": ["QB.environment", "WR.opportunity"],
        "excluded_consumers": ["RB.expected_td_equity"],
    }
    previous_forward_provenance = forward_provenance
    previous_forward_implied = forward_implied
    if previous_output:
        previous_forward_provenance = (
            previous_output.get("provenance", {}).get("vegas", {}).get(
                "forward") or forward_provenance)
        previous_forward_implied = (
            previous_output.get("teams", {}).get("forward_implied_total") or
            forward_implied)
    build_transition = classify_forward_transition(
        previous_forward_provenance, previous_forward_implied,
        forward_provenance, forward_implied)
    enforce_forward_transition(build_transition)
    sync_prior_implied = forward_meta.get("prior_implied_total")
    sync_transition = validate_sync_transition(
        forward_meta.get("sync_transition"), sync_prior_implied,
        forward_provenance, forward_implied)
    forward_transition, forward_counterfactual = select_forward_transition(
        sync_transition, build_transition, sync_prior_implied,
        previous_forward_implied if previous_output else None,
        forward_implied)
    forward_provenance["delta_event"] = forward_transition
    # td-per-point from 2025 actuals: offensive TDs / points implied by them is
    # circular; use TDs per team point scored (final scores from spw totals is
    # indirect) - compute points from league-neutral basis: 2025 team points =
    # sum of 6*TDs + FG/XP unknown here, so derive tds-per-point directly from
    # implied-scale: league offensive TDs / league points scored, points from
    # pbp scores. Simpler and stated: use total offensive TDs / total implied-
    # style points = TDs / (sum of team final scores from schedules 2025).
    pts_2025 = defaultdict(int)
    with open(games_path) as fh:
        for r in csv.DictReader(fh):
            if r["season"] == "2025" and r["game_type"] == "REG" and r.get("home_score"):
                pts_2025[r["home_team"]] += int(float(r["home_score"]))
                pts_2025[r["away_team"]] += int(float(r["away_score"]))
    total_tds = sum(off_tds.values())
    total_pts = sum(pts_2025.values())
    td_per_point = round(total_tds / total_pts, 4)
    implied_tds = {t: round(v * td_per_point, 2) for t, v in implied.items()}

    # ---- shards
    eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
    engine_digest = require_engine_digest(eng)
    usage_art = json.load(open(os.path.join(D, "usage_2025.json")))
    usage = usage_art["players"]
    goal = json.load(open(os.path.join(D, "goalline_2025.json")))
    ceil_art = json.load(open(os.path.join(D, "ceiling_2026.json")))
    ceiling_digest = ceil_art.get("provenance", {}).get("engine_content_sha256")
    if ceiling_digest != engine_digest:
        raise ValueError(
            "ceiling inputs were built from a different engine payload; "
            "rebuild src/build_ceiling.py first"
        )
    depth_art = json.load(open(os.path.join(D, "depth_charts.json")))
    depth = depth_art["entries"]
    xwalk = json.load(open(os.path.join(D, "crosswalk.json")))
    input_content_sha256 = {
        "ceiling_2026.json": json_content_sha256(ceil_art),
        "usage_2025.json": json_content_sha256(usage_art),
        "goalline_2025.json": json_content_sha256(goal),
        "depth_charts.json": json_content_sha256(depth_art),
        "crosswalk.json": json_content_sha256(xwalk),
        FORWARD_SCHEDULE_REL: forward_schedule_digest,
        FORWARD_META_REL: forward_meta_digest,
    }

    usage_by_gsis = {u["gsis_id"]: u for u in usage}
    ceiling_identity = PlayerIdentityResolver(ceil_art["players"])
    team_now = {e["gsis_id"]: e["team"] for e in depth}
    gsis_of = xwalk["matched"]           # sleeper id -> gsis id
    # goalline player table is keyed by gsis id
    goal_p = goal["player_2025"]
    goal_team = goal["team_2025"]

    # Team rec yards (for YMS) and RB carry competition. The live RB sample
    # assigns 2025 production to its 2025 team. The current-roster grouping is
    # retained only as a same-build counterfactual so this one change is
    # attributable rather than compared with yesterday's artifact.
    team_rec = defaultdict(float)
    for u in usage:
        team_rec[u["team"]] += u["rec_yards"]
    rb_carry_ledger = usage_art["rb_player_team_carries"]
    historical_rb_samples = historical_rb_backfield_samples(rb_carry_ledger)
    trimmed_usage_by_player = _validated_rb_usage(usage)
    historical_trimmed_counterfactual = _rb_backfield_samples(
        usage,
        {player_id: row["team"]
         for player_id, row in trimmed_usage_by_player.items()},
    )
    current_roster_rb_counterfactual = (
        current_roster_rb_backfield_counterfactual(usage, depth))

    # QB epa/att from spw
    qb_epa = defaultdict(lambda: [0.0, 0])
    with open(os.path.join(HISTORY, "spw_2025.csv")) as fh:
        for r in csv.DictReader(fh):
            if r.get("season_type") != "REG" or r.get("position") != "QB":
                continue
            key = r["player_id"]
            try:
                qb_epa[key][0] += float(r.get("passing_epa") or 0)
                qb_epa[key][1] += float(r.get("attempts") or 0)
            except ValueError:
                pass

    draftable = [p for p in eng["players"]
                 if p["adp"] <= 14 * 12 and p["pos"] in ("QB", "RB", "WR", "TE")]

    players = []
    for p in draftable:
        sid = str(p.get("sleeper_id") or "")
        gid = gsis_of.get(sid)
        u = usage_by_gsis.get(gid)
        ceiling_result = ceiling_identity.resolve(p["name"], position=p["pos"])
        cl = ceiling_result.record or {}
        team26 = team_now.get(gid) or p.get("team")
        e = {"name": p["name"], "pos": p["pos"], "adp": p["adp"],
             "team_2026": team26,
             "implied_total": implied.get(team26),
             "implied_tds": implied_tds.get(team26),
             "team_line_ybc": team_line.get(team26),
             "gp_rate_2yr": cl.get("gp_rate_2yr"),
             "exp_missed": cl.get("exp_missed")}
        if p["pos"] in ("QB", "WR"):
            e["forward_implied_total"] = forward_implied.get(
                canonical_team(team26))
        if gid and routes.get(gid):
            r = routes[gid]
            k = tgt.get(gid, 0)
            tm = rcv_team.get(gid) or (u or {}).get("team")
            e["routes_proxy"] = r
            e["tprr_proxy"] = {"k": k, "n": r}
            e["yprr_proxy"] = round(rec_yds.get(gid, 0.0) / r, 3)
            if tm and team_dropbacks.get(tm):
                e["on_field_dropback_share"] = {
                    "k": r,
                    "n": team_dropbacks[tm],
                    "basis": ("2025 regular-season team dropbacks with the player "
                              "listed on offense; pass-block snaps are included"),
                }
            if tm and fr_team_n.get(tm):
                e["first_read"] = {"k": fr_tgt.get(gid, 0), "n": fr_team_n[tm]}
        if u:
            if u["weeks"]:
                e["targets_pg"] = round(u["targets"] / u["weeks"], 2)
                e["carries_pg"] = round(u["carries"] / u["weeks"], 2)
                e["rush_ypg"] = round(u["rush_yards"] / u["weeks"], 2)
            if p["pos"] == "TE" and team_rec.get(u["team"]):
                e["yms_2025"] = round(u["rec_yards"] / team_rec[u["team"]], 4)
        if p["pos"] == "RB" and gid and gid in goal_p:
            g25team = goal_p[gid]["team"]
            tt = goal_team.get(g25team, {})
            if tt.get("i5"):
                e["inside5_share"] = {"k": goal_p[gid]["i5"], "n": tt["i5"],
                                      "basis": f"2025 role on {g25team}"}
        if p["pos"] == "RB":
            share = historical_rb_samples.get(gid)
            if share is not None:
                e["backfield_share"] = share["value"]
                e["backfield_share_sample"] = {
                    "season": share["season"],
                    "historical_team": share["team"],
                    "player_carries": share["player_carries"],
                    "historical_team_rb_carries": share["team_rb_carries"],
                }
            counterfactual = current_roster_rb_counterfactual.get(gid)
            if counterfactual is not None:
                e["backfield_share_counterfactual_current_roster"] = (
                    counterfactual["value"])
                e["backfield_share_counterfactual_sample"] = {
                    "season": counterfactual["season"],
                    "current_roster_team": counterfactual["team"],
                    "player_carries": counterfactual["player_carries"],
                    "current_roster_team_rb_carries":
                        counterfactual["team_rb_carries"],
                }
            trimmed_historical = historical_trimmed_counterfactual.get(gid)
            if trimmed_historical is not None:
                e["backfield_share_counterfactual_historical_trimmed"] = (
                    trimmed_historical["value"])
                e["backfield_share_historical_trimmed_sample"] = {
                    "season": trimmed_historical["season"],
                    "historical_team": trimmed_historical["team"],
                    "player_carries": trimmed_historical["player_carries"],
                    "historical_team_rb_carries":
                        trimmed_historical["team_rb_carries"],
                }
        if p["pos"] == "QB" and gid in qb_epa and qb_epa[gid][1] >= 150:
            e["epa_per_att"] = round(qb_epa[gid][0] / qb_epa[gid][1], 4)
        players.append(e)

    # ---- thresholds: percentiles of qualifying distributions
    wr = [e for e in players if e["pos"] == "WR" and e.get("routes_proxy", 0) >= 150]
    rb = [e for e in players if e["pos"] == "RB" and e.get("targets_pg") is not None]
    te = [e for e in players if e["pos"] == "TE" and e.get("routes_proxy", 0) >= 100]
    qb = [e for e in players if e["pos"] == "QB" and e.get("carries_pg") is not None]
    rb_all = [e for e in players if e["pos"] == "RB"]
    rb_backfield = [e["backfield_share"] for e in rb_all
                    if e.get("backfield_share") is not None]
    rb_backfield_dist = distribution(
        rb_backfield, "rb_backfield_share",
        excluded_unobserved_n=len(rb_all) - len(rb_backfield),
        observation_rule=("the untrimmed 2025 player-team carry ledger contains "
                          "one positive historical team for the canonical player "
                          "and that team's observed RB carry total is at least 100; "
                          "observed zero is included, absence or a positive "
                          "multi-team split is null"),
    )
    # Stage 2 historically uses the upper middle observation for an even-n
    # median. Preserve that convention explicitly; changing quantile methods is
    # a separate model change, not part of the absent-vs-zero repair.
    rb_backfield_dist["p50"] = round(sorted(rb_backfield)[len(rb_backfield) // 2], 4)
    rb_backfield_dist["p50_method"] = (
        "upper middle observation for even n; preserved stage-2 convention")
    rb_backfield_counterfactual = [
        e["backfield_share_counterfactual_current_roster"] for e in rb_all
        if e.get("backfield_share_counterfactual_current_roster") is not None
    ]
    rb_backfield_counterfactual_dist = distribution(
        rb_backfield_counterfactual,
        "rb_backfield_share_counterfactual_current_roster",
        excluded_unobserved_n=len(rb_all) - len(rb_backfield_counterfactual),
        observation_rule=("same usage_2025.json rows assigned to 2026 depth-chart "
                          "teams; retained only as the retired same-build baseline"),
    )
    rb_backfield_counterfactual_dist["p50"] = round(
        sorted(rb_backfield_counterfactual)[
            len(rb_backfield_counterfactual) // 2], 4)
    rb_backfield_counterfactual_dist["p50_method"] = (
        "upper middle observation for even n; retired stage-2 baseline")
    rb_backfield_historical_trimmed = [
        e["backfield_share_counterfactual_historical_trimmed"] for e in rb_all
        if e.get("backfield_share_counterfactual_historical_trimmed") is not None
    ]
    rb_backfield_historical_trimmed_dist = distribution(
        rb_backfield_historical_trimmed,
        "rb_backfield_share_counterfactual_historical_trimmed",
        excluded_unobserved_n=len(rb_all) - len(rb_backfield_historical_trimmed),
        observation_rule=("trimmed usage_2025.json player rows assigned to their "
                          "stored historical team; grouping-only intermediate"),
    )
    rb_backfield_historical_trimmed_dist["p50"] = round(
        sorted(rb_backfield_historical_trimmed)[
            len(rb_backfield_historical_trimmed) // 2], 4)
    rb_backfield_historical_trimmed_dist["p50_method"] = (
        "upper middle observation for even n; grouping-only intermediate")
    thresholds = {
        "wr_tprr": distribution(
            [e["tprr_proxy"]["k"] / e["tprr_proxy"]["n"] for e in wr], "tprr"),
        "wr_yprr": distribution([e["yprr_proxy"] for e in wr], "yprr"),
        "wr_first_read": distribution(
            [e["first_read"]["k"] / e["first_read"]["n"]
             for e in wr if "first_read" in e], "fr",
            excluded_unobserved_n=sum("first_read" not in e for e in wr)),
        "rb_targets_pg": distribution([e["targets_pg"] for e in rb], "tgt",
                                      excluded_unobserved_n=len(rb_all) - len(rb)),
        "rb_inside5": distribution(
            [e["inside5_share"]["k"] / e["inside5_share"]["n"]
             for e in rb if "inside5_share" in e], "i5",
            excluded_unobserved_n=sum("inside5_share" not in e for e in rb),
            observation_rule="2025 inside-five sample has n > 0; k=0 is observed"),
        "rb_backfield_share": rb_backfield_dist,
        "rb_backfield_share_counterfactual_current_roster":
            rb_backfield_counterfactual_dist,
        "rb_backfield_share_counterfactual_historical_trimmed":
            rb_backfield_historical_trimmed_dist,
        "team_line_ybc": distribution(sorted(team_line.values()), "ybc"),
        "on_field_dropback_share_reference": distribution(
            [e["on_field_dropback_share"]["k"] /
             e["on_field_dropback_share"]["n"]
             for e in te if "on_field_dropback_share" in e], "dropback_share",
            excluded_unobserved_n=sum(
                "on_field_dropback_share" not in e for e in te),
            observation_rule=("2025 TE population with at least 100 observed "
                              "on-field team dropbacks; pass-block snaps count")),
        "qb_rush_ypg": distribution([e["rush_ypg"] for e in qb], "rypg"),
        "implied_total": distribution(sorted(implied.values()), "imp"),
        "forward_implied_total": distribution(
            list(forward_implied.values()), "forward_imp",
            observation_rule="all canonical teams in the maximal fully priced horizon"),
        "note": ("qualification floors: WR/TE routes-proxy >= 150/100, QB 150+ "
                 "attempts, RB with 2025 usage; proxies count pass-block snaps "
                 "as on-field dropbacks (stated weakness), so thresholds are percentiles "
                 "of OUR distribution, never PFF-unit imports"),
    }

    # ---- QB gap derivation (settings correction item 1)
    def season_qb_table(year, weights):
        agg = defaultdict(lambda: defaultdict(float))
        with open(os.path.join(HISTORY, f"spw_{year}.csv")) as fh:
            for r in csv.DictReader(fh):
                if r.get("season_type") != "REG" or r.get("position") != "QB":
                    continue
                key = r["player_id"]
                a = agg[key]
                a["g"] += 1
                for col, w in weights.items():
                    v = r.get(col)
                    if v:
                        try:
                            a["pts"] += float(v) * w
                        except ValueError:
                            pass
                v = r.get("rushing_yards")
                if v:
                    try:
                        a["ry"] += float(v)
                    except ValueError:
                        pass
        return agg

    def gap(weights):
        rush_pts, pocket_pts = [], []
        for year in range(2016, 2026):
            agg = season_qb_table(year, weights)
            rows = [(a["pts"], a["ry"] / a["g"]) for a in agg.values() if a["g"] >= 8]
            rows.sort(reverse=True)
            top12 = rows[:12]
            med_ry = pctile(sorted(r for _, r in rows), 0.75)
            for pts, ry in top12:
                (rush_pts if ry >= med_ry else pocket_pts).append(pts)
        def stats(xs):
            m = sum(xs) / len(xs)
            sd = (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5
            return m, sd, len(xs)
        rm, rsd, rn = stats(rush_pts)
        pm, psd, pn = stats(pocket_pts)
        diff = rm - pm
        se = (rsd ** 2 / rn + psd ** 2 / pn) ** 0.5
        return {"rushing": {"mean": round(rm, 1), "sd": round(rsd, 1), "n": rn},
                "pocket": {"mean": round(pm, 1), "sd": round(psd, 1), "n": pn},
                "gap": round(diff, 1),
                "gap_ci95": [round(diff - 1.96 * se, 1), round(diff + 1.96 * se, 1)]}
    qb_gap = {
        "definition": ("top-12 QB season finishes 2016-2025 (n=120), rushing "
                       "class = rush yds/g >= that season's p75 among 8+ game "
                       "QBs; season TOTAL points under each scoring"),
        "league_6pt": gap(W),
        "counterfactual_4pt": gap(W4),
    }

    out = {
        "provenance": {
            "generated": datetime.datetime.now(
                datetime.timezone.utc).date().isoformat(),
            "engine_generated": eng["generated"],
            "engine_content_sha256": engine_digest,
            "input_content_sha256": input_content_sha256,
            "vegas": {
                "week1_rb": {
                    "source": "nflverse HISTORY games.csv, Week-1 2026 lines",
                    "pulled": games_pulled,
                    "games": len(implied) // 2,
                    "consumers": ["RB.expected_td_equity"],
                },
                "forward": forward_provenance,
            },
            "td_per_point": {"value": td_per_point,
                             "basis": "2025 offensive TDs / 2025 points scored"},
            "roles": "inside-5 share and YMS are 2025-role priors and say so",
            "rb_backfield": {
                "status": "ACTIVATED",
                "source": ("out/data/usage_2025.json#rb_player_team_carries"),
                "replacement": ("2025 player carries divided by the complete "
                                "untrimmed 2025 RB carry total on that historical "
                                "team; multi-team rows stay split"),
                "retired_counterfactual": ("the same committed usage rows grouped "
                                           "by each player's 2026 depth-chart team"),
                "grouping_only_intermediate": (
                    "the retired trimmed player rows regrouped by their stored "
                    "historical team before adding the untrimmed split ledger"),
                "counterfactual_reproduces_committed_baseline": True,
                "season_scope": ("all 2025 season types present in the weekly "
                                 "source, preserving the prior all-week basis"),
                "multi_team_player_policy": ("all split rows contribute to team "
                                             "denominators; a player with positive "
                                             "carries for multiple teams has a null "
                                             "individual share"),
            },
            "proxy": "routes = on-field membership on team dropbacks "
                     "(participation 2025); counts pass-block snaps as routes",
        },
        "teams": {"implied_total": implied, "implied_tds": implied_tds,
                  "forward_implied_total": forward_implied,
                  "forward_counterfactual_implied_total":
                      forward_counterfactual,
                  "line_ybc_2025": team_line},
        "thresholds": thresholds,
        "qb_gap": qb_gap,
        "players": players,
    }
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}: {len(players)} players")
    print("qb gap 6pt:", qb_gap["league_6pt"])
    print("qb gap 4pt:", qb_gap["counterfactual_4pt"])
    print("thresholds:", {k: v for k, v in thresholds.items() if k != "note"})


if __name__ == "__main__":
    main()
