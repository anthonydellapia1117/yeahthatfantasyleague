#!/usr/bin/env python3
"""C5 guards: BULLISH engine - probabilistic gates, state machine, edge
accountability, delta report, and display-only wiring.

Runs WITHOUT network on the committed artifacts and pages.
Run: python3 tests/test_bullish.py
"""
import hashlib
import json
import math
import os
import re
import sys
import datetime
import csv
import copy
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "out", "data")
sys.path.insert(0, os.path.join(ROOT, "src"))
from analyze_recency import HISTORY
from build_bullish_inputs import (classify_forward_transition,
                                  current_roster_rb_backfield_counterfactual,
                                  derive_forward_vegas, distribution,
                                  enforce_forward_transition, observed_share,
                                  historical_rb_backfield_samples,
                                  select_forward_transition,
                                  validate_sync_transition)
from build_pages_data import aggregate_rb_player_team_carries
from engine_lineage import file_content_sha256, json_content_sha256
from player_names import PlayerIdentityResolver
from team_codes import CANONICAL_NFL_TEAMS, canonical_team
from sync_forward_schedule import sync as sync_forward_schedule
fails = []


def ok(cond, name, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "  -> " + detail))
    if not cond:
        fails.append(name)


inp = json.load(open(os.path.join(D, "bullish_inputs_2026.json")))
d = json.load(open(os.path.join(D, "bullish_2026.json")))
try:
    _computed_at = datetime.datetime.fromisoformat(
        d["provenance"]["computed_at"])
    _computed_is_utc = (_computed_at.utcoffset() == datetime.timedelta(0))
    _computed_utc_date = _computed_at.astimezone(
        datetime.timezone.utc).date().isoformat()
except (KeyError, TypeError, ValueError):
    _computed_is_utc = False
    _computed_utc_date = None
ok(_computed_is_utc and
   d.get("provenance", {}).get("generated") == _computed_utc_date,
   "BULLISH timestamp is UTC and generated is its UTC date",
   f"generated {d.get('provenance', {}).get('generated')}, "
   f"computed_at {d.get('provenance', {}).get('computed_at')}")
inp_digest = inp.get("provenance", {}).get("engine_content_sha256", "")
tag_digest = d.get("provenance", {}).get("engine_content_sha256", "")
ok(len(inp_digest) == 64 and tag_digest == inp_digest,
   "BULLISH inputs and tags record one exact engine payload")
source_payloads = {
    name: json.load(open(os.path.join(D, name)))
    for name in ("ceiling_2026.json", "usage_2025.json", "goalline_2025.json",
                 "depth_charts.json", "crosswalk.json")
}
source_digests = {
    name: json_content_sha256(payload) for name, payload in source_payloads.items()
}
forward_schedule_rel = "docs/ffopportunity/schedule_2026.csv"
forward_schedule_path = os.path.join(ROOT, forward_schedule_rel)
source_digests[forward_schedule_rel] = file_content_sha256(forward_schedule_path)
forward_meta_rel = "docs/ffopportunity/schedule_2026.meta.json"
forward_meta_path = os.path.join(ROOT, forward_meta_rel)
source_digests[forward_meta_rel] = file_content_sha256(forward_meta_path)
ok(inp.get("provenance", {}).get("input_content_sha256") ==
   source_digests,
   "BULLISH inputs record every committed source payload exactly")
ok(d.get("provenance", {}).get("inputs_content_sha256") ==
   json_content_sha256(inp),
   "BULLISH tags record the exact computed-input payload")
if os.environ.get("REQUIRE_DISPLAY_ENGINE_MATCH") == "1":
    eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
    ok(all(a.get("provenance", {}).get("engine_content_sha256") ==
           eng.get("content_sha256")
           for a in (source_payloads["ceiling_2026.json"], inp, d)),
       "pages-data repaired every display artifact to the current engine")

# 1. inputs: proportions carry k and n; thresholds carry distributions;
#    provenance states the proxy weakness and the Vegas window
thr = inp["thresholds"]
for k, population in ((k, v) for k, v in thr.items() if isinstance(v, dict)):
    ps = [population.get(q) for q in ("p50", "p75", "p80")]
    ok(population.get("n", 0) > 0 and
       population.get("zero_n", -1) >= 0 and
       population.get("excluded_unobserved_n", -1) >= 0 and
       all(isinstance(x, (int, float)) and math.isfinite(x) for x in ps) and
       ps == sorted(ps),
       f"threshold {k} carries finite observed-population accounting",
       str(population))
ok("pass-block snaps" in thr["note"], "route-proxy weakness stated")
week1_vegas = inp["provenance"]["vegas"]["week1_rb"]
forward_vegas = inp["provenance"]["vegas"]["forward"]
ok("Week-1" in week1_vegas["source"] and
   week1_vegas["consumers"] == ["RB.expected_td_equity"],
   "Week-1 Vegas source is isolated to RB expected-TD equity")
try:
    datetime.date.fromisoformat(week1_vegas["pulled"])
    _pulled_is_date = True
except (KeyError, TypeError, ValueError):
    _pulled_is_date = False
ok(_pulled_is_date, "Week-1 Vegas provenance carries a parseable source pull date")
_games = os.path.join(HISTORY, "games.csv")
if os.path.exists(_games):
    _games_date = datetime.datetime.fromtimestamp(
        os.path.getmtime(_games), tz=datetime.timezone.utc).date().isoformat()
    ok(week1_vegas["pulled"] == _games_date,
       "Week-1 Vegas provenance reports the cached source file's UTC fetch date",
       f"artifact {week1_vegas['pulled']}, file {_games_date}")
else:
    ok(_pulled_is_date and
       week1_vegas["pulled"] <=
       inp["provenance"]["generated"],
       "Week-1 Vegas source date is plausible when the local cache is absent",
       f"pulled {week1_vegas.get('pulled')}, "
       f"generated {inp['provenance'].get('generated')}")

# Forward Vegas is independently rederived from the committed schedule. The
# horizon length is evidence, never a typed six-week policy.
with open(forward_schedule_path) as fh:
    schedule_rows = list(csv.DictReader(fh))
