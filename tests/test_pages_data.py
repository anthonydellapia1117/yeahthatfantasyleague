#!/usr/bin/env python3
"""Guards N2 + page-data schema for the expansion shards (Phase A).

Runs WITHOUT network: operates only on committed repository files.
Run: python3 tests/test_pages_data.py
"""
import ast
import csv
import datetime
import copy
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "out", "data")
sys.path.insert(0, os.path.join(ROOT, "src"))
from player_names import (PlayerIdentityResolver, comparison_key,
                          nflverse_roster_identity, search_key)
from build_pages_data import merge_ffc_market
from team_codes import (CANONICAL_NFL_TEAMS, TEAM_CODE_ALIASES,
                        canonical_team)

fails = []


def ok(cond, name, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "  -> " + detail))
    if not cond:
        fails.append(name)


def load(shard):
    p = os.path.join(D, f"{shard}.json")
    if not os.path.exists(p):
        return None
    return json.load(open(p))


SHARDS = ["adp", "crosswalk", "reconciliation", "depth_charts", "usage_2025",
          "team_proe_2025", "playcallers", "provenance"]

# Provider team codes are a join contract, not source-specific folklore.
_team_alias_contract = {"LA": "LAR", "JAC": "JAX",
                        "WSH": "WAS", "ARZ": "ARI"}
ok(TEAM_CODE_ALIASES == _team_alias_contract and
   all(canonical_team(source) == target
       for source, target in _team_alias_contract.items()) and
   all(canonical_team(team) == team for team in CANONICAL_NFL_TEAMS),
   "team-code contract maps provider aliases and is idempotent on all 32 clubs")
_team_sources = {
    "depth": {canonical_team(row["team"])
              for row in load("depth_charts")["entries"]},
    "usage": {canonical_team(row["team"])
              for row in load("usage_2025")["players"]},
    "PROE": {canonical_team(row["team"])
             for row in load("team_proe_2025")["teams"]},
    "SOS": {canonical_team(row["team"])
            for row in json.load(open(os.path.join(D, "sos_2026.json")))["teams"]},
}
_canonical_team_set = set(CANONICAL_NFL_TEAMS)
_bad_team_sets = {name: sorted(teams ^ _canonical_team_set)
                  for name, teams in _team_sources.items()
                  if teams != _canonical_team_set}
ok(not _bad_team_sets,
   "all team-keyed shards reconcile to the same canonical 32-team vocabulary",
   str(_bad_team_sets))
_python_alias_consumers = {
    "build_cvs.py": open(os.path.join(ROOT, "src", "build_cvs.py")).read(),
    "build_cvs_inputs.py": open(os.path.join(ROOT, "src", "build_cvs_inputs.py")).read(),
    "parse_walter.py": open(os.path.join(ROOT, "src", "parse_walter.py")).read(),
}
ok(all("from team_codes import" in source
       for source in _python_alias_consumers.values()) and
   "TEAM_ALIAS" not in _python_alias_consumers["parse_walter.py"] and
   "ALIAS =" not in _python_alias_consumers["build_cvs_inputs.py"],
   "Python team-code consumers import the canonical contract instead of duplicating maps")

# Every NFL team-code field in every committed output artifact must resolve to
# the app's canonical 32-team vocabulary.  This is deliberately discovered from
# git rather than maintained as a file list: a newly committed JSON/CSV artifact
# joins the guard automatically.  `FA` is an explicit non-team state, not an NFL
# code.  Fantasy `team_id`, `team_name`, and numeric `teams` fields are not codes.
_team_code_fields = {
    "team", "nfl_team", "home_team", "away_team", "recent_team",
    "opponent_team", "player_team", "team_live", "draft_club",
    "team_abbr", "team_code", "posteam", "defteam",
}
_non_team_sentinels = {"FA"}


def _is_team_code_field(field):
    lowered = field.lower()
    return (lowered in _team_code_fields or
            re.fullmatch(r"team_\d{4}", lowered) is not None)


def _unresolved_team_codes(value, path="$"):
    issues = []
    if isinstance(value, dict):
        # Several artifacts use team codes as keys rather than leaves. Detect
        # the domain from its resolved-key majority, so a future typo such as
        # LAX is checked instead of disappearing merely because it is unknown.
        code_like_keys = [
            key for key in value
            if isinstance(key, str) and re.fullmatch(r"[A-Za-z]{2,4}", key)
        ]
        resolved_keys = [
            key for key in code_like_keys
            if canonical_team(key) in _canonical_team_set
        ]
        if len(code_like_keys) >= 4 and \
           len(resolved_keys) / len(code_like_keys) >= 0.75:
            for key in code_like_keys:
                if canonical_team(key) not in _canonical_team_set:
                    issues.append((f"{path}.<key>", key))
        for field, child in value.items():
            child_path = f"{path}.{field}"
            if _is_team_code_field(field) and not isinstance(child, (dict, list)):
                if child in (None, ""):
                    continue
                if not isinstance(child, str):
                    issues.append((child_path, repr(child)))
                    continue
                code = child.strip().upper()
                if code not in _non_team_sentinels and \
                   canonical_team(code) not in _canonical_team_set:
                    issues.append((child_path, child))
            issues.extend(_unresolved_team_codes(child, child_path))
    elif isinstance(value, list):
        # SOS and similar artifacts encode opponents as [team, value] pairs.
        pair_codes = [
            child[0] for child in value
            if isinstance(child, list) and len(child) >= 2 and
            isinstance(child[0], str) and
            re.fullmatch(r"[A-Za-z]{2,4}", child[0])
        ]
        pair_resolved = [
            code for code in pair_codes
            if canonical_team(code) in _canonical_team_set
        ]
        if len(pair_codes) >= 4 and \
           len(pair_resolved) / len(pair_codes) >= 0.75:
            for index, code in enumerate(pair_codes):
                if canonical_team(code) not in _canonical_team_set:
                    issues.append((f"{path}[{index}][0]", code))
        for index, child in enumerate(value):
            issues.extend(_unresolved_team_codes(child, f"{path}[{index}]"))
    return issues


_tracked_out = subprocess.run(
    ["git", "ls-files", "-z", "--", "out"], cwd=ROOT,
    text=True, capture_output=True, check=True).stdout.split("\0")
_tracked_json = sorted(path for path in _tracked_out if path.endswith(".json"))
_tracked_csv = sorted(path for path in _tracked_out if path.endswith(".csv"))
_artifact_team_issues = []
for _rel in _tracked_json:
    with open(os.path.join(ROOT, _rel)) as _handle:
        _payload = json.load(_handle)
    _artifact_team_issues.extend(
        (_rel + path[1:], code)
        for path, code in _unresolved_team_codes(_payload))
for _rel in _tracked_csv:
    with open(os.path.join(ROOT, _rel), newline="") as _handle:
        for _row_index, _row in enumerate(csv.DictReader(_handle), start=2):
            for _field, _value in _row.items():
                if not _is_team_code_field(_field) or _value in (None, ""):
                    continue
                _code = _value.strip().upper()
                if _code not in _non_team_sentinels and \
                   canonical_team(_code) not in _canonical_team_set:
                    _artifact_team_issues.append(
                        (f"{_rel}:{_row_index}:{_field}", _value))
ok(not _artifact_team_issues and bool(_tracked_json),
   "every team code in every committed output artifact resolves canonically",
   str(_artifact_team_issues[:20]))
ok(_unresolved_team_codes({"players": [{"team": "XYZ"}]}) ==
   [("$.players[0].team", "XYZ")] and
   not _unresolved_team_codes({"players": [{"team": "LA"}, {"team": "FA"}]}),
   "artifact team-code guard rejects an unknown code but accepts aliases and FA")
_team_domain_mutant = {
    "by_team": {"ARI": 1, "ATL": 2, "BAL": 3, "LAX": 4},
    "opponents": [["ARI", 1], ["ATL", 2], ["BAL", 3], ["LAX", 4]],
}
ok(_unresolved_team_codes(_team_domain_mutant) ==
   [("$.by_team.<key>", "LAX"), ("$.opponents[3][0]", "LAX")],
   "artifact team-code guard covers mapping keys and unlabelled pair domains")

# 1. Every shard exists and carries provenance (guard N2)
for s in SHARDS:
    d = load(s)
    ok(d is not None, f"shard exists: {s}")
    if d is None:
        continue
    if s != "provenance":
        ok("provenance" in d, f"N2: {s} carries provenance",
           "missing provenance key")

# 2. ADP shard: source stamped, both sources present, band fields live
adp = load("adp")
if adp:
    prov = adp["provenance"]
    ok(prov.get("adp_source") in ("sleeper", "ffc"),
       "N2: adp_source stamped sleeper|ffc", str(prov.get("adp_source")))
    ok("ffc_attribution" in prov, "FFC attribution string present")
    top = adp["players"][:50]
    with_band = sum(1 for p in top if p.get("stdev") is not None)
    ok(with_band >= 35, "market bands present for most of the top 50",
       f"only {with_band}/50")
    ok(all(p.get("adp_sleeper") for p in top), "sleeper ADP present in top 50")

# 3. Crosswalk + reconciliation: unmatched logged, never dropped
xw, rec = load("crosswalk"), load("reconciliation")
if xw and rec and adp:
    n_matched = len(xw["matched"])
    n_unmatched = rec["unmatched_count"]
    total = len(adp["players"])
    ok(n_matched + n_unmatched >= total * 0.9 - 32,
       "crosswalk accounts for ADP players (matched + logged; DEF excluded)",
       f"{n_matched}+{n_unmatched} vs {total}")
    # The guard that matters: players inside the real draft window must
    # match. The window is ADP < 200 (the league drafts 12x15 = 180 picks;
    # 200 leaves margin) - the old ADP < 250 window broke the cron for four
    # straight days in late August when Sleeper's deepening preseason pool
    # pushed camp bodies with ADP 237-249 past the 2% budget, players
    # nflverse does not carry and no page renders. A normalizer regression
    # still trips this instantly: it would unmatch names across the whole
    # window, not just the fringe.
    matched_ids = set(xw["matched"])
    window = [p for p in adp["players"]
              if (p.get("adp_sleeper") or 999) < 200 and p["pos"] != "DEF"]
    un_window = [p["name"] for p in window if p["player_id"] not in matched_ids]
    ok(len(un_window) <= max(2, len(window) * 0.02),
       "draft-window players (ADP < 200) match at >=98% (suffix-normalized)",
       f"{len(un_window)}/{len(window)}: {un_window[:5]}")
    # The 200-249 fringe may legitimately miss (Sleeper lists camp bodies
    # nflverse lacks), but the law stands: unmatched is LOGGED, never
    # silently dropped.
    fringe = [p for p in adp["players"]
              if 200 <= (p.get("adp_sleeper") or 999) < 250 and p["pos"] != "DEF"]
    logged = {r["name"] for r in rec.get("unmatched", [])}
    un_fringe = [p["name"] for p in fringe if p["player_id"] not in matched_ids]
    ok(all(n in logged for n in un_fringe),
       "every unmatched fringe player (ADP 200-249) is logged in reconciliation",
       f"unlogged: {[n for n in un_fringe if n not in logged][:5]}")
    # Match rate is a useful tripwire, but it is not the specification.  The
    # canonical key and identity resolver have an explicit behavioral corpus
    # below so the next source-specific spelling incident cannot redefine the
    # contract in only one consumer.

    # Source uniqueness is not enough: one FFC row must not fan out to two
    # Sleeper identities which the deliberately blind key collapses.
    _target_buckets = {}
    for _player in adp["players"]:
        _target_buckets.setdefault(
            (comparison_key(_player["name"]), _player["pos"]), []).append(_player)
    _target_collisions = [rows for rows in _target_buckets.values()
                          if len(rows) > 1]
    _market_fields = ("adp_ffc", "stdev", "high", "low", "bye")
    _target_leaks = [
        [(p["player_id"], p["name"]) for p in rows]
        for rows in _target_collisions
        if any(any(field in p for field in _market_fields) for p in rows)]
    ok(not _target_leaks,
       "FFC market rows fail closed on every ambiguous Sleeper target bucket",
       f"{len(_target_collisions)} current buckets; leaks {_target_leaks}")

