"""fdgrade.py - grade a saved card against ESPN box scores and log the result.

Usage:  python3 fdgrade.py cards/2026-09-13.json

Writes results/<date>.json with every leg's actual number and hit flag, and
prints the scorecard plus running calibration across every results file:
realised hit rate against the probabilities the card was built on, by stat
type and by probability bucket. That record is what tunes the model.
"""
import glob, json, os, sys
import espn

path = sys.argv[1]
card = json.load(open(path))
date = card["date"]
ymd = date.replace("-", "")
games = {g["game"]: g for g in espn.scoreboard(ymd)}
lines = {}
for g in games.values():
    if g["status"] != "STATUS_FINAL":
        continue
    for r in espn.player_lines(espn.summary(g["id"])):
        lines[(r["team"], espn.norm(r["player"]))] = r
        lines.setdefault(espn.norm(r["player"]), r)          # name-only fallback
out = {"date": date, "tickets": []}
tot = hit = 0
for t in card["tickets"]:
    legs = []
    for l in t["legs"]:
        g = games.get(l["game"])
        r = lines.get(espn.norm(l["player"]))
        if g is None or g["status"] != "STATUS_FINAL":
            res = {"actual": None, "hit": None, "note": "game not final"}
        elif r is None:
            res = {"actual": 0, "hit": False, "note": "no stat line (inactive or zero)"}
        else:
            act = r.get(l["stat"], 0)
            usage = f"{r['rec']}/{r['tgt']} tgt" if l["stat"] in ("receptions", "rec_yards") else (
                f"{r['carries']} carries" if l["stat"] == "rush_yards" else f"{r['pass_att']} att")
            res = {"actual": act, "hit": act > l["line"], "note": usage}
        legs.append({**l, **res})
        if res["hit"] is not None:
            tot += 1
            hit += res["hit"]
    n_hit = sum(1 for x in legs if x["hit"])
    won = all(x["hit"] for x in legs)
    out["tickets"].append({"name": t["name"], "band": t["band"],
                           "page_price": t.get("page_price"), "slip_price": t.get("slip_price") or t.get("page_price"),
                           "legs": legs, "legs_hit": n_hit, "won": won,
                           "stake": card.get("stake_per_ticket", 25)})
    print(f"Ticket {t['name']} ({t['band']}) {'WON' if won else 'lost'}: {n_hit}/{len(legs)} legs")
    for x in legs:
        flag = "HIT " if x["hit"] else ("miss" if x["hit"] is False else "n/a ")
        print(f"   {flag} {x['player']:<20}{x['stat']:<11}over {x['line']:<6} actual {str(x['actual']):>4}   {x['note']}")
os.makedirs("results", exist_ok=True)
json.dump(out, open(f"results/{date}.json", "w"), indent=1)
print(f"\n{date}: {hit}/{tot} legs hit; results/{date}.json written")

# running calibration across every logged week
allr = [json.load(open(f)) for f in sorted(glob.glob("results/*.json"))]
legs = [l for r in allr for t in r["tickets"] for l in t["legs"] if l["hit"] is not None]
if legs:
    by = {}
    for l in legs:
        by.setdefault(l["stat"], []).append(l["hit"])
    print(f"\nrunning record over {len(allr)} week(s): {sum(l['hit'] for l in legs)}/{len(legs)} legs "
          f"({100*sum(l['hit'] for l in legs)/len(legs):.0f}%), tickets won "
          f"{sum(t['won'] for r in allr for t in r['tickets'])}/{sum(len(r['tickets']) for r in allr)}")
    for st, hs in sorted(by.items()):
        print(f"   {st:<12} {sum(hs)}/{len(hs)}")
    withp = [l for l in legs if "p" in l]
    if withp:
        print(f"   model said {100*sum(l['p'] for l in withp)/len(withp):.0f}% per leg, realised {100*sum(l['hit'] for l in withp)/len(withp):.0f}%")