forward_meta = json.load(open(forward_meta_path))
forward_expected = derive_forward_vegas(copy.deepcopy(schedule_rows))
ok(forward_expected["weeks"] == forward_vegas["weeks"] and
   forward_expected["game_count"] == forward_vegas["games"] and
   forward_expected["team_game_count"] == forward_vegas["team_games"] and
   forward_expected["team_game_counts"] == forward_vegas["team_game_counts"] and
   forward_expected["full_schedule_games"] ==
   forward_vegas["full_schedule_games"] and
   forward_expected["regular_season_games_per_team"] ==
   forward_vegas["regular_season_games_per_team"] and
   forward_expected["coverage"] == forward_vegas["coverage"] and
   forward_expected["boundary"] == forward_vegas["next_partial_week"] and
   forward_expected["decision_input_sha256"] ==
   forward_vegas["decision_input_sha256"] and
   forward_expected["pricing_by_week_sha256"] ==
   forward_vegas["pricing_by_week_sha256"] and
   forward_vegas["first_week"] == forward_expected["weeks"][0] and
   forward_vegas["last_week"] == forward_expected["weeks"][-1] and
   forward_vegas["teams"] == 32 and
   forward_vegas["source"] == forward_schedule_rel and
   forward_vegas["consumers"] == ["QB.environment", "WR.opportunity"] and
   forward_vegas["excluded_consumers"] == ["RB.expected_td_equity"],
   "forward Vegas horizon and coverage rederive from the schedule",
   str(forward_vegas))
ok(forward_vegas["source_content_sha256"] ==
   file_content_sha256(forward_schedule_path) and
   forward_vegas["snapshot_content_sha256"] ==
   forward_meta["snapshot_content_sha256"] and
   forward_vegas["upstream_content_sha256"] ==
   forward_meta["upstream_content_sha256"] and
   forward_vegas["pulled_at"] == forward_meta["pulled_at"] and
   forward_vegas["games_priced"] == forward_meta["games_priced"] and
   forward_vegas["team_games_priced"] ==
   forward_meta["team_games_priced"] and
   d["provenance"]["forward_vegas"] == forward_vegas,
   "forward Vegas pull, digests, counts, and scope propagate to the tag artifact")
ok(set(forward_expected["implied_total"]) == set(CANONICAL_NFL_TEAMS) and
   inp["teams"]["forward_implied_total"] == forward_expected["implied_total"] and
   sum(forward_expected["team_game_counts"].values()) ==
   2 * forward_expected["game_count"],
   "forward Vegas covers and reconciles all 32 canonical teams")
selected = set(forward_expected["weeks"])
sign_ok = True
independent_team_values = {team: [] for team in CANONICAL_NFL_TEAMS}
for row in schedule_rows:
    if (str(row.get("season")) != "2026" or row.get("game_type") != "REG" or
            int(row["week"]) not in selected):
        continue
    total, spread = float(row["total_line"]), float(row["spread_line"])
    home, away = total / 2 + spread / 2, total / 2 - spread / 2
    home_team = canonical_team(row["home_team"])
    away_team = canonical_team(row["away_team"])
    independent_team_values[home_team].append(home)
    independent_team_values[away_team].append(away)
    sign_ok &= (math.isclose(home + away, total) and
                math.isclose(home - away, spread) and
                ((spread > 0) == (home > away) if spread else home == away))
independent_totals = {
    team: round(sum(values) / len(values), 2)
    for team, values in independent_team_values.items()
}
ok(sign_ok and independent_totals == inp["teams"]["forward_implied_total"],
   "production forward totals match an independent verified-sign aggregate")
expected_top5 = sorted(independent_totals,
                       key=lambda team: (-independent_totals[team], team))[:5]
ok(forward_vegas["top_five_teams"] == expected_top5 and
   forward_vegas["top_five_tie_policy"] ==
   "higher mean, then canonical team code",
   "forward provenance names the actual deterministic top-five environment")

short_rows = copy.deepcopy(schedule_rows)
last_week = forward_expected["weeks"][-1]
short_target = next(r for r in short_rows
                    if r.get("season") == "2026" and r.get("game_type") == "REG"
                    and int(r["week"]) == last_week)
short_target["total_line"] = short_target["spread_line"] = ""
ok(derive_forward_vegas(short_rows)["weeks"] ==
   forward_expected["weeks"][:-1],
   "forward horizon shortens when its last complete week becomes partial")

later_partial_rows = copy.deepcopy(schedule_rows)
later_partial = next(r for r in later_partial_rows
                     if r.get("season") == "2026" and
                     r.get("game_type") == "REG" and
                     int(r["week"]) > forward_expected["weeks"][-1] and
                     not str(r.get("total_line") or "").strip() and
                     not str(r.get("spread_line") or "").strip())
later_partial["total_line"] = "44.5"
ok(derive_forward_vegas(later_partial_rows)["weeks"] ==
   forward_expected["weeks"],
   "a half-posted line beyond the priced horizon is recorded, not fatal")

# The producer must classify the decision input, not unrelated CSV churn. Its
# synthetic horizon extension is the bite test for the event that was added
# before the first real extension occurred.
def write_schedule(path, rows):
    fieldnames = list(rows[0])
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sync_fixture(mutator):
    with tempfile.TemporaryDirectory() as td:
        source = os.path.join(td, "games.csv")
        snapshot = os.path.join(td, "schedule.csv")
        metadata = os.path.join(td, "schedule.meta.json")
        write_schedule(source, copy.deepcopy(schedule_rows))
        baseline = sync_forward_schedule(source, snapshot, metadata)
        before_snapshot = open(snapshot, "rb").read()
        before_metadata = open(metadata, "rb").read()
        changed = copy.deepcopy(schedule_rows)
        mutator(changed)
        write_schedule(source, changed)
        try:
            result = sync_forward_schedule(source, snapshot, metadata)
            error = None
        except ValueError as exc:
            result = None
            error = str(exc)
        return {
            "baseline": baseline,
            "result": result,
            "error": error,
            "snapshot_unchanged": open(snapshot, "rb").read() == before_snapshot,
            "metadata_unchanged": open(metadata, "rb").read() == before_metadata,
        }


def complete_week7(rows):
    for row in rows:
        if int(row["week"]) == 7 and not (
                str(row.get("total_line") or "").strip() and
                str(row.get("spread_line") or "").strip()):
            row["total_line"] = "44.0"
            row["spread_line"] = "0.0"


extended = sync_fixture(complete_week7)
ext = extended["result"]["sync_transition"]
ok(extended["baseline"]["sync_transition"]["event"] == "UNCHANGED" and
   ext["event"] == "HORIZON_EXTENDED" and
   ext["prior"]["last_week"] == 6 and ext["current"]["last_week"] == 7 and
   ext["prior"]["games_priced"] == 93 and
   ext["current"]["games_priced"] == 107 and
   ext["current"]["team_games_priced"] == 214,
   "synthetic Week-7 completion fires HORIZON_EXTENDED at 93->107 games",
   str(ext))


