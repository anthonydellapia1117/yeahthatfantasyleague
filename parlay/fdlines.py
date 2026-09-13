"""fdlines.py - flatten FanDuel outcomes into priced, linked legs.

Reads every ev_*.json written by fdpull.py. Every leg carries the posted
price, the FanDuel bet-slip link, and the book's no-vig probability. When a
projection file is supplied the model's own mean and hit probability are
attached too; the weekly pipeline runs without one, because fdfinal.py
prices every rung from FanDuel's own fitted ladder instead.
"""
import json, glob, re
import propmath as m, build as B

STAT = {"player_receptions": "receptions", "player_receptions_alternate": "receptions",
        "player_reception_yds": "rec_yards", "player_reception_yds_alternate": "rec_yards",
        "player_pass_yds": "pass_yards", "player_pass_yds_alternate": "pass_yards",
        "player_rush_reception_yds": "rush_rec_yards"}
TEAMS = {"Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL",
         "Buffalo Bills": "BUF", "Carolina Panthers": "CAR", "Chicago Bears": "CHI",
         "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE", "Dallas Cowboys": "DAL",
         "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
         "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX",
         "Kansas City Chiefs": "KC", "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC",
         "Los Angeles Rams": "LAR", "Miami Dolphins": "MIA", "Minnesota Vikings": "MIN",
         "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
         "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT",
         "San Francisco 49ers": "SF", "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB",
         "Tennessee Titans": "TEN", "Washington Commanders": "WAS"}


SUFFIX = re.compile(r"\s+(jr|sr|ii|iii|iv|v)\.?$", re.I)


def norm(n):
    """Lower-case letters only, generational suffix dropped, so 'Marvin Harrison Jr.' matches the engine."""
    return re.sub(r"[^a-z]", "", SUFFIX.sub("", n.strip()).lower())


def abbr(team_name):
    if team_name in TEAMS:
        return TEAMS[team_name]
    return "".join(w[0] for w in team_name.split()).upper()


def load(means_path=None, team_of=None):
    """Return (legs, mains, games). games maps 'AWY@HOM' to commence time and ids."""
    MU = json.load(open(means_path)) if means_path else {}
    mu_by = {norm(k): (k, v) for k, v in MU.items()}
    legs, mains, games = [], {}, {}
    for f in sorted(glob.glob("ev_*.json")):
        d = json.load(open(f))
        if not isinstance(d, dict) or "bookmakers" not in d:
            continue
        away, home = abbr(d["away_team"]), abbr(d["home_team"])
        game = f"{away}@{home}"
        games[game] = {"commence": d.get("commence_time"), "home": home, "away": away,
                       "id": d.get("id"), "home_name": d["home_team"], "away_name": d["away_team"]}
        for bk in d["bookmakers"]:
            if bk.get("key") not in (None, "fanduel"):
                continue
            for mk in bk["markets"]:
                stat = STAT.get(mk["key"])
                if not stat:
                    continue
                alt = mk["key"].endswith("_alternate")
                if not alt:
                    pair = {}
                    for o in mk["outcomes"]:
                        pair.setdefault((o["description"], o["point"]), {})[o["name"]] = o["price"]
                    for (pl, pt), sides in pair.items():
                        if "Over" in sides and "Under" in sides:
                            p_over, hold = m.devig_two_way(sides["Over"], sides["Under"])
                            mains[(norm(pl), stat)] = {"line": pt, "p_over": p_over, "hold": hold,
                                                       "over_price": sides["Over"]}
                for o in mk["outcomes"]:
                    if o["name"] != "Over":
                        continue
                    name, mean = o["description"], None
                    if means_path:
                        key = norm(name)
                        if key not in mu_by:
                            continue
                        name, mu = mu_by[key]
                        if stat not in mu:
                            continue
                        mean = mu[stat]
                    leg = {"player": name, "fd_name": o["description"], "game": game,
                           "team": team_of.get(name, "?") if team_of else "?",
                           "stat": stat, "line": o["point"], "price": o["price"],
                           "decimal": m.american_to_decimal(o["price"]),
                           "implied": m.american_to_implied(o["price"]),
                           "link": o.get("link"), "sid": o.get("sid"), "alt": alt,
                           "mean": mean}
                    if mean is not None:
                        leg["p"] = B.prob(leg)
                        leg["cushion"] = (leg["mean"] - leg["line"]) / leg["mean"]
                    legs.append(leg)
    for l in legs:
        mn = mains.get((norm(l["player"]), l["stat"]))
        h = mn["hold"] if mn else 0.05
        l["q"] = l["implied"] / (1.0 + h)
        if "p" in l:
            l["edge"] = l["p"] / l["q"]
            l["ev1"] = l["p"] * l["decimal"]
    return legs, mains, games


def market_mean(legs_for_player_stat, stat):
    """Fit the mean that best reproduces the book's alt ladder under my distribution.

    Coarse grid then refinement. A ternary search fails here because the
    error surface is flat once the mean is far above every rung.
    """
    pts = [(l["line"], l["q"]) for l in legs_for_player_stat if 0.05 < l["q"] < 0.97]
    if len(pts) < 3:
        return None
    top = max(x for x, _ in pts) * 3.0 + 5.0

    def err(mu):
        return sum((B.prob({"stat": stat, "mean": mu, "line": line}) - q) ** 2 for line, q in pts)
    step = top / 400.0
    grid = [0.5 + i * step for i in range(400)]
    best = min(grid, key=err)
    lo, hi = max(0.3, best - step), best + step
    for _ in range(40):
        m1 = lo + (hi - lo) / 3
        m2 = hi - (hi - lo) / 3
        if err(m1) < err(m2):
            hi = m2
        else:
            lo = m1
    return (lo + hi) / 2
