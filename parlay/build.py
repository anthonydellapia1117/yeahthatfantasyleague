"""build.py - assemble correlated prop parlays into payout tiers."""
import json, math, propmath as m, project as pj

CV = {"rec_yards": 0.55, "rush_yards": 0.50, "rush_rec_yards": 0.44,
      "pass_yards": 0.28}
COUNT = {"receptions": 1.45, "completions": 1.25}

# Pairwise latent correlation between legs. Same game only; legs in
# different games are independent and get 0.
CORR = {
    ("QBpass", "WRrec"): 0.50, ("QBpass", "TErec"): 0.35,
    ("QBcomp", "WRrec"): 0.55, ("QBcomp", "TErec"): 0.38,
    ("QBpass", "QBcomp"): 0.85,
    ("WRrec", "WRrec"): 0.15, ("WRrec", "TErec"): 0.12,
    ("TErec", "TErec"): 0.15,
    ("QBpass", "RBrush"): -0.20, ("QBcomp", "RBrush"): -0.18,
    ("RBrush", "WRrec"): -0.08, ("RBrush", "TErec"): -0.06,
    ("RBrush", "RBrush"): 0.10,
}

def pair_corr(a, b):
    if a["game"] != b["game"] or a["team"] != b["team"]:
        # different game entirely -> independent
        if a["game"] != b["game"]:
            return 0.0
        # same game, opposing teams: mild shootout coupling
        return 0.12
    k1, k2 = a["kind"], b["kind"]
    return CORR.get((k1, k2), CORR.get((k2, k1), 0.0))

def matrix(legs):
    n = len(legs)
    M = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            r = pair_corr(legs[i], legs[j])
            M[i][j] = M[j][i] = r
    return M

def prob(leg):
    if leg["stat"] in COUNT:
        return m.prob_over_count(leg["mean"], leg["line"], COUNT[leg["stat"]])
    return m.prob_over_continuous(leg["mean"], leg["line"], CV[leg["stat"]])

def fair(p):
    return m.decimal_to_american(1.0 / p)

def pick_line(mean, stat, target_p):
    """Smallest standard x.5 line whose hit probability is >= target."""
    step = 0.5 if stat in COUNT else 0.5
    hi = mean * 2.0
    best = 0.5
    x = 0.5
    while x < hi:
        p = (m.prob_over_count(mean, x, COUNT[stat]) if stat in COUNT
             else m.prob_over_continuous(mean, x, CV[stat]))
        if p >= target_p:
            best = x
        x += step
    return best

def report(name, legs, target_band):
    for l in legs:
        l["p"] = prob(l)
        l["fair"] = fair(l["p"])
    M = matrix(legs)
    probs = [l["p"] for l in legs]
    ind = m.independent_probability(probs)
    joint = m.joint_probability(probs, M, trials=200000)
    dec_fair = 1.0
    for l in legs:
        dec_fair *= 1.0 / l["p"]
    # realistic book price: book shades each leg by a 4.5% hold
    dec_book = 1.0
    for l in legs:
        dec_book *= 1.0 / min(0.985, l["p"] * 1.045)
    hold_cost = 1 / (0.957 ** len(legs)) - 1
    lift = joint / ind - 1
    return {"name": name, "legs": legs, "band": target_band,
            "p_ind": ind, "p_joint": joint, "lift": lift,
            "hold_cost": hold_cost,
            "net_edge": (1 + lift) / (1 + hold_cost) - 1,
            "fair_american": m.decimal_to_american(dec_fair),
            "book_american": m.decimal_to_american(dec_book),
            "ev_at_book": joint * dec_book,
            "kelly": m.kelly_fraction(joint, dec_book)}