# The live scan above is vacuous-safe because an upstream provider may remove
# every collision. This fixed corpus makes the no-fanout behavior non-vacuous:
# the suffix-blind key collides on the two Harrisons, while the punctuation-only
# D.J./DJ variant remains a valid one-to-one market join.
_synthetic_market = merge_ffc_market(
    {
        "father": {"name": "Marvin Harrison", "pos": "WR",
                   "adp_sleeper": 201.0},
        "son": {"name": "Marvin Harrison Jr.", "pos": "WR",
                "adp_sleeper": 20.0},
        "dj": {"name": "D.J. Moore", "pos": "WR", "adp_sleeper": 40.0},
    },
    [
        {"name": "Marvin Harrison Jr.", "pos": "WR",
         "fields": {"adp_ffc": 21.0}},
        {"name": "DJ Moore", "pos": "WR",
         "fields": {"adp_ffc": 41.0}},
    ])
_synthetic_by_id = {row["player_id"]: row for row in _synthetic_market}
ok("adp_ffc" not in _synthetic_by_id["father"] and
   "adp_ffc" not in _synthetic_by_id["son"],
   "FFC synthetic collision cannot fan one market row across two identities")
ok(_synthetic_by_id["dj"].get("adp_ffc") == 41.0,
   "FFC synthetic one-to-one typography variant still joins")

# 3b. PLAYER-NAME CONTRACT.  comparison_key is intentionally blind to source
#     typography.  PlayerIdentityResolver retains the collision and requires
#     independent evidence before it returns an identity.
_equivalent_names = [
    ("Audric Estime", "Audric Estimé"),
    ("John Metchie", "John Metchie III"),
    ("D.J. Moore", "DJ Moore"),
    ("Ja'Marr Chase", "Ja’Marr Chase", "Jamarr Chase"),
    ("Jaxon Smith-Njigba", "Jaxon Smith Njigba", "JaxonSmithNjigba"),
    ("Amon-Ra St. Brown", "Amon Ra St Brown", "AmonRaStBrown"),
]
_apostrophe_variants = (
    ("U+0027 APOSTROPHE", "'"),
    ("U+2019 RIGHT SINGLE QUOTATION MARK", "\u2019"),
    ("U+02BC MODIFIER LETTER APOSTROPHE", "\u02bc"),
    ("U+0060 GRAVE ACCENT", "`"),
    ("U+00B4 ACUTE ACCENT", "\u00b4"),
    ("U+2018 LEFT SINGLE QUOTATION MARK", "\u2018"),
)
_apostrophe_names = tuple(
    f"Wan{variant}Dale Robinson" for _label, variant in _apostrophe_variants)
_equivalent_names.append(_apostrophe_names + ("WanDale Robinson",))
_suffix_forms = tuple(f"Example Player {suffix}"
                      for suffix in ("Jr", "Sr", "II", "III", "IV", "V"))
_equivalent_names.append(("Example Player",) + _suffix_forms)
for _group in _equivalent_names:
    _keys = {comparison_key(name) for name in _group}
    ok(len(_keys) == 1,
       "comparison key is blind to: " + " / ".join(_group),
       str(sorted(_keys)))
ok(comparison_key("Joshua Alexander") != comparison_key("Josh Alexander"),
   "comparison key does not invent nickname equivalence")
ok({search_key(name) for name in _apostrophe_names + ("WanDale Robinson",)} ==
   {"wandale robinson"},
   "search key folds every named apostrophe/quote contract variant",
   str([(label, search_key(f"Wan{variant}Dale Robinson"))
        for label, variant in _apostrophe_variants]))
_apostrophe_identity = PlayerIdentityResolver([
    {"name": "Wan'Dale Robinson", "pos": "WR", "id": "wandale"},
])
ok(all(_apostrophe_identity.resolve(name, position="WR").record["id"] ==
       "wandale" for name in _apostrophe_names),
   "identity resolver accepts every apostrophe/quote contract variant")
_alias_identity = PlayerIdentityResolver([
    {"name": "Kenneth Gainwell", "aliases": ["Kenny Gainwell"],
     "pos": "RB", "id": "gainwell"},
])
ok(comparison_key("Kenneth Gainwell") != comparison_key("Kenny Gainwell") and
   _alias_identity.resolve("Kenny Gainwell", position="RB").record["id"] ==
   "gainwell",
   "identity aliases are explicit evidence, never comparison-key blindness")
_alias_collision = PlayerIdentityResolver([
    {"name": "First Player", "aliases": ["Shared Alias"], "pos": "WR"},
    {"name": "Second Player", "aliases": ["Shared Alias"], "pos": "WR"},
])
ok(_alias_collision.resolve("Shared Alias", position="WR").record is None,
   "an alias collision stays unresolved")
_primary_over_alias = PlayerIdentityResolver([
    {"name": "Michael Thomas", "aliases": [], "pos": "WR", "id": "primary"},
    {"name": "Mike Thomas", "aliases": ["Michael Thomas"],
     "pos": "WR", "id": "alias"},
])
_primary_result = _primary_over_alias.resolve("Michael Thomas", position="WR")
ok(_primary_result.record and _primary_result.record["id"] == "primary" and
   _primary_result.rule == "position + exact primary name",
   "an exact primary name outranks another record's colliding alias")
_reverse_alias = PlayerIdentityResolver([
    {"name": "Michael Thomas", "aliases": [], "pos": "WR", "id": "other"},
    {"name": "Mike Thomas", "aliases": ["Michael Thomas Jr."],
     "pos": "WR", "id": "alias"},
])
_reverse_result = _reverse_alias.resolve("Michael Thomas Jr.", position="WR")
ok(_reverse_result.record and _reverse_result.record["id"] == "alias" and
   _reverse_result.rule == "position + exact alias name",
   "a suffix-blind primary cannot steal another record's exact alias")
_evidence_only = nflverse_roster_identity(
    [], positions=("RB",), alias_rows=[
        {"player_id": "00-identity", "player_name": "Ray Rice", "pos": "RB"},
        {"player_id": "espn-local", "player_name": "Wrong Namespace", "pos": "RB"},
    ])
ok(_evidence_only.resolve("Ray Rice", position="RB").record["gsis_id"] ==
   "00-identity" and
   _evidence_only.resolve("Wrong Namespace", position="RB").record is None,
   "stable GSIS evidence survives a missing roster row; foreign ids do not")

_identity_corpus = [
    {"name": "Marvin Harrison", "pos": "WR", "draft_year": 1996,
     "id": "father"},
    {"name": "Marvin Harrison Jr.", "pos": "WR", "draft_year": 2024,
     "id": "son"},
    {"name": "Frank Gore", "pos": "RB", "draft_year": 2005,
     "id": "father-gore"},
    {"name": "Frank Gore Jr.", "pos": "RB", "draft_year": None,
     "id": "son-gore"},
]
_identity = PlayerIdentityResolver(_identity_corpus)
ok(len(_identity.candidates("Marvin Harrison Jr.")) == 2 and
   _identity.resolve("Marvin Harrison Jr.", position="WR").record is None,
   "identity layer retains the Harrison father/son collision")
_harrison = _identity.resolve(
    "Marvin Harrison Jr.", position="WR", prefer_latest_draft_year=True)
ok(_harrison.record and _harrison.record["id"] == "son" and
   _harrison.rule == "most recent draft_year",
   "current-player resolver uses the unique latest draft year explicitly")
ok(_identity.resolve("Frank Gore Jr.", position="RB",
                     prefer_latest_draft_year=True).record is None,
   "identity layer fails closed when Gore father/son years are incomplete")
_tied = PlayerIdentityResolver([
    {"name": "Tie Player", "pos": "WR", "draft_year": 2025, "id": "a"},
    {"name": "Tie Player Jr.", "pos": "WR", "draft_year": 2025, "id": "b"},
])
ok(_tied.resolve("Tie Player", position="WR",
                 prefer_latest_draft_year=True).record is None,
   "identity layer fails closed when the latest year is tied")
_positioned = PlayerIdentityResolver([
    {"name": "Shared Name", "pos": "RB", "id": "rb"},
    {"name": "Shared Name", "pos": "WR", "id": "wr"},
])
ok(_positioned.resolve("Shared Name", position="WR").record["id"] == "wr",
   "identity layer uses position when it uniquely separates a collision")
_position_mismatch = PlayerIdentityResolver([
    {"name": "Position Changer", "pos": "TE", "id": "te"},
])
ok(_position_mismatch.resolve("Position Changer", position="WR").record is None,
   "identity layer fails closed on a unique-name position mismatch")
_legacy_position = _position_mismatch.resolve(
    "Position Changer", position="WR", allow_unique_position_mismatch=True)
ok(_legacy_position.record and _legacy_position.record["id"] == "te" and
   "position mismatch" in _legacy_position.rule,
   "the crosswalk's legacy position-mismatch fallback is explicit and opt-in")

if adp:
    # This integration scan is allowed to see zero current collisions; the
    # fixed Harrison/Gore corpus above is the non-vacuous behavior contract.
    _current = [{"name": p["name"], "pos": p["pos"],
                 "id": p["player_id"]} for p in adp["players"]]
    _current_resolver = PlayerIdentityResolver(_current)
    _current_buckets = {}
    for _record in _current:
        _current_buckets.setdefault(
            (comparison_key(_record["name"]), _record["pos"]), []).append(_record)
    _ambiguous_current = [records for records in _current_buckets.values()
                          if len(records) > 1]
    _silently_resolved = []
    for _records in _ambiguous_current:
        _result = _current_resolver.resolve(
            _records[0]["name"], position=_records[0]["pos"])
        if _result.record is not None:
            _silently_resolved.append(_records[0]["name"])
    ok(not _silently_resolved,
       "identity layer fails closed for every current same-key/position collision",
       f"{len(_ambiguous_current)} buckets; resolved {_silently_resolved}")

# 3c. STRUCTURAL SINGLE-DEFINITION GUARD.  Every consumer imports the
#     canonical layer; a retyped suffix/punctuation normalizer fails even if
#     today's match-rate happens to stay green.
_python_sites = []
_duplicate_normalizers = []
_missing_imports = []
_duplicate_nfkd = []
_normalizer_name = re.compile(
    r"(^|_)(norm(?:aliz(?:e|er|ation))?|comparison_?key|search_?key|"
    r"canonical_?name|name_?canonical|name_?key|key_?name|player_?key|"
    r"strip_?suffix|fold_?name|name_?fold)($|_)", re.I)
_suffix_literal = re.compile(
    r"(?:['\"]jr['\"].*['\"]sr['\"].*['\"]ii['\"]|"
    r"jr\\?\|sr\\?\|ii)", re.I | re.S)


def _assigned_names(node):
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return [child.id for target in targets for child in ast.walk(target)
            if isinstance(child, ast.Name)]


