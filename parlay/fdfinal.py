"""fdfinal.py - price legs from FanDuel's own ladder, then build the three tickets.

Markets used: receptions, receiving yards and passing yards for receivers,
tight ends and quarterbacks; rushing yards for running backs. Quarterback
rushing and running-back receiving ladders are excluded as too thin.

For each player and stat, the alternate ladder is a set of (line, implied)
points. Fitting a two-parameter distribution to it recovers the book's own
view of mean and spread. Each rung's hit probability is then read from that
fitted curve, so p is the market's number, not mine. The only thing a rung
can then have going for it is being priced below the book's own smooth
curve, which is a real and model-free inefficiency.

Ticket EV is computed with NO correlation credit, because FanDuel groups
same-game legs into an SGP and strips it. That makes the emailed EV a
floor, not a promise.

Inputs:  ev_*.json (fdpull.py), fdcal.json (fdcal.py), optional exclude.txt
         (one player per line, questionable or worse on the injury report),
         ../out/engine_2026.json for positions and teams.
Outputs: fdfit.json, fdlegs4.json, fdcard.json, fdsummary.json
"""
import json, os, random, re, statistics, sys
from collections import defaultdict
import datetime, zoneinfo
import propmath as m, build as B, fdlines, usage
from fdlines import norm

ENGINE = "../out/engine_2026.json"
STAKE = 25
# A rung below these lines is a one-catch prop whose price is mostly margin.
LINE_FLOOR = {"rec_yards": 9.5, "receptions": 2.5, "pass_yards": 149.5, "rush_yards": 19.5, "rush_rec_yards": 19.5}
# Rungs needed before a fitted ladder is trusted.
MIN_RUNGS = {"receptions": 4}
DEFAULT_MIN_RUNGS = 5
# A rung may be credited at most this far above its own de-vigged price, so a
# poor fit cannot be harvested as edge (the failure mode of the first build).
P_CAP = 0.02


CAL = json.load(open("fdcal.json"))
ALT = CAL["alt_margin_mult"]
legs, mains, games = fdlines.load()
if not os.path.exists(ENGINE):
    sys.exit(f"cannot build: {ENGINE} is missing; positions and teams come from it")
POS, TEAM = {}, {}
for p in json.load(open(ENGINE))["players"]:
    POS[norm(p["name"])] = p["pos"]
    TEAM[norm(p["name"])] = p["team"]
EXCL = set()
if os.path.exists("exclude.txt"):
    EXCL = {norm(x) for x in open("exclude.txt").read().splitlines()
            if x.strip() and not x.startswith("#")}

grp = defaultdict(list)
excluded, unknown_pos = set(), set()
for l in legs:
    if l["alt"]:
        l["q"] = l["implied"] / (1.0 + ALT)
    k = norm(l["player"])
    if k in EXCL:
        excluded.add(l["player"])
        continue
    pos = POS.get(k)
    if pos is None:
        unknown_pos.add(l["player"])
        pos = "QB" if l["stat"] == "pass_yards" else "WR"
    if pos in ("K", "DEF"):
        continue
    if l["stat"] in ("rush_yards", "rush_rec_yards"):
        if pos != "RB":
            continue                               # rushing ladders only for backs; quarterback rushing stays excluded
    elif pos == "RB":
        continue                                   # backs only on rushing ladders; their receiving ladders are thin
    elif k not in POS and l["stat"] != "pass_yards":
        continue                                   # receivers outside the season engine: usage too thin to trust
    l["pos"] = pos
    g = games[l["game"]]
    t = TEAM.get(k, "?")
    l["team"] = t if t in (g["home"], g["away"]) else "?"
    grp[(l["player"], l["stat"])].append(l)


