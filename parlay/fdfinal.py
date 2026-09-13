"""fdfinal.py - price legs from FanDuel's own ladder, then build the three tickets.

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
import json, os, random, re, statistics
from collections import defaultdict
import propmath as m, build as B, fdlines
from fdlines import norm

ENGINE = "../out/engine_2026.json"
STAKE = 25
# A rung below these lines is a one-catch prop whose price is mostly margin.
LINE_FLOOR = {"rec_yards": 9.5, "receptions": 2.5, "pass_yards": 149.5, "rush_rec_yards": 19.5}
# Rungs needed before a fitted ladder is trusted.
MIN_RUNGS = {"receptions": 4}
DEFAULT_MIN_RUNGS = 5
# A rung may be credited at most this far above its own de-vigged price, so a
# poor fit cannot be harvested as edge (the failure mode of the first build).
P_CAP = 0.02


CAL = json.load(open("fdcal.json"))
ALT = CAL["alt_margin_mult"]
legs, mains, games = fdlines.load()
POS, TEAM = {}, {}
if os.path.exists(ENGINE):
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
    if pos == "RB" and l["stat"] != "rush_rec_yards":
        continue                                   # RB rush/receive split is not priced well enough
    if pos in ("K", "DEF"):
        continue
    if k not in POS and l["stat"] != "pass_yards":
        continue                                   # receivers outside the season engine: usage too thin to trust
    l["pos"] = pos
    g = games[l["game"]]
    t = TEAM.get(k, "?")
    l["team"] = t if t in (g["home"], g["away"]) else "?"
    grp[(l["player"], l["stat"])].append(l)


def fit(ls, stat):
    pts = [(l["line"], l["q"]) for l in ls if 0.04 < l["q"] < 0.97]
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
        d["kind"] = {"pass_yards": "QBpass", "rush_rec_yards": "RBrush"}.get(
            st, "TErec" if l["pos"] == "TE" else "WRrec")
        out.append(d)
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


# band, min odds, max odds, leg counts to try, iterations, relaxation ladder of
# (legs per game, min p, min cushion, price floor). The first rung is the
# standard build; later rungs only apply when a slate is too small to fill it.
BANDS = [("LOW", 250, 499, (3, 4, 5, 6), 160000,
          [(2, 0.62, 0.25, -700), (3, 0.62, 0.25, -700), (4, 0.55, 0.20, -700)]),
         ("MED", 500, 999, (5, 6, 7, 8), 220000,
          [(2, 0.62, 0.25, -700), (3, 0.62, 0.25, -700), (4, 0.55, 0.20, -700)]),
         ("HIGH", 1000, 2600, (8, 9, 10, 11), 320000,
          [(3, 0.62, 0.25, -800), (4, 0.62, 0.25, -800), (5, 0.55, 0.20, -800), (6, 0.50, 0.15, -800)])]
rng = random.Random(2113)
chosen, used = [], set()
for band, lo, hi, ns, iters, ladder in BANDS:
    best, relax = None, 0
    for cap, pmin, cmin, floor in ladder:
        avail = [l for l in out if l["cushion"] >= cmin and pmin <= l["p"] <= 0.95 and l["link"]
                 and l["price"] >= floor and l["player"] not in used]
        seen = set()
        for _ in range(iters):
            k = rng.choice(ns)
            if k > len(avail):
                continue
            idx = tuple(sorted(rng.sample(range(len(avail)), k)))
            if idx in seen:
                continue
            seen.add(idx)
            ls = [avail[i] for i in idx]
            if not ok(ls, cap):
                continue
            d = price(ls)
            a = m.decimal_to_american(d)
            if a < lo or a > hi:
                continue
            pind = 1.0
            for l in ls:
                pind *= l["p"]
            ev = pind * d
            if best is None or ev > best[0]:
                best = (ev, pind, a, ls)
        if best is not None:
            break
        relax += 1
    if best is None:
        print(f"{band}: nothing in band even after relaxing the per-game cap; slate too small")
        continue
    ev, pind, a, ls = best
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
        print(f"      {l['player']:<20}{l['stat'].replace('_', ' '):<14}over {l['line']:<6}{l['price']:>6}  FD mean {l['fd_mean']:>6.1f}  cush {l['cushion']*100:>3.0f}%  p {l['p']*100:>3.0f}%  legEV {l['ev1']:.3f}  resid {l['resid']*100:+.1f}pts")
order = {"HIGH": 0, "MED": 1, "LOW": 2}
chosen.sort(key=lambda c: order[c["band"]])
json.dump(chosen, open("fdcard.json", "w"), indent=1)
json.dump({"games": games, "rungs": len(legs), "ladders": len(FIT), "priced": len(out),
           "excluded": sorted(excluded), "unknown_pos": sorted(unknown_pos),
           "alt_margin_mult": ALT, "main_hold_two_way": CAL.get("main_hold_two_way"),
           "bands_built": [c["band"] for c in chosen]},
          open("fdsummary.json", "w"), indent=1)