def _has_blind_chain(tree):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        calls = [child for child in ast.walk(node)
                 if isinstance(child, ast.Call)]
        has_case_fold = any(
            isinstance(call.func, ast.Attribute) and
            call.func.attr in ("lower", "casefold") for call in calls)
        has_punctuation_fold = any(
            (isinstance(call.func, ast.Attribute) and
             call.func.attr in ("replace", "translate")) or
            (isinstance(call.func, ast.Attribute) and
             isinstance(call.func.value, ast.Name) and
             call.func.value.id == "re" and call.func.attr == "sub")
            for call in calls)
        if has_case_fold and has_punctuation_fold:
            return True
    return False


def _synthetic_python_duplicate(source):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and \
           _normalizer_name.search(node.name):
            return True
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and any(
                _normalizer_name.search(name)
                for name in _assigned_names(node)):
            return True
    return _has_blind_chain(tree) or bool(_suffix_literal.search(source))


_guard_mutants = (
    "def norm(n): return n.lower().replace('.', '')",
    "opaque = lambda n: n.casefold().replace('-', '')",
    "import re\nclean = lambda n: re.sub(r\"[.'’]\", '', n.casefold())",
    "def fold_name(n): return n.casefold()\ndef strip_suffix(n): return n",
    "SUFFIXES = {'jr', 'sr', 'ii', 'iii'}",
)
ok(all(_synthetic_python_duplicate(source) for source in _guard_mutants),
   "structural guard bites on reduced, lambda, split-helper, and suffix mutants")


