#!/usr/bin/env python3
"""Phase A data plumbing for the expansion (docs/EXPANSION_BUILD_ORDER_DRAFT.md).

Fetches every verified source from the platform-research register, computes ONLY
literal-column aggregates (no invented derivations), and writes JSON shards to
out/data/. Every shard carries provenance per guard N2: source, url, fetched_at,
and adp_source where ADP is involved.

Byte-stability contract: re-running against unchanged upstream data produces
byte-identical shards (keys sorted, floats rounded, fetch timestamp lives in a
separate provenance file so data shards do not churn on every cron tick).

Requires: pyarrow (Actions installs it; locally use a venv).

Run: python3 src/build_pages_data.py [--skip-pbp]
"""
import argparse
import csv
import datetime
import io
import json
import math
import os
import sys
import urllib.request

from player_names import PlayerIdentityResolver, comparison_key

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "data")
UA = {"User-Agent": "ff-hub-pages/1.0 (github.com/anthonydellapia1117/yeahthatfantasyleague)"}
NV = "https://github.com/nflverse/nflverse-data/releases/download"
FFC_ATTR = "ADP data courtesy of FantasyFootballCalculator.com"

FETCHED = {}   # shard -> {source, url, fetched_at}


def fetch(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def parquet(url, columns=None):
    import pyarrow.parquet as pq
    buf = io.BytesIO(fetch(url))
    return pq.read_table(buf, columns=columns)


def stamp(shard, source, url):
    FETCHED[shard] = {"source": source, "url": url,
                      "fetched_at": datetime.datetime.now(datetime.timezone.utc)
                      .strftime("%Y-%m-%dT%H:%M:%SZ")}


def prov(shard, **extra):
    """Timestamp-FREE provenance for embedding in data shards. fetched_at lives
    only in provenance.json, so identical upstream data hashes identically."""
    base = {k: v for k, v in FETCHED[shard].items() if k != "fetched_at"}
    base.update(extra)
    return base


def write(shard, obj):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{shard}.json")
    with open(path, "w") as f:
        json.dump(obj, f, sort_keys=True, separators=(",", ":"))
    print(f"  wrote {shard}.json ({os.path.getsize(path)//1024} KB)")


def r2(x):
    return None if x is None else round(float(x), 2)


def build_adp():
    """Sleeper ADP (the engine's input) + FFC ADP with market bands. Both stamped."""
    url_s = ("https://api.sleeper.app/projections/nfl/2026?season_type=regular"
             "&position[]=QB&position[]=RB&position[]=WR&position[]=TE&position[]=K&position[]=DEF")
    sleeper = json.loads(fetch(url_s))
    stamp("adp", "sleeper (undocumented projections endpoint)", url_s)
    s_rows = {}
    for p in sleeper:
        st = p.get("stats") or {}
        pl = p.get("player") or {}
        if st.get("adp_ppr"):
            pid = p.get("player_id")
            s_rows[pid] = {"name": f"{pl.get('first_name','')} {pl.get('last_name','')}".strip(),
                           "pos": pl.get("position"), "team": pl.get("team"),
                           "adp_sleeper": r2(st.get("adp_ppr"))}

    url_f = "https://fantasyfootballcalculator.com/api/v1/adp/ppr?teams=12&year=2026"
    ffc = json.loads(fetch(url_f))
    stamp("adp_ffc", "fantasyfootballcalculator (documented, attribution requested)", url_f)
    f_rows = []
    for p in ffc.get("players", []):
        # FFC calls kickers PK; Sleeper calls the same roster position K.
        # Provider position taxonomy is separate from name normalization.
        ffc_pos = "K" if p.get("position") == "PK" else p.get("position")
        f_rows.append({
            "name": p["name"], "pos": ffc_pos,
            "fields": {
                "adp_ffc": r2(p.get("adp")), "stdev": r2(p.get("stdev")),
                "high": p.get("high"), "low": p.get("low"),
                "bye": p.get("bye")}})
    ffc_resolver = PlayerIdentityResolver(f_rows)
    sleeper_buckets = {}
    for player_id, row in s_rows.items():
        sleeper_buckets.setdefault(
            (comparison_key(row["name"]), row["pos"]), []).append(player_id)

    merged = []
    for pid, row in s_rows.items():
        resolved = ffc_resolver.resolve(row["name"], position=row["pos"])
        target_unique = len(sleeper_buckets[
            (comparison_key(row["name"]), row["pos"])]) == 1
        # Source uniqueness is not enough: one FFC row must never fan out to
        # two Sleeper identities which comparison_key deliberately collapses.
        f = (resolved.record["fields"]
             if resolved.record is not None and target_unique else {})
        merged.append({"player_id": pid, **row, **f})
    merged.sort(key=lambda r: (r.get("adp_sleeper") or 999, r["player_id"]))
    write("adp", {"provenance": {"adp_source": "sleeper",
                                 "band_source": "ffc", "ffc_attribution": FFC_ATTR,
                                 "ffc_meta": {"drafts": ffc.get("meta", {}).get("total_drafts"),
                                              "window": [ffc.get("meta", {}).get("start_date"),
                                                         ffc.get("meta", {}).get("end_date")]}},
                  "players": merged})
    return s_rows

def build_crosswalk(sleeper_ids):
    """Sleeper player_id <-> gsis_id via nflverse players (v2). Unmatched logged.
    Team defenses are excluded up front: Sleeper models DEF as pseudo-players and
    nflverse players.parquet has no team entities - structurally unmatchable."""
    url = f"{NV}/players/players.parquet"
    t = parquet(url, columns=["gsis_id", "display_name", "latest_team", "position",
                              "birth_date", "draft_year", "draft_round", "draft_pick"])
    stamp("crosswalk", "nflverse players v2 (CC-BY-4.0)", url)
    nflverse_players = []
    for i in range(t.num_rows):
        nm = str(t["display_name"][i])
        nflverse_players.append({
            "name": nm, "gsis_id": str(t["gsis_id"][i]),
            "team": str(t["latest_team"][i]),
            "pos": str(t["position"][i]),
            "draft_year": None if t["draft_year"][i].as_py() is None else int(t["draft_year"][i].as_py()),
            "draft_round": None if t["draft_round"][i].as_py() is None else int(t["draft_round"][i].as_py()),
            "draft_pick": None if t["draft_pick"][i].as_py() is None else int(t["draft_pick"][i].as_py()),
        })
    resolver = PlayerIdentityResolver(nflverse_players)
    matched, unmatched, disambiguated = {}, [], []
    for pid, row in sleeper_ids.items():
        if row["pos"] == "DEF":
            continue                    # team entity, no gsis crosswalk exists
        result = resolver.resolve(row["name"], position=row["pos"],
                                  prefer_latest_draft_year=True,
                                  allow_unique_position_mismatch=True)
        cands = result.candidates
        pos_match = [c for c in cands if c["pos"] == row["pos"]]
        if result.record is not None:
            matched[pid] = result.record
        if result.rule == "most recent draft_year":
            # Same name, same position, different men. The suffix strip that
            # rescues "Kenneth Walker" vs "Kenneth Walker III" also collapses
            # fathers onto sons: Marvin Harrison (1996, IND) and Marvin Harrison
            # Jr. (2024, ARI) are one key. latest_team cannot separate them -
            # nflverse keeps the last team a retired player suited up for - so
            # the discriminator is entry year: an ADP list for the coming season
            # means the most recent entrant. Applied ONLY when that is unique,
            # and every use is logged rather than resolved silently.
            # Only compare like with like. draft_year is None for the
            # UNDRAFTED, not the old, so a father/son pair where the son went
            # undrafted (Frank Gore vs Frank Gore Jr.) would resolve backwards
            # onto the retired father. If any candidate lacks an entry year the
            # pair stays unmatched, which is exactly the status quo.
            chosen = result.record
            disambiguated.append({"player_id": pid, "name": row["name"],
                                  "pos": row["pos"],
                                  "chose_draft_year": chosen["draft_year"],
                                  "over": sorted(c["draft_year"] or 0 for c in pos_match
                                                 if c is not chosen),
                                  "rule": result.rule})
        elif result.record is None:
            entry = {"player_id": pid, **row, "candidates": len(cands)}
            if len(pos_match) > 1:
                entry["why"] = result.reason
            unmatched.append(entry)
    write("crosswalk", {"provenance": prov("crosswalk"),
                        "matched": {k: v["gsis_id"] for k, v in matched.items()},
                        "prospect": {k: {kk: v[kk] for kk in ("draft_year", "draft_round", "draft_pick")}
                                     for k, v in matched.items()}})
    write("reconciliation", {"provenance": prov("crosswalk"),
                             "unmatched_count": len(unmatched),
                             "unmatched": sorted(unmatched, key=lambda r: r.get("adp_sleeper") or 999)[:50],
                             "disambiguated_count": len(disambiguated),
                             "disambiguated": sorted(disambiguated, key=lambda r: r["name"]),
                             "note": "unmatched players are logged, never silently dropped; "
                                     "same-name collisions resolved by entry year are logged too"})
    return matched


def build_depth_charts():
    """Latest ESPN-derived depth chart per team from the nflverse mirror."""
    url = f"{NV}/depth_charts/depth_charts_2026.parquet"
    t = parquet(url, columns=["team", "player_name", "gsis_id", "pos_abb", "pos_rank", "dt"])
    stamp("depth_charts", "nflverse depth_charts (ESPN-derived, CC-BY-4.0)", url)
    latest = max(str(t["dt"][i]) for i in range(t.num_rows))
    rows = []
    for i in range(t.num_rows):
        if str(t["dt"][i]) != latest:
            continue
        rows.append({"team": str(t["team"][i]), "player": str(t["player_name"][i]),
                     "gsis_id": str(t["gsis_id"][i]), "pos": str(t["pos_abb"][i]),
                     "rank": None if t["pos_rank"][i].as_py() is None else int(t["pos_rank"][i].as_py())})
    rows.sort(key=lambda r: (r["team"], r["pos"], r["rank"] if r["rank"] is not None else 99, r["player"]))
    write("depth_charts", {"provenance": prov("depth_charts", as_of=latest),
                           "entries": rows})


def build_usage_2025():
    """Per-player 2025 season sums of LITERAL stats_player columns. No derivations
    beyond share = player_sum / team_sum where the column is itself a share's
    numerator (documented per field)."""
    url = f"{NV}/stats_player/stats_player_week_2025.parquet"
    cols = ["player_id", "player_display_name", "position", "team", "week",
            "targets", "receptions", "receiving_yards", "receiving_air_yards",
            "target_share", "air_yards_share", "wopr",
            "carries", "rushing_yards", "attempts", "passing_yards", "passing_tds",
            "receiving_tds", "rushing_tds", "fantasy_points_ppr"]
    t = parquet(url, columns=cols)
    stamp("usage_2025", "nflverse stats_player weekly 2025 (CC-BY-4.0)", url)
    agg = {}
    for i in range(t.num_rows):
        pid = str(t["player_id"][i])
        a = agg.setdefault(pid, {"name": str(t["player_display_name"][i]),
                                 "pos": str(t["position"][i]), "team": str(t["team"][i]),
                                 "weeks": 0, "targets": 0, "receptions": 0, "rec_yards": 0,
                                 "air_yards": 0, "carries": 0, "rush_yards": 0,
                                 "pass_att": 0, "pass_yards": 0, "pass_tds": 0,
                                 "rec_tds": 0, "rush_tds": 0, "ppr_pts": 0.0,
                                 "_ts": [], "_ays": [], "_wopr": []})
        def val(col):
            v = t[col][i].as_py()
            return 0 if v is None else v
        a["weeks"] += 1
        a["targets"] += int(val("targets")); a["receptions"] += int(val("receptions"))
        a["rec_yards"] += int(val("receiving_yards")); a["air_yards"] += int(val("receiving_air_yards"))
        a["carries"] += int(val("carries")); a["rush_yards"] += int(val("rushing_yards"))
        a["pass_att"] += int(val("attempts")); a["pass_yards"] += int(val("passing_yards"))
        a["pass_tds"] += int(val("passing_tds"))
        a["rec_tds"] += int(val("receiving_tds")); a["rush_tds"] += int(val("rushing_tds"))
        a["ppr_pts"] += float(val("fantasy_points_ppr"))
        for col, key in (("target_share", "_ts"), ("air_yards_share", "_ays"), ("wopr", "_wopr")):
            v = t[col][i].as_py()
            if v is not None:
                a[key].append(float(v))
    players = []
    for pid, a in agg.items():
        if a["ppr_pts"] < 10:            # trim the long tail of non-fantasy rows
            continue
        row = {k: v for k, v in a.items() if not k.startswith("_")}
        # weekly-share means, labelled as such (mean of nflverse's own weekly share cols)
        for src, dst in (("_ts", "target_share_mean"), ("_ays", "air_yards_share_mean"),
                         ("_wopr", "wopr_mean")):
            row[dst] = r2(sum(a[src]) / len(a[src])) if a[src] else None
        row["ppr_pts"] = r2(row["ppr_pts"])
        players.append({"gsis_id": pid, **row})
    players.sort(key=lambda r: -r["ppr_pts"])
    write("usage_2025", {"provenance": prov("usage_2025",
                                            basis="2025 season sums of literal columns; share fields are means of nflverse weekly share columns"),
                         "players": players})


def build_proe_2025(skip_pbp=False):
    """Team-level 2025 PROE and neutral pace from literal pbp fields."""
    if skip_pbp:
        print("  (pbp skipped)")
        return
    url = f"{NV}/pbp/play_by_play_2025.parquet"
    t = parquet(url, columns=["posteam", "pass_oe", "xpass", "wp",
                              "half_seconds_remaining", "play_type"])
    stamp("team_proe_2025", "nflverse pbp 2025 (CC-BY-4.0)", url)
    acc = {}
    for i in range(t.num_rows):
        team = t["posteam"][i].as_py()
        if not team:
            continue
        a = acc.setdefault(team, {"oe_sum": 0.0, "oe_n": 0, "neutral_plays": 0})
        oe = t["pass_oe"][i].as_py()
        if oe is not None:
            a["oe_sum"] += float(oe)
            a["oe_n"] += 1
        wp = t["wp"][i].as_py()
        pt = t["play_type"][i].as_py()
        if wp is not None and 0.2 <= wp <= 0.8 and pt in ("pass", "run"):
            a["neutral_plays"] += 1
    teams = [{"team": tm, "proe_2025": r2(a["oe_sum"] / a["oe_n"]) if a["oe_n"] else None,
              "plays_measured": a["oe_n"], "neutral_snaps": a["neutral_plays"]}
             for tm, a in acc.items()]
    teams.sort(key=lambda r: (r["proe_2025"] is None, -(r["proe_2025"] or 0)))
    write("team_proe_2025", {"provenance": prov("team_proe_2025",
                                                 basis="mean of nflverse pass_oe per posteam, 2025; neutral = wp in [0.2,0.8]"),
                             "teams": teams})


def build_playcallers():
    """Curated file rendered to a shard with its REPORTED/VERIFIED tags intact."""
    path = os.path.join(ROOT, "data", "playcallers.csv")
    rows = list(csv.DictReader(open(path)))
    watch = list(csv.DictReader(open(os.path.join(ROOT, "data", "playcallers_watch.csv"))))
    write("playcallers", {"provenance": {"source": "data/playcallers.csv (hand-curated, per-row sourced)",
                                         "row_count": len(rows),
                                         "curation_note": "review on any coaching news and draft week; "
                                                          "19 teams per RESEARCH_ADDENDUM_2026-08-13"},
                          "callers": rows, "watch": watch})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-pbp", action="store_true", help="skip the 20MB pbp pull")
    a = ap.parse_args()

    print("building page-data shards -> out/data/")
    sleeper_ids = build_adp()
    matched = build_crosswalk(sleeper_ids)
    build_depth_charts()
    build_usage_2025()
    build_proe_2025(skip_pbp=a.skip_pbp)
    build_playcallers()

    # provenance manifest: fetch timestamps live HERE so data shards stay byte-stable
    write("provenance", {"shards": FETCHED,
                         "built_by": "src/build_pages_data.py",
                         "note": "guard N2: every shard carries source and basis; "
                                 "fetch timestamps centralized here"})
    # heartbeat for the Actions 60-day-disable guard
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "heartbeat.txt"), "w") as f:
        f.write(datetime.date.today().isoformat() + "\n")
    print("done")


if __name__ == "__main__":
    main()
