"""gamelogs.py - build per-player per-game usage logs from ESPN box scores.

Usage:  python3 gamelogs.py 2025-09-04 2026-01-05 data/gamelogs_2025.json
        python3 gamelogs.py 2026-09-10 2026-09-14 data/gamelogs_2026.json

Walks every Eastern date in the range, lists that day's games, pulls each
final box score and appends one row per player: date, game, team, targets,
receptions, receiving yards, carries, rushing yards, pass attempts, passing
yards, and the team's pass attempts. Re-running merges into the existing
file and skips games already logged, so the weekly refresh is cheap.
"""
import datetime, json, os, sys, time
import espn

start, end, path = sys.argv[1], sys.argv[2], sys.argv[3]
logs = json.load(open(path)) if os.path.exists(path) else {"games": {}, "rows": []}
have = set(logs["games"])
d0 = datetime.date.fromisoformat(start)
d1 = datetime.date.fromisoformat(end)
day = d0
new = 0
while day <= d1:
    try:
        games = espn.scoreboard(day.strftime("%Y%m%d"))
    except RuntimeError as e:
        print(e); games = []
    for g in games:
        if g["id"] in have or g["status"] != "STATUS_FINAL":
            continue
        try:
            rows = espn.player_lines(espn.summary(g["id"]))
        except RuntimeError as e:
            print(e); continue
        for r in rows:
            r.update({"date": day.isoformat(), "game": g["game"], "event": g["id"]})
            logs["rows"].append(r)
        logs["games"][g["id"]] = {"date": day.isoformat(), "game": g["game"]}
        have.add(g["id"]); new += 1
        time.sleep(0.3)
    day += datetime.timedelta(days=1)
os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
json.dump(logs, open(path, "w"))
print(f"{new} new games logged; {len(logs['games'])} games, {len(logs['rows'])} player rows in {path}")