for _scope in ("src", "tests"):
    _base = os.path.join(ROOT, _scope)
    for _dirpath, _, _filenames in os.walk(_base):
        for _filename in _filenames:
            if not _filename.endswith(".py"):
                continue
            _path = os.path.join(_dirpath, _filename)
            _rel = os.path.relpath(_path, ROOT)
            _source = open(_path).read()
            _tree = ast.parse(_source, filename=_path)
            _is_canonical = _rel == "src/player_names.py"
            _is_guard = _rel == "tests/test_pages_data.py"
            if not (_is_canonical or _is_guard) and \
               ("NFKD" in _source or "unicodedata" in _source):
                _duplicate_nfkd.append(_rel)
            if not (_is_canonical or _is_guard) and _suffix_literal.search(_source):
                _duplicate_normalizers.append((_rel, "suffix literal", 1))
            if not (_is_canonical or _is_guard) and _has_blind_chain(_tree):
                _duplicate_normalizers.append((_rel, "blind transform chain", 1))
            _imports = set()
            for _node in ast.walk(_tree):
                if isinstance(_node, ast.ImportFrom) and \
                   _node.module == "player_names":
                    _imports.update(alias.name for alias in _node.names)
            for _node in ast.walk(_tree):
                if isinstance(_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if _node.name in ("comparison_key", "search_key",
                                      "_comparison_parts"):
                        _python_sites.append((_rel, _node.name, _node.lineno))
                    if _normalizer_name.search(_node.name) and \
                       not (_is_canonical or _is_guard):
                        _duplicate_normalizers.append(
                            (_rel, _node.name, _node.lineno))
                if isinstance(_node, (ast.Assign, ast.AnnAssign)) and \
                   not (_is_canonical or _is_guard):
                    for _assigned in _assigned_names(_node):
                        if _normalizer_name.search(_assigned):
                            value = _node.value
                            canonical_alias = (isinstance(value, ast.Name) and
                                               value.id in ("comparison_key",
                                                            "search_key"))
                            if not canonical_alias:
                                _duplicate_normalizers.append(
                                    (_rel, _assigned, _node.lineno))
                if isinstance(_node, ast.Call) and isinstance(_node.func, ast.Name) and \
                   _node.func.id in ("comparison_key", "search_key",
                                     "PlayerIdentityResolver",
                                     "nflverse_roster_identity") and \
                   _rel != "src/player_names.py" and _node.func.id not in _imports:
                    _missing_imports.append((_rel, _node.func.id, _node.lineno))
ok([(path, name) for path, name, _ in _python_sites] == [
       ("src/player_names.py", "_comparison_parts"),
       ("src/player_names.py", "comparison_key"),
       ("src/player_names.py", "search_key")],
   "Python player-name transformation is defined in one canonical module",
   str(_python_sites))
ok(not _duplicate_normalizers,
   "no Python consumer retypes the player-name transformation",
   str(_duplicate_normalizers))
ok(not _duplicate_nfkd,
   "no Python consumer retypes the canonical Unicode fold",
   str(_duplicate_nfkd))
ok(not _missing_imports,
   "every Python normalizer/resolver consumer imports the canonical symbol",
   str(_missing_imports))

_browser_key_path = os.path.join(ROOT, "out", "player_names.js")
_browser_key_source = open(_browser_key_path).read()
_browser_pages = ("draft_room.html", "big_board.html", "players.html", "teams.html")
_browser_duplicates = []


def _javascript_duplicate(source):
    without_shared_alias = re.sub(
        r"\bconst\s+norm\s*=\s*playerComparisonKey\s*;", "", source)
    return bool(
        "function playerComparisonKey" in source or
        re.search(r"\.normalize\([\"']NFKD[\"']\)", source) or
        re.search(r"(?:toLowerCase\(\)[^;\n]{0,300}\.replace\(|"
                  r"\.replace\([^;\n]{0,300}toLowerCase\(\))", source) or
        re.search(r"(?:function|const|let|var)\s+[\w$]*"
                  r"(?:norm|normaliz|nameKey|playerKey|stripSuffix|foldName)"
                  r"[\w$]*\s*(?:\(|=)", without_shared_alias, re.I))


ok(_javascript_duplicate(
       "const keyForPlayer = n => n.toLowerCase().replace(/[^a-z]/g, '');") and
   _javascript_duplicate(
       "const clean = n => n.replace(/[.']/g, '').toLowerCase();") and
   _javascript_duplicate(
       "const foldName = n => n.toLowerCase(); const stripSuffix = n => n;") and
   not _javascript_duplicate("const norm = playerComparisonKey;"),
   "browser duplication guard bites on inline and split-helper mutants")
for _page_name in _browser_pages:
    _page_source = open(os.path.join(ROOT, "out", _page_name)).read()
    if ("player_names.js" not in _page_source or
        "const norm = playerComparisonKey" not in _page_source):
        _browser_duplicates.append(_page_name + ": shared key absent")
    if re.search(r"jr\|sr\|ii\|iii\|iv\|v", _page_source, re.I):
        _browser_duplicates.append(_page_name + ": suffix logic duplicated")
for _dirpath, _, _filenames in os.walk(os.path.join(ROOT, "out")):
    for _filename in _filenames:
        if not _filename.endswith((".html", ".js")) or \
           _filename == "player_names.js":
            continue
        _path = os.path.join(_dirpath, _filename)
        _source = open(_path).read()
        if _javascript_duplicate(_source):
            _browser_duplicates.append(
                os.path.relpath(_path, ROOT) + ": key logic duplicated")
ok(_browser_key_source.count("function playerComparisonKey") == 1 and
   not _browser_duplicates,
   "four browser consumers share one JavaScript comparison-key definition",
   "; ".join(_browser_duplicates))

_parity_names = [name for group in _equivalent_names for name in group]
if adp:
    _parity_names.extend(p["name"] for p in adp["players"])
_parity_names = list(dict.fromkeys(_parity_names))
_node_program = (
    "const fs=require('fs');"
    "const m=require(process.argv[1]);"
    "const xs=JSON.parse(fs.readFileSync(0,'utf8'));"
    "process.stdout.write(JSON.stringify(xs.map(m.playerComparisonKey)));"
)
try:
    _node_result = subprocess.run(
        ["node", "-e", _node_program, _browser_key_path],
        input=json.dumps(_parity_names), text=True, capture_output=True,
        check=True)
    _js_keys = json.loads(_node_result.stdout)
    _py_keys = [comparison_key(name) for name in _parity_names]
    _parity_bad = [name for name, py, js in
                   zip(_parity_names, _py_keys, _js_keys) if py != js]
    ok(not _parity_bad,
       "browser comparison key matches Python for the corpus and current pool",
       str(_parity_bad[:5]))
except (OSError, subprocess.CalledProcessError, ValueError) as _exc:
    ok(False, "browser comparison key parity test executes", str(_exc))

# 4. Depth charts: all 32 teams, as-of date fresh (within 7 days of build)
dc = load("depth_charts")
if dc:
    teams = {e["team"] for e in dc["entries"]}
    ok(len(teams) == 32, "depth charts cover 32 teams", f"{len(teams)}")
    as_of = dc["provenance"].get("as_of", "")[:10]
    try:
        age = (datetime.date.today() - datetime.date.fromisoformat(as_of)).days
        ok(age <= 7, "depth chart as-of within 7 days", f"{age} days ({as_of})")
    except ValueError:
        ok(False, "depth chart as-of parseable", as_of)

# 5. Usage: literal-column basis declared, shares are means of weekly cols
us = load("usage_2025")
if us:
    ok("literal columns" in us["provenance"].get("basis", ""),
       "usage shard declares its literal-column basis")
    top = us["players"][:100]
    ok(all(0 <= (p.get("target_share_mean") or 0) <= 1 for p in top),
       "share fields bounded in [0,1]")

# 6. PROE: plausible range (league PROE means sit within a few points of zero)
pr = load("team_proe_2025")
if pr:
    vals = [t["proe_2025"] for t in pr["teams"] if t["proe_2025"] is not None]
    ok(len(vals) == 32, "PROE for 32 teams", f"{len(vals)}")
    ok(all(-15 <= v <= 15 for v in vals), "PROE values in plausible band",
       f"range {min(vals)}..{max(vals)}")

# 7. Playcallers: curated file rendered with tags; count matches addendum
pc = load("playcallers")
if pc:
    ok(len(pc["callers"]) == 19, "19 play-caller rows per addendum",
       f"{len(pc['callers'])}")
    ok(all(r.get("tag") in ("VERIFIED-LIVE", "SOURCED", "REPORTED")
           for r in pc["callers"]), "every play-caller row tagged")
    ok(all(r.get("source_url") for r in pc["callers"]),
       "every play-caller row carries a source URL")

# 8. N1 (intel isolation, standing guard): no team-intel field name appears in
#    the engine's decision payload. The engine does not read out/data/; this
#    guard catches anyone wiring it in later.
eng_path = os.path.join(ROOT, "src", "engine_2026.py")
src = open(eng_path).read()
ok("build_pages_data" not in src and "team_proe" not in src and "playcallers" not in src,
   "N1: engine imports nothing from the pages-data layer")

# 8b. P0 PICK CLOCK LAW: the clock derives from the draft's own settings
#     and anchors to Sleeper's last_picked - never a hardcoded duration,
#     never poll-detection time. The 2x silent-clock defect stays dead.
_room = open(os.path.join(ROOT, "out", "draft_room.html")).read()
ok("pick_timer" in _room and "last_picked" in _room,
   "P0: the room reads pick_timer and last_picked from the draft")
ok("two minutes" not in _room and ">2:00<" not in _room,
   "P0: no two-minute language or hardcoded 2:00 anywhere in the room")
ok("120 - Math.floor" not in _room and "clockStart" not in _room,
   "P0: the hardcoded duration and the poll-anchored clock are gone")
ok("clock unavailable - use Sleeper" in _room,
   "P0: absent clock data renders an honest absence, not a plausible number")
ok("LiveState.pickTimer = (draft.settings && Number(draft.settings.pick_timer)) || null" in _room,
   "P0: the duration is captured from settings on every fetch")

# 8d. RESPONSE VALIDITY AND FRESHNESS (review P1-C): a resolved fetch is
#     not current data. The room must cache-bust, check response.ok,
#     validate shape, refuse to move the board backwards, and show source
#     age beside fetch time.
ok('"?cb=" + Date.now()' in _room and '"/picks?cb=" + Date.now()' in _room,
   "P1-C: both draft fetches are cache-busted per poll")
ok("Array.isArray(picks)" in _room,
   "P1-C: picks must be an array before the board renders from them")
ok("picks.length < LiveState.lastPickCount" in _room and
   "LiveState.pendingShrink" in _room and "picksSnapshotKey" in _room,
   "P1-C: one-off shrink is held; an identical confirming snapshot can recover visibly")
ok("data \" + Math.max" in _room or "- data " in _room,
   "P1-C: source age renders beside fetch time")
ok("e.httpStatus" in _room and "badSchema" in _room,
   "P1-C: HTTP errors and unusable payloads are named, not swallowed")

# 8c. DEPLOY COMPLETENESS: pages.yml copies an explicit file list, which
#     silently omitted a brand-new page once (paths.html shipped to main,
#     every gate green, live site 404). Every page the shared nav links to
#     must appear in the deploy copy list.
_pgy = open(os.path.join(ROOT, ".github", "workflows", "pages.yml")).read()
_navsrc0 = open(os.path.join(ROOT, "out", "nav.js")).read()
import re as _re
_nav_hrefs = _re.findall(r'\["\w+",\s*"[^"]+",\s*"([^"]+)"\]', _navsrc0)
_missing_deploy = [h for h in _nav_hrefs if f"out/{h}" not in _pgy]
ok(not _missing_deploy,
   "every nav-linked page is in the pages.yml deploy list",
   "; ".join(_missing_deploy))

# 9. Heartbeat exists (Actions keepalive)
ok(os.path.exists(os.path.join(D, "heartbeat.txt")), "heartbeat file present")

# 10. PHASE C PLAYER PAGES. Acceptance: every number the page renders traces
#     to a real shard field. The page marks each one pv(value, shard, field);
#     this guard resolves every reference against the committed shards.
import re

pp = os.path.join(ROOT, "out", "players.html")
ok(os.path.exists(pp), "players.html exists")
if os.path.exists(pp):
    page = open(pp).read()
    # anchored on the trailing (shard, field) string args so pv() calls whose
    # value argument itself contains parentheses are still captured
    refs = set(re.findall(r',\s*"([A-Za-z0-9_]+\.json)"\s*,\s*"([A-Za-z0-9_]+)"\s*\)', page))
    ok(len(refs) >= 15, "page carries tappable provenance references",
       f"only {len(refs)}")
    # field universe per shard, from the committed files themselves
    fields = {}
    if adp:
        fields["adp.json"] = set().union(*(set(p) for p in adp["players"][:300]))
    if us:
        fields["usage_2025.json"] = set().union(*(set(p) for p in us["players"][:300]))
    if xw:
        fields["crosswalk.json"] = set().union(
            *(set(v) for v in list(xw["prospect"].values())[:300]))
    epath = os.path.join(ROOT, "out", "engine_2026.json")
    em = json.load(open(epath))
    fields["engine_2026.json"] = set().union(
        *(set(p) for p in em["players"][:300])) | {"vor_rank"}
    bad = [f"{s}:{f}" for s, f in refs
           if s not in fields or f not in fields[s]]
    ok(not bad, "every page-data reference resolves to a shard field",
       "; ".join(bad[:5]))
    ok("Provenance (guard N2)" in page, "provenance footer present")
    ok("ffc_attribution" in page, "FFC attribution rendered from the shard")
    ok("projection = floor" in page and "kdef_note" in page,
       "K/DST floor label and note wired")
    ok("no free in-season source" in page.lower()
       or "prior season - no free in-season source" in page,
       "route/usage metrics carry the prior-season honesty label")
    ok("Nothing on this page is estimated" in page,
       "absent blocks declared absent, not estimated")

# 11. PHASE D TEAM PAGES. Same acceptance as the player pages: every number
#     traces to a shard field, and every instrument shows its computation note.
tp_page = os.path.join(ROOT, "out", "teams.html")
ok(os.path.exists(tp_page), "teams.html exists")
if os.path.exists(tp_page):
    tpage = open(tp_page).read()
    trefs = set(re.findall(r',\s*"([A-Za-z0-9_]+\.json)"\s*,\s*"([A-Za-z0-9_]+)"\s*\)', tpage))
    ok(len(trefs) >= 8, "team page carries tappable provenance references",
       f"only {len(trefs)}")
    tfields = {}
    if pc:
        tfields["playcallers.json"] = set().union(*(set(r) for r in pc["callers"]))
    if pr:
        tfields["team_proe_2025.json"] = set().union(*(set(t) for t in pr["teams"]))
    if dc:
        tfields["depth_charts.json"] = set().union(*(set(e) for e in dc["entries"][:300]))
    if us:
        tfields["usage_2025.json"] = set().union(*(set(p) for p in us["players"][:300]))
    epath = os.path.join(ROOT, "out", "engine_2026.json")
    em2 = json.load(open(epath))
    tfields["engine_2026.json"] = set().union(*(set(p) for p in em2["players"][:300]))
    tbad = [f"{s}:{f}" for s, f in trefs if s not in tfields or f not in tfields[s]]
    ok(not tbad, "every team-page reference resolves to a shard field",
       "; ".join(tbad[:5]))
    ok(tpage.count("computation:") >= 4,
       "every instrument shows its computation note",
       f"only {tpage.count('computation:')}")
    ok("N1" in tpage and "p=0.99" in tpage,
       "team page states the N1 display-only rule with the backtest number")
    ok("Provenance (guard N2)" in tpage, "team page provenance footer present")
    ok("not zero" in tpage and "Nothing on this page is estimated" in tpage,
       "team page declares absent data absent")
    _room_team_source = open(os.path.join(ROOT, "out", "draft_room.html")).read()
    _js_team_map = 'LA:"LAR",JAC:"JAX",WSH:"WAS",ARZ:"ARI"'
    ok(_js_team_map in tpage and _js_team_map in _room_team_source and
       "[canonTeam(t.team), t]" in tpage and
       "[canonTeam(x.team), x.proe_2025]" in _room_team_source,
       "browser team-code boundaries mirror the Python alias contract")

# 11b. BIG BOARD (CVS). The rank is the anchor law and nothing else; the cap
#      and kill-switch are stated on the page; all seven signals carry three
#      channels (container treatment + icon + text label) with a legend and
#      persistent filters; the payload itself is ordered by CVS.
bb_page = os.path.join(ROOT, "out", "big_board.html")
ok(os.path.exists(bb_page), "big_board.html exists")
cvs_path = os.path.join(ROOT, "out", "cvs.json")
ok(os.path.exists(cvs_path), "cvs.json exists")
if os.path.exists(bb_page) and os.path.exists(cvs_path):
    bpage = open(bb_page).read()
    ok("CVS = VOR + z_point_scale x weighted-z" in bpage,
       "big board declares the anchor law on its face")
    ok("walter_enabled" in bpage and "kill-switch" in bpage
       and "capped" in bpage,
       "big board states the cap and the kill-switch as the risk bounds")
    ok("REJECTED" in bpage and "p=0.99" in bpage,
       "big board states the rejected tendency fold with its number")
    ok("NOT WIRED, ON PURPOSE" in bpage,
       "unwired factors declared not wired, with the reason")
    ok("floors" in bpage and "off the CVS board" in bpage,
       "K and DST floors stated off the board, with the reason")
    ok('get("cvs.json")' in bpage, "board is driven by cvs.json")
    ok("Provenance (guard N2)" in bpage, "big board provenance footer present")
    # signal encoding: every signal has a container treatment, an icon, and a
    # text label; the legend and conflict marker render; filters persist
    SIGNALS = ["personal_dnd", "consensus_dnd", "single_dnd",
               "consensus_target", "single_target", "consensus_sleeper",
               "single_sleeper"]
    miss = [s for s in SIGNALS if f'.brow[data-sig="{s}"]' not in bpage]
    ok(not miss, "every signal state has a container treatment",
       "; ".join(miss))
    for lbl in ("MY DND", "DND x2", '"DND"', "TARGET x2", '"TARGET"',
                "SLEEPER x2", '"SLEEPER"'):
        ok(lbl.strip('"') in bpage, f"signal text label {lbl} present")
    ok("renderLegend" in bpage and "! CONFLICT" in bpage,
       "legend always visible, conflict marker in it")
    ok("signal_conflict" in bpage and "Conflicts view" in bpage,
       "conflicts stay visible with their own marker and view")
    ok("ytfl_bb2" in bpage and "localStorage" in bpage,
       "filter and view state persists across refresh")
    ok("ytfl_walter_live" in bpage and "WALTER LAYER" in bpage,
       "live kill-switch toggle present, shared-key persisted")
    ok("no_walter" in bpage and "cvs_base" in bpage,
       "kill-switch renders the server-ranked pure-model variant")
    ok("tier_move" in bpage and "tiermoves" in bpage,
       "tier-boundary crossings flagged on rows and named in the delta view")
    drp = open(os.path.join(ROOT, "out", "draft_room.html")).read()
    ok("ytfl_walter_live" in drp and "cvs_base" in drp,
       "pick engine reads the same kill-switch and pure-model variant")
    # the draft-order hypothesis: quarantined, persisted, and explicitly
    # subordinate to Sleeper's real draw
    ok("ORDERHYP-BEGIN" in drp and "ORDERHYP-END" in drp
       and "ytfl_order_hyp" in drp,
       "order hypothesis is marker-quarantined and persisted")
    ok("THE LIVE SOURCE WINS" in drp and "hypothesis is retired" in drp,
       "order hypothesis states that Sleeper's draw wins, and retires visibly")
    ok(drp.index("ORDERHYP-BEGIN") > drp.index("engine-data-end"),
       "order hypothesis code sits outside the engine sentinels")
    # the survival calibration layer (ADOPTED, scope ii): payload table is
    # the committed constant, monotone, kill-switchable; the room consumes
    # it through the wrapper with the frozen fallback and shows the delta
    # on threshold-straddling picks only
    _esrc = open(os.path.join(ROOT, "src", "engine_2026.py")).read()
    _m = re.search(r"SURVIVAL_CALIBRATION = \[([^\]]+)\]", _esrc)
    _tbl = [float(x) for x in _m.group(1).replace("\n", " ").split(",")]
    emb2 = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
    ok(emb2.get("survival_calibration") == _tbl,
       "calibration table in the payload equals the committed constant")
    ok(len(_tbl) == 20 and all(0 <= v <= 1 for v in _tbl)
       and all(_tbl[i] <= _tbl[i + 1] + 1e-9 for i in range(19)),
       "calibration table is a monotone 20-bin probability table")
    ok(isinstance(emb2.get("survival_calibration_enabled"), bool),
       "payload carries the calibration kill switch")
    ok("SURVCAL-BEGIN" in drp and "ytfl_survcal_live" in drp
       and "function calCondSurvival" in drp,
       "room carries the calibrated wrapper and its one-tap toggle")
    ok("|| !survCalOn()) return p" in drp.replace("  ", " ")
       or "!survCalOn()) return p" in drp,
       "wrapper falls back to the frozen number when any switch is off")
    ok("const s = calCondSurvival(comp.adp" in drp
       and "the calibration flips this call" in drp,
       "verdict consumes the calibrated number and shows both on straddles")
    ok(drp.index("SURVCAL-BEGIN") > drp.index("engine-data-end"),
       "calibration code sits outside the engine sentinels")
    ok("1 - condSurvival(p.adp, ctx.myNext" in drp,
       "grade urgency stays on the frozen number (not in the approved diff)")
    ok("CALIBRATED SURVIVAL UNAVAILABLE" in drp,
       "toggle label honors the payload kill switch, never claims ON falsely")
    _cref = emb2.get("calibration_reference") or []
    ok(len(_cref) >= 5 and all(0 <= r["cal"] <= 1 for r in _cref),
       "payload carries Python-computed calibration anchors for JS parity")
    ok("2019-2025 era" in drp,
       "the room's disclosure names the deployed era fit, not the rejected blend")
    ok("pre-draft verdicts use the frozen survival model" in drp,
       "the frozen/calibrated boundary is stated on the pre-draft surface")
    # signal encoding in the room: same seven states, three channels,
    # server-side precedence, walter-toggle aware, display only
    ok("SIGENC-BEGIN" in drp and "SIGENC-END" in drp
       and drp.index("SIGENC-BEGIN") > drp.index("engine-data-end"),
       "room signal encoding is marker-quarantined outside the sentinels")
    for lbl in ("MY DND", "DND x2", "TARGET x2", "SLEEPER x2"):
        ok(lbl in drp, f"room carries signal label {lbl}")
    for c in ("#b91c1c", "#b45309", "#047857", "#1e3a8a", "#1d4ed8"):
        ok(c in drp, f"room carries signal color {c} (contrast-proven set)")
    ok("peWalterOn() ? c : c.no_walter" in drp,
       "room signals honor the walter live toggle via the server variants")
    _pe_seg = drp[drp.index("function peScore"):drp.index("function peCondition")]
    _gr_seg = drp[drp.index("const GRADE_W"):drp.index("function renderRecs")]
    ok("sigOf" not in _pe_seg and "sigBadge" not in _pe_seg
       and "sigOf" not in _gr_seg and "sigBadge" not in _gr_seg,
       "signals are display only - never inside the score or the grade")
    _vb_seg = drp[drp.index("function renderValueBoard"):drp.index("function simGauss")]
    ok("sigAttr(" in _vb_seg and "sigBadge(" in _vb_seg and "sigLegend()" in _vb_seg,
       "the value board (best-available view) carries all three signal channels")
    # byte-identity with the big board: the SIG and ICON maps must never
    # drift between the two pages (labels, colors, icon assignment, SVGs)
    def _blk(src, name):
        i = src.index(f"const {name} = {{")
        return src[i:src.index("};", i) + 2]
    ok(_blk(drp, "SIG") == _blk(bpage, "SIG")
       and _blk(drp, "ICON") == _blk(bpage, "ICON"),
       "room SIG and ICON maps are byte-identical to the big board")
    # a novel cvs.json signal value must render nothing, never throw inside
    # the render loop (refresh() swallows render errors AFTER stamping the
    # freshness dot, so a throw here would freeze the room silently)
    _sb_seg = drp[drp.index("function sigBadge"):drp.index("function sigAttr")]
    _sa_seg = drp[drp.index("function sigAttr"):drp.index("function sigLegend")]
    ok('if (!s) return "";' in _sb_seg and "SIG[s0.sig]" in _sa_seg,
       "unknown signal keys are guarded in both channels (badge and data-sig)")
    # gone/taken rows never carry a signal - pin the suppression branches
    ok('${gone ? "" : sigAttr(p)}' in drp and '${gone ? "" : sigBadge(p)}' in drp,
       "value board gone rows are signal-free (both channels suppressed)")
    ok('${c.taken ? "" : sigAttr(c.p)}' in drp
       and '${c.taken ? "" : sigBadge(c.p)}' in drp,
       "a taken searched player in recs is signal-free (both channels suppressed)")
    # ordering is pinned by the exact comparators - the signal cannot reach
    # them without breaking these strings
    ok(".sort((a, b) => b.s.total - a.s.total)" in drp,
       "pick-engine alternatives order by score alone (comparator pinned)")
    ok(".sort((a, b) => b.g - a.g)" in drp,
       "recs order by grade alone (comparator pinned)")
    # C1 RUNDETECT: the position-run alert derives from the league's own base
    # rates, never a fixed count
    _rd_seg = drp[drp.index("function runDetect"):drp.index("function renderFeatures")]
    ok("pos_base_rates" in _rd_seg and "binomTail" in _rd_seg,
       "run detection is binomial surprise against the archive's base rates")
    ok("c[pos] < 3" in _rd_seg and "0.05" in _rd_seg,
       "run floor (k>=3) and significance convention (p<0.05) are stated in code")
    ok("the archive expects" in drp,
       "run banner shows the expected count, not just the observed one")
    # C1 FLEX: payload carries the derived allocation with its source
    ok('"flex_allocation"' in open(os.path.join(ROOT, "src", "engine_2026.py")).read(),
       "engine payload carries the derived flex allocation")
    # IDENT + UPNEXT: the Sleeper identity layer and the "am I next" strip
    ok("IDENT-BEGIN" in drp and "UPNEXT-BEGIN" in drp
       and drp.index("IDENT-BEGIN") > drp.index("engine-data-end"),
       "identity and up-next blocks are marker-quarantined outside the sentinels")
    # the room's link must be DERIVED from the polled draft id, never typed
    # in - in DRAFT MODE it derives from the loaded mock id the same way
    ok('"https://sleeper.com/draft/nfl/" +\n  (MOCK_MODE ? MOCK_ID : (E.league ? E.league.draft_id : ""))' in drp,
       "the room's Sleeper link is derived from the polled draft id")
    ok("https://sleeper.com/draft/nfl/1389" not in drp,
       "the room hardcodes no draft url - it cannot drift from the feed")
    ok('$("sleeper-link").href = DRAFT_URL;' in drp,
       "the header link is wired to the derived draft url")
    # team_name is display only and must never displace the history join key
    eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
    rs = eng["rosters"]
    ok(all("team_name" in r and "franchise" in r for r in rs),
       "every roster carries both the Sleeper team name and the franchise era")
    mine = [r for r in rs if r["roster_id"] == eng["league"]["anthony_roster_id"]]
    ok(len(mine) == 1,
       "Anthony's stable roster id resolves exactly one roster",
       str([row["roster_id"] for row in mine]))
    ok(mine and isinstance(mine[0].get("handle"), str) and mine[0]["handle"] and
       (mine[0].get("team_name") is None or
        isinstance(mine[0].get("team_name"), str)),
       "mutable Sleeper handle/team name are display fields, not identity",
       str(mine and (mine[0].get("handle"), mine[0].get("team_name"))))
    ok(mine and mine[0]["franchise"] == "Antdell & Ernie",
       "the franchise era key is unchanged by the team-name work")
    _up = drp[drp.index("UPNEXT-BEGIN"):drp.index("UPNEXT-END")]
    ok("YOU ARE ON THE CLOCK" in _up and "UP IN " in _up and "before you:" in _up,
       "the up-next strip states the clock, the count, and who picks first")
    ok("teamLabel(" in _up, "the up-next queue names teams, not bare slot numbers")
    # display only: identity must not reach the score or the grade
    _pe2 = drp[drp.index("function peScore"):drp.index("function peCondition")]
    ok("teamLabel" not in _pe2 and "team_name" not in _pe2,
       "the Sleeper team name never enters the pick-engine score")
    for pg_ in ("big_board.html", "home.html"):
        _t = open(os.path.join(ROOT, "out", pg_)).read()
        ok(eng["league"]["draft_id"] in _t,
           f"{pg_} links to the live Sleeper draft")
    ok("${S(p).cvs_rank}" in bpage,
       "rows render the payload's server-ranked variant - no page-side re-rank")
    # the ordering lives in the payload: strictly ranked, CVS-descending
    cvsp = json.load(open(cvs_path))["players"]
    ok([p["cvs_rank"] for p in cvsp] == list(range(1, len(cvsp) + 1)),
       "cvs.json players arrive ranked 1..N in order")
    ok(all(cvsp[i]["cvs"] >= cvsp[i + 1]["cvs"] for i in range(len(cvsp) - 1)),
       "cvs.json order is CVS-descending - no hidden composite in the page")

# 12. PHASE E HOME PAGE. The action board: countdown from the payload (not a
#     second hardcode), staleness thresholds stated, overlay completeness from
#     the engine payload, trending attributed, all four surfaces linked, and
#     the history fact carried WITH its p-value caveat.
hp = os.path.join(ROOT, "out", "home.html")
ok(os.path.exists(hp), "home.html exists")
if os.path.exists(hp):
    hpage = open(hp).read()
    ok("E.league.draft_date" in hpage,
       "countdown reads the draft date from the engine payload")
    ok("Fresh under 36h" in hpage and "aging under 7 days" in hpage,
       "staleness thresholds stated on the board")
    ok(all(f'href="{s}"' in hpage for s in
           ("draft_room.html", "big_board.html", "players.html", "teams.html",
            "ff-hub.html")),
       "home links every surface")
    ok("0 times in 13 seasons" in hpage and "p=0.323" in hpage
       and "not significant" in hpage,
       "history fact carries its p-value and the honesty caveat")
    ok("trending" in hpage and "never a projection" in hpage,
       "trending adds attributed and labelled non-projection")
    ok("25-call grading floor" in hpage or "25 calls" in hpage,
       "overlay completeness states the grading floor")
    ok("my_board" in hpage and "byte-identical" in hpage,
       "overlay card explains the empty-board guarantee")

# 12b. FINDINGS N.1. The user-facing findings page consumes the reviewed
#      BULLISH-vs-ADP artifact as its single source, fails visibly when that
#      source is unavailable or malformed, and never copies the fixed verdict
#      or its figures into a second static truth.
ffp = os.path.join(ROOT, "out", "ff-hub.html")
n1p = os.path.join(D, "bullish_vs_adp.json")
ok(os.path.exists(ffp) and os.path.exists(n1p),
   "ff-hub N.1 page and computed artifact both exist")
if os.path.exists(ffp) and os.path.exists(n1p):
    ffsrc = open(ffp).read()
    n1 = json.load(open(n1p))
    ok('data-p="p5"' in ffsrc and 'id="p5"' in ffsrc
       and "N.1 BULLISH vs ADP" in ffsrc,
       "ff-hub exposes N.1 as a dedicated findings tab")
    ok("data/bullish_vs_adp.json" in ffsrc and "cache:'no-store'" in ffsrc,
       "ff-hub reads the committed N.1 artifact without a browser cache")
    ok("if (!r.ok)" in ffsrc and "unusable schema" in ffsrc,
       "ff-hub rejects both HTTP failure and an unusable N.1 payload")
    ok(all(k in ffsrc for k in
           ("d.verdict", "d.within_band", "d.concentration",
            "d.provenance.method", "d.provenance.limitation")),
       "ff-hub renders verdict, cells, concentration, method, and limitation from the artifact")
    ok('id="n1State" data-state="loading" aria-live="polite"' in ffsrc
       and "data-state" in ffsrc and "No verdict is inferred in its absence" in ffsrc,
       "ff-hub has visible loading and honest error states")
    ok("computed artifact has not loaded yet" in ffsrc
       and "no verdict is shown" in ffsrc and "$('#n1Hero').textContent" in ffsrc,
       "ff-hub hero stays verdict-neutral until the artifact succeeds")
    ok(all(token in ffsrc for token in
           ("n1SideOk", "n1LiftOk", "n1BandOk", "provenance.generated",
            "concentration.note", "hit12.ci95", "p_two_sided")),
       "ff-hub validates every nested N.1 field it renders")
    ok(n1["verdict"] not in ffsrc
       and all(s not in ffsrc for s in
               ("28/43", "133/257", "65.1%", "51.8%", "+13.4pp")),
       "ff-hub does not duplicate the reviewed verdict or computed figures")
    n1section = ffsrc[ffsrc.index('<section class="panel" id="p5"'):
                      ffsrc.index("<footer>")]
    ok('class="tag k"' not in n1section and 'class="tag l"' not in n1section,
       "INCONCLUSIVE uses a neutral tag, not reserved verdict colors")
    ok("eight original draft-day" in ffsrc.lower()
       and "later BULLISH-vs-ADP test" in ffsrc,
       "the original eight nulls stay distinct from the inconclusive N.1 test")
    pages_workflow = open(os.path.join(ROOT, ".github", "workflows", "pages.yml")).read()
    ok("cp out/data/*.json" in pages_workflow and "out/ff-hub.html" in pages_workflow,
       "Pages deploys both the N.1 artifact family and its findings page")

# 13. APP SHELL (Phase 1). One nav, five pages: nav.js is the single source
#     of truth, every link target exists, every page includes it exactly once
#     with a distinct active key, and on the draft room the include lives
#     OUTSIDE the engine sentinels so regeneration can never touch it.
navp = os.path.join(ROOT, "out", "nav.js")
ok(os.path.exists(navp), "nav.js exists (single source of truth)")
if os.path.exists(navp):
    navsrc = open(navp).read()
    nav_items = re.findall(r'\["(\w+)",\s*"[^"]+",\s*"([^"]+)"\]', navsrc)
    ok(len(nav_items) == 7, "nav defines exactly seven items", f"{len(nav_items)}")
    missing = [href for _, href in nav_items
               if not os.path.exists(os.path.join(ROOT, "out", href))]
    ok(not missing, "every nav link target resolves to a real file",
       "; ".join(missing))
    PAGES = {"draft_room.html": "draft", "big_board.html": "board",
             "players.html": "players", "paths.html": "paths",
             "teams.html": "teams",
             "ff-hub.html": "findings", "home.html": "hub"}
    seen_keys = []
    for fname, want in PAGES.items():
        psrc = open(os.path.join(ROOT, "out", fname)).read()
        tags = re.findall(r'<script src="nav\.js" data-active="(\w+)"[^>]*\bdefer\b[^>]*></script>', psrc)
        ok(tags == [want], f"{fname} includes the shared nav once, active={want}",
           str(tags))
        seen_keys += tags
        # the old ad-hoc navs must be gone - one navigation system per page
        ok('<nav class="small">' not in psrc,
           f"{fname} carries no second navigation system")
    ok(sorted(seen_keys) == sorted(k for k, _ in nav_items),
       "each active key is used exactly once across the seven pages")
    dr = open(os.path.join(ROOT, "out", "draft_room.html")).read()
    tag_at = dr.index('src="nav.js"')
    ok(tag_at < dr.index('<script id="engine-data"'),
       "draft room nav include sits OUTSIDE (before) the engine sentinels")
    ok("nav.js" in open(os.path.join(ROOT, ".github", "workflows", "pages.yml")).read(),
       "pages workflow deploys nav.js")

# 14. APP SHELL (Phase 2). Token, layout, and header consistency: one dark
#     family (#0b1120, ff-hub's), one container width, one kicker treatment -
#     and the semantic verdict colors did not move.
ALL_PAGES = ["draft_room.html", "big_board.html", "players.html",
             "teams.html", "home.html", "ff-hub.html"]
_tokened = ["draft_room.html", "big_board.html", "players.html", "teams.html",
            "home.html"]
for fname in ALL_PAGES:
    psrc = open(os.path.join(ROOT, "out", fname)).read()
    ok("#0A0E1A" not in psrc and "0a0e1a" not in psrc.lower()
       or fname not in _tokened,
       f"{fname}: old dark background family fully retired")
    ok("max-width:1100px" in psrc, f"{fname}: shared 1100px container")
    ok('class="kick"' in psrc, f"{fname}: kicker header treatment present")
for fname in _tokened:
    psrc = open(os.path.join(ROOT, "out", fname)).read()
    ok("--bg:#0b1120" in psrc, f"{fname}: dark bg aligned to #0b1120")
    ok("--go:#34D399" in psrc and "--stop:#F87171" in psrc
       and "--warn:#FBBF24" in psrc,
       f"{fname}: semantic verdict colors did not move")
ok(".kick{" in open(navp).read(), "kicker style lives in nav.js (single source)")

# 15. APP SHELL (Phase 3). Polish stays inside its fence: reveals are opt-in
#     per page and the draft room never opts in; hover is a border-color lift
#     only; reduced-motion turns everything off.
navsrc2 = open(navp).read()
ok("data-reveal" not in open(os.path.join(ROOT, "out", "draft_room.html")).read(),
   "draft room NEVER carries the reveal attribute")
for fname in ("big_board.html", "players.html", "teams.html", "home.html", "ff-hub.html"):
    ok("data-reveal" in open(os.path.join(ROOT, "out", fname)).read(),
       f"{fname} opts into the phase 3 polish")
ok("prefers-reduced-motion:no-preference" in navsrc2
   and "prefers-reduced-motion: reduce" in navsrc2,
   "every phase 3 animation is fenced behind motion preference")
ok("translateY(8px)" in navsrc2 and ".4s" in navsrc2,
   "reveal is the specified 8px rise at 400ms")
ok("box-shadow" not in navsrc2 and "scale(" not in navsrc2,
   "hover lift is border-color only - no shadows, no transforms")

# 16. DARK LOCK. The hub matches a dark-only design target and must never
#     repaint on an OS theme flip - least of all mid-draft at sunset. No page
#     may carry a color-scheme preference rule; every page declares dark to
#     the browser so form controls and chrome match.
for fname in ALL_PAGES:
    psrc = open(os.path.join(ROOT, "out", fname)).read()
    ok("prefers-color-scheme" not in psrc,
       f"{fname}: no color-scheme preference rule - dark always")
    ok("data-theme" not in psrc,
       f"{fname}: no theme-attribute escape hatch either")
    ok('<meta name="color-scheme" content="dark">' in psrc,
       f"{fname}: declares color-scheme dark to the browser")
ok("prefers-color-scheme" not in navsrc2,
   "nav.js carries no color-scheme preference rule")

# 17. CONTRAST GUARD (the white-card fix). WCAG ratios are COMPUTED here from
#     the committed token values, never hardcoded as expected numbers - if a
#     future token change breaks legibility this section fails loudly.
def _srgb_lum(hexcolor):
    h = hexcolor.lstrip("#")
    chans = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        chans.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * chans[0] + 0.7152 * chans[1] + 0.0722 * chans[2]

def _contrast(a, b):
    la, lb = _srgb_lum(a), _srgb_lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)

