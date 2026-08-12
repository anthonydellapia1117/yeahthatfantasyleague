#!/usr/bin/env python3
"""Export the specified Yahoo and Sleeper fantasy-football league history.

Tested with Python 3.12 and yfpy 17.0.0. Yahoo data comes from Yahoo's
authenticated Fantasy Sports REST API through yfpy. Sleeper data comes from
Sleeper's public, read-only API.

Outputs one directory per platform/season containing:
  draft_results.csv
  weekly_rosters.csv
  transactions.csv
  standings.csv
  matchups.csv
  scoring_settings.json

The Yahoo weekly_rosters.csv fantasy_points value is copied directly from
Yahoo player_points.total. It is not recomputed from stat rows, so Yahoo's
league-scored bonuses are retained.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any, Callable, Iterable


SCRIPT_VERSION = "1.0.0"
SCRIPT_DIR = Path(__file__).resolve().parent

# IDs are authoritative. League names are deliberately not present or used.
YAHOO_LEAGUES: dict[int, list[str]] = {
    2013: ["777575"],
    2014: ["605315"],
    2015: ["902076"],
    2016: ["827116"],
    2017: ["351067", "701692"],  # Probe both; prefer the supplied working URL if both respond.
    2018: ["562266"],
    2019: ["222624"],
    2020: ["275203"],
    2021: ["428007"],
    2022: ["367036"],
    2023: ["243817"],
    2024: ["42081"],
}

SLEEPER_LEAGUES: dict[int, str] = {
    2025: "1245905122328846336",
    2026: "1389378429505241088",
}

# Intentionally excluded: the verified-empty 2024 trial shell 1092592577628426240.
EXCLUDED_SLEEPER_LEAGUES = {2024: "1092592577628426240"}

SLEEPER_API = "https://api.sleeper.app/v1"
RESERVE_SLOTS = {"IR", "IR+", "IL", "IL+", "DL", "NA", "RES", "RESERVE", "TAXI"}


DRAFT_FIELDS = [
    "platform", "season", "league_id", "league_key", "draft_id", "draft_type",
    "round", "overall_pick", "draft_slot", "team_id", "team_key", "team_name",
    "owner_id", "owner_name", "player_id", "player_key", "player_name", "position",
    "nfl_team", "adp_overall", "adp_round", "average_draft_cost", "percent_drafted",
    "adp_source", "auction_cost", "is_keeper", "raw_json",
]

ROSTER_FIELDS = [
    "platform", "season", "league_id", "league_key", "week", "team_id", "team_key",
    "team_name", "owner_id", "owner_name", "player_id", "player_key", "player_name",
    "position", "nfl_team", "lineup_slot", "lineup_status", "started", "is_flex",
    "fantasy_points", "points_source", "team_week_points", "starter_points_sum",
    "score_check_difference", "stat_values_json", "raw_json",
]

TRANSACTION_FIELDS = [
    "platform", "season", "league_id", "league_key", "week", "week_source",
    "transaction_id", "transaction_key", "type", "status", "timestamp_epoch",
    "timestamp_utc", "status_updated_utc", "asset_type", "action", "player_id",
    "player_key", "player_name", "position", "nfl_team", "draft_pick_season",
    "draft_pick_round", "original_team_id", "source_team_id", "source_team_key",
    "source_team_name", "destination_team_id", "destination_team_key",
    "destination_team_name", "faab_bid", "waiver_priority", "waiver_sequence",
    "destination_team_waiver_priority_at_export", "faab_transfer_amount", "creator_id",
    "raw_json",
]

STANDINGS_FIELDS = [
    "platform", "season", "league_id", "league_key", "rank", "rank_source", "team_id",
    "team_key", "team_name", "owner_id", "owner_name", "wins", "losses", "ties",
    "win_percentage", "points_for", "points_against", "possible_points", "waiver_priority",
    "faab_balance", "faab_used", "total_moves", "playoff_seed", "streak", "division",
    "raw_json",
]

MATCHUP_FIELDS = [
    "platform", "season", "league_id", "league_key", "week", "matchup_id", "status",
    "is_playoffs", "is_consolation", "team_id", "team_key", "team_name", "team_points",
    "custom_points", "opponent_team_id", "opponent_team_key", "opponent_team_name",
    "opponent_points", "result", "winner_team_id", "is_tied", "league_median_points",
    "median_result", "raw_json",
]


def eprint(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def as_list(obj: Any) -> list[Any]:
    if obj is None or obj == {} or obj == []:
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, tuple):
        return list(obj)
    return [obj]


def plain(obj: Any) -> Any:
    """Recursively turn yfpy objects and bytes into JSON-safe Python values."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if isinstance(obj, dict):
        return {str(k): plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [plain(v) for v in obj]
    if hasattr(obj, "serialized"):
        return plain(obj.serialized())
    if hasattr(obj, "__dict__"):
        return {
            str(k): plain(v)
            for k, v in vars(obj).items()
            if not str(k).startswith("_")
        }
    return str(obj)


def json_compact(obj: Any) -> str:
    return json.dumps(plain(obj), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def text(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    return str(obj)


def integer(obj: Any, default: int | None = None) -> int | None:
    try:
        if obj is None or obj == "":
            return default
        return int(obj)
    except (TypeError, ValueError):
        return default


def number(obj: Any, default: float | None = None) -> float | None:
    try:
        if obj is None or obj == "":
            return default
        return float(obj)
    except (TypeError, ValueError):
        return default


def nonempty(obj: Any) -> bool:
    return obj is not None and obj != "" and obj != [] and obj != {}


def iso_timestamp(epoch: Any, milliseconds: bool = False) -> str:
    numeric = number(epoch)
    if numeric is None:
        return ""
    if milliseconds:
        numeric /= 1000.0
    try:
        return datetime.fromtimestamp(numeric, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (OverflowError, OSError, ValueError):
        return ""


def team_id_from_key(team_key: Any) -> str:
    key = text(team_key)
    return key.rsplit(".t.", 1)[-1] if ".t." in key else ""


def player_id_from_key(player_key: Any) -> str:
    key = text(player_key)
    return key.rsplit(".p.", 1)[-1] if ".p." in key else ""


def write_csv_atomic(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    os.replace(temporary, path)


def write_json_atomic(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(plain(obj), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def chunks(items: list[str], size: int) -> Iterable[list[str]]:
    for start in range(0, len(items), size):
        yield items[start:start + size]


def result_from_scores(team_points: float | None, opponent_points: float | None) -> str:
    if team_points is None or opponent_points is None:
        return ""
    if team_points > opponent_points:
        return "W"
    if team_points < opponent_points:
        return "L"
    return "T"


def median_result(team_points: float | None, median_points: float | None) -> str:
    return result_from_scores(team_points, median_points)


def sleeper_combined_points(settings: dict[str, Any], base: str) -> float | None:
    whole = settings.get(base)
    if whole is None:
        return None
    decimal_value = integer(settings.get(f"{base}_decimal"), 0) or 0
    return float(whole) + decimal_value / 100.0


def owner_fields_from_yahoo(team: Any) -> tuple[str, str]:
    managers = as_list(value(team, "managers", []))
    owner_ids: list[str] = []
    owner_names: list[str] = []
    for manager in managers:
        owner_id = text(value(manager, "manager_id", ""))
        owner_name = text(value(manager, "nickname", ""))
        if owner_id:
            owner_ids.append(owner_id)
        if owner_name:
            owner_names.append(owner_name)
    return "|".join(owner_ids), "|".join(owner_names)


def yahoo_team_info(team: Any) -> dict[str, Any]:
    owner_id, owner_name = owner_fields_from_yahoo(team)
    team_key = text(value(team, "team_key", ""))
    return {
        "team_id": text(value(team, "team_id", "")) or team_id_from_key(team_key),
        "team_key": team_key,
        "team_name": text(value(team, "name", "")),
        "owner_id": owner_id,
        "owner_name": owner_name,
        "wins": integer(value(team, "wins", None)),
        "losses": integer(value(team, "losses", None)),
        "ties": integer(value(team, "ties", None)),
        "win_percentage": number(value(team, "percentage", None)),
        "points_for": number(value(team, "points_for", None)),
        "points_against": number(value(team, "points_against", None)),
        "waiver_priority": integer(value(team, "waiver_priority", None)),
        "faab_balance": integer(value(team, "faab_balance", None)),
        "total_moves": integer(value(team, "number_of_moves", None)),
        "playoff_seed": integer(value(team, "playoff_seed", None)),
        "rank": integer(value(team, "rank", None)),
        "draft_slot": integer(value(team, "draft_position", None)),
        "streak": "".join(
            part for part in [text(value(team, "streak_length", "")), text(value(team, "streak_type", ""))] if part
        ),
        "division": text(value(team, "division_id", "")),
        "raw": plain(team),
    }


def merge_yahoo_team_maps(team_groups: Iterable[Iterable[Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_id: dict[str, dict[str, Any]] = {}
    by_key: dict[str, dict[str, Any]] = {}
    for group in team_groups:
        for team in as_list(group):
            incoming = yahoo_team_info(team)
            team_id = incoming["team_id"]
            team_key = incoming["team_key"]
            current = by_id.get(team_id, {}).copy()
            for key, item in incoming.items():
                if nonempty(item) or key not in current:
                    current[key] = item
            if team_id:
                by_id[team_id] = current
            if team_key:
                by_key[team_key] = current
    return by_id, by_key


class YahooCaller:
    def __init__(self, query: Any, data_not_found_type: type[Exception], delay: float, attempts: int = 6):
        self.query = query
        self.data_not_found_type = data_not_found_type
        self.delay = max(0.0, delay)
        self.attempts = max(1, attempts)

    def call(
        self,
        label: str,
        function: Callable[[], Any],
        *,
        empty_on_not_found: bool = False,
    ) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, self.attempts + 1):
            try:
                result = function()
                return result
            except self.data_not_found_type as exc:
                if empty_on_not_found:
                    return None
                last_error = exc
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as exc:  # Network/library errors are retried and surfaced if exhausted.
                last_error = exc
            finally:
                # yfpy retains every Response object; clear it to keep a 12-season run bounded in memory.
                if hasattr(self.query, "executed_queries"):
                    self.query.executed_queries.clear()

            if attempt < self.attempts:
                message = text(last_error).lower()
                rate_limited = "rate limit" in message or "status code of 999" in message or " 999" in message
                base = 60.0 if rate_limited else 3.0
                wait = min(300.0, base * (2 ** (attempt - 1))) + random.uniform(0.0, 1.0)
                eprint(f"{label} failed ({last_error}); retry {attempt}/{self.attempts - 1} in {wait:.1f}s")
                time.sleep(wait)

        assert last_error is not None
        raise RuntimeError(f"{label} failed after {self.attempts} attempts: {last_error}") from last_error

        # Unreachable; delay is applied in call_with_delay below.

    def call_with_delay(
        self,
        label: str,
        function: Callable[[], Any],
        *,
        empty_on_not_found: bool = False,
    ) -> Any:
        try:
            return self.call(label, function, empty_on_not_found=empty_on_not_found)
        finally:
            if self.delay:
                time.sleep(self.delay)


def set_yahoo_league(query: Any, game_key: str, league_id: str) -> None:
    query.game_id = integer(game_key)
    query.league_id = str(league_id)
    # game_key was resolved moments earlier by get_game_key_by_season; it is never hard-coded.
    query.league_key = f"{game_key}.l.{league_id}"


def yahoo_lineup_slot_classes(settings: Any) -> tuple[set[str], set[str], set[str]]:
    starters: set[str] = set()
    benches: set[str] = set()
    reserves: set[str] = set(RESERVE_SLOTS)
    for roster_position in as_list(value(settings, "roster_positions", [])):
        slot = text(value(roster_position, "position", ""))
        if not slot:
            continue
        if integer(value(roster_position, "is_starting_position", 0), 0) == 1:
            starters.add(slot)
        elif integer(value(roster_position, "is_bench", 0), 0) == 1 or slot == "BN":
            benches.add(slot)
        else:
            reserves.add(slot)
    benches.add("BN")
    return starters, benches, reserves


def classify_yahoo_slot(slot: str, starters: set[str], benches: set[str], reserves: set[str]) -> tuple[str, int]:
    if slot in starters:
        return "starter", 1
    if slot in benches:
        return "bench", 0
    if slot in reserves or slot.upper() in RESERVE_SLOTS:
        return "reserve", 0
    if not slot:
        return "unknown", 0
    # Old Yahoo settings occasionally omit the is_starting_position flag. A non-reserve football slot is active.
    return "starter", 1


def yahoo_player_record(player: Any) -> dict[str, Any]:
    raw = plain(player)
    name = value(player, "full_name", "")
    if not name:
        name_obj = value(player, "name", {})
        name = value(name_obj, "full", "")
    key = text(value(player, "player_key", ""))
    return {
        "player_id": text(value(player, "player_id", "")) or player_id_from_key(key),
        "player_key": key,
        "player_name": text(name),
        "position": text(value(player, "primary_position", "")) or text(value(player, "display_position", "")),
        "nfl_team": text(value(player, "editorial_team_abbr", "")),
        "raw": raw,
    }


def yahoo_standings_rows(
    season: int,
    league_id: str,
    league_key: str,
    teams_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ordered = sorted(
        teams_by_id.values(),
        key=lambda team: (team.get("rank") is None, team.get("rank") or 999, integer(team.get("team_id"), 999)),
    )
    for team in ordered:
        rows.append({
            "platform": "yahoo", "season": season, "league_id": league_id, "league_key": league_key,
            "rank": team.get("rank"), "rank_source": "Yahoo standings", "team_id": team.get("team_id"),
            "team_key": team.get("team_key"), "team_name": team.get("team_name"),
            "owner_id": team.get("owner_id"), "owner_name": team.get("owner_name"),
            "wins": team.get("wins"), "losses": team.get("losses"), "ties": team.get("ties"),
            "win_percentage": team.get("win_percentage"), "points_for": team.get("points_for"),
            "points_against": team.get("points_against"), "possible_points": "",
            "waiver_priority": team.get("waiver_priority"), "faab_balance": team.get("faab_balance"),
            "faab_used": "", "total_moves": team.get("total_moves"),
            "playoff_seed": team.get("playoff_seed"), "streak": team.get("streak"),
            "division": team.get("division"), "raw_json": json_compact(team.get("raw", {})),
        })
    return rows


def yahoo_matchup_rows(
    query: Any,
    caller: YahooCaller,
    season: int,
    league_id: str,
    league_key: str,
    start_week: int,
    end_week: int,
    teams_by_id: dict[str, dict[str, Any]],
    teams_by_key: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[tuple[int, str], float]]:
    rows: list[dict[str, Any]] = []
    team_week_points: dict[tuple[int, str], float] = {}
    for week in range(start_week, end_week + 1):
        eprint(f"[Yahoo {season}] matchups week {week}/{end_week}")
        matchups = caller.call_with_delay(
            f"Yahoo {season} matchups week {week}",
            lambda week=week: query.get_league_matchups_by_week(week),
            empty_on_not_found=True,
        )
        week_entries: list[tuple[Any, list[Any]]] = []
        all_week_points: list[float] = []
        for index, matchup in enumerate(as_list(matchups), start=1):
            matchup_teams = as_list(value(matchup, "teams", []))
            week_entries.append((matchup, matchup_teams))
            for matchup_team in matchup_teams:
                points = number(value(matchup_team, "points", None))
                if points is not None:
                    all_week_points.append(points)
        week_median = statistics.median(all_week_points) if all_week_points else None

        for index, (matchup, matchup_teams) in enumerate(week_entries, start=1):
            matchup_week = integer(value(matchup, "week", week), week) or week
            winner_key = text(value(matchup, "winner_team_key", ""))
            for team_index, matchup_team in enumerate(matchup_teams):
                team_key = text(value(matchup_team, "team_key", ""))
                team_id = text(value(matchup_team, "team_id", "")) or team_id_from_key(team_key)
                info = teams_by_key.get(team_key) or teams_by_id.get(team_id, {})
                points = number(value(matchup_team, "points", None))
                opponent = matchup_teams[1 - team_index] if len(matchup_teams) == 2 else None
                opponent_key = text(value(opponent, "team_key", "")) if opponent else ""
                opponent_id = (
                    text(value(opponent, "team_id", "")) or team_id_from_key(opponent_key)
                    if opponent else ""
                )
                opponent_info = teams_by_key.get(opponent_key) or teams_by_id.get(opponent_id, {})
                opponent_points = number(value(opponent, "points", None)) if opponent else None
                result = result_from_scores(points, opponent_points)
                winner_id = team_id_from_key(winner_key)
                if points is not None:
                    team_week_points[(matchup_week, team_id)] = points
                rows.append({
                    "platform": "yahoo", "season": season, "league_id": league_id,
                    "league_key": league_key, "week": matchup_week,
                    "matchup_id": f"{matchup_week}-{index}", "status": text(value(matchup, "status", "")),
                    "is_playoffs": integer(value(matchup, "is_playoffs", 0), 0),
                    "is_consolation": integer(value(matchup, "is_consolation", 0), 0),
                    "team_id": team_id, "team_key": team_key,
                    "team_name": info.get("team_name") or text(value(matchup_team, "name", "")),
                    "team_points": points, "custom_points": "", "opponent_team_id": opponent_id,
                    "opponent_team_key": opponent_key,
                    "opponent_team_name": opponent_info.get("team_name") or text(value(opponent, "name", "")),
                    "opponent_points": opponent_points, "result": result, "winner_team_id": winner_id,
                    "is_tied": integer(value(matchup, "is_tied", result == "T"), int(result == "T")),
                    "league_median_points": week_median, "median_result": median_result(points, week_median),
                    "raw_json": json_compact(matchup),
                })
    return rows, team_week_points


def yahoo_weekly_roster_rows(
    query: Any,
    caller: YahooCaller,
    season: int,
    league_id: str,
    league_key: str,
    start_week: int,
    end_week: int,
    teams_by_id: dict[str, dict[str, Any]],
    team_week_points: dict[tuple[int, str], float],
    settings: Any,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, int]]:
    rows: list[dict[str, Any]] = []
    player_catalog: dict[str, dict[str, Any]] = {}
    starters, benches, reserves = yahoo_lineup_slot_classes(settings)
    score_checks = {"exact": 0, "mismatched": 0, "missing": 0}
    ordered_teams = sorted(teams_by_id.values(), key=lambda item: integer(item.get("team_id"), 999) or 999)

    for week in range(start_week, end_week + 1):
        eprint(f"[Yahoo {season}] weekly rosters week {week}/{end_week}")
        for team in ordered_teams:
            team_id = text(team.get("team_id"))
            players = caller.call_with_delay(
                f"Yahoo {season} team {team_id} roster week {week}",
                lambda team_id=team_id, week=week: query.get_team_roster_player_stats_by_week(team_id, week),
                empty_on_not_found=True,
            )
            team_rows: list[dict[str, Any]] = []
            starter_points: list[float] = []
            missing_started_points = False
            for player in as_list(players):
                info = yahoo_player_record(player)
                if info["player_key"]:
                    player_catalog[info["player_key"]] = info
                raw = info["raw"] if isinstance(info["raw"], dict) else {}
                selected = value(player, "selected_position", {})
                slot = text(value(selected, "position", "")) or text(value(player, "selected_position_value", ""))
                lineup_status, started = classify_yahoo_slot(slot, starters, benches, reserves)
                player_points = raw.get("player_points") if isinstance(raw, dict) else None
                point_total = number(value(player_points, "total", None)) if player_points else None
                if started:
                    if point_total is None:
                        missing_started_points = True
                    else:
                        starter_points.append(point_total)
                team_rows.append({
                    "platform": "yahoo", "season": season, "league_id": league_id,
                    "league_key": league_key, "week": week, "team_id": team_id,
                    "team_key": team.get("team_key"), "team_name": team.get("team_name"),
                    "owner_id": team.get("owner_id"), "owner_name": team.get("owner_name"),
                    "player_id": info["player_id"], "player_key": info["player_key"],
                    "player_name": info["player_name"], "position": info["position"],
                    "nfl_team": info["nfl_team"], "lineup_slot": slot,
                    "lineup_status": lineup_status, "started": started,
                    "is_flex": integer(value(selected, "is_flex", 0), 0),
                    "fantasy_points": point_total,
                    "points_source": "Yahoo player_points.total (league-scored)",
                    "stat_values_json": json_compact(raw.get("player_stats", {})),
                    "raw_json": json_compact(raw),
                })

            official_team_points = team_week_points.get((week, team_id))
            starter_sum = None if missing_started_points else round(sum(starter_points), 6)
            difference = (
                round(official_team_points - starter_sum, 6)
                if official_team_points is not None and starter_sum is not None else None
            )
            if difference is None:
                score_checks["missing"] += 1
            elif abs(difference) <= 0.01:
                score_checks["exact"] += 1
            else:
                score_checks["mismatched"] += 1
            for row in team_rows:
                row["team_week_points"] = official_team_points
                row["starter_points_sum"] = starter_sum
                row["score_check_difference"] = difference
            rows.extend(team_rows)

    return rows, player_catalog, score_checks


def yahoo_draft_rows(
    query: Any,
    caller: YahooCaller,
    season: int,
    league_id: str,
    league_key: str,
    draft_results: Any,
    teams_by_id: dict[str, dict[str, Any]],
    teams_by_key: dict[str, dict[str, Any]],
    roster_catalog: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    results = as_list(draft_results)
    player_keys = sorted({text(value(result, "player_key", "")) for result in results if value(result, "player_key", "")})
    enriched: dict[str, Any] = {}
    for batch in chunks(player_keys, 25):
        joined = ",".join(batch)
        players = caller.call_with_delay(
            f"Yahoo {season} draft player enrichment ({batch[0]} ...)",
            lambda joined=joined: query.query(
                f"https://fantasysports.yahooapis.com/fantasy/v2/league/{league_key}/players;"
                f"player_keys={joined}/draft_analysis",
                ["league", "players"],
            ),
            empty_on_not_found=True,
        )
        for player in as_list(players):
            key = text(value(player, "player_key", ""))
            if key:
                enriched[key] = player

    rows: list[dict[str, Any]] = []
    for result in results:
        team_key = text(value(result, "team_key", ""))
        team_id = team_id_from_key(team_key)
        team = teams_by_key.get(team_key) or teams_by_id.get(team_id, {})
        player_key = text(value(result, "player_key", ""))
        player = enriched.get(player_key)
        info = yahoo_player_record(player) if player is not None else roster_catalog.get(player_key, {})
        analysis = value(player, "draft_analysis", {}) if player is not None else {}
        rows.append({
            "platform": "yahoo", "season": season, "league_id": league_id, "league_key": league_key,
            "draft_id": "", "draft_type": "", "round": integer(value(result, "round", None)),
            "overall_pick": integer(value(result, "pick", None)), "draft_slot": team.get("draft_slot"),
            "team_id": team_id, "team_key": team_key, "team_name": team.get("team_name"),
            "owner_id": team.get("owner_id"), "owner_name": team.get("owner_name"),
            "player_id": (info or {}).get("player_id") or player_id_from_key(player_key),
            "player_key": player_key, "player_name": (info or {}).get("player_name", ""),
            "position": (info or {}).get("position", ""), "nfl_team": (info or {}).get("nfl_team", ""),
            "adp_overall": number(value(analysis, "average_pick", None)),
            "adp_round": number(value(analysis, "average_round", None)),
            "average_draft_cost": number(value(analysis, "average_cost", None)),
            "percent_drafted": number(value(analysis, "percent_drafted", None)),
            "adp_source": "Yahoo draft_analysis" if analysis and plain(analysis) else "",
            "auction_cost": integer(value(result, "cost", None)),
            "is_keeper": integer(value(player, "is_keeper", 0), 0) if player is not None else "",
            "raw_json": json_compact({"draft_result": plain(result), "player": plain(player)}),
        })
    return sorted(rows, key=lambda row: row.get("overall_pick") or 9999)


def derive_yahoo_week(timestamp: Any, league_start_date: str, start_week: int) -> int | str:
    epoch = number(timestamp)
    if epoch is None or not league_start_date:
        return ""
    try:
        transaction_date = datetime.fromtimestamp(epoch, tz=timezone.utc).date()
        # NFL fantasy weeks turn over on Tuesday; Yahoo metadata start_date is generally opening Thursday.
        first_window_start = date.fromisoformat(league_start_date) - timedelta(days=2)
    except (OverflowError, OSError, ValueError):
        return ""
    if transaction_date < first_window_start:
        return 0
    return start_week + (transaction_date - first_window_start).days // 7


def yahoo_all_transactions(query: Any, caller: YahooCaller, season: int, league_key: str) -> list[Any]:
    transactions: list[Any] = []
    seen: set[str] = set()
    page_size = 25
    for start in range(0, 5000, page_size):
        page = caller.call_with_delay(
            f"Yahoo {season} transactions start={start}",
            lambda start=start: query.query(
                f"https://fantasysports.yahooapis.com/fantasy/v2/league/{league_key}/transactions;"
                f"start={start};count={page_size}",
                ["league", "transactions"],
            ),
            empty_on_not_found=True,
        )
        page_items = as_list(page)
        if not page_items:
            break
        new_count = 0
        for transaction in page_items:
            transaction_key = text(value(transaction, "transaction_key", ""))
            identity = transaction_key or json_compact(transaction)
            if identity not in seen:
                seen.add(identity)
                transactions.append(transaction)
                new_count += 1
        if len(page_items) < page_size or new_count == 0:
            break
    else:
        raise RuntimeError(f"Yahoo {season} transaction pagination exceeded 5,000 records")
    return transactions


def yahoo_transaction_rows(
    query: Any,
    caller: YahooCaller,
    season: int,
    league_id: str,
    league_key: str,
    start_date: str,
    start_week: int,
    teams_by_id: dict[str, dict[str, Any]],
    teams_by_key: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for transaction in yahoo_all_transactions(query, caller, season, league_key):
        raw = plain(transaction)
        timestamp = value(transaction, "timestamp", None)
        base = {
            "platform": "yahoo", "season": season, "league_id": league_id, "league_key": league_key,
            "week": derive_yahoo_week(timestamp, start_date, start_week),
            "week_source": "derived Tuesday-Monday from Yahoo league start_date",
            "transaction_id": text(value(transaction, "transaction_id", "")),
            "transaction_key": text(value(transaction, "transaction_key", "")),
            "type": text(value(transaction, "type", "")), "status": text(value(transaction, "status", "")),
            "timestamp_epoch": timestamp, "timestamp_utc": iso_timestamp(timestamp), "status_updated_utc": "",
            "faab_bid": integer(value(transaction, "faab_bid", None)),
            "waiver_priority": value(transaction, "waiver_priority", ""), "waiver_sequence": "",
            "creator_id": "", "raw_json": json_compact(raw),
        }
        asset_count = 0
        for player in as_list(value(transaction, "players", [])):
            asset_count += 1
            info = yahoo_player_record(player)
            transaction_data = value(player, "transaction_data", {})
            source_key = text(value(transaction_data, "source_team_key", ""))
            destination_key = text(value(transaction_data, "destination_team_key", ""))
            source_id = team_id_from_key(source_key)
            destination_id = team_id_from_key(destination_key)
            source = teams_by_key.get(source_key) or teams_by_id.get(source_id, {})
            destination = teams_by_key.get(destination_key) or teams_by_id.get(destination_id, {})
            rows.append({
                **base, "asset_type": "player", "action": text(value(transaction_data, "type", "")),
                "player_id": info["player_id"], "player_key": info["player_key"],
                "player_name": info["player_name"], "position": info["position"], "nfl_team": info["nfl_team"],
                "source_team_id": source_id, "source_team_key": source_key,
                "source_team_name": text(value(transaction_data, "source_team_name", "")) or source.get("team_name", ""),
                "destination_team_id": destination_id, "destination_team_key": destination_key,
                "destination_team_name": text(value(transaction_data, "destination_team_name", "")) or destination.get("team_name", ""),
                "destination_team_waiver_priority_at_export": destination.get("waiver_priority", ""),
            })
        for pick in as_list(value(transaction, "picks", [])):
            asset_count += 1
            source_key = text(value(pick, "source_team_key", ""))
            destination_key = text(value(pick, "destination_team_key", ""))
            original_key = text(value(pick, "original_team_key", ""))
            source_id = team_id_from_key(source_key)
            destination_id = team_id_from_key(destination_key)
            destination = teams_by_key.get(destination_key) or teams_by_id.get(destination_id, {})
            rows.append({
                **base, "asset_type": "draft_pick", "action": "trade",
                "draft_pick_season": "", "draft_pick_round": integer(value(pick, "round", None)),
                "original_team_id": team_id_from_key(original_key), "source_team_id": source_id,
                "source_team_key": source_key, "source_team_name": text(value(pick, "source_team_name", "")),
                "destination_team_id": destination_id, "destination_team_key": destination_key,
                "destination_team_name": text(value(pick, "destination_team_name", "")),
                "destination_team_waiver_priority_at_export": destination.get("waiver_priority", ""),
            })
        if asset_count == 0:
            rows.append({**base, "asset_type": "transaction", "action": text(value(transaction, "type", ""))})
    return sorted(rows, key=lambda row: (number(row.get("timestamp_epoch"), 0) or 0, text(row.get("transaction_id")), text(row.get("action"))))


def export_yahoo_season(
    query: Any,
    caller: YahooCaller,
    season: int,
    candidates: list[str],
    output_root: Path,
) -> dict[str, Any]:
    eprint(f"[Yahoo {season}] resolving game key with get_game_key_by_season({season})")
    game_key = text(caller.call_with_delay(
        f"Yahoo {season} game key",
        lambda: query.get_game_key_by_season(season),
    ))
    probe_results: list[dict[str, Any]] = []
    valid: list[tuple[str, Any]] = []
    for candidate in candidates:
        set_yahoo_league(query, game_key, candidate)
        metadata = caller.call_with_delay(
            f"Yahoo {season} candidate league {candidate}",
            query.get_league_metadata,
            empty_on_not_found=True,
        )
        returned_id = text(value(metadata, "league_id", "")) if metadata else ""
        returned_season = integer(value(metadata, "season", None)) if metadata else None
        has_data = bool(
            metadata and returned_id == candidate and returned_season == season
            and (integer(value(metadata, "num_teams", 0), 0) or 0) > 0
        )
        probe_results.append({
            "candidate_league_id": candidate,
            "returned_league_id": returned_id,
            "returned_season": returned_season,
            "returns_data": has_data,
        })
        eprint(f"[Yahoo {season}] candidate {candidate}: {'DATA' if has_data else 'no data'}")
        if has_data:
            valid.append((candidate, metadata))

    if not valid:
        raise RuntimeError(f"Yahoo {season}: none of the candidate league IDs returned matching season data")
    valid_by_id = {candidate: metadata for candidate, metadata in valid}
    if "701692" in valid_by_id:
        league_id = "701692"
        metadata = valid_by_id[league_id]
        selection_reason = "URL-confirmed 2017 ID preferred" if len(valid) > 1 else "only matching candidate"
    else:
        league_id, metadata = valid[0]
        selection_reason = "only matching candidate" if len(valid) == 1 else "first matching candidate"
    set_yahoo_league(query, game_key, league_id)
    league_key = f"{game_key}.l.{league_id}"
    eprint(f"[Yahoo {season}] selected league ID {league_id} ({selection_reason})")

    settings = caller.call_with_delay(f"Yahoo {season} settings", query.get_league_settings)
    standings = caller.call_with_delay(f"Yahoo {season} standings", query.get_league_standings)
    league_teams = caller.call_with_delay(f"Yahoo {season} teams", query.get_league_teams)
    standings_teams = as_list(value(standings, "teams", []))
    teams_by_id, teams_by_key = merge_yahoo_team_maps([league_teams, standings_teams])
    if not teams_by_id:
        raise RuntimeError(f"Yahoo {season}: league {league_id} returned no teams")

    start_week = integer(value(metadata, "start_week", 1), 1) or 1
    end_week = integer(value(metadata, "end_week", value(metadata, "current_week", start_week)), start_week) or start_week
    standings_rows = yahoo_standings_rows(season, league_id, league_key, teams_by_id)
    matchup_rows, team_week_points = yahoo_matchup_rows(
        query, caller, season, league_id, league_key, start_week, end_week,
        teams_by_id, teams_by_key,
    )
    roster_rows, roster_catalog, score_checks = yahoo_weekly_roster_rows(
        query, caller, season, league_id, league_key, start_week, end_week,
        teams_by_id, team_week_points, settings,
    )
    draft_results = caller.call_with_delay(
        f"Yahoo {season} draft results", query.get_league_draft_results, empty_on_not_found=True,
    )
    draft_rows = yahoo_draft_rows(
        query, caller, season, league_id, league_key, draft_results,
        teams_by_id, teams_by_key, roster_catalog,
    )
    transaction_rows = yahoo_transaction_rows(
        query, caller, season, league_id, league_key, text(value(metadata, "start_date", "")),
        start_week, teams_by_id, teams_by_key,
    )

    season_dir = output_root / "yahoo" / str(season)
    write_csv_atomic(season_dir / "draft_results.csv", DRAFT_FIELDS, draft_rows)
    write_csv_atomic(season_dir / "weekly_rosters.csv", ROSTER_FIELDS, roster_rows)
    write_csv_atomic(season_dir / "transactions.csv", TRANSACTION_FIELDS, transaction_rows)
    write_csv_atomic(season_dir / "standings.csv", STANDINGS_FIELDS, standings_rows)
    write_csv_atomic(season_dir / "matchups.csv", MATCHUP_FIELDS, matchup_rows)
    write_json_atomic(season_dir / "scoring_settings.json", {
        "platform": "yahoo", "season": season, "league_id": league_id,
        "league_key": league_key, "game_key": game_key,
        "league_metadata": plain(metadata), "settings": plain(settings),
        "notes": {
            "league_selection": selection_reason,
            "league_id_candidates": probe_results,
            "weekly_player_points_source": "Yahoo player_points.total from team roster player stats by week",
            "transaction_week": "Derived because Yahoo transaction objects do not expose a fantasy week",
        },
    })
    return {
        "platform": "yahoo", "season": season, "status": "complete", "league_id": league_id,
        "league_key": league_key, "game_key": game_key, "league_id_candidates": probe_results,
        "selection_reason": selection_reason,
        "counts": {
            "draft_results": len(draft_rows), "weekly_rosters": len(roster_rows),
            "transactions": len(transaction_rows), "standings": len(standings_rows),
            "matchups": len(matchup_rows),
        },
        "weekly_score_checks": score_checks,
    }


class SleeperClient:
    def __init__(self, delay: float = 0.08, attempts: int = 6):
        self.delay = max(delay, 0.061)  # stays below Sleeper's documented 1,000 calls/minute ceiling
        self.attempts = max(1, attempts)

    def get(self, path: str) -> Any:
        url = f"{SLEEPER_API}{path}"
        last_error: Exception | None = None
        for attempt in range(1, self.attempts + 1):
            try:
                request = urllib.request.Request(url, headers={"User-Agent": f"fantasy-history-export/{SCRIPT_VERSION}"})
                with urllib.request.urlopen(request, timeout=90) as response:
                    data = json.load(response)
                time.sleep(self.delay)
                return data
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as exc:
                last_error = exc
                if isinstance(exc, urllib.error.HTTPError) and exc.code == 404:
                    return []
                if attempt < self.attempts:
                    wait = min(60.0, 2.0 ** (attempt - 1)) + random.uniform(0.0, 0.5)
                    eprint(f"Sleeper {path} failed ({exc}); retry {attempt}/{self.attempts - 1} in {wait:.1f}s")
                    time.sleep(wait)
        assert last_error is not None
        raise RuntimeError(f"Sleeper request {path} failed after {self.attempts} attempts: {last_error}") from last_error


def load_sleeper_players(client: SleeperClient, cache_dir: Path) -> dict[str, Any]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "sleeper_players_nfl.json"
    if cache_file.exists() and time.time() - cache_file.stat().st_mtime < 24 * 60 * 60:
        with cache_file.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    eprint("[Sleeper] downloading the NFL player catalog (cached for 24 hours)")
    players = client.get("/players/nfl")
    write_json_atomic(cache_file, players)
    return players if isinstance(players, dict) else {}


def sleeper_player_info(player_id: Any, catalog: dict[str, Any], metadata: Any = None) -> dict[str, str]:
    player_id_text = text(player_id)
    player = catalog.get(player_id_text, {}) if isinstance(catalog, dict) else {}
    metadata = metadata if isinstance(metadata, dict) else {}
    first = metadata.get("first_name") or player.get("first_name") or ""
    last = metadata.get("last_name") or player.get("last_name") or ""
    full = metadata.get("full_name") or player.get("full_name") or " ".join(part for part in [first, last] if part)
    position = metadata.get("position") or player.get("position") or ""
    nfl_team = metadata.get("team") or metadata.get("team_abbr") or player.get("team") or ""
    if not position and player_id_text.isalpha() and len(player_id_text) <= 4:
        position = "DEF"
        nfl_team = player_id_text
    if not full and position == "DEF":
        full = f"{player_id_text} D/ST"
    return {
        "player_id": player_id_text, "player_key": player_id_text, "player_name": text(full),
        "position": text(position), "nfl_team": text(nfl_team),
    }


def sleeper_team_maps(
    league: dict[str, Any], users: list[dict[str, Any]], rosters: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    users_by_id = {text(user.get("user_id")): user for user in users}
    total_budget = integer(value(league.get("settings", {}), "waiver_budget", 0), 0) or 0
    teams: list[dict[str, Any]] = []
    for roster in rosters:
        roster_id = text(roster.get("roster_id"))
        owner_id = text(roster.get("owner_id"))
        owner = users_by_id.get(owner_id, {})
        co_owner_ids = [text(item) for item in (roster.get("co_owners") or [])]
        owner_ids = [item for item in [owner_id, *co_owner_ids] if item]
        owner_names = [
            text(users_by_id.get(item, {}).get("display_name", "")) for item in owner_ids
            if users_by_id.get(item, {}).get("display_name")
        ]
        user_metadata = owner.get("metadata") or {}
        team_name = user_metadata.get("team_name") or owner.get("display_name") or f"Roster {roster_id}"
        settings = roster.get("settings") or {}
        wins = integer(settings.get("wins"), 0) or 0
        losses = integer(settings.get("losses"), 0) or 0
        ties = integer(settings.get("ties"), 0) or 0
        points_for = sleeper_combined_points(settings, "fpts")
        points_against = sleeper_combined_points(settings, "fpts_against")
        possible_points = sleeper_combined_points(settings, "ppts")
        faab_used = integer(settings.get("waiver_budget_used"), 0) or 0
        games = wins + losses + ties
        teams.append({
            "team_id": roster_id, "team_key": roster_id, "team_name": text(team_name),
            "owner_id": "|".join(owner_ids), "owner_name": "|".join(owner_names),
            "wins": wins, "losses": losses, "ties": ties,
            "win_percentage": round((wins + ties / 2) / games, 6) if games else 0.0,
            "points_for": points_for, "points_against": points_against, "possible_points": possible_points,
            "waiver_priority": integer(settings.get("waiver_position")),
            "faab_used": faab_used, "faab_balance": total_budget - faab_used,
            "total_moves": integer(settings.get("total_moves")), "playoff_seed": "",
            "streak": text(value(roster.get("metadata") or {}, "streak", "")),
            "division": text(settings.get("division", "")), "raw": roster,
        })

    ranked = sorted(
        teams,
        key=lambda team: (
            -(team.get("wins") or 0), team.get("losses") or 0,
            -(team.get("ties") or 0), -(team.get("points_for") or 0.0), integer(team.get("team_id"), 999) or 999,
        ),
    )
    for rank, team in enumerate(ranked, start=1):
        team["rank"] = rank
    return {team["team_id"]: team for team in teams}, ranked


def sleeper_standings_rows(
    season: int, league_id: str, ranked_teams: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for team in ranked_teams:
        rows.append({
            "platform": "sleeper", "season": season, "league_id": league_id, "league_key": "",
            "rank": team["rank"], "rank_source": "derived: wins, losses, ties, points_for",
            "team_id": team["team_id"], "team_key": team["team_key"], "team_name": team["team_name"],
            "owner_id": team["owner_id"], "owner_name": team["owner_name"], "wins": team["wins"],
            "losses": team["losses"], "ties": team["ties"], "win_percentage": team["win_percentage"],
            "points_for": team["points_for"], "points_against": team["points_against"],
            "possible_points": team["possible_points"], "waiver_priority": team["waiver_priority"],
            "faab_balance": team["faab_balance"], "faab_used": team["faab_used"],
            "total_moves": team["total_moves"], "playoff_seed": team["playoff_seed"],
            "streak": team["streak"], "division": team["division"], "raw_json": json_compact(team["raw"]),
        })
    return rows


def sleeper_draft_rows(
    client: SleeperClient,
    season: int,
    league_id: str,
    drafts: list[dict[str, Any]],
    teams_by_id: dict[str, dict[str, Any]],
    player_catalog: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for draft in drafts:
        draft_id = text(draft.get("draft_id"))
        picks = client.get(f"/draft/{draft_id}/picks") if draft_id else []
        for pick in picks or []:
            team_id = text(pick.get("roster_id"))
            team = teams_by_id.get(team_id, {})
            player = sleeper_player_info(pick.get("player_id"), player_catalog, pick.get("metadata"))
            rows.append({
                "platform": "sleeper", "season": season, "league_id": league_id, "league_key": "",
                "draft_id": draft_id, "draft_type": text(draft.get("type", "")),
                "round": integer(pick.get("round")), "overall_pick": integer(pick.get("pick_no")),
                "draft_slot": integer(pick.get("draft_slot")), "team_id": team_id, "team_key": team_id,
                "team_name": team.get("team_name", ""), "owner_id": team.get("owner_id", pick.get("picked_by", "")),
                "owner_name": team.get("owner_name", ""), **player,
                "adp_overall": "", "adp_round": "", "average_draft_cost": "", "percent_drafted": "",
                "adp_source": "not exposed by Sleeper draft API", "auction_cost": "",
                "is_keeper": integer(pick.get("is_keeper")) if pick.get("is_keeper") is not None else "",
                "raw_json": json_compact(pick),
            })
    return sorted(rows, key=lambda row: (text(row.get("draft_id")), row.get("overall_pick") or 9999))


def sleeper_matchups_and_rosters(
    client: SleeperClient,
    season: int,
    league_id: str,
    league: dict[str, Any],
    teams_by_id: dict[str, dict[str, Any]],
    player_catalog: dict[str, Any],
    weeks: list[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    matchup_rows: list[dict[str, Any]] = []
    roster_rows: list[dict[str, Any]] = []
    score_checks = {"exact": 0, "mismatched": 0, "missing": 0}
    active_slots = [slot for slot in (league.get("roster_positions") or []) if slot != "BN"]

    for week in weeks:
        eprint(f"[Sleeper {season}] matchups and weekly rosters week {week}/{weeks[-1]}")
        entries = client.get(f"/league/{league_id}/matchups/{week}") or []
        grouped: dict[Any, list[dict[str, Any]]] = defaultdict(list)
        for entry in entries:
            grouped[entry.get("matchup_id")].append(entry)
        all_points = [number(entry.get("points")) for entry in entries]
        numeric_points = [point for point in all_points if point is not None]
        week_median = statistics.median(numeric_points) if numeric_points else None

        for matchup_id, group in grouped.items():
            for entry_index, entry in enumerate(group):
                team_id = text(entry.get("roster_id"))
                team = teams_by_id.get(team_id, {})
                points = number(entry.get("points"))
                opponent = group[1 - entry_index] if len(group) == 2 else None
                opponent_id = text(opponent.get("roster_id")) if opponent else ""
                opponent_team = teams_by_id.get(opponent_id, {})
                opponent_points = number(opponent.get("points")) if opponent else None
                result = result_from_scores(points, opponent_points)
                winner_id = team_id if result == "W" else opponent_id if result == "L" else ""
                matchup_rows.append({
                    "platform": "sleeper", "season": season, "league_id": league_id, "league_key": "",
                    "week": week, "matchup_id": matchup_id if matchup_id is not None else f"bye-{team_id}",
                    "status": text(league.get("status", "")), "is_playoffs": int(
                        week >= (integer(value(league.get("settings", {}), "playoff_week_start", 999), 999) or 999)
                    ),
                    "is_consolation": "", "team_id": team_id, "team_key": team_id,
                    "team_name": team.get("team_name", ""), "team_points": points,
                    "custom_points": entry.get("custom_points") if entry.get("custom_points") is not None else "",
                    "opponent_team_id": opponent_id, "opponent_team_key": opponent_id,
                    "opponent_team_name": opponent_team.get("team_name", ""),
                    "opponent_points": opponent_points, "result": result, "winner_team_id": winner_id,
                    "is_tied": int(result == "T"), "league_median_points": week_median,
                    "median_result": median_result(points, week_median), "raw_json": json_compact(entry),
                })

                starters = [text(player_id) for player_id in (entry.get("starters") or [])]
                starter_slots = {
                    player_id: active_slots[index] if index < len(active_slots) else "START"
                    for index, player_id in enumerate(starters) if player_id and player_id != "0"
                }
                players = [text(player_id) for player_id in (entry.get("players") or [])]
                for player_id in starters:
                    if player_id and player_id != "0" and player_id not in players:
                        players.append(player_id)
                player_points = entry.get("players_points") or {}
                team_player_rows: list[dict[str, Any]] = []
                starter_point_values: list[float] = []
                missing_started_points = False
                for player_id in players:
                    if not player_id or player_id == "0":
                        continue
                    player = sleeper_player_info(player_id, player_catalog)
                    started = int(player_id in starter_slots)
                    point_total = number(player_points.get(player_id)) if player_id in player_points else None
                    if started:
                        if point_total is None:
                            missing_started_points = True
                        else:
                            starter_point_values.append(point_total)
                    slot = starter_slots.get(player_id, "BN")
                    team_player_rows.append({
                        "platform": "sleeper", "season": season, "league_id": league_id, "league_key": "",
                        "week": week, "team_id": team_id, "team_key": team_id,
                        "team_name": team.get("team_name", ""), "owner_id": team.get("owner_id", ""),
                        "owner_name": team.get("owner_name", ""), **player, "lineup_slot": slot,
                        "lineup_status": "starter" if started else "bench", "started": started,
                        "is_flex": int("FLEX" in slot), "fantasy_points": point_total,
                        "points_source": "Sleeper matchups.players_points", "stat_values_json": "",
                        "raw_json": json_compact(player_catalog.get(player_id, {})),
                    })
                starter_sum = None if missing_started_points else round(sum(starter_point_values), 6)
                difference = round(points - starter_sum, 6) if points is not None and starter_sum is not None else None
                if difference is None:
                    score_checks["missing"] += 1
                elif abs(difference) <= 0.01:
                    score_checks["exact"] += 1
                else:
                    score_checks["mismatched"] += 1
                for row in team_player_rows:
                    row["team_week_points"] = points
                    row["starter_points_sum"] = starter_sum
                    row["score_check_difference"] = difference
                roster_rows.extend(team_player_rows)

    return matchup_rows, roster_rows, score_checks


def sleeper_transaction_rows(
    client: SleeperClient,
    season: int,
    league_id: str,
    teams_by_id: dict[str, dict[str, Any]],
    player_catalog: dict[str, Any],
    transaction_rounds: list[int],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for round_number in transaction_rounds:
        transactions = client.get(f"/league/{league_id}/transactions/{round_number}") or []
        for transaction in transactions:
            transaction_id = text(transaction.get("transaction_id"))
            if transaction_id in seen:
                continue
            seen.add(transaction_id)
            settings = transaction.get("settings") or {}
            created = transaction.get("created")
            base = {
                "platform": "sleeper", "season": season, "league_id": league_id, "league_key": "",
                "week": integer(transaction.get("leg"), round_number), "week_source": "Sleeper transaction.leg",
                "transaction_id": transaction_id, "transaction_key": transaction_id,
                "type": text(transaction.get("type", "")), "status": text(transaction.get("status", "")),
                "timestamp_epoch": created, "timestamp_utc": iso_timestamp(created, milliseconds=True),
                "status_updated_utc": iso_timestamp(transaction.get("status_updated"), milliseconds=True),
                "faab_bid": integer(settings.get("waiver_bid")),
                "waiver_priority": settings.get("waiver_position", ""),
                "waiver_sequence": settings.get("seq", ""), "creator_id": text(transaction.get("creator", "")),
                "raw_json": json_compact(transaction),
            }
            adds = {text(k): text(v) for k, v in (transaction.get("adds") or {}).items()}
            drops = {text(k): text(v) for k, v in (transaction.get("drops") or {}).items()}
            asset_count = 0
            for player_id in sorted(set(adds) | set(drops)):
                asset_count += 1
                source_id = drops.get(player_id, "")
                destination_id = adds.get(player_id, "")
                source = teams_by_id.get(source_id, {})
                destination = teams_by_id.get(destination_id, {})
                action = "trade" if source_id and destination_id else "add" if destination_id else "drop"
                player = sleeper_player_info(player_id, player_catalog)
                rows.append({
                    **base, "asset_type": "player", "action": action, **player,
                    "source_team_id": source_id, "source_team_key": source_id,
                    "source_team_name": source.get("team_name", ""),
                    "destination_team_id": destination_id, "destination_team_key": destination_id,
                    "destination_team_name": destination.get("team_name", ""),
                    "destination_team_waiver_priority_at_export": destination.get("waiver_priority", ""),
                })
            for pick in transaction.get("draft_picks") or []:
                asset_count += 1
                source_id = text(pick.get("previous_owner_id"))
                destination_id = text(pick.get("owner_id"))
                original_id = text(pick.get("roster_id"))
                rows.append({
                    **base, "asset_type": "draft_pick", "action": "trade",
                    "draft_pick_season": text(pick.get("season", "")),
                    "draft_pick_round": integer(pick.get("round")), "original_team_id": original_id,
                    "source_team_id": source_id, "source_team_key": source_id,
                    "source_team_name": teams_by_id.get(source_id, {}).get("team_name", ""),
                    "destination_team_id": destination_id, "destination_team_key": destination_id,
                    "destination_team_name": teams_by_id.get(destination_id, {}).get("team_name", ""),
                    "destination_team_waiver_priority_at_export": teams_by_id.get(destination_id, {}).get("waiver_priority", ""),
                })
            for transfer in transaction.get("waiver_budget") or []:
                asset_count += 1
                source_id = text(transfer.get("sender"))
                destination_id = text(transfer.get("receiver"))
                rows.append({
                    **base, "asset_type": "faab", "action": "transfer",
                    "source_team_id": source_id, "source_team_key": source_id,
                    "source_team_name": teams_by_id.get(source_id, {}).get("team_name", ""),
                    "destination_team_id": destination_id, "destination_team_key": destination_id,
                    "destination_team_name": teams_by_id.get(destination_id, {}).get("team_name", ""),
                    "destination_team_waiver_priority_at_export": teams_by_id.get(destination_id, {}).get("waiver_priority", ""),
                    "faab_transfer_amount": number(transfer.get("amount")),
                })
            if asset_count == 0:
                rows.append({**base, "asset_type": "transaction", "action": text(transaction.get("type", ""))})
    return sorted(rows, key=lambda row: (number(row.get("timestamp_epoch"), 0) or 0, text(row.get("transaction_id")), text(row.get("action"))))


def export_sleeper_season(
    client: SleeperClient,
    season: int,
    league_id: str,
    output_root: Path,
    player_catalog: dict[str, Any],
) -> dict[str, Any]:
    eprint(f"[Sleeper {season}] league {league_id}")
    league = client.get(f"/league/{league_id}")
    if not isinstance(league, dict) or text(league.get("league_id")) != league_id:
        raise RuntimeError(f"Sleeper {season}: league {league_id} did not return matching data")
    returned_season = integer(league.get("season"))
    if returned_season != season:
        raise RuntimeError(f"Sleeper league {league_id} returned season {returned_season}, expected {season}")
    users = client.get(f"/league/{league_id}/users") or []
    rosters = client.get(f"/league/{league_id}/rosters") or []
    drafts = client.get(f"/league/{league_id}/drafts") or []
    teams_by_id, ranked_teams = sleeper_team_maps(league, users, rosters)
    standings_rows = sleeper_standings_rows(season, league_id, ranked_teams)
    draft_rows = sleeper_draft_rows(client, season, league_id, drafts, teams_by_id, player_catalog)

    settings = league.get("settings") or {}
    last_scored_week = integer(settings.get("last_scored_leg"), 0) or 0
    current_week = integer(settings.get("leg"), 0) or 0
    status = text(league.get("status", ""))
    max_week = max(last_scored_week, current_week)
    weeks = [] if status == "pre_draft" and last_scored_week == 0 else list(range(1, max_week + 1))
    matchup_rows, roster_rows, score_checks = sleeper_matchups_and_rosters(
        client, season, league_id, league, teams_by_id, player_catalog, weeks,
    )
    transaction_rounds = list(range(0, max(max_week, 0) + 1))
    transaction_rows = sleeper_transaction_rows(
        client, season, league_id, teams_by_id, player_catalog, transaction_rounds,
    )

    season_dir = output_root / "sleeper" / str(season)
    write_csv_atomic(season_dir / "draft_results.csv", DRAFT_FIELDS, draft_rows)
    write_csv_atomic(season_dir / "weekly_rosters.csv", ROSTER_FIELDS, roster_rows)
    write_csv_atomic(season_dir / "transactions.csv", TRANSACTION_FIELDS, transaction_rows)
    write_csv_atomic(season_dir / "standings.csv", STANDINGS_FIELDS, standings_rows)
    write_csv_atomic(season_dir / "matchups.csv", MATCHUP_FIELDS, matchup_rows)
    write_json_atomic(season_dir / "scoring_settings.json", {
        "platform": "sleeper", "season": season, "league_id": league_id,
        "league": league, "drafts": drafts,
        "notes": {
            "authentication": "none; Sleeper read API is public",
            "weekly_player_points_source": "Sleeper matchups.players_points",
            "bench_definition": "matchup players minus ordered starters",
        },
    })
    return {
        "platform": "sleeper", "season": season, "status": "complete", "league_id": league_id,
        "league_status": status,
        "counts": {
            "draft_results": len(draft_rows), "weekly_rosters": len(roster_rows),
            "transactions": len(transaction_rows), "standings": len(standings_rows),
            "matchups": len(matchup_rows),
        },
        "weekly_score_checks": score_checks,
    }


def build_yahoo_query(delay: float) -> tuple[Any, YahooCaller]:
    try:
        installed = package_version("yfpy")
    except PackageNotFoundError as exc:
        raise RuntimeError("yfpy is not installed. Install exactly yfpy==17.0.0 first.") from exc
    if installed != "17.0.0":
        eprint(f"WARNING: this script was tested with yfpy 17.0.0; installed version is {installed}")
    from yfpy.exceptions import YahooFantasySportsDataNotFound
    from yfpy.query import YahooFantasySportsQuery

    query = YahooFantasySportsQuery(
        league_id=YAHOO_LEAGUES[2024][0],
        game_code="nfl",
        env_file_location=SCRIPT_DIR,
        save_token_data_to_env_file=True,
        browser_callback=True,
        retries=0,
        backoff=0,
    )
    env_file = SCRIPT_DIR / ".env"
    if env_file.exists():
        env_file.chmod(0o600)
    return query, YahooCaller(query, YahooFantasySportsDataNotFound, delay)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=SCRIPT_DIR / "output",
        help="Output root (default: ./output next to this script)",
    )
    parser.add_argument(
        "--platform", choices=["all", "yahoo", "sleeper"], default="all",
        help="Export both platforms or only one (default: all)",
    )
    parser.add_argument(
        "--yahoo-delay", type=float, default=0.50,
        help="Seconds between Yahoo API calls; rate-limit retries use longer backoff (default: 0.50)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = args.output_dir.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "script_version": SCRIPT_VERSION,
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "output_root": str(output_root),
        "excluded_sleeper_leagues": EXCLUDED_SLEEPER_LEAGUES,
        "seasons": [],
    }

    if args.platform in {"all", "yahoo"}:
        query = None
        try:
            query, caller = build_yahoo_query(args.yahoo_delay)
            for season, candidates in sorted(YAHOO_LEAGUES.items()):
                try:
                    season_report = export_yahoo_season(query, caller, season, candidates, output_root)
                except (KeyboardInterrupt, SystemExit):
                    raise
                except Exception as exc:
                    eprint(f"[Yahoo {season}] FAILED: {exc}")
                    season_report = {
                        "platform": "yahoo", "season": season, "status": "failed",
                        "candidate_league_ids": candidates, "error": text(exc),
                    }
                report["seasons"].append(season_report)
                write_json_atomic(output_root / "export_report.json", report)
                try:
                    query.save_access_token_data_to_env_file(SCRIPT_DIR)
                    (SCRIPT_DIR / ".env").chmod(0o600)
                except Exception as exc:
                    eprint(f"WARNING: could not refresh the cached Yahoo token in .env: {exc}")
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            eprint(f"[Yahoo] authentication/setup FAILED: {exc}")
            report["seasons"].append({"platform": "yahoo", "status": "failed", "error": text(exc)})
            write_json_atomic(output_root / "export_report.json", report)

    if args.platform in {"all", "sleeper"}:
        client = SleeperClient()
        try:
            player_catalog = load_sleeper_players(client, SCRIPT_DIR / ".cache")
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            eprint(f"[Sleeper] player catalog FAILED: {exc}")
            player_catalog = {}
        for season, league_id in sorted(SLEEPER_LEAGUES.items()):
            try:
                season_report = export_sleeper_season(client, season, league_id, output_root, player_catalog)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as exc:
                eprint(f"[Sleeper {season}] FAILED: {exc}")
                season_report = {
                    "platform": "sleeper", "season": season, "status": "failed",
                    "league_id": league_id, "error": text(exc),
                }
            report["seasons"].append(season_report)
            write_json_atomic(output_root / "export_report.json", report)

    failed = [item for item in report["seasons"] if item.get("status") == "failed"]
    report["finished_at_utc"] = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
    report["status"] = "failed" if failed else "complete"
    report["failed_count"] = len(failed)
    write_json_atomic(output_root / "export_report.json", report)
    eprint(f"Export {report['status']}: {output_root}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
