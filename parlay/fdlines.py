"""fdlines.py - flatten FanDuel outcomes into priced, linked legs.

Every leg carries the posted price, the FanDuel deep link, my projection,
my hit probability, and the edge ratio my_p / book_implied. This is the
first time the engine has real per-leg prices, so edge is measured, not
assumed.
"""
import json, glob, re, math
import propmath as m, build as B

STAT = {"player_receptions":"receptions","player_receptions_alternate":"receptions",
        "player_reception_yds":"rec_yards","player_reception_yds_alternate":"rec_yards",
        "player_pass_yds":"pass_yards","player_pass_yds_alternate":"pass_yards",
        "player_rush_reception_yds":"rush_rec_yards"}
TEAMS = {"Arizona Cardinals":"ARI","Los Angeles Chargers":"LAC","Green Bay Packers":"GB",
         "Minnesota Vikings":"MIN","Miami Dolphins":"MIA","Las Vegas Raiders":"LV",
         "Washington Commanders":"WAS","Philadelphia Eagles":"PHI","Dallas Cowboys":"DAL",
         "New York Giants":"NYG"}

def norm(n):
    return re.sub(r"[^a-z]", "", n.lower())

def load(means_path="means.json", team_of=None):
    MU = json.load(open(means_path))
    mu_by = {norm(k): (k, v) for k, v in MU.items()}
    legs, mains = [], {}
    for f in glob.glob("ev_*.json"):
        d = json.load(open(f))
        if not isinstance(d, dict) or "bookmakers" not in d: continue
        game = f"{TEAMS[d['away_team']]}@{TEAMS[d['home_team']]}"
        for bk in d["bookmakers"]:
            for mk in bk["markets"]:
                stat = STAT.get(mk["key"]);
                if not stat: continue
                alt = mk["key"].endswith("_alternate")
                # collect two-way pairs for de-vig on main lines
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
                    if o["name"] != "Over": continue
                    key = norm(o["description"])
                    if key not in mu_by: continue
                    name, mu = mu_by[key]
                    if stat not in mu: continue
                    leg = {"player": name, "fd_name": o["description"], "game": game,
                           "team": team_of.get(name, "?") if team_of else "?",
                           "stat": stat, "line": o["point"], "price": o["price"],
                           "decimal": m.american_to_decimal(o["price"]),
                           "implied": m.american_to_implied(o["price"]),
                           "link": o.get("link"), "sid": o.get("sid"), "alt": alt,
                           "mean": mu[stat]}
                    leg["p"] = B.prob(leg)
                    leg["cushion"] = (leg["mean"] - leg["line"]) / leg["mean"]
                    legs.append(leg)
    # de-vig: two-way hold where available, else 5% one-sided estimate on alt ladders
    for l in legs:
        mn = mains.get((norm(l["player"]), l["stat"]))
        h = mn["hold"] if mn else 0.05
        l["q"] = l["implied"] / (1.0 + h)          # book's no-vig P(over)
        l["edge"] = l["p"] / l["q"]
        l["ev1"] = l["p"] * l["decimal"]            # EV of this leg alone at posted price
    return legs, mains

def market_mean(legs_for_player_stat, stat):
    """Fit the mean that best reproduces the book's alt ladder under my distribution.

    Coarse grid then refinement. A ternary search fails here because the
    error surface is flat once the mean is far above every rung.
    """
    pts = [(l["line"], l["q"]) for l in legs_for_player_stat if 0.05 < l["q"] < 0.97]
    if len(pts) < 3: return None
    top = max(x for x, _ in pts) * 3.0 + 5.0
    def err(mu):
        return sum((B.prob({"stat": stat, "mean": mu, "line": line}) - q) ** 2 for line, q in pts)
    step = top / 400.0
    grid = [0.5 + i * step for i in range(400)]
    best = min(grid, key=err)
    lo, hi = max(0.3, best - step), best + step
    for _ in range(40):
        m1 = lo + (hi - lo) / 3; m2 = hi - (hi - lo) / 3
        if err(m1) < err(m2): hi = m2
        else: lo = m1
    return (lo + hi) / 2