def _scope_tokens(src, marker="CARD SCOPE"):
    i = src.index(marker)
    block = src[src.index("{", i):src.index("}", i)]
    return dict(re.findall(r'--([\w-]+):\s*(#[0-9a-fA-F]{6})', block))

def _root_tokens(src):
    i = src.index(":root{")
    block = src[i:src.index("}", i)]
    return dict(re.findall(r'--([\w-]+):\s*(#[0-9a-fA-F]{6})', block))

for fname in ("draft_room.html", "big_board.html", "players.html", "teams.html", "home.html"):
    psrc = open(os.path.join(ROOT, "out", fname)).read()
    card = _scope_tokens(psrc)
    page = _root_tokens(psrc)
    cs = card["s1"]
    bad = [f"--{t} {_contrast(card[t], cs):.2f}" for t in
           ("ink", "ink2", "ink3", "go", "stop", "warn", "info")
           if _contrast(card[t], cs) < 4.5]
    ok(not bad, f"{fname}: every card text and verdict token clears 4.5:1",
       "; ".join(bad))
    ok(_contrast(cs, page["bg"]) >= 3.0,
       f"{fname}: card surface vs page clears 3:1",
       f"{_contrast(cs, page['bg']):.2f}")
    dbad = [f"--{t} {_contrast(page[t], page['bg']):.2f}" for t in
            ("go", "stop", "warn")
            if _contrast(page[t], page["bg"]) < 4.5]
    ok(not dbad, f"{fname}: dark-context verdict colors clear 4.5:1 on the page",
       "; ".join(dbad))

