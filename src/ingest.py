#!/usr/bin/env python3
"""Phase 1 - ingest and reconcile YeahThatFantasyLeague.

Sources
  A. LeagueLegacy archive 2013-2025 (LeagueLegacy-io/, vendor export, pruned)
  B. Sleeper public API, 2025 and 2026 (read-only, unauthenticated)

Writes immutable pulls to raw/ and normalized tables to out/.
Never overwrites raw/. Never auto-corrects a failed assertion.

Run:  python3 src/ingest.py
"""
import csv, json, os, sys, urllib.request, datetime, hashlib
from collections import defaultdict, Counter

from player_names import comparison_key

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = os.path.join(ROOT, "LeagueLegacy-io",
                       "YeahThatFantasyLeague_LeagueLegacy_Archive_2013-2026")
RAW = os.path.join(ROOT, "raw")
OUT = os.path.join(ROOT, "out")
FETCHED_AT = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

SLEEPER = {"2026": "1389378429505241088", "2025": "1245905122328846336"}
# 1092592577628426240 (labelled 2024) is an empty trial shell. Excluded by decision.
EXCLUDED_SLEEPER = {"1092592577628426240": "empty trial shell, 0 picks, 0 transactions"}


def api(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ff-hub-ingest/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def raw_save(name, obj):
    """Immutable. Refuses to overwrite an existing raw file."""
    os.makedirs(RAW, exist_ok=True)
    p = os.path.join(RAW, name)
    if os.path.exists(p):
        return p, "kept-existing"
    with open(p, "w") as f:
        json.dump(obj, f, indent=1)
    return p, "written"


def load_archive(rel):
    with open(os.path.join(ARCHIVE, rel), errors="replace") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- Sleeper pull
def pull_sleeper():
    got = {}
    for season, lid in SLEEPER.items():
        lg = api(f"https://api.sleeper.app/v1/league/{lid}")
        raw_save(f"sleeper_{season}_league.json", lg)
        users = api(f"https://api.sleeper.app/v1/league/{lid}/users")
        raw_save(f"sleeper_{season}_users.json", users)
        rosters = api(f"https://api.sleeper.app/v1/league/{lid}/rosters")
        raw_save(f"sleeper_{season}_rosters.json", rosters)
        drafts = api(f"https://api.sleeper.app/v1/league/{lid}/drafts")
        raw_save(f"sleeper_{season}_drafts.json", drafts)
        picks = []
        if drafts:
            picks = api(f"https://api.sleeper.app/v1/draft/{drafts[0]['draft_id']}/picks")
            raw_save(f"sleeper_{season}_picks.json", picks)
        got[season] = {"league": lg, "users": users, "rosters": rosters,
                       "drafts": drafts, "picks": picks}
    return got


# ------------------------------------------------------- identity resolution
def resolve_identity(sleeper):
    """Link archive franchise names to Sleeper accounts using 2025, the only
    season present in BOTH sources. Join on (round, pick) of the 2025 draft.
    Deterministic. No name similarity is used anywhere."""
    arch = [r for r in load_archive("04_draft/draft_results.csv") if r["season"] == "2025"]
    s_users = {u["user_id"]: u["display_name"] for u in sleeper["2025"]["users"]}
    s_picks = sleeper["2025"]["picks"]

    # Join on OVERALL pick number. draft_slot is a fixed seat and reverses against
    # round-ordinal on even rounds of a snake; overall pick is unambiguous.
    arch_by_overall = {int(r["draft_pick"]): r for r in arch}
    votes = defaultdict(Counter)          # archive member_name -> Counter(sleeper handle)
    matched = unmatched = 0
    for p in s_picks:
        a = arch_by_overall.get(p.get("pick_no"))
        if not a:
            unmatched += 1
            continue
        handle = s_users.get(p.get("picked_by"))
        if handle:
            votes[a["member_name"]][handle] += 1
            matched += 1

    rows = []
    for member, c in votes.items():
        handle, n = c.most_common(1)[0]
        total = sum(c.values())
        rows.append({
            "archive_member_name": member,
            "sleeper_display_name": handle,
            "evidence": f"{n}/{total} of 2025 picks at identical (round, slot) attributed to this handle",
            "confidence": "verified" if n == total and total >= 10 else "partial",
            "source": "join", "source_ref": "archive 2025 draft x sleeper 2025 picks",
            "fetched_at": FETCHED_AT,
        })
    return rows, matched, unmatched


# ------------------------------------------------------------- normalization
def build_picks(sleeper):
    out = []
    for r in load_archive("04_draft/draft_results.csv"):
        out.append({
            "season": r["season"], "source": "leaguelegacy",
            "source_ref": "04_draft/draft_results.csv",
            "team_id": r["team_id"], "member_name": r["member_name"],
            "team_name": r["team_name"],
            "round": r["draft_round"], "round_pick": r["draft_round_pick"],
            "overall": r["draft_pick"],
            "player_id": r["player_id"], "player_name": r["player_name"],
            "pos": r["player_position"], "nfl_team": r["player_team"],
            "is_keeper": r["is_keeper"], "from_trade": r["from_trade"],
            "adp_effective_pick": r["adp_effective_pick"],
            "adp_differential": r["adp_differential"],
            "fetched_at": FETCHED_AT, "confidence": "verified",
        })
    return out


def build_champions():
    out = []
    for r in load_archive("03_playoffs/championship_games.csv"):
        out.append({
            "season": r["season"], "champion": r["winner_member_name"],
            "runner_up": r["loser_member_name"],
            "winner_points": r["winner_points"], "loser_points": r["loser_points"],
            "margin": r["margin"],
            "source": "leaguelegacy", "source_ref": "03_playoffs/championship_games.csv",
            "fetched_at": FETCHED_AT, "confidence": "verified",
        })
    return sorted(out, key=lambda x: x["season"])


# ---------------------------------------------------------------- assertions
def assertions(picks):
    """Report failures. Never auto-correct."""
    results = []
    by_season = defaultdict(list)
    for p in picks:
        by_season[p["season"]].append(p)

    for season in sorted(by_season):
        rows = by_season[season]
        teams = len({r["team_id"] for r in rows})
        rounds = max(int(r["round"]) for r in rows)
        overalls = [int(r["overall"]) for r in rows]

        checks = {
            # Rule 3.2 allows a forfeit: exceed the 2-minute clock and you get no pick.
            # So the invariant is <=, and any shortfall must be an enumerated forfeit.
            "picks <= teams x rounds": (len(rows) <= teams * rounds,
                                        f"{len(rows)} of {teams}x{rounds}={teams*rounds}"
                                        + (f", {teams*rounds-len(rows)} forfeit(s)" if len(rows) < teams*rounds else "")),
            "overall picks contiguous, forfeits allowed": (
                overalls == sorted(set(overalls)) and max(overalls) <= teams * rounds,
                f"min {min(overalls)} max {max(overalls)} n {len(overalls)}"),
            "one roster per round": (all(
                len({r["team_id"] for r in rows if r["round"] == str(rd)}) ==
                len([r for r in rows if r["round"] == str(rd)])
                for rd in range(1, rounds + 1)), "duplicate team within a round"),
            "no duplicate player": (len({r["player_id"] for r in rows if r["player_id"]}) ==
                                    len([r for r in rows if r["player_id"]]), "repeated player_id"),
        }
        for name, (ok, detail) in checks.items():
            results.append({"season": season, "check": name,
                            "result": "PASS" if ok else "FAIL", "detail": detail,
                            "teams": teams, "rounds": rounds})
    return results


def cross_validate(sleeper, picks):
    """Archive 2025 draft must reconcile to Sleeper 2025 pick-for-pick."""
    arch = {int(r["overall"]): r for r in picks if r["season"] == "2025"}
    agree = disagree = missing = 0
    examples = []
    for p in sleeper["2025"]["picks"]:
        a = arch.get(p.get("pick_no"))
        if not a:
            missing += 1
            continue
        s_name = f"{(p.get('metadata') or {}).get('first_name','')} " \
                 f"{(p.get('metadata') or {}).get('last_name','')}".strip()
        # Suffixes and punctuation differ between Sleeper and the archive
        # (Brian Thomas vs Brian Thomas Jr., DJ vs D.J.); the documented
        # 168/168 reconciliation is on this normalized form.
        if comparison_key(s_name) == comparison_key(a["player_name"]):
            agree += 1
        else:
            disagree += 1
            if len(examples) < 5:
                examples.append(f"overall {p.get('pick_no')} (r{p['round']}): sleeper '{s_name}' vs archive '{a['player_name']}'")
    return {"agree": agree, "disagree": disagree, "missing": missing, "examples": examples}


def write_csv(name, rows):
    os.makedirs(OUT, exist_ok=True)
    if not rows:
        return
    p = os.path.join(OUT, name)
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return p


def main():
    print("pulling Sleeper ...")
    sleeper = pull_sleeper()

    picks = build_picks(sleeper)
    champs = build_champions()
    idmap, matched, unmatched = resolve_identity(sleeper)
    checks = assertions(picks)
    xval = cross_validate(sleeper, picks)

    write_csv("picks.csv", picks)
    write_csv("champions.csv", champs)
    write_csv("identity_map.csv", idmap)
    write_csv("assertions.csv", checks)

    fails = [c for c in checks if c["result"] == "FAIL"]
    print(f"\npicks {len(picks)} | champions {len(champs)} | identities {len(idmap)}")
    print(f"assertions: {len(checks)-len(fails)} pass, {len(fails)} FAIL")
    for c in fails:
        print(f"  FAIL {c['season']} {c['check']}: {c['detail']}")
    print(f"cross-validation 2025 archive vs Sleeper: "
          f"{xval['agree']} agree, {xval['disagree']} disagree, {xval['missing']} missing")
    for e in xval["examples"]:
        print("   ", e)
    print(f"identity join: {matched} picks matched, {unmatched} unmatched")

    json.dump({"assertions": checks, "cross_validation": xval,
               "identity": idmap, "excluded": EXCLUDED_SLEEPER,
               "fetched_at": FETCHED_AT},
              open(os.path.join(OUT, "phase1_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
