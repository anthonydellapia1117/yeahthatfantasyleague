#!/usr/bin/env python3
"""C5 guards: BULLISH engine - probabilistic gates, state machine, edge
accountability, delta report, and display-only wiring.

Runs WITHOUT network on the committed artifacts and pages.
Run: python3 tests/test_bullish.py
"""
import json
import math
import os
import re
import sys
import datetime
import csv
import copy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "out", "data")
sys.path.insert(0, os.path.join(ROOT, "src"))
from analyze_recency import HISTORY
from build_bullish_inputs import derive_forward_vegas, distribution, observed_share
from engine_lineage import file_content_sha256, json_content_sha256
from player_names import PlayerIdentityResolver
from team_codes import CANONICAL_NFL_TEAMS, canonical_team
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
   d["provenance"]["forward_vegas"] == forward_vegas,
   "forward Vegas exact source and scope propagate to the tag artifact")
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
usage_by_gsis = {u["gsis_id"]: u for u in source_payloads["usage_2025.json"]["players"]}
team_now = {e["gsis_id"]: e["team"]
            for e in source_payloads["depth_charts.json"]["entries"]}
observed_rb = {}
for depth_row in source_payloads["depth_charts.json"]["entries"]:
    if depth_row["pos"] != "RB":
        continue
    usage_row = usage_by_gsis.get(depth_row["gsis_id"])
    if usage_row is not None:
        observed_rb.setdefault(depth_row["team"], {})[depth_row["gsis_id"]] = \
            usage_row["carries"]

backfield_ok = True
candidate_n = observed_n = 0
for player in (p for p in inp["players"] if p["pos"] == "RB"):
    identity = engine_identity.resolve(player["name"], position="RB").record
    sleeper_id = str(identity.get("sleeper_id") or "") if identity else ""
    gsis_id = matched.get(sleeper_id)
    team = team_now.get(gsis_id) or (identity or {}).get("team")
    observations = observed_rb.get(team, {})
    total = sum(observations.values())
    if total >= 100:
        candidate_n += 1
    expected = (None if not gsis_id or gsis_id not in observations or total < 100
                else {"value": round(observations[gsis_id] / total, 4),
                      "player": observations[gsis_id], "total": total})
    actual = player.get("backfield_share")
    sample = player.get("backfield_share_sample")
    if expected is None:
        backfield_ok &= actual is None and sample is None
    else:
        observed_n += 1
        backfield_ok &= (actual == expected["value"] and
                         sample == {"season": 2025,
                                    "player_carries": expected["player"],
                                    "team_carries": expected["total"]})
ok(backfield_ok,
   "every backfield percentile member has a canonical observed carry sample")
bf = thr["rb_backfield_share"]
ok(bf["n"] == observed_n and
   bf["excluded_unobserved_n"] == candidate_n - observed_n and
   bf["n"] + bf["excluded_unobserved_n"] == candidate_n,
   "backfield population reconciles observed and excluded identities",
   f"artifact={bf}, candidates={candidate_n}, observed={observed_n}")
inside5_zeros = [p for p in inp["players"]
                 if p.get("inside5_share", {}).get("k") == 0 and
                 p.get("inside5_share", {}).get("n", 0) > 0]
ok(bf["p50"] == 0.506 and
   "upper middle" in bf.get("p50_method", "") and
   thr["rb_inside5"]["zero_n"] == len(inside5_zeros) == 1,
   "corrected backfield median ships while the real inside-five zero remains",
   f"backfield={bf}, inside5 zeros={[p['name'] for p in inside5_zeros]}")

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

# 8. pages: chips wired display-only, beside the signal encoding
bp = open(os.path.join(ROOT, "out", "big_board.html")).read()
drp = open(os.path.join(ROOT, "out", "draft_room.html")).read()
ok("bullishChip" in bp and 'get("data/bullish_2026.json")' in bp,
   "board chip wired with optional load")
ok("bullishTag" in bp and "x.name === p.name" not in bp and
   "x.pos === p.pos" not in bp,
   "big board joins BULLISH tags by Sleeper identity, never raw name")
ok("bullChip" in drp and 'fetch("data/bullish_2026.json")' in drp,
   "room chip wired with optional load")
ok("never" in drp[drp.index("C5 BULLISH layer"):drp.index("C5 BULLISH layer") + 300]
   and "replacing" in drp[drp.index("C5 BULLISH layer"):drp.index("C5 BULLISH layer") + 300],
   "room states the tag sits beside the signal encoding, never replacing it")
for page, chip in ((bp, "bullishChip"), (drp, "bullChip")):
    seg = page[page.index(f"function {chip}"):]
    seg = seg[:seg.index("\n}")]
    ok("ttl_hours" in seg and "ageH" in seg, f"{chip} enforces the 72h TTL with age display")
ok("TAGS STALE" in bp and "TAGS STALE" in drp,
   "engine mismatch renders a neutral stale tag, never a current verdict")
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