_drsrc = open(os.path.join(ROOT, "out", "draft_room.html")).read()
_drcard = _scope_tokens(_drsrc)["s1"]
_pos = dict(re.findall(r'\.p(QB|RB|WR|TE|K|DEF)\{border-left-color:(#[0-9a-fA-F]{6})\}', _drsrc))
pbad = [f"{k} {_contrast(v, _drcard):.2f}" for k, v in _pos.items()
        if _contrast(v, _drcard) < 4.5]
ok(len(_pos) == 6 and not pbad,
   "draft grid position colors clear 4.5:1 on the card", "; ".join(pbad))

# the seven signal colors are load-bearing (names must stay legible inside
# every signal treatment) - verify each against the big-board card surface
_bbsrc = open(os.path.join(ROOT, "out", "big_board.html")).read()
_bbcard = _scope_tokens(_bbsrc)["s1"]
_sigcolors = set(re.findall(r'\.brow\[data-sig="[a-z_]+"\]\{border-color:(#[0-9a-fA-F]{6})', _bbsrc))
sbad = [f"{c} {_contrast(c, _bbcard):.2f}" for c in _sigcolors
        if _contrast(c, _bbcard) < 4.5]
ok(len(_sigcolors) == 5 and not sbad,
   "all five signal colors clear 4.5:1 on the big-board card",
   f"{len(_sigcolors)} colors; " + "; ".join(sbad))

# the players-page VOR ramp is a CONTINUOUS scale, so every interpolated
# color between the anchors must clear 4.5:1 on that card - not just the
# three anchors. It is also a DISTINCT scale: the ramp must not reuse the
# reserved verdict hexes (--go / --stop / --warn) in that card scope.
_plsrc = open(os.path.join(ROOT, "out", "players.html")).read()
_plcard = _scope_tokens(_plsrc)["s1"]
_anchors = re.search(
    r"const VOR_LO = \[(\d+), (\d+), (\d+)\], VOR_MID = \[(\d+), (\d+), (\d+)\],"
    r" VOR_HI = \[(\d+), (\d+), (\d+)\]", _plsrc)
ok(bool(_anchors), "players page declares the three VOR ramp anchors")
if _anchors:
    _n = [int(x) for x in _anchors.groups()]
    _lo, _mid, _hi = tuple(_n[0:3]), tuple(_n[3:6]), tuple(_n[6:9])
    _hex = lambda c: "#%02x%02x%02x" % c
    _ramp = []
    for _a, _b in ((_lo, _mid), (_mid, _hi)):
        for _i in range(21):
            _t = _i / 20
            _ramp.append(tuple(round(_a[j] + (_b[j] - _a[j]) * _t)
                               for j in range(3)))
    _rbad = [f"{_hex(c)} {_contrast(_hex(c), _plcard):.2f}" for c in _ramp
             if _contrast(_hex(c), _plcard) < 4.5]
    ok(not _rbad, "every interpolated VOR ramp color clears 4.5:1 on the card",
       "; ".join(_rbad[:3]))
    _pltok = _scope_tokens(_plsrc)
    _reserved = {_pltok[t].lower() for t in ("go", "stop", "warn") if t in _pltok}
    ok(not ({_hex(c) for c in (_lo, _mid, _hi)} & _reserved),
       "the VOR ramp is a distinct scale - no reserved verdict hexes reused",
       str(_reserved))