def fit(ls, stat):
    # One observation per line. Where the main line and an alternate rung sit
    # on the same number, keep the main line: its two-way de-vig is the better
    # read of the book's curve. Depth is counted on distinct lines.
    by_line = {}
    for l in sorted(ls, key=lambda x: x["alt"]):
        if 0.04 < l["q"] < 0.97 and l["line"] not in by_line:
            by_line[l["line"]] = l["q"]
    pts = sorted(by_line.items())
    if len(pts) < 3:
        return None
    top = max(x for x, _ in pts) * 2.5 + 5
    count = stat == "receptions"
    best = None
    grid_m = [0.5 + i * (top / 120.0) for i in range(120)]
    grid_s = ([1.1, 1.25, 1.45, 1.7, 2.0, 2.4] if count
              else [0.35, 0.42, 0.5, 0.55, 0.62, 0.7, 0.8, 0.9, 1.0])

    def pr(mu, line, sp):
        return m.prob_over_count(mu, line, sp) if count else m.prob_over_continuous(mu, line, sp)
    for mu in grid_m:
        for sp in grid_s:
            e = sum((pr(mu, line, sp) - q) ** 2 for line, q in pts)
            if best is None or e < best[0]:
                best = (e, mu, sp)
    e, mu, sp = best
    lo, hi = max(0.3, mu - top / 120), mu + top / 120
    for _ in range(30):
        m1 = lo + (hi - lo) / 3
        m2 = hi - (hi - lo) / 3
        if sum((pr(m1, line, sp) - q) ** 2 for line, q in pts) < sum((pr(m2, line, sp) - q) ** 2 for line, q in pts):
            hi = m2
        else:
            lo = m1
    return (lo + hi) / 2, sp, len(pts)


FIT, out = {}, []
for (pl, st), ls in grp.items():
    f = fit(ls, st)
    if f is None:
        continue
    mu, sp, n = f
    if n < MIN_RUNGS.get(st, DEFAULT_MIN_RUNGS):
        continue
    FIT[f"{pl}|{st}"] = {"mean": mu, "spread": sp, "n": n}
    count = st == "receptions"
    for l in ls:
        if l["line"] < LINE_FLOOR.get(st, 0):
            continue
        p_fit = m.prob_over_count(mu, l["line"], sp) if count else m.prob_over_continuous(mu, l["line"], sp)
        p = min(p_fit, l["q"] + P_CAP)
        d = dict(l)
        d["fd_mean"], d["fd_spread"], d["p"], d["p_fit"] = mu, sp, p, p_fit
        d["resid"] = l["q"] - p_fit                 # negative = rung cheap vs its own ladder
        d["ev1"] = p * l["decimal"]
        d["cushion"] = (mu - l["line"]) / mu
        d["kind"] = {"pass_yards": "QBpass", "rush_yards": "RBrush", "rush_rec_yards": "RBrush"}.get(
            st, "TErec" if l["pos"] == "TE" else "WRrec")
        out.append(d)
# Usage second opinion: the market's mean says nothing about how stable a
# player's role is. Every ticket-killing miss in week one was a usage failure.
U = None
try:
    U = usage.Usage()
except Exception as e:
    print(f"usage logs unavailable ({e}); market probabilities only")
fragile, no_history, kept = [], set(), []
if U is not None and U.n_rows:
    for d in out:
        st = d["stat"]
        if st not in ("receptions", "rec_yards", "rush_yards"):
            kept.append(d)
            continue
        g = games[d["game"]]
        teams = [d["team"]] if d["team"] in (g["home"], g["away"]) else [g["away"], g["home"]]
        prof = None
        for tm in teams:
            prof = U.profile(d["player"], tm)
            if prof:
                d["team"] = tm
                break
        if prof is None:
            team_played = any(dt >= usage.SEASON_START for (dt, _) in U.team_att.get(d["team"] if d["team"] in (g["home"], g["away"]) else teams[0], {}))
            if team_played:
                d["fragile"] = True
                d["usage"] = "no current-season usage on a team that has played"
                fragile.append(d)
                continue
            d["usage"] = "no usage history on this team"
            no_history.add(d["player"])
            kept.append(d)
            continue
        pu = U.p_over(prof, st, d["line"])
        d["p_market"], d["p_usage"] = d["p"], pu
        d["exp_tgt"], d["exp_carries"], d["usage_games"] = prof["exp_tgt"], prof["exp_carries"], prof["games"]
        d["p"] = min(d["p"], pu)
        d["ev1"] = d["p"] * d["decimal"]
        if U.fragile(prof, st, d["line"]):
            d["fragile"] = True
            fragile.append(d)
            continue
        kept.append(d)
    out = kept
    print(f"usage check: {len(fragile)} fragile rungs dropped, {len(no_history)} players without usage history kept on market numbers")