def reprice_week1(rows):
    row = next(row for row in rows if int(row["week"]) == 1)
    row["total_line"] = str(float(row["total_line"]) + 1.0)


repriced = sync_fixture(reprice_week1)["result"]["sync_transition"]
ok(repriced["event"] == "REPRICED" and
   repriced["current"]["games_priced"] == 93 and
   repriced["flags"]["decision_pricing_changed"] is True,
   "same-horizon line change fires REPRICED")


def change_moneyline_only(rows):
    row = next(row for row in rows if int(row["week"]) == 1)
    row["home_moneyline"] = str(float(row.get("home_moneyline") or 0) + 1.0)


source_only = sync_fixture(change_moneyline_only)["result"]["sync_transition"]
ok(source_only["event"] == "UNCHANGED" and
   source_only["flags"]["source_changed"] is True and
   source_only["flags"]["decision_pricing_changed"] is False,
   "non-decision source churn remains UNCHANGED")


def contract_week6(rows):
    row = next(row for row in rows if int(row["week"]) == 6)
    row["total_line"] = row["spread_line"] = ""


contracted = sync_fixture(contract_week6)
ok("CONTRACTED" in (contracted["error"] or "") and
   contracted["snapshot_unchanged"] and contracted["metadata_unchanged"],
   "horizon contraction fails closed before replacing either snapshot file",
   str(contracted))

_contract_state = classify_forward_transition(
    {"weeks": [1, 2, 3, 4, 5, 6], "games_priced": 93,
     "team_games_priced": 186}, {},
    {"weeks": [1, 2, 3, 4, 5], "games_priced": 79,
     "team_games_priced": 158}, {})
try:
    enforce_forward_transition(_contract_state)
    _contract_rejected = False
except ValueError:
    _contract_rejected = True
ok(_contract_rejected and _contract_state["event"] == "CONTRACTED",
   "pure transition guard rejects a narrower 93->79-game horizon")

# The metadata consumer must rederive the producer event rather than trusting a
# plausible-looking label/prior frame. These totals are schedule-only values
# produced under the current model logic.
_current_state = forward_vegas
_current_totals = forward_expected["implied_total"]
_sync_prior_totals = dict(_current_totals)
_valid_unchanged = classify_forward_transition(
    _current_state, _sync_prior_totals, _current_state, _current_totals)
try:
    validate_sync_transition(
        _valid_unchanged, _sync_prior_totals,
        _current_state, _current_totals)
    _valid_transition_accepted = True
except ValueError:
    _valid_transition_accepted = False
_fabricated = copy.deepcopy(_valid_unchanged)
_fabricated["event"] = "HORIZON_EXTENDED"
_fabricated["prior"]["last_week"] = 1
_fabricated_prior_totals = dict(_sync_prior_totals)
_fabricated_prior_totals["ARI"] = 999.0
try:
    validate_sync_transition(
        _fabricated, _fabricated_prior_totals,
        _current_state, _current_totals)
    _fabricated_transition_rejected = False
except ValueError:
    _fabricated_transition_rejected = True
ok(_valid_transition_accepted and _fabricated_transition_rejected,
   "builder rederives sync metadata and rejects fabricated event/prior values")

# A model-only change may move derived totals, but it is not a schedule-only
# tag delta. The current-code sync prior is therefore the counterfactual; the
# old-model artifact totals must not be presented as if current code were held.
_old_model_state = copy.deepcopy(_current_state)
_new_model_state = copy.deepcopy(_current_state)
_old_model_state["model_logic_sha256"] = "a" * 64
_new_model_state["model_logic_sha256"] = "b" * 64
_old_model_totals = dict(_current_totals)
_old_model_totals["ARI"] = round(_old_model_totals["ARI"] + 1.0, 2)
_model_build_transition = classify_forward_transition(
    _old_model_state, _old_model_totals,
    _new_model_state, _current_totals)
_selected_model_event, _selected_model_counterfactual = \
    select_forward_transition(
        _valid_unchanged, _model_build_transition,
        _sync_prior_totals, _old_model_totals, _current_totals)
ok(_model_build_transition["event"] == "REPRICED" and
   _model_build_transition["attribution"] == "MODEL_LOGIC" and
   _selected_model_event == _model_build_transition and
   _selected_model_counterfactual == _current_totals and
   _selected_model_counterfactual != _old_model_totals,
   "model-only movement keeps the same-build schedule counterfactual at zero")

_conflicting_material = copy.deepcopy(_model_build_transition)
_conflicting_material["event"] = "HORIZON_EXTENDED"
try:
    select_forward_transition(
        extended["result"]["sync_transition"], _conflicting_material,
        extended["result"]["prior_implied_total"],
        _old_model_totals, extended["result"]["current_implied_total"])
    _conflicting_material_rejected = False
except ValueError:
    _conflicting_material_rejected = True
ok(_conflicting_material_rejected,
   "builder rejects disagreeing material sync and prior-artifact transitions")

def raises_forward(mutator):
    rows = copy.deepcopy(schedule_rows)
    mutator(rows)
    try:
        derive_forward_vegas(rows)
        return False
    except ValueError:
        return True

ok(raises_forward(lambda rows: rows.__setitem__(
       next(i for i, r in enumerate(rows) if r.get("season") == "2026" and
            r.get("game_type") == "REG"),
       {**rows[next(i for i, r in enumerate(rows)
                 if r.get("season") == "2026" and r.get("game_type") == "REG")],
        "home_team": "UNKNOWN"})),
   "forward parser fails on an unresolved team code")
ok(raises_forward(lambda rows: rows.append(copy.deepcopy(next(
       r for r in rows if r.get("season") == "2026" and r.get("game_type") == "REG")))),
   "forward parser fails on a duplicate game/team-week")
ok(raises_forward(lambda rows: rows.pop(next(
       i for i, r in enumerate(rows) if r.get("season") == "2026" and
       r.get("game_type") == "REG" and int(r["week"]) in selected))),
   "forward parser rejects a missing scheduled game before pricing coverage")

consumer_join_ok = all(
    e.get("forward_implied_total") ==
    independent_totals[canonical_team(e["team_2026"])]
    for e in inp["players"] if e["pos"] in ("QB", "WR"))
nonconsumer_absent = all(
    "forward_implied_total" not in e
    for e in inp["players"] if e["pos"] in ("RB", "TE"))