# the scale must be database-wide and median-anchored, both stated in code
ok("D.engine.players.map(p => p.vor)" in _plsrc,
   "VOR scale anchors are computed across the whole player database")
ok("right-skewed" in _plsrc and "median" in _plsrc,
   "the median-not-mean midpoint choice is stated on the page")
ok(".idxrow{display:flex;justify-content:flex-start" in _plsrc,
   "player rows are tight-packed, not space-between")
ok("grid-template-columns:repeat(3,minmax(0,1fr))" in _plsrc,
   "position groups render three across")

_ffsrc = open(os.path.join(ROOT, "out", "ff-hub.html")).read()
_ffcard = _scope_tokens(_ffsrc)
_ffpage = _root_tokens(_ffsrc)
_fcs = _ffcard["s1"]
fbad = [f"--{t} {_contrast(_ffcard[t], _fcs):.2f}" for t in
        ("t1", "t2", "t3", "teal", "red", "gold")
        if _contrast(_ffcard[t], _fcs) < 4.5]
ok(not fbad, "ff-hub: card text, accents, and darkened gold clear 4.5:1",
   "; ".join(fbad))
ok(_contrast(_fcs, _ffpage["bg"]) >= 3.0,
   "ff-hub: card surface vs page clears 3:1",
   f"{_contrast(_fcs, _ffpage['bg']):.2f}")
fdbad = [f"--{t} {_contrast(_ffpage[t], _ffpage['bg']):.2f}" for t in
         ("teal", "red")
         if _contrast(_ffpage[t], _ffpage["bg"]) < 4.5]
ok(not fdbad, "ff-hub: dark-context accents clear 4.5:1 on the page",
   "; ".join(fdbad))

# 18. TEASER LEAK GUARD. The shared build must give nothing away: redaction
#     happens at build time, so these are assertions about what the committed
#     teaser files CONTAIN, not about what CSS hides.
TEASER = os.path.join(ROOT, "out", "teaser")
_tfiles = ["index.html", "draft_room.html", "players.html", "teams.html",
           "ff-hub.html"]
ok(all(os.path.exists(os.path.join(TEASER, f)) for f in _tfiles),
   "teaser: all five pages built")
if all(os.path.exists(os.path.join(TEASER, f)) for f in _tfiles):
    em3 = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
    _pl = sorted(em3["players"], key=lambda p: -p["vor"])
    _top = lambda pos, n: [p["name"] for p in _pl if p["pos"] == pos][:n]
    allowed = set(_top("QB", 3) + _top("RB", 3) + _top("WR", 3)
                  + _top("TE", 1) + _top("K", 1) + _top("DEF", 1))
    handles = {r["handle"] for r in em3["rosters"] if r.get("handle")}
    franchises = {r["franchise"] for r in em3["rosters"] if r.get("franchise")}
    team_names = {r["team_name"] for r in em3["rosters"] if r.get("team_name")}
    top150 = [p["name"] for p in _pl[:150]]
    for f in _tfiles:
        src_t = open(os.path.join(TEASER, f)).read()
        leaks = [t for t in ("engine_2026", "data/", "nav.js", "../",
                             "my_board", "n_eff", "prior", "survival(",
                             "0.0772", "88.55", "p=0.323", "2,039",
                             "cvs", "walter", "Walter")
                 if t in src_t]
        ok(not leaks, f"teaser {f}: reaches no data, no shard, no real page",
           "; ".join(leaks))
        oleaks = [h for h in (handles | franchises | team_names)
                  if h and h in src_t]
        ok(not oleaks,
           f"teaser {f}: nothing about how this league's teams draft",
           "; ".join(oleaks[:3]))
        nleaks = [n for n in top150 if n in src_t and n not in allowed]
        ok(not nleaks, f"teaser {f}: no player beyond the allowed subset",
           "; ".join(nleaks[:3]))
        ok("YTFL PRIVATE BUILD" in src_t and "blur(" in src_t,
           f"teaser {f}: watermark and blur present")
    psrc_t = open(os.path.join(TEASER, "players.html")).read()
    ok(sum(1 for n in allowed if n in psrc_t) == len(allowed) == 12,
       "teaser players: exactly the 12 allowed names, all present",
       f"{sum(1 for n in allowed if n in psrc_t)}/{len(allowed)}")
    ok("teaser" in open(os.path.join(ROOT, ".github", "workflows",
                                     "pages.yml")).read(),
       "pages workflow deploys the teaser")

# ---------------------------------------------------------------------------
# REPRODUCIBILITY. Every historical input any src/ module reads out of the
# HISTORY cache must be a family src/fetch_history.py knows how to download.
# fetch_history was committed so anyone could rebuild the cache and reproduce
# the artifacts byte-for-byte; later work then added five dependencies it
# never learned about (pbp, participation, ftn, advrush, games), with no URL
# recorded anywhere in the repo, which left the C5 BULLISH inputs
# unreproducible by anyone. The guarantee lapsed silently because nothing
# tied the builders' inputs to the fetcher's coverage. This is that tie.
import re as _re2
_fetcher = open(os.path.join(ROOT, "src", "fetch_history.py")).read()
# Match against what the fetcher actually WRITES, not its prose: the
# docstring names every family, so a whole-file substring test passes even
# when the download has been deleted (verified - it did).
_fetch_dests = set()
for _m in _re2.finditer(r'os\.path\.join\(\s*(?:HISTORY|"/tmp/fresh_hist")\s*,\s*f?"([^"]+)"',
                        _fetcher):
    _fetch_dests.add(_m.group(1))
for _m in _re2.finditer(r'^\s*\("([^"]+\.(?:parquet|csv|json))",', _fetcher, _re2.M):
    _fetch_dests.add(_m.group(1))


def _fam_key(fn):
    """spw_{y}.csv and spw_2025.csv both -> spw.csv ; pbp_2025.parquet ->
    pbp.parquet. Collapses the year, whether it is a literal or an
    f-string placeholder, plus the separator it leaves behind."""
    bare = _re2.sub(r"\{[^}]*\}", "", fn)
    bare = _re2.sub(r"_?\d{4}", "", bare)
    return _re2.sub(r"_+(?=\.)", "", bare)


_known = {_fam_key(d) for d in _fetch_dests}
_srcdir = os.path.join(ROOT, "src")
_wanted = set()
for _mod in sorted(os.listdir(_srcdir)):
    if not _mod.endswith(".py") or _mod == "fetch_history.py":
        continue
    _txt = open(os.path.join(_srcdir, _mod)).read()
    for _m in _re2.finditer(r'(?:HISTORY|base\.HISTORY)\s*,\s*f?"([^"]+)"', _txt):
        _wanted.add((_mod, _m.group(1)))
_unknown = [f"{m} reads {fn}" for m, fn in sorted(_wanted)
            if _fam_key(fn) not in _known]
ok(not _unknown,
   "every HISTORY input a builder reads is a family fetch_history can download",
   "; ".join(_unknown[:4]))
ok(len(_wanted) >= 8 and len(_known) >= 8,
   "the reproducibility scan found both the builders' inputs and the fetcher's",
   f"builders want {len(_wanted)} refs, fetcher provides {len(_known)} families")

# One canonical default, imported everywhere. Derive the value from the
# canonical assignment so this guard does not type the path it prohibits.
_history_source = os.path.join(_srcdir, "analyze_recency.py")
_history_tree = ast.parse(open(_history_source).read(), filename=_history_source)
_history_assignment = next(
    node for node in _history_tree.body
    if isinstance(node, ast.Assign) and
    any(isinstance(target, ast.Name) and target.id == "HISTORY"
        for target in node.targets))
_history_default = ast.literal_eval(_history_assignment.value.args[1])
_history_literal_sites = []
for _scope in ("src", "tests"):
    _base = os.path.join(ROOT, _scope)
    for _dirpath, _, _filenames in os.walk(_base):
        for _filename in _filenames:
            if not _filename.endswith(".py"):
                continue
            _path = os.path.join(_dirpath, _filename)
            _tree = ast.parse(open(_path).read(), filename=_path)
            for _node in ast.walk(_tree):
                if isinstance(_node, ast.Constant) and \
                   _node.value == _history_default:
                    _history_literal_sites.append(
                        (os.path.relpath(_path, ROOT), _node.lineno))
_history_literal_sites.sort()
ok(len(_history_literal_sites) == 1 and
   _history_literal_sites[0][0] == "src/analyze_recency.py",
   "the default HISTORY path is defined once and imported everywhere",
   f"found {_history_literal_sites}")

# The live-source refresh must bypass the cache without making a failed fetch
# destructive. Exercise the helper without network so this is behavior, not only
# workflow-text coverage.
_fetch_spec = importlib.util.spec_from_file_location(
    "ytfl_fetch_history", os.path.join(ROOT, "src", "fetch_history.py"))
_fetch_mod = importlib.util.module_from_spec(_fetch_spec)
_fetch_spec.loader.exec_module(_fetch_mod)
with tempfile.TemporaryDirectory() as _td:
    _dest = os.path.join(_td, "games.csv")
    _old = b"old-cache," + b"x" * 1200
    with open(_dest, "wb") as _fh:
        _fh.write(_old)
    with mock.patch.object(_fetch_mod.urllib.request, "urlopen") as _urlopen:
        _kept = _fetch_mod.fetch("https://example.invalid/games.csv", _dest)
    ok(_kept == "have" and not _urlopen.called and open(_dest, "rb").read() == _old,
       "history fetch retains a populated cache unless refresh is explicit")

    _fresh = b"game_id,season,game_type,week," + b"y" * 1200
    _response = mock.Mock()
    _response.read.return_value = _fresh
    with mock.patch.object(_fetch_mod.urllib.request, "urlopen",
                           return_value=_response):
        _updated = _fetch_mod.fetch(
            "https://example.invalid/games.csv", _dest, refresh=True,
            required_prefix=b"game_id,season,game_type,week,")
    ok(_updated == "ok" and open(_dest, "rb").read() == _fresh and
       _response.close.call_count == 1,
       "explicit live refresh atomically replaces the cache and closes the response")

    _read_failure = mock.Mock()
    _read_failure.read.side_effect = RuntimeError("read interrupted")
    with mock.patch.object(_fetch_mod.urllib.request, "urlopen",
                           return_value=_read_failure):
        _failed_read = _fetch_mod.fetch(
            "https://example.invalid/games.csv", _dest, refresh=True,
            required_prefix=b"game_id,season,game_type,week,")
    ok(_failed_read.startswith("FAIL") and
       _read_failure.close.call_count == 1 and
       open(_dest, "rb").read() == _fresh,
       "failed response read closes the socket and preserves the complete cache")

    with mock.patch.object(_fetch_mod.urllib.request, "urlopen",
                           side_effect=RuntimeError("offline")):
        _failed = _fetch_mod.fetch(
            "https://example.invalid/games.csv", _dest, refresh=True,
            required_prefix=b"game_id,season,game_type,week,")
    ok(_failed.startswith("FAIL") and open(_dest, "rb").read() == _fresh,
       "failed live refresh preserves the last complete games file")

