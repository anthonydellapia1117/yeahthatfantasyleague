#!/usr/bin/env python3
"""Snapshot the live 2026 schedule/lines source for reproducible BULLISH builds.

pages-data refreshes HISTORY/games.csv daily. This producer filters its complete
2026 regular season into the committed snapshot that draft-refresh can validate
without adding HISTORY or a live endpoint to the draft-morning critical path.

A shorter priced horizon fails closed before either snapshot file is replaced.
Run: python3 src/sync_forward_schedule.py
"""
import argparse
import csv
import datetime
import hashlib
import io
import json
import os
import tempfile

from analyze_recency import HISTORY
from build_bullish_inputs import (
    FORWARD_META,
    FORWARD_SCHEDULE,
    classify_forward_transition,
    derive_forward_vegas,
    enforce_forward_transition,
    forward_model_logic_sha256,
)
from fetch_history import LIVE_GAMES_URL


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def serialize_snapshot(fieldnames, rows):
    """Canonical CSV bytes: source columns, deterministic game order, LF only."""
    out = io.StringIO(newline="")
    writer = csv.DictWriter(
        out, fieldnames=fieldnames, extrasaction="ignore",
        lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    for row in sorted(rows, key=lambda r: (
            int(r["week"]), r.get("gameday") or "", r.get("gametime") or "",
            r["game_id"])):
        writer.writerow({name: row.get(name, "") for name in fieldnames})
    return out.getvalue().encode("utf-8")


def schedule_state(derived, snapshot_digest, upstream_digest=None,
                   model_logic_digest=None):
    weeks = derived["weeks"]
    return {
        "source_content_sha256": snapshot_digest,
        "snapshot_content_sha256": snapshot_digest,
        "upstream_content_sha256": upstream_digest,
        "model_logic_sha256": model_logic_digest,
        "decision_input_sha256": derived["decision_input_sha256"],
        "pricing_by_week_sha256": derived["pricing_by_week_sha256"],
        "weeks": weeks,
        "games": derived["game_count"],
        "games_priced": derived["game_count"],
        "team_games": derived["team_game_count"],
        "team_games_priced": derived["team_game_count"],
        "next_partial_week": derived["boundary"],
    }


def atomic_write(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + ".",
                               dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def sync(source_path, snapshot_path, metadata_path):
    with open(source_path, "rb") as fh:
        source_bytes = fh.read()
    with open(source_path, newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        if len(fieldnames) != len(set(fieldnames)):
            raise ValueError("live games source has duplicate CSV columns")
        required = {"game_id", "season", "game_type", "week", "away_team",
                    "home_team", "spread_line", "total_line"}
        missing = sorted(required - set(fieldnames))
        if missing:
            raise ValueError(f"live games source is missing columns: {missing}")
        rows = []
        for row in reader:
            if None in row:
                raise ValueError("live games source has malformed extra CSV cells")
            if (str(row.get("season") or "") == "2026" and
                    row.get("game_type") == "REG"):
                rows.append(row)
    if not fieldnames:
        raise ValueError("live games source has no CSV header")

    derived = derive_forward_vegas(rows)
    snapshot_bytes = serialize_snapshot(fieldnames, rows)
    reparsed = list(csv.DictReader(
        io.StringIO(snapshot_bytes.decode("utf-8"), newline="")))
    expected_rows = [
        {name: row.get(name, "") for name in fieldnames}
        for row in sorted(rows, key=lambda row: (
            int(row["week"]), row.get("gameday") or "",
            row.get("gametime") or "", row["game_id"]))
    ]
    if reparsed != expected_rows:
        raise ValueError("forward schedule snapshot failed round-trip validation")
    snapshot_digest = sha256_bytes(snapshot_bytes)
    upstream_digest = sha256_bytes(source_bytes)
    model_logic_digest = forward_model_logic_sha256()
    current_state = schedule_state(
        derived, snapshot_digest, upstream_digest=upstream_digest,
        model_logic_digest=model_logic_digest)

    prior_state = current_state
    prior_totals = derived["implied_total"]
    if os.path.exists(snapshot_path):
        with open(snapshot_path, "rb") as fh:
            prior_bytes = fh.read()
        with open(snapshot_path, newline="") as fh:
            prior_rows = list(csv.DictReader(fh))
        prior_derived = derive_forward_vegas(prior_rows)
        prior_state = schedule_state(
            prior_derived, sha256_bytes(prior_bytes),
            model_logic_digest=model_logic_digest)
        prior_totals = prior_derived["implied_total"]

    transition = classify_forward_transition(
        prior_state, prior_totals, current_state, derived["implied_total"])
    enforce_forward_transition(transition)

    pulled_at = datetime.datetime.fromtimestamp(
        os.path.getmtime(source_path), tz=datetime.timezone.utc
    ).isoformat(timespec="seconds")
    metadata = {
        "season": 2026,
        "upstream_source": LIVE_GAMES_URL,
        "pulled_at": pulled_at,
        "upstream_content_sha256": upstream_digest,
        "snapshot_content_sha256": snapshot_digest,
        "decision_input_sha256": derived["decision_input_sha256"],
        "pricing_by_week_sha256": derived["pricing_by_week_sha256"],
        "model_logic_sha256": model_logic_digest,
        "rows": len(rows),
        "games_priced": derived["game_count"],
        "team_games_priced": derived["team_game_count"],
        "weeks": derived["weeks"],
        "next_partial_week": derived["boundary"],
        "prior_implied_total": prior_totals,
        "current_implied_total": derived["implied_total"],
        "sync_transition": transition,
    }
    metadata_bytes = (json.dumps(metadata, indent=1, sort_keys=True) + "\n").encode()
    atomic_write(snapshot_path, snapshot_bytes)
    atomic_write(metadata_path, metadata_bytes)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=os.path.join(HISTORY, "games.csv"))
    parser.add_argument("--snapshot", default=FORWARD_SCHEDULE)
    parser.add_argument("--metadata", default=FORWARD_META)
    args = parser.parse_args()
    metadata = sync(args.source, args.snapshot, args.metadata)
    event = metadata["sync_transition"]["event"]
    last_week = metadata["weeks"][-1]
    print(
        f"FORWARD SCHEDULE {event} - W1-{last_week}, "
        f"{metadata['games_priced']} games / "
        f"{metadata['team_games_priced']} team-games priced")


if __name__ == "__main__":
    main()
