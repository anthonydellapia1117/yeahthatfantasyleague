#!/usr/bin/env python3
"""Pull YeahThatFantasyLeague history from Yahoo via yfpy, and Sleeper via its public API.

Yahoo needs OAuth. Credentials come from .env and are NEVER hardcoded, logged, or committed.
Game keys are queried per season with get_game_key_by_season, never hardcoded.

Setup, once:
  1. Register an app at https://developer.yahoo.com/apps/  (see README_YAHOO.md)
  2. cp .env.example .env  and fill in the two values
  3. .venv-yahoo/bin/python src/fetch_yahoo.py --season 2024
     The first run opens a browser. Approve, paste the verification code.

Then:
  .venv-yahoo/bin/python src/fetch_yahoo.py --all
"""
import argparse, json, os, sys, datetime, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw")

# Owner-supplied 2026-08-11. Yahoo league_id per season, NFL.
YAHOO = {
    2024: "42081",  2023: "243817", 2022: "367036", 2021: "428007",
    2020: "275203", 2019: "222624", 2018: "562266", 2017: "351067",
    2016: "827116", 2015: "902076", 2014: "605315", 2013: "777575",
}
# League renamed twice. Match on id, never on name.
YAHOO_NAMES = {
    2013: "Rondros Fantasy League",
    2014: "#BunchaFaggetsFantasyLeague", 2015: "#BunchaFaggetsFantasyLeague",
    2016: "#BunchaFaggetsFantasyLeague", 2017: "#BunchaFaggetsFantasyLeague",
    2018: "#BunchaFaggetsFantasyLeague",
    2019: "#TotallyHeterosexualMensFFL", 2020: "#TotallyHeterosexualMensFFL",
    2021: "#TotallyHeterosexualMensFFL", 2022: "#TotallyHeterosexualMensFFL",
    2023: "#TotallyHeterosexualMensFFL", 2024: "#TotallyHeterosexualMensFFL",
}
SLEEPER = {2026: "1389378429505241088", 2025: "1245905122328846336"}


def outdir(*parts):
    p = os.path.join(RAW, *parts)
    os.makedirs(p, exist_ok=True)
    return p


def save(path, name, obj):
    """Immutable. Never overwrites an existing raw pull."""
    f = os.path.join(path, name)
    if os.path.exists(f):
        print(f"    kept  {name}")
        return
    with open(f, "w") as fh:
        json.dump(obj, fh, indent=1, default=str)
    print(f"    wrote {name}")


def creds():
    """Read from .env. Never printed, never returned to a caller that logs."""
    env = os.path.join(ROOT, ".env")
    vals = {}
    if os.path.exists(env):
        for line in open(env):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip().strip('"').strip("'")
    key = os.environ.get("YAHOO_CONSUMER_KEY") or vals.get("YAHOO_CONSUMER_KEY")
    sec = os.environ.get("YAHOO_CONSUMER_SECRET") or vals.get("YAHOO_CONSUMER_SECRET")
    if not key or not sec:
        print("MISSING CREDENTIALS. Yahoo needs an OAuth app.\n"
              "  1. Create one at https://developer.yahoo.com/apps/\n"
              "     Application Type: Web Application\n"
              "     Redirect URI:     https://localhost:8080\n"
              "     API Permissions:  Fantasy Sports, Read\n"
              "  2. cp .env.example .env\n"
              "  3. Put the Consumer Key and Consumer Secret in .env\n"
              "  4. Re-run. A browser opens once; approve and paste the code.\n"
              "See README_YAHOO.md. Nothing was fetched.", file=sys.stderr)
        sys.exit(2)
    return key, sec