# ---------------------------------------------------------------------------
# ENGINE CONTENT LINKAGE. A generation DATE cannot distinguish two builds on
# the same calendar day: that hole once let 14 stale mock tiers pass the guard.
# The strict registered set must match the canonical payload digest. The three
# HISTORY-bound display artifacts also carry lineage, but may deliberately lag
# the 06:00 engine until pages-data repairs them at 08:00; their pages must make
# that mismatch visible instead of presenting old values as current.
sys.path.insert(0, os.path.join(ROOT, "src"))
from engine_lineage import (content_sha256 as _engine_sha,
                            is_valid as _engine_valid,
                            json_content_sha256 as _json_sha)
_eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
_cvs = json.load(open(os.path.join(ROOT, "out", "cvs.json")))
ok(_engine_valid(_eng),
   "engine content digest independently recomputes from the shipped payload")
_same_day = copy.deepcopy(_eng)
_same_day["players"][0]["tier"] = (_same_day["players"][0].get("tier") or 0) + 1
ok(_same_day["generated"] == _eng["generated"] and
   _engine_sha(_same_day) != _eng["content_sha256"],
   "same-day content mutation changes the digest while the date stays equal")

_strict_engine_derivatives = {
    "cvs.json": (_cvs, _cvs),
    "vona_tree_2026.json": (
        json.load(open(os.path.join(D, "vona_tree_2026.json"))), "provenance"),
    "mock_drafts_2026.json": (
        json.load(open(os.path.join(D, "mock_drafts_2026.json"))), "provenance"),
}
for _name, (_artifact, _where) in _strict_engine_derivatives.items():
    _lineage = _artifact if isinstance(_where, dict) else _artifact[_where]
    ok(_lineage.get("engine_content_sha256") == _eng["content_sha256"],
       f"{_name}: exact engine content matches the shipped payload",
       f"artifact says {_lineage.get('engine_content_sha256')}, "
       f"engine says {_eng['content_sha256']}")
_display_lag_paths = ("ceiling_2026.json", "bullish_inputs_2026.json",
                      "bullish_2026.json")
_display_lag = {name: json.load(open(os.path.join(D, name)))
                for name in _display_lag_paths}
for _name, _artifact in _display_lag.items():
    _digest = _artifact.get("provenance", {}).get("engine_content_sha256", "")
    ok(bool(re.fullmatch(r"[0-9a-f]{64}", _digest)),
       f"{_name}: display-only engine lineage is explicit")
ok(_display_lag["bullish_inputs_2026.json"]["provenance"]["engine_content_sha256"] ==
   _display_lag["bullish_2026.json"]["provenance"]["engine_content_sha256"],
   "BULLISH tags and their computed inputs share one engine payload")
_bull_inputs = _display_lag["bullish_inputs_2026.json"]
_source_payloads = {
    "ceiling_2026.json": _display_lag["ceiling_2026.json"],
    "usage_2025.json": json.load(open(os.path.join(D, "usage_2025.json"))),
    "goalline_2025.json": json.load(open(os.path.join(D, "goalline_2025.json"))),
    "depth_charts.json": json.load(open(os.path.join(D, "depth_charts.json"))),
    "crosswalk.json": json.load(open(os.path.join(D, "crosswalk.json"))),
}
_source_manifest = _bull_inputs.get("provenance", {}).get(
    "input_content_sha256", {})
ok(_source_manifest == {name: _json_sha(payload)
                        for name, payload in _source_payloads.items()},
   "BULLISH inputs match every committed source payload they consumed")
ok(_display_lag["bullish_2026.json"]["provenance"].get(
       "inputs_content_sha256") == _json_sha(_bull_inputs),
   "BULLISH tags match the exact computed-input payload they consumed")
_mutated_ceiling = copy.deepcopy(_display_lag["ceiling_2026.json"])
_mutated_ceiling["players"][0]["p90_week"] += 0.1
ok(_mutated_ceiling["provenance"]["engine_content_sha256"] ==
   _display_lag["ceiling_2026.json"]["provenance"]["engine_content_sha256"] and
   _json_sha(_mutated_ceiling) != _source_manifest["ceiling_2026.json"],
   "same-engine ceiling mutation changes the BULLISH source digest")
_mutated_inputs = copy.deepcopy(_bull_inputs)
_mutated_inputs["thresholds"]["wr_tprr"]["p75"] += 0.0001
ok(_mutated_inputs["provenance"]["engine_content_sha256"] ==
   _bull_inputs["provenance"]["engine_content_sha256"] and
   _json_sha(_mutated_inputs) !=
   _display_lag["bullish_2026.json"]["provenance"]["inputs_content_sha256"],
   "same-engine input mutation changes the BULLISH tag-source digest")

_declared_lineage = {"cvs.json"}
for _name in sorted(os.listdir(D)):
    if not _name.endswith(".json"):
        continue
    try:
        _candidate = json.load(open(os.path.join(D, _name)))
    except (OSError, ValueError):
        continue
    if isinstance(_candidate, dict) and isinstance(_candidate.get("provenance"), dict) and \
       "engine_content_sha256" in _candidate["provenance"]:
        _declared_lineage.add(_name)
_registered_lineage = set(_strict_engine_derivatives) | set(_display_lag_paths)
ok(_declared_lineage == _registered_lineage,
   "every artifact declaring engine lineage is in the strict or display registry",
   f"declared {sorted(_declared_lineage)}, registered {sorted(_registered_lineage)}")

_room_src = open(os.path.join(ROOT, "out", "draft_room.html")).read()
_open = '<script id="engine-data" type="application/json">'
_close = '</script><!--engine-data-end-->'
_embedded = json.loads(_room_src.split(_open, 1)[1].split(_close, 1)[0])
ok(_embedded == _eng,
   "draft room embeds the exact engine object that ships beside it")
ok("CVS.engine_content_sha256" in _room_src and
   "cvsDigest !== engineDigest" in _room_src and
   "pick engine is offline until both rebuild together" in _room_src and
   "CVS.engine_generated || CVS.generated" not in _room_src,
   "draft room fails closed on a missing or mismatched CVS digest")
_board_src = open(os.path.join(ROOT, "out", "big_board.html")).read()
_paths_src = open(os.path.join(ROOT, "out", "paths.html")).read()
ok("D.cvs.engine_content_sha256 !== D.eng.content_sha256" in _board_src,
   "big board refuses a CVS payload from a different engine")
ok('fetch("engine_2026.json")' in _paths_src and
   "j.provenance.engine_content_sha256 !== digest" in _paths_src,
   "PATHS fetches the engine and refuses a mismatched tree")
ok(all(_eng["content_sha256"] in
       open(os.path.join(ROOT, "out", "teaser", name)).read()
       for name in ("index.html", "players.html", "draft_room.html",
                    "teams.html", "ff-hub.html")),
   "all five teaser pages name the exact engine content they render")
ok(_eng["content_sha256"] in
   open(os.path.join(ROOT, "out", "decision_cards_2026.md")).read(),
   "decision cards name the exact engine content they render")

# ---------------------------------------------------------------------------
# PRODUCER/PUBLICATION COVERAGE. The exact CVS determinism proof lives in
# test_cvs.py; these checks make sure every automated path that can publish a
# changed input rebuilds the declared consumers and runs their invariant guards.
# This is deliberately enforced at the producer and at the shared Pages boundary,
# rather than patched only into the workflow that most recently failed.
_pages_data_yml = open(os.path.join(ROOT, ".github", "workflows",
                                    "pages-data.yml")).read()
_pages_yml = open(os.path.join(ROOT, ".github", "workflows", "pages.yml")).read()
_draft_refresh_yml = open(os.path.join(ROOT, ".github", "workflows",
                                       "draft-refresh.yml")).read()
_downstream_builders = ("parse_walter.py", "build_cvs.py", "build_archetypes.py",
                        "build_ceiling.py", "build_bullish_inputs.py",
                        "build_bullish.py")
_downstream_guards = ("test_cvs.py", "test_archetypes.py", "test_ceiling.py",
                      "test_bullish.py")
ok(all(f"python3 src/{name}" in _pages_data_yml
       for name in _downstream_builders) and
   all(f"run_gate.sh python3 tests/{name}" in _pages_data_yml
       for name in _downstream_guards),
   "pages-data runs every declared shard-derived builder and invariant guard")
ok("REQUIRE_DISPLAY_ENGINE_MATCH=1 sh tests/run_gate.sh python3 "
   "tests/test_bullish.py" in _pages_data_yml,
   "pages-data proves its 08:00 display-lineage repair reached the current engine")
_producer_order = ("build_pages_data.py", "parse_walter.py", "build_cvs.py",
                   "build_archetypes.py", "build_ceiling.py",
                   "build_bullish_inputs.py",
                   "build_bullish.py")
ok(all(_pages_data_yml.index(_producer_order[i]) <
       _pages_data_yml.index(_producer_order[i + 1])
       for i in range(len(_producer_order) - 1)),
   "pages-data orders refreshed shards before every declared consumer")
ok("actions/cache@v4" in _pages_data_yml and
   "python3 src/fetch_history.py --refresh-live" in _pages_data_yml and
   _fetcher.count("refresh=args.refresh_live") == 1 and
   _re2.search(r'\("games\.csv",\s*fetch\(.{0,300}'
               r'refresh=args\.refresh_live', _fetcher, _re2.S),
   "pages-data retains versioned history but refreshes live games.csv")
ok("git add out/data/ out/cvs.json data/walter/" in _pages_data_yml,
   "pages-data stages shards, Walter resolution, and derived artifacts atomically")
ok("gh workflow run pages.yml --ref main" in _pages_data_yml and
   "actions: write" in _pages_data_yml,
   "pages-data explicitly dispatches Pages after its token-authored push")
_publication_guards = _downstream_guards + ("test_vona.py", "test_mock.py")
ok(all(f"run_gate.sh python3 tests/{name}" in _pages_yml and
       _pages_yml.index(f"run_gate.sh python3 tests/{name}") <
       _pages_yml.index("Assemble site") for name in _publication_guards),
   "Pages runs declared invariant and exact artifact guards before assembly")
ok("gh workflow run pages.yml --ref main" in _draft_refresh_yml and
   "actions: write" in _draft_refresh_yml,
   "draft-refresh explicitly dispatches Pages after its token-authored push")
_engine_i = _draft_refresh_yml.index("python3 src/engine_2026.py")
_vona_i = _draft_refresh_yml.index("python3 src/build_vona_tree.py")
_mock_i = _draft_refresh_yml.index("python3 src/mock_draft.py")
_teaser_i = _draft_refresh_yml.index("python3 src/build_teaser.py")
_draft_gates_i = _draft_refresh_yml.index("python3 tests/test_mock.py")
ok(all(_engine_i < i < _draft_gates_i
       for i in (_vona_i, _mock_i, _teaser_i)),
   "draft-refresh rebuilds VONA, mock, and teaser after their engine input")
ok("156 MB" in _draft_refresh_yml and
   not re.search(r"^\s*run:\s*python3 src/build_(?:ceiling|bullish)",
                 _draft_refresh_yml, re.M),
   "draft-refresh names the HISTORY-bound display exception instead of "
   "adding it to the decision-critical path")

print()
print(f"{len(fails)} FAILURES" if fails else "ALL PASS")
sys.exit(1 if fails else 0)