ok(consumer_join_ok and nonconsumer_absent,
   "forward values join every QB/WR and are absent from RB/TE inputs")

# Absence and observed zero are opposite states. A percentile must keep the
# latter and exclude the former.
ok(observed_share({"real-zero": 0, "other": 100}, "real-zero") ==
   {"value": 0.0, "player": 0, "total": 100} and
   observed_share({"real-zero": 0, "other": 100}, "absent") is None,
   "observed-share helper keeps real zero and rejects absent identity")
_synthetic_dist = distribution([0.0, 0.2, 0.4, 0.6, 1.0], "synthetic",
                               excluded_unobserved_n=1)
_same_values_more_missing = distribution([0.0, 0.2, 0.4, 0.6, 1.0], "synthetic",
                                         excluded_unobserved_n=999)
_without_observed_zero = distribution([0.2, 0.4, 0.6, 1.0], "synthetic",
                                      excluded_unobserved_n=1)
ok(_synthetic_dist["n"] == 5 and _synthetic_dist["zero_n"] == 1 and
   _synthetic_dist["excluded_unobserved_n"] == 1 and
   all(_synthetic_dist[key] == _same_values_more_missing[key]
       for key in ("p50", "p75", "p80")) and
   _synthetic_dist["p50"] != _without_observed_zero["p50"],
   "percentiles ignore absent observations but retain observed zero")
n_prop = sum(1 for e in inp["players"] for f in ("tprr_proxy", "first_read",
             "on_field_dropback_share", "inside5_share")
            if isinstance(e.get(f), dict)
             and "k" in e[f] and "n" in e[f])
ok(n_prop >= 100, "proportion inputs ship as k/n for interval math", str(n_prop))

engine_for_ids = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
engine_identity = PlayerIdentityResolver(engine_for_ids["players"])
matched = source_payloads["crosswalk.json"]["matched"]
usage_rows = source_payloads["usage_2025.json"]["players"]
carry_ledger = source_payloads["usage_2025.json"]["rb_player_team_carries"]
historical_rb = historical_rb_backfield_samples(carry_ledger)
historical_trimmed_counterfactual = historical_rb_backfield_samples(
    [row for row in usage_rows if row.get("pos") == "RB"])
current_roster_counterfactual = current_roster_rb_backfield_counterfactual(
    usage_rows, source_payloads["depth_charts.json"]["entries"])