def fetch_yahoo(season, key, sec):
    from yfpy.query import YahooFantasySportsQuery
    league_id = YAHOO[season]
    d = outdir("yahoo", str(season))
    # env_file_location must be set or yfpy saves no token and re-prompts every run
    from pathlib import Path
    q = YahooFantasySportsQuery(
        league_id=league_id, game_code="nfl",
        yahoo_consumer_key=key, yahoo_consumer_secret=sec,
        env_file_location=Path(ROOT), save_token_data_to_env_file=True,
    )
    # never hardcode the game key
    q.game_id = q.get_game_key_by_season(season)
    print(f"  {season}  league {league_id}  game_key {q.game_id}  ({YAHOO_NAMES[season]})")

    jobs = [
        ("league_metadata.json",  q.get_league_metadata),
        ("league_settings.json",  q.get_league_settings),
        ("standings.json",        q.get_league_standings),
        ("teams.json",            q.get_league_teams),
        ("draft_results.json",    q.get_league_draft_results),
        ("transactions.json",     q.get_league_transactions),
        ("scoreboard.json",       q.get_league_scoreboard_by_week),
    ]
    for name, fn in jobs:
        try:
            save(d, name, fn())
        except Exception as e:
            print(f"    FAIL  {name}: {type(e).__name__}: {e}", file=sys.stderr)

    # weekly detail: matchups and per-team rosters. This is what closes the bonus gap.
    try:
        meta = q.get_league_metadata()
        end = int(getattr(meta, "end_week", 17) or 17)
    except Exception:
        end = 17
    for wk in range(1, end + 1):
        try:
            save(d, f"matchups_wk{wk:02d}.json", q.get_league_matchups_by_week(wk))
        except Exception as e:
            print(f"    FAIL  matchups_wk{wk:02d}: {e}", file=sys.stderr)
    try:
        teams = q.get_league_teams()
        for t in teams:
            tid = getattr(t, "team_id", None)
            if tid is None:
                continue
            for wk in range(1, end + 1):
                try:
                    save(d, f"roster_t{tid}_wk{wk:02d}.json",
                         q.get_team_roster_player_stats_by_week(tid, wk))
                except Exception:
                    pass
    except Exception as e:
        print(f"    FAIL  rosters: {e}", file=sys.stderr)


def fetch_sleeper(season):
    lid = SLEEPER[season]
    d = outdir("sleeper", str(season))
    def api(u):
        r = urllib.request.Request(u, headers={"User-Agent": "ff-hub/1.0"})
        with urllib.request.urlopen(r, timeout=30) as resp:
            return json.load(resp)
    base = f"https://api.sleeper.app/v1/league/{lid}"
    save(d, "league.json", api(base))
    save(d, "users.json", api(base + "/users"))
    save(d, "rosters.json", api(base + "/rosters"))
    drafts = api(base + "/drafts")
    save(d, "drafts.json", drafts)
    if drafts:
        save(d, "picks.json", api(f"https://api.sleeper.app/v1/draft/{drafts[0]['draft_id']}/picks"))
    for wk in range(1, 19):
        try:
            save(d, f"matchups_wk{wk:02d}.json", api(f"{base}/matchups/{wk}"))
        except Exception:
            pass
    try:
        save(d, "transactions.json",
             [t for wk in range(1, 19) for t in api(f"{base}/transactions/{wk}")])
    except Exception as e:
        print(f"    FAIL transactions: {e}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, help="one season")
    ap.add_argument("--all", action="store_true", help="every season, both platforms")
    ap.add_argument("--sleeper-only", action="store_true", help="no Yahoo, no credentials needed")
    a = ap.parse_args()

    if a.sleeper_only or (a.season in SLEEPER):
        for s in ([a.season] if a.season in SLEEPER else sorted(SLEEPER)):
            print(f"sleeper {s}")
            fetch_sleeper(s)
        if not a.all:
            return

    seasons = sorted(YAHOO) if (a.all or not a.season) else [a.season]
    seasons = [s for s in seasons if s in YAHOO]
    if not seasons:
        return
    key, sec = creds()
    print(f"yahoo: {len(seasons)} season(s)")
    for s in seasons:
        fetch_yahoo(s, key, sec)
    if a.all:
        for s in sorted(SLEEPER):
            print(f"sleeper {s}")
            fetch_sleeper(s)


if __name__ == "__main__":
    main()