json.dump(FIT, open("fdfit.json", "w"), indent=1)
json.dump(out, open("fdlegs4.json", "w"))
print(f"{len(games)} games | {len(legs)} rungs loaded | {len(FIT)} ladders fitted | {len(out)} rungs priced from FanDuel's own curve")
if excluded:
    print(f"excluded by injury list: {', '.join(sorted(excluded))}")
if unknown_pos:
    print(f"not in season engine (treated by market): {', '.join(sorted(unknown_pos))}")
for st, lab in (("rec_yards", "rec yards CV"), ("pass_yards", "pass yards CV"), ("receptions", "receptions dispersion")):
    v = [f["spread"] for k, f in FIT.items() if k.endswith("|" + st)]
    if v:
        print(f"   FanDuel-implied {lab:<22} median {statistics.median(v):.2f}   range {min(v):.2f}-{max(v):.2f}   n={len(v)}")


def ok(ls, cap):
    pl, g = set(), {}
    for l in ls:
        if l["player"] in pl:
            return False
        pl.add(l["player"])
        g[l["game"]] = g.get(l["game"], 0) + 1
        if g[l["game"]] > cap:
            return False
    return True


def price(ls):
    d = 1.0
    for l in ls:
        d *= l["decimal"]
    return d


# Standing gates. They never relax: a small slate relaxes only the legs-per-game
# cap, one step at a time, and a band that still cannot fill stays empty.
#
# Structure: fewest legs that reach the band. FanDuel's margin is about 7
# percent on every rung, flat across the price ladder (measured 2026-09-13),
# so each extra leg costs the ticket 7 percent of its true hit rate at the
# same payout. At +1000 a 4-leg ticket keeps 76 cents of true value per
# dollar; an 8-leg ticket keeps 58. The objective is the highest joint
# probability inside the band, which is what "most likely to cash" means.
LONG = "--long" in sys.argv        # the original many-likely-legs profile, kept for comparison
if LONG:
    P_MIN, P_MAX, CUSHION_MIN = 0.62, 0.95, 0.25
    BANDS = [("LOW", 250, 499, (3, 4, 5, 6), 160000, -800, (2, 3)),
             ("MED", 500, 999, (5, 6, 7, 8), 220000, -800, (2, 3)),
             ("HIGH", 1000, 2600, (8, 9, 10, 11), 320000, -800, (3, 4))]
else:
    P_MIN, P_MAX, CUSHION_MIN = 0.45, 0.95, 0.10
    # band, min odds, max odds, leg counts to try, iterations, price floor, legs-per-game ladder
    BANDS = [("LOW", 250, 499, (2, 3, 4), 160000, -800, (2, 3)),
             ("MED", 500, 999, (3, 4, 5), 220000, -800, (2, 3)),
             ("HIGH", 1000, 2600, (4, 5, 6), 320000, -800, (2, 3))]
