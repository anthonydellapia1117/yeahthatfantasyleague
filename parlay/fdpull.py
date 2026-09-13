"""fdpull.py - pull today's FanDuel player-prop ladders with bet-slip links.

Usage:  ODDS_API_KEY=<key> python3 fdpull.py [--dry-run] [--lead 20]

Lists NFL events, keeps those that kick off today (Eastern) at least --lead
minutes from now, and pulls FanDuel receptions, receiving-yard and
passing-yard markets (main and alternate) for each with includeLinks and
includeSids, which is what makes every rung tappable. Six markets cost six
credits per game on The Odds API. The key is read from the environment and
never written to disk or printed. Writes events.json, ev_<id>.json per game,
hdr_<id>.txt response headers and pull_meta.json.
"""
import os, sys, json, glob, subprocess, datetime, zoneinfo

KEY = os.environ.get("ODDS_API_KEY", "").strip()
if not KEY:
    sys.exit("ODDS_API_KEY is not set")
ET = zoneinfo.ZoneInfo("America/New_York")
BASE = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl"
MARKETS = ("player_receptions,player_receptions_alternate,"
           "player_reception_yds,player_reception_yds_alternate,"
           "player_pass_yds,player_pass_yds_alternate")
DRY = "--dry-run" in sys.argv
LEAD = int(sys.argv[sys.argv.index("--lead") + 1]) if "--lead" in sys.argv else 20


def get(url, hdr_path):
    r = subprocess.run(["curl", "-sS", "-o", "-", "-D", hdr_path, "-w", "\n%{http_code}", url],
                       capture_output=True, text=True)
    body, _, code = r.stdout.rpartition("\n")
    if r.returncode != 0 or code != "200":
        sys.exit(f"feed request failed: http {code}, curl exit {r.returncode}")
    return json.loads(body)


def remaining(hdr_path):
    for line in open(hdr_path):
        if line.lower().startswith("x-requests-remaining:"):
            return int(float(line.split(":", 1)[1].strip()))
    return None


now = datetime.datetime.now(ET)
today = now.date()
events = get(f"{BASE}/events?apiKey={KEY}", "hdr_events.txt")
keep = []
for e in events:
    t = datetime.datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")).astimezone(ET)
    if t.date() == today and t >= now + datetime.timedelta(minutes=LEAD):
        e["commence_et"] = t.isoformat()
        keep.append(e)
keep.sort(key=lambda e: e["commence_time"])
print(f"{len(events)} NFL events listed; {len(keep)} kick off today after {now.strftime('%-I:%M %p')} ET")
for e in keep:
    print(f"   {e['commence_et'][11:16]} ET  {e['away_team']} @ {e['home_team']}")
meta = {"pulled_at_et": now.isoformat(), "games": len(keep), "lead_minutes": LEAD,
        "credits_remaining": remaining("hdr_events.txt"), "markets": MARKETS.split(",")}
if not keep:
    json.dump([], open("events.json", "w"))
    json.dump(meta, open("pull_meta.json", "w"), indent=1)
    print("NO GAMES TODAY")
    sys.exit(0)
json.dump(keep, open("events.json", "w"), indent=1)
if DRY:
    print("dry run: events listed, no odds pulled, no credits spent")
    sys.exit(0)
for f in glob.glob("ev_*.json") + glob.glob("hdr_*.txt"):
    if f != "hdr_events.txt":
        os.remove(f)
rem = None
for e in keep:
    url = (f"{BASE}/events/{e['id']}/odds?apiKey={KEY}&regions=us&bookmakers=fanduel"
           f"&markets={MARKETS}&oddsFormat=american&includeLinks=true&includeSids=true")
    d = get(url, f"hdr_{e['id']}.txt")
    json.dump(d, open(f"ev_{e['id']}.json", "w"))
    rem = remaining(f"hdr_{e['id']}.txt")
    n = sum(len(mk["outcomes"]) for bk in d.get("bookmakers", []) for mk in bk["markets"])
    print(f"   pulled {e['away_team']} @ {e['home_team']}: {n} priced outcomes")
meta["credits_remaining"] = rem
json.dump(meta, open("pull_meta.json", "w"), indent=1)
print(f"credits remaining this month: {rem}")