# The producer fixture below specifies how the ledger is built. These committed-
# payload checks separately prove that build_usage_2025 actually wired the full
# all-week, pre-trim result into the shard rather than feeding the helper a
# trimmed or regular-season-only subset.
ledger_keys = [(row["team"], row["gsis_id"]) for row in carry_ledger]
ledger_content_sha256 = hashlib.sha256(json.dumps(
    carry_ledger, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
ledger_by_player = {}
for row in carry_ledger:
    ledger_by_player.setdefault(row["gsis_id"], []).append(row)
trimmed_rb_usage = {row["gsis_id"]: row for row in usage_rows
                    if row.get("pos") == "RB"}
depth_rb_teams = {
    row["gsis_id"]: canonical_team(row["team"])
    for row in source_payloads["depth_charts.json"]["entries"]
    if row.get("pos") == "RB" and row.get("gsis_id")
}
ledger_only_positive_ids = {
    player_id for player_id, rows in ledger_by_player.items()
    if player_id not in trimmed_rb_usage and
    any(row["carries"] > 0 for row in rows)
}
positive_multiteam_ids = {
    player_id for player_id, rows in ledger_by_player.items()
    if sum(row["carries"] > 0 for row in rows) > 1
}
trimmed_carry_mismatches = [
    player_id for player_id, usage_row in trimmed_rb_usage.items()
    if player_id not in ledger_by_player or
    sum(row["carries"] for row in ledger_by_player[player_id]) !=
    usage_row["carries"]
]
historical_team_mismatches = []
historical_current_movers = []
for player_id, usage_row in trimmed_rb_usage.items():
    positive_teams = [row["team"] for row in ledger_by_player.get(player_id, [])
                      if row["carries"] > 0]
    if len(positive_teams) != 1:
        continue
    historical_team = positive_teams[0]
    if historical_team != canonical_team(usage_row["team"]):
        historical_team_mismatches.append(player_id)
    if (player_id in depth_rb_teams and
            historical_team != depth_rb_teams[player_id]):
        historical_current_movers.append(player_id)
ok(ledger_keys == sorted(ledger_keys) and
   len(ledger_keys) == len(set(ledger_keys)) and
   len(carry_ledger) == 161 and
   len(ledger_by_player) == 154 and
   sum(row["carries"] for row in carry_ledger) == 12399 and
   {row["team"] for row in carry_ledger} == set(CANONICAL_NFL_TEAMS) and
   source_payloads["usage_2025.json"]["provenance"].get(
       "rb_carry_ledger_season_types") == ["POST", "REG"] and
   source_payloads["usage_2025.json"]["provenance"].get(
       "source_content_sha256") ==
       "2a461becaa9adb3c93a3074a3a31f1e960162a50163371a2d34e28393b5fff10" and
   ledger_content_sha256 ==
       "6efd886a6aafc396879edefeba227fd990d2cec82f1020540181b2f4a15ae3f0" and
   source_payloads["usage_2025.json"]["provenance"].get(
       "rb_carry_ledger_content_sha256") == ledger_content_sha256,
   "fixed 2025 RB source and ledger are exact, all-team, and explicitly all-week",
   (f"rows={len(carry_ledger)}, ids={len(ledger_by_player)}, "
    f"carries={sum(row['carries'] for row in carry_ledger)}, "
    f"ledger_sha={ledger_content_sha256}"))
ok(bool(ledger_only_positive_ids) and bool(positive_multiteam_ids) and
   not trimmed_carry_mismatches and not historical_team_mismatches and
   bool(historical_current_movers),
   "committed RB ledger preserves pre-trim rows, historical teams, splits, and all-week totals",
   (f"ledger-only={len(ledger_only_positive_ids)}, "
    f"multi-team={len(positive_multiteam_ids)}, "
    f"carry-mismatches={trimmed_carry_mismatches[:8]}, "
    f"team-mismatches={historical_team_mismatches[:8]}, "
    f"historical/current movers={len(historical_current_movers)}"))

synthetic_raw = [
    {"player_id": "incumbent", "player_display_name": "Incumbent",
     "position": "RB", "team": "DET", "season": 2025,
     "season_type": "REG", "carries": 240},
    {"player_id": "incumbent", "player_display_name": "Incumbent",
     "position": "RB", "team": "DET", "season": 2025,
     "season_type": "POST", "carries": 3},
    {"player_id": "departed", "player_display_name": "Departed",
     "position": "RB", "team": "DET", "season": 2025,
     "season_type": "REG", "carries": 158},
    {"player_id": "long-tail", "player_display_name": "Long Tail",
     "position": "RB", "team": "DET", "season": 2025,
     "season_type": "REG", "carries": 6},
    {"player_id": "traveler", "player_display_name": "Traveler",
     "position": "RB", "team": "JAX", "season": 2025,
     "season_type": "REG", "carries": 5},
    {"player_id": "traveler", "player_display_name": "Traveler",
     "position": "RB", "team": "PHI", "season": 2025,
     "season_type": "REG", "carries": 62},
    {"player_id": "jax-incumbent", "player_display_name": "Jax Incumbent",
     "position": "RB", "team": "JAX", "season": 2025,
     "season_type": "REG", "carries": 270},
    {"player_id": "phi-incumbent", "player_display_name": "Phi Incumbent",
     "position": "RB", "team": "PHI", "season": 2025,
     "season_type": "REG", "carries": 306},
    {"player_id": "qb", "player_display_name": "Quarterback",
     "position": "QB", "team": "DET", "season": 2025,
     "season_type": "REG", "carries": 100},
]
synthetic_ledger_result = aggregate_rb_player_team_carries(synthetic_raw)
synthetic_ledger = synthetic_ledger_result["rows"]
synthetic_historical = historical_rb_backfield_samples(synthetic_ledger)
ok(synthetic_ledger_result["season_types"] == ["POST", "REG"] and
   not any(row["gsis_id"] == "qb" for row in synthetic_ledger) and
   sorted(row["carries"] for row in synthetic_ledger
          if row["gsis_id"] == "traveler") == [5, 62] and
   "traveler" not in synthetic_historical and
   synthetic_historical["incumbent"]["player_carries"] == 243 and
   synthetic_historical["incumbent"]["team_rb_carries"] == 407 and
   synthetic_historical["jax-incumbent"]["team_rb_carries"] == 275 and
   synthetic_historical["phi-incumbent"]["team_rb_carries"] == 368,
   "RB ledger is all-week, untrimmed, position-specific, and split by team")

synthetic_usage = [
    {"gsis_id": "incumbent", "pos": "RB", "team": "DET", "carries": 243},
    {"gsis_id": "departed", "pos": "RB", "team": "DET", "carries": 158},
    {"gsis_id": "new-teammate", "pos": "RB", "team": "HOU", "carries": 100},
]
synthetic_depth = [
    {"gsis_id": "incumbent", "pos": "RB", "team": "DET"},
    {"gsis_id": "departed", "pos": "RB", "team": "HOU"},
    {"gsis_id": "new-teammate", "pos": "RB", "team": "HOU"},
]
synthetic_trimmed_historical = historical_rb_backfield_samples(synthetic_usage)
synthetic_retired = current_roster_rb_backfield_counterfactual(
    synthetic_usage, synthetic_depth)
ok(synthetic_trimmed_historical["incumbent"]["team"] == "DET" and
   synthetic_trimmed_historical["incumbent"]["team_rb_carries"] == 401 and
   synthetic_trimmed_historical["incumbent"]["value"] == 0.606 and
   synthetic_retired["incumbent"]["team_rb_carries"] == 243 and
   synthetic_retired["incumbent"]["value"] == 1.0,
   "departed RB stays in his historical denominator, not his current roster")

backfield_ok = True
observed_n = 0
expected_values = []
expected_trimmed_values = []
bad_backfield = []
for player in (p for p in inp["players"] if p["pos"] == "RB"):
    identity = engine_identity.resolve(player["name"], position="RB").record
    sleeper_id = str(identity.get("sleeper_id") or "") if identity else ""
    gsis_id = matched.get(sleeper_id)
    expected = historical_rb.get(gsis_id)
    actual = player.get("backfield_share")
    sample = player.get("backfield_share_sample")
    if expected is None:
        backfield_ok &= actual is None and sample is None
        if actual is not None or sample is not None:
            bad_backfield.append(player["name"])
    else:
        observed_n += 1
        expected_values.append(expected["value"])
        expected_sample = {
            "season": 2025,
            "historical_team": expected["team"],
            "player_carries": expected["player_carries"],
            "historical_team_rb_carries": expected["team_rb_carries"],
        }
        if actual != expected["value"] or sample != expected_sample:
            backfield_ok = False
            bad_backfield.append(player["name"])
    retired = current_roster_counterfactual.get(gsis_id)
    retired_sample = (None if retired is None else {
        "season": 2025,
        "current_roster_team": retired["team"],
        "player_carries": retired["player_carries"],
        "current_roster_team_rb_carries": retired["team_rb_carries"],
    })
    if (player.get("backfield_share_counterfactual_current_roster") !=
            (retired or {}).get("value") or
            player.get("backfield_share_counterfactual_sample") != retired_sample):
        backfield_ok = False
        bad_backfield.append(player["name"])
    trimmed = historical_trimmed_counterfactual.get(gsis_id)
    trimmed_sample = (None if trimmed is None else {
        "season": 2025,
        "historical_team": trimmed["team"],
        "player_carries": trimmed["player_carries"],
        "historical_team_rb_carries": trimmed["team_rb_carries"],
    })
    if (player.get("backfield_share_counterfactual_historical_trimmed") !=
            (trimmed or {}).get("value") or
            player.get("backfield_share_historical_trimmed_sample") !=
            trimmed_sample):
        backfield_ok = False
        bad_backfield.append(player["name"])
    if trimmed is not None:
        expected_trimmed_values.append(trimmed["value"])
ok(backfield_ok,
   "backfield shares use 2025 RB carries grouped by each player's 2025 team",
   ", ".join(bad_backfield[:8]))
bf = thr["rb_backfield_share"]
ok(bf["n"] == observed_n and
   bf["excluded_unobserved_n"] ==
       sum(p["pos"] == "RB" for p in inp["players"]) - observed_n,
   "backfield population reconciles observed and excluded identities",
   f"artifact={bf}, observed={observed_n}")
inside5_zeros = [p for p in inp["players"]
                 if p.get("inside5_share", {}).get("k") == 0 and
                 p.get("inside5_share", {}).get("n", 0) > 0]
expected_backfield_p50 = round(
    sorted(expected_values)[len(expected_values) // 2], 4)
def expected_backfield_distribution(values, excluded):
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "zero_n": sum(value == 0 for value in ordered),
        "excluded_unobserved_n": excluded,
        "p50": round(ordered[len(ordered) // 2], 4),
        "p75": round(ordered[int(round(.75 * (len(ordered) - 1)))], 4),
        "p80": round(ordered[int(round(.80 * (len(ordered) - 1)))], 4),
    }
expected_backfield_dist = expected_backfield_distribution(
    expected_values,
    sum(p["pos"] == "RB" for p in inp["players"]) - observed_n)
ok(all(bf[key] == expected_backfield_dist[key]
       for key in ("n", "zero_n", "excluded_unobserved_n", "p50", "p75", "p80")) and
   "upper middle" in bf.get("p50_method", "") and
   "untrimmed 2025 player-team carry ledger" in
       bf.get("observation_rule", ""),
   "historical-team backfield distribution rederives from committed usage",
   f"artifact={bf}, expected={expected_backfield_dist}")
counterfactual_values = [
    current_roster_counterfactual[matched.get(str(
        (engine_identity.resolve(player["name"], position="RB").record or {}).get(
            "sleeper_id") or ""))]["value"]
    for player in inp["players"] if player["pos"] == "RB" and
    matched.get(str((engine_identity.resolve(
        player["name"], position="RB").record or {}).get("sleeper_id") or ""))
    in current_roster_counterfactual
]
expected_counterfactual_dist = expected_backfield_distribution(
    counterfactual_values,
    sum(p["pos"] == "RB" for p in inp["players"]) -
    len(counterfactual_values))
counterfactual_dist = thr[
    "rb_backfield_share_counterfactual_current_roster"]
ok(all(counterfactual_dist[key] == expected_counterfactual_dist[key]
       for key in ("n", "zero_n", "excluded_unobserved_n", "p50", "p75", "p80")),
   "retired current-roster distribution remains an exact same-build baseline",
   f"artifact={counterfactual_dist}, expected={expected_counterfactual_dist}")
expected_trimmed_dist = expected_backfield_distribution(
    expected_trimmed_values,
    sum(p["pos"] == "RB" for p in inp["players"]) -
    len(expected_trimmed_values))
trimmed_dist = thr[
    "rb_backfield_share_counterfactual_historical_trimmed"]
ok(all(trimmed_dist[key] == expected_trimmed_dist[key]
       for key in ("n", "zero_n", "excluded_unobserved_n", "p50", "p75", "p80")),
   "grouping-only intermediate remains independently reproducible",
   f"artifact={trimmed_dist}, expected={expected_trimmed_dist}")
ok(thr["rb_inside5"]["zero_n"] == len(inside5_zeros) == 1,
   "real inside-five zero remains observed rather than excluded",
   str([p["name"] for p in inside5_zeros]))

# 2. QB gap derivation present with n and CI, both scorings
for key in ("league_6pt", "counterfactual_4pt"):
    g = inp["qb_gap"][key]
    ok(g["rushing"]["n"] + g["pocket"]["n"] == 120,
       f"qb gap {key} covers all 120 top-12 seasons",
       str(g["rushing"]["n"] + g["pocket"]["n"]))
    ok(g["gap_ci95"][0] < g["gap"] < g["gap_ci95"][1],
       f"qb gap {key} CI brackets the point estimate")

# 3. tags: statuses legal, scores match, criteria in [0,1], reasons on
#    demotions, TTL and timestamps present
LEGAL = {"BULLISH", "WATCH", "SUSPENDED", "REVOKED"}
engine_ids = {str(p.get("sleeper_id") or "")
              for p in engine_for_ids["players"]}
tag_ids = [str(t.get("sleeper_id") or "") for t in d["tags"]]
ok(all(tag_ids) and len(tag_ids) == len(set(tag_ids)) and
   set(tag_ids).issubset(engine_ids),
   "every BULLISH tag carries one unique canonical Sleeper identity")
for t in d["tags"]:
    if t["status"] not in LEGAL:
        ok(False, f"legal status for {t['name']}", t["status"])
    for c, p in t["criteria"].items():
        if p is not None and not (0 <= p <= 1):
            ok(False, f"criterion probability in range for {t['name']}/{c}", str(p))
    if t["status"] in ("SUSPENDED",) and not any("injury" in r for r in t["reasons"]):
        ok(False, f"suspension carries an injury reason for {t['name']}")
    if not (t.get("ttl_hours") == 72 and t.get("computed_at")):
        ok(False, f"ttl and timestamp on {t['name']}")
print(f"PASS  every tag has legal status, bounded criteria, ttl, timestamp "
      f"({len(d['tags'])} tags)")
ok(any(t["status"] == "BULLISH" for t in d["tags"]), "a nonempty BULLISH set")
ok(any(t["status"] == "WATCH" for t in d["tags"]),
   "near-misses render as WATCH, not silently dropped")

te_susp = d.get("te_gate_suspension", {})
omitted_te = te_susp.get("omitted_tags", [])
expected_te = {
    ("Trey McBride", "BULLISH", 90.0),
    ("Tyler Warren", "BULLISH", 90.0),
    ("Kyle Pitts", "BULLISH", 90.0),
    ("Travis Kelce", "BULLISH", 88.9),
    ("Hunter Henry", "WATCH", 45.0),
}
ok(not any(t["pos"] == "TE" for t in d["tags"]) and
   {(t["name"], t["status"], t["score"]) for t in omitted_te} == expected_te,
   "TE rows are omitted while the five-row computed shadow ledger remains")
te_evidence = te_susp.get("evidence", {})
mismatches = te_evidence.get("historical_share_current_team_mismatches", [])
ok(te_susp.get("status") == "SUSPENDED" and
   te_evidence.get("draftable_tes") == 20 and
   te_evidence.get("veterans_with_both_inputs") == 19 and
   te_evidence.get("market_share_probability_counts") == {"0.9": 19, "0.2": 0},
   "TE suspension proves the former second criterion was constant")
ok(len(mismatches) == 1 and
   mismatches[0].get("share_team") == "BAL" and
   mismatches[0].get("rank_group_team") == "NYG" and
   mismatches[0].get("rank_group_size") == 1 and
   mismatches[0].get("assigned_probability") == 0.9,
   "TE suspension records the historical-share/current-team grouping defect",
   str(mismatches))
ok("one varying input" in te_susp.get("display_note", "") and
   "genuine routes-run input" in " ".join(te_susp.get("resume_requires", [])).lower(),
   "TE absence is explained and has explicit resume conditions")
ok(all("route_participation" not in tag.get("criteria", {})
       for tag in d["tags"] + omitted_te) and
   all("route_part" not in player and
       "on_field_dropback_share" in player
       for player in inp["players"] if player.get("routes_proxy") and
       player.get("on_field_dropback_share")),
   "live and shadow artifacts name on-field dropbacks honestly, never routes")

# 4. no hard cliffs: WATCH band exists between the conventions
conv = d["provenance"]["conventions"]
ok(conv["watch_p"] < conv["bullish_p"], "watch band below the bullish level")

# 5. ADP-edge accountability: the question is answered either way
edge = d["adp_edge"]
ok("what do the tags find" in edge["question"], "the edge question is stated")
ok(edge["statement"].startswith("NULL RESULT") or len(edge["divergent"]) > 0,
   "edge statement is explicit: divergence list or a recorded null")
if edge["divergent"]:
    ok(all(x["gap"] >= 4 for x in edge["divergent"]),
       "every divergent entry clears the stated margin")

# 6. TE adjudication logged with a verdict naming both reports' claims
te = d["te_scarcity_adjudication"]
ok("SUPPORTED" in te["verdict"] or "CONTRADICTED" in te["verdict"],
   "TE scarcity verdict is explicit")
ok(len(te["gaps_ppg"]["te1_te12"]) == 3, "TE gaps computed for all three seasons")

# 7. delta report structure (the T-24h diff engine)
ok(set(d["delta"].keys()) == {"previous", "gained", "lost", "status_changed"},
   "delta report structure present")
activation = d.get("forward_vegas_activation", {})
ok(activation.get("status") == "ACTIVATED" and
   activation.get("scope") == ["QB.environment", "WR.opportunity"] and
   activation.get("replacement") == forward_vegas and
   activation.get("rb_invariance", {}).get("tag_records_identical") is True and
   activation["rb_invariance"]["before_count"] ==
   activation["rb_invariance"]["after_count"],
   "forward activation ledger is permanent, scoped, and proves RB invariance")
ok(all(item.endswith("|QB") or item.endswith("|WR")
       for item in activation.get("gained", []) + activation.get("lost", [])) and
   all(item.get("player", "").endswith("|QB") or
       item.get("player", "").endswith("|WR")
       for item in activation.get("status_changed", []) +
       activation.get("score_changed", [])),
   "forward activation delta contains only the approved QB/WR consumers")
backfield_repair = d.get("rb_backfield_denominator_repair", {})
backfield_changed = (
    backfield_repair.get("gained", []) + backfield_repair.get("lost", []) +
    [x.get("player", "") for x in
     backfield_repair.get("status_changed", [])] +
    [x.get("player", "") for x in
     backfield_repair.get("score_changed", []) +
     backfield_repair.get("gate_score_changed", [])]
)
expected_input_changes = []
for player in inp["players"]:
    if (player["pos"] == "RB" and
            player.get("backfield_share") !=
            player.get("backfield_share_counterfactual_current_roster")):
        expected_input_changes.append({
            "player": f"{player['name']}|RB",
            "before": player.get(
                "backfield_share_counterfactual_current_roster"),
            "after": player.get("backfield_share"),
            "before_sample": player.get(
                "backfield_share_counterfactual_sample"),
            "after_sample": player.get("backfield_share_sample"),
        })
live_tags = {f"{tag['name']}|{tag['pos']}": tag for tag in d["tags"]}
ok(backfield_repair.get("status") == "ACTIVATED" and
   backfield_repair.get("scope") == ["RB.backfield_command"] and
   bool(expected_input_changes) and
   backfield_repair.get("input_changed") == expected_input_changes and
   backfield_repair.get("thresholds", {}).get("before") ==
       counterfactual_dist and
   backfield_repair.get("thresholds", {}).get("after") == bf,
   "RB denominator activation ledger is complete and same-build",
   str(backfield_repair))
components = backfield_repair.get("component_attribution", {})
grouping_component = components.get("grouping_only", {})
completeness_component = components.get("untrimmed_split_ledger", {})
ok(grouping_component.get("before_threshold") == counterfactual_dist and
   grouping_component.get("after_threshold") == trimmed_dist and
   completeness_component.get("before_threshold") == trimmed_dist and
   completeness_component.get("after_threshold") == bf,
   "RB repair separates historical grouping from the untrimmed split ledger",
   str(components))
component_changed = []
for component in (grouping_component, completeness_component):
    component_changed += component.get("gained", []) + component.get("lost", [])
    component_changed += [
        item.get("player", "") for item in
        component.get("status_changed", []) + component.get("score_changed", []) +
        component.get("gate_score_changed", [])]
grouping_changed = (grouping_component.get("gained", []) +
                    grouping_component.get("lost", []) +
                    grouping_component.get("status_changed", []) +
                    grouping_component.get("score_changed", []) +
                    grouping_component.get("gate_score_changed", []))
completeness_changed = (completeness_component.get("gained", []) +
                        completeness_component.get("lost", []) +
                        completeness_component.get("status_changed", []) +
                        completeness_component.get("score_changed", []) +
                        completeness_component.get("gate_score_changed", []))
ok(bool(grouping_changed) and bool(completeness_changed) and
   all(key.endswith("|RB") for key in component_changed),
   "both RB attribution components bite and remain position-isolated")
ok(bool(backfield_changed) and
   all(key.endswith("|RB") for key in backfield_changed) and
   backfield_repair.get("non_rb_invariance", {}).get(
       "tag_records_identical") is True and
   backfield_repair["non_rb_invariance"]["before_count"] ==
       backfield_repair["non_rb_invariance"]["after_count"],
   "RB denominator repair changes only RB records and proves non-RB invariance")
ok(bool(backfield_repair.get("score_changed")) and
   all(item["player"] in live_tags and
       live_tags[item["player"]]["score"] == item["after"]
       for item in backfield_repair.get("score_changed", [])),
   "RB denominator score delta reconciles to the live same-build tags")
ok(bool(backfield_repair.get("gate_score_changed")) and
   all(item["player"] not in live_tags or
       live_tags[item["player"]]["score"] == item["after"]
       for item in backfield_repair.get("gate_score_changed", [])) and
   {item["player"] for item in backfield_repair.get("score_changed", [])} <=
   {item["player"] for item in
    backfield_repair.get("gate_score_changed", [])},
   "full RB gate-score ledger includes and reconciles every displayed score move")
ok("does not measure 2026 carries opened" in
   backfield_repair.get("open_inverse_gap", ""),
   "RB ledger states the vacated-carries inverse gap without claiming a fix")
refresh_delta = d.get("forward_vegas_delta", {})
refresh_same_build = refresh_delta.get("same_build_counterfactual", {})
refresh_changed = (
    refresh_same_build.get("gained", []) + refresh_same_build.get("lost", []) +
    [x.get("player", "") for x in refresh_same_build.get("status_changed", [])] +
    [x.get("player", "") for x in refresh_same_build.get("score_changed", [])]
)
ok(refresh_delta.get("event") in
   {"HORIZON_EXTENDED", "CONTRACTED", "REPRICED", "UNCHANGED"} and
   refresh_delta.get("current", {}).get("games_priced") ==
   forward_vegas["games_priced"] and
   refresh_delta.get("current", {}).get("team_games_priced") ==
   forward_vegas["team_games_priced"] and
   refresh_same_build.get("rb_invariance", {}).get(
       "tag_records_identical") is True and
   all(x.endswith("|QB") or x.endswith("|WR") for x in refresh_changed),
   "daily forward event is explicit, same-build, and QB/WR isolated",
   str(refresh_delta))

# 8. pages: chips wired display-only, beside the signal encoding
bp = open(os.path.join(ROOT, "out", "big_board.html")).read()
drp = open(os.path.join(ROOT, "out", "draft_room.html")).read()
ok("bullishChip" in bp and 'get("data/bullish_2026.json")' in bp,
   "board chip wired with optional load")
ok("bullishTag" in bp and "x.name === p.name" not in bp and
   "x.pos === p.pos" not in bp,
   "big board joins BULLISH tags by Sleeper identity, never raw name")
ok("bullChip" in drp and
   'fetch("data/bullish_2026.json", {cache:"no-store"})' in drp,
   "room chip wired with an uncached optional load")
ok("never" in drp[drp.index("C5 BULLISH layer"):drp.index("C5 BULLISH layer") + 300]
   and "replacing" in drp[drp.index("C5 BULLISH layer"):drp.index("C5 BULLISH layer") + 300],
   "room states the tag sits beside the signal encoding, never replacing it")
for page, chip in ((bp, "bullishChip"), (drp, "bullChip")):
    seg = page[page.index(f"function {chip}"):]
    seg = seg[:seg.index("\n}")]
    ok("ttl_hours" in seg and "ageH" in seg, f"{chip} enforces the 72h TTL with age display")
ok("TAGS STALE" in bp and "TAGS STALE" in drp,
   "engine mismatch renders a neutral stale tag, never a current verdict")
home_page = open(os.path.join(ROOT, "out", "home.html")).read()
ok("forward-vegas-delta" in home_page and
   'fetch(f, {cache:"no-store"})' in home_page and
   "last_material_event" in home_page and
   "same-build schedule-only comparison" in home_page and
   "forwardVegasStatus" in drp and "forward_vegas_delta" in drp,
   "home provenance and draft room expose the persisted forward refresh event")
players_page = open(os.path.join(ROOT, "out", "players.html")).read()
ok("pBullCurrent" in players_page and
   "BULLISH tags stale versus current board" in players_page,
   "players filter disables stale BULLISH semantics visibly")
for page, label in ((bp, "board"), (drp, "room"), (players_page, "players")):
    ok('id="bull-status"' in page and "te_gate_suspension" in page and
       "display_note" in page,
       f"{label} renders the artifact's neutral TE-suspension explanation")
builder = open(os.path.join(ROOT, "src", "build_bullish.py")).read()
ok("inputs_digest != engine_digest" in builder and
   "build_bullish_inputs.py first" in builder,
   "tag builder refuses inputs from a different engine payload")
rb_consumer = builder[builder.index('if pos == "RB":'):
                      builder.index('elif pos == "WR":')]
wr_consumer = builder[builder.index('elif pos == "WR":'):
                      builder.index('elif pos == "QB":')]
qb_consumer = builder[builder.index('elif pos == "QB":'):
                      builder.index('else:  # TE')]
ok("forward_implied_total" not in rb_consumer and "implied_tds" in rb_consumer and
   "top5_forward_implied" in wr_consumer and
   "forward_implied_total" in qb_consumer,
   "forward Vegas feeds QB/WR only; RB remains on Week-1 expected TDs")
inputs_builder = open(os.path.join(ROOT, "src", "build_bullish_inputs.py")).read()
ok("ceiling_digest != engine_digest" in inputs_builder and
   "build_ceiling.py first" in inputs_builder,
   "input builder refuses ceiling values from a different engine payload")
_pe_seg = drp[drp.index("function peScore"):drp.index("function peCondition")]
ok("bullChip" not in _pe_seg and "BULL" not in _pe_seg,
   "the tag never enters the pick-engine score")

# 9. builder sources carry no player-name constants (canary, code body only)
for srcf in ("build_bullish.py", "build_bullish_inputs.py"):
    src = open(os.path.join(ROOT, "src", srcf)).read()
    body = re.sub(r'\A(#![^\n]*\n)?"""[\s\S]*?"""', "", src, count=1)
    canaries = ["McCaffrey", "Gibbs", "Bijan", "Bowers", "McBride", "Nacua",
                "Allen", "Prescott", "Chase"]
    hit = [c for c in canaries if c in body]
    ok(not hit, f"{srcf} code body has no player-name constants", str(hit))

# 10. The historical TE extract is evidence, not a second fake route source.
te_csv = os.path.join(ROOT, "docs", "ffopportunity", "bullish_te_2020_2025.csv")
with open(te_csv, newline="") as fh:
    te_reader = csv.DictReader(fh)
    te_rows = list(te_reader)
    te_fields = te_reader.fieldnames or []
ok(len(te_rows) == 6730 and len(te_fields) == 20 and
   all((row.get("player_id") or "").strip() and row.get("position") == "TE"
       for row in te_rows),
   "historical TE extract has 6,730 identified TE rows and no NA-subsetting junk")
ok("route_participation_proxy" not in te_fields,
   "historical TE extract does not relabel expected receptions as routes")
for rel in ("ALL_R_CODE.R", "ALL_R_CODE.md"):
    r_source = open(os.path.join(ROOT, "docs", "ffopportunity", rel)).read()
    ok("route_participation_proxy <-" not in r_source and
       'wk[wk$position == "TE"' not in r_source,
       f"{rel} cannot regenerate the false route alias or NA-subsetting junk")

print()
if fails:
    print(f"{len(fails)} FAILURES")
    sys.exit(1)
print("ALL PASS")