rng = random.Random(2113)
chosen, used = [], set()
for band, lo, hi, ns, iters, floor, caps in BANDS:
    best, relax = None, 0
    avail = [l for l in out if l["cushion"] >= CUSHION_MIN and P_MIN <= l["p"] <= P_MAX and l["link"]
             and l["price"] >= floor and l["player"] not in used]
    # A k-leg ticket lands in the band only when every leg's price sits near the
    # band's k-th root, so each leg count searches its own price window rather
    # than the whole pool. Without this a random search almost never finds the
    # short tickets that carry the least margin.
    lo_dec, hi_dec = m.american_to_decimal(lo), m.american_to_decimal(hi)
    for cap in caps:
        for k in ns:
            t_lo, t_hi = lo_dec ** (1.0 / k) / 1.45, hi_dec ** (1.0 / k) * 1.45
            window = [l for l in avail if t_lo <= l["decimal"] <= t_hi]
            if k > len(window):
                continue
            seen = set()
            for _ in range(iters // len(ns)):
                idx = tuple(sorted(rng.sample(range(len(window)), k)))
                if idx in seen:
                    continue
                seen.add(idx)
                ls = [window[i] for i in idx]
                if not ok(ls, cap):
                    continue
                d = price(ls)
                a = m.decimal_to_american(d)
                if a < lo or a > hi:
                    continue
                pind = 1.0
                for l in ls:
                    pind *= l["p"]
                if best is None or pind > best[0]:
                    best = (pind, a, ls)
        if best is not None:
            break
        relax += 1
    if best is None:
        print(f"{band}: nothing in band even after relaxing the per-game cap; slate too small")
        continue
    pind, a, ls = best
    jm = m.joint_probability([l["p"] for l in ls], B.matrix(ls), trials=150000)
    d = price(ls)
    chosen.append({"band": band, "legs": ls, "p_ind": pind, "joint": jm, "american": a, "decimal": d,
                   "ev": pind * d, "ev_corr": jm * d, "fair": m.decimal_to_american(1 / pind),
                   "mincush": min(l["cushion"] for l in ls), "relaxed": relax,
                   "games": len({l["game"] for l in ls}), "stake": STAKE})
    used |= {l["player"] for l in ls}
    tag = "" if relax == 0 else f"  (relaxed x{relax}: small slate)"
    print(f"{band:<5}{len(ls):>2} legs  posted product {a:+6d}  hit {pind*100:5.1f}% (with corr {jm*100:4.1f}%)  fair {m.decimal_to_american(1/pind):+6d}  EV {pind*d:.3f}  worst cushion {min(l['cushion'] for l in ls)*100:.0f}%{tag}")
    for l in sorted(ls, key=lambda x: (x["game"], x["player"])):
        u = f"usage p {l['p_usage']*100:3.0f}% exp tgt {l['exp_tgt']:.1f}" if "p_usage" in l else l.get("usage", "")
        print(f"      {l['player']:<20}{l['stat'].replace('_', ' '):<14}over {l['line']:<6}{l['price']:>6}  FD mean {l['fd_mean']:>6.1f}  p {l['p']*100:>3.0f}%  {u}")
order = {"HIGH": 0, "MED": 1, "LOW": 2}
chosen.sort(key=lambda c: order[c["band"]])
json.dump(chosen, open("fdcard.json", "w"), indent=1)
json.dump({"games": games, "rungs": len(legs), "ladders": len(FIT), "priced": len(out),
           "excluded": sorted(excluded), "unknown_pos": sorted(unknown_pos),
           "fragile_dropped": sorted({d["player"] for d in fragile}), "no_usage_history": sorted(no_history),
           "usage_rows": U.n_rows if U else 0,
           "alt_margin_mult": ALT, "main_hold_two_way": CAL.get("main_hold_two_way"),
           "bands_built": [c["band"] for c in chosen]},
          open("fdsummary.json", "w"), indent=1)
# Persist the card so next week's run can grade it (fdgrade.py) and the record accumulates.
today = datetime.datetime.now(zoneinfo.ZoneInfo("America/New_York")).date().isoformat()
os.makedirs("cards", exist_ok=True)
KEEP = ("player", "stat", "line", "price", "game", "team", "p", "p_fit", "p_market", "p_usage", "fd_mean", "cushion", "exp_tgt")
json.dump({"date": today, "book": "FanDuel", "stake_per_ticket": STAKE,
           "tickets": [{"name": {"HIGH": "A", "MED": "B", "LOW": "C"}[c["band"]], "band": c["band"],
                        "page_price": c["american"], "joint": c["p_ind"],
                        "legs": [{k: l.get(k) for k in KEEP} for l in c["legs"]]} for c in chosen]},
          open(f"cards/{today}.json", "w"), indent=1)
print(f"card saved to cards/{today}.json")
