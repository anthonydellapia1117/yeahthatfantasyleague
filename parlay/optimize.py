"""optimize.py - search leg combinations for the best net edge inside a payout band.

Hand-picking legs optimises the wrong thing. What matters is the ratio of
correlation lift to compounded hold, and that is a property of the whole
ticket, not of any leg. This searches candidate tickets under three
constraints - payout band, leg count, and at most two legs per player -
and ranks by expected value per dollar at realistic book pricing.
"""
import itertools, random, json
import propmath as m
import build as B

HOLD = 1.045   # book shades each leg's implied probability by this factor


def book_decimal(legs):
    d = 1.0
    for l in legs:
        d *= 1.0 / min(0.985, l["p"] * HOLD)
    return d


def evaluate(legs, trials=40000):
    probs = [l["p"] for l in legs]
    M = B.matrix(legs)
    joint = m.joint_probability(probs, M, trials=trials, seed=11)
    ind = m.independent_probability(probs)
    dec = book_decimal(legs)
    return {"joint": joint, "ind": ind, "dec": dec,
            "american": m.decimal_to_american(dec),
            "ev": joint * dec, "lift": joint / ind - 1 if ind else 0,
            "kelly": m.kelly_fraction(joint, dec)}


def search(library, lo, hi, n_legs, iters=4000, seed=5, max_per_player=2):
    """Random-restart search for the highest-EV ticket in a payout band."""
    rng = random.Random(seed)
    best = []
    seen = set()
    for _ in range(iters):
        k = rng.choice(n_legs) if isinstance(n_legs, (list, tuple)) else n_legs
        if k > len(library):
            continue
        pick = rng.sample(range(len(library)), k)
        key = tuple(sorted(pick))
        if key in seen:
            continue
        seen.add(key)
        legs = [library[i] for i in pick]
        cnt = {}
        bad = False
        for l in legs:
            cnt[l["player"]] = cnt.get(l["player"], 0) + 1
            if cnt[l["player"]] > max_per_player:
                bad = True
                break
        if bad:
            continue
        dec = book_decimal(legs)
        am = m.decimal_to_american(dec)
        if am < lo or am > hi:
            continue
        r = evaluate(legs, trials=12000)
        best.append((r["ev"], key, r))
        best.sort(key=lambda x: -x[0])
        best = best[:12]
    out = []
    for ev, key, _ in best:
        legs = [library[i] for i in key]
        out.append((evaluate(legs, trials=200000), legs))
    out.sort(key=lambda x: -x[0]["ev"])
    return out
