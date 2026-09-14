"""espn.py - box scores and game logs from ESPN's public site API (no key).

scoreboard(date) lists that Eastern day's games; summary(event_id) returns the
box score. player_lines(summary) flattens it to one row per player with
targets, receptions, receiving yards, carries, rushing yards, passing
attempts and yards, plus the team's pass attempts for share calculations.
"""
import json, re, subprocess, time

BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
ABBR = {"WSH": "WAS", "JAC": "JAX", "LA": "LAR"}          # ESPN codes that differ from the engine's
SUFFIX = re.compile(r"\s+(jr|sr|ii|iii|iv|v)\.?$", re.I)


def norm(n):
    return re.sub(r"[^a-z]", "", SUFFIX.sub("", n.strip()).lower())


def get(url, retries=3):
    for i in range(retries):
        r = subprocess.run(["curl", "-sS", "--max-time", "30", url], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip().startswith("{"):
            return json.loads(r.stdout)
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"espn fetch failed: {url}")


def scoreboard(yyyymmdd):
    d = get(f"{BASE}/scoreboard?dates={yyyymmdd}")
    out = []
    for e in d.get("events", []):
        c = e["competitions"][0]
        home = away = None
        for t in c["competitors"]:
            code = ABBR.get(t["team"]["abbreviation"], t["team"]["abbreviation"])
            if t["homeAway"] == "home":
                home = (code, t.get("score"))
            else:
                away = (code, t.get("score"))
        out.append({"id": e["id"], "date": e["date"], "status": e["status"]["type"]["name"],
                    "home": home[0], "away": away[0], "home_score": home[1], "away_score": away[1],
                    "game": f"{away[0]}@{home[0]}"})
    return out


def summary(event_id):
    return get(f"{BASE}/summary?event={event_id}")


def player_lines(summ):
    """One row per player who recorded a stat, with team pass attempts attached."""
    rows = {}
    team_att = {}
    for team in summ["boxscore"]["players"]:
        tm = ABBR.get(team["team"]["abbreviation"], team["team"]["abbreviation"])
        for cat in team["statistics"]:
            keys = cat["keys"]
            for a in cat["athletes"]:
                v = dict(zip(keys, a["stats"]))
                name = a["athlete"]["displayName"]
                r = rows.setdefault((tm, norm(name)), {"team": tm, "player": name, "tgt": 0, "rec": 0, "rec_yards": 0,
                                                        "carries": 0, "rush_yards": 0, "pass_att": 0, "pass_yards": 0})
                if cat["name"] == "receiving":
                    r["tgt"] = int(v.get("receivingTargets", 0) or 0)
                    r["rec"] = int(v.get("receptions", 0) or 0)
                    r["rec_yards"] = int(v.get("receivingYards", 0) or 0)
                elif cat["name"] == "rushing":
                    r["carries"] = int(v.get("rushingAttempts", 0) or 0)
                    r["rush_yards"] = int(v.get("rushingYards", 0) or 0)
                elif cat["name"] == "passing":
                    ca = v.get("completions/passingAttempts", "0/0")
                    r["pass_att"] = int(ca.split("/")[1]) if "/" in ca else 0
                    r["pass_yards"] = int(v.get("passingYards", 0) or 0)
                    team_att[tm] = team_att.get(tm, 0) + r["pass_att"]
    out = []
    for r in rows.values():
        if r["tgt"] + r["carries"] + r["pass_att"] == 0:
            continue                                   # defenders, kickers, returners: no usage to track
        r["team_pass_att"] = team_att.get(r["team"], 0)
        r["receptions"] = r["rec"]
        out.append(r)
    return out
