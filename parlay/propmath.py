"""
propmath.py - probability engine for NFL player-prop parlays.

Pure standard library. No numpy, no scipy, so it runs anywhere the
automation lands.

The engine answers three questions:

  1. Given a projected mean for a stat, what is P(stat > line)?
  2. Given several correlated legs, what is P(all legs hit)?
  3. Given a payout target, which combination of legs maximises
     expected value rather than just reaching the number?

The governing identity, derived in README.md, is that a parlay's
expected value equals the PRODUCT of its per-leg edge ratios p_i/q_i.
Leg count and payout length do not enter it. That is why a long stack
of high-probability legs dominates a short stack of longshots: edge
compounds, and the estimate of p is proportionally far more reliable
when p is large.
"""

import math
import random

# ---------------------------------------------------------------- odds

def american_to_decimal(american):
    a = float(american)
    return 1.0 + (a / 100.0 if a > 0 else 100.0 / abs(a))


def decimal_to_american(dec):
    dec = float(dec)
    if dec >= 2.0:
        return round((dec - 1.0) * 100.0)
    return round(-100.0 / (dec - 1.0))


def american_to_implied(american):
    """Implied probability INCLUDING the vig."""
    return 1.0 / american_to_decimal(american)


def devig_two_way(odds_over, odds_under):
    """Multiplicative (proportional) de-vig of a two-way market.

    Returns the no-vig probability of the OVER plus the hold. The book's
    posted pair sums to more than 1; the excess is the hold. Removing it
    proportionally is the standard estimator and is unbiased when the
    hold is applied symmetrically.
    """
    a = american_to_implied(odds_over)
    b = american_to_implied(odds_under)
    total = a + b
    return a / total, total - 1.0


def parlay_decimal(leg_odds):
    d = 1.0
    for o in leg_odds:
        d *= american_to_decimal(o)
    return d


# ------------------------------------------------------- distributions

def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p):
    """Inverse normal CDF, Acklam's rational approximation.

    Relative error below 1.15e-9 across the open unit interval, which is
    far tighter than anything our inputs justify.
    """
    if p <= 0.0 or p >= 1.0:
        raise ValueError("norm_ppf needs 0 < p < 1")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def _ln_gamma(x):
    return math.lgamma(x)


def gamma_sf(x, shape, scale):
    """P(X > x) for a Gamma. Series below the mean, continued fraction above."""
    if x <= 0:
        return 1.0
    a, z = shape, x / scale
    if z < a + 1.0:
        term = 1.0 / a
        total = term
        n = a
        for _ in range(500):
            n += 1.0
            term *= z / n
            total += term
            if abs(term) < abs(total) * 1e-14:
                break
        lower = total * math.exp(-z + a * math.log(z) - _ln_gamma(a))
        return max(0.0, min(1.0, 1.0 - lower))
    tiny = 1e-300
    b = z + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    upper = math.exp(-z + a * math.log(z) - _ln_gamma(a)) * h
    return max(0.0, min(1.0, upper))


def prob_over_continuous(mean, line, cv):
    """P(stat > line) for a yardage stat modelled as Gamma.

    Gamma, not normal: yardage is non-negative, right-skewed, and a
    normal model puts real mass below zero for low-volume players, which
    inflates the under. Shape = 1/cv^2 pins the coefficient of variation
    to the empirical week-to-week value for that stat type.
    """
    if mean <= 0:
        return 0.0
    shape = 1.0 / (cv * cv)
    scale = mean / shape
    return gamma_sf(line, shape, scale)


def prob_over_count(mean, line, dispersion=1.45):
    """P(count > line) for receptions or completions, negative binomial.

    NFL reception counts are overdispersed relative to Poisson: target
    share itself varies game to game on top of the catch process. The
    variance-to-mean ratio sits near 1.45 for established route runners.
    `line` is a betting line such as 4.5, so "over" means >= 5.
    """
    if mean <= 0:
        return 0.0
    need = int(math.floor(line)) + 1
    if dispersion <= 1.0001:
        r_ = None
    else:
        r_ = mean / (dispersion - 1.0)
    cum = 0.0
    if r_ is None:
        term = math.exp(-mean)
        for k in range(need):
            if k:
                term *= mean / k
            cum += term
    else:
        p_ = r_ / (r_ + mean)
        term = math.exp(r_ * math.log(p_))
        for k in range(need):
            if k:
                term *= (r_ + k - 1) / k * (1 - p_)
            cum += term
    return max(0.0, min(1.0, 1.0 - cum))


# ---------------------------------------------------------- correlation

def joint_probability(probs, corr, trials=200000, seed=17):
    """P(all legs hit) under a Gaussian copula with correlation matrix corr.

    Each leg's marginal probability p_i is mapped to a latent standard
    normal threshold t_i = Phi^-1(1 - p_i); the leg hits when its latent
    draw exceeds t_i. Correlated latents are produced by a Cholesky
    factor of corr. With corr = I this reduces to the product of the
    marginals, which is the independence case and the correct default
    for legs in different games.
    """
    n = len(probs)
    if n == 0:
        return 1.0
    if n == 1:
        return probs[0]
    thresh = [norm_ppf(1.0 - p) for p in probs]
    L = _cholesky(corr)
    rng = random.Random(seed)
    hits = 0
    for _ in range(trials):
        z = [rng.gauss(0.0, 1.0) for _ in range(n)]
        ok = True
        for i in range(n):
            xi = 0.0
            Li = L[i]
            for j in range(i + 1):
                xi += Li[j] * z[j]
            if xi <= thresh[i]:
                ok = False
                break
        if ok:
            hits += 1
    return hits / float(trials)


def _cholesky(a):
    n = len(a)
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = sum(L[i][k] * L[j][k] for k in range(j))
            if i == j:
                v = a[i][i] - s
                L[i][j] = math.sqrt(max(v, 1e-12))
            else:
                L[i][j] = (a[i][j] - s) / L[j][j]
    return L


def independent_probability(probs):
    p = 1.0
    for x in probs:
        p *= x
    return p


# --------------------------------------------------------------- value

def edge_ratio(true_p, odds):
    """p / q. Above 1.0 the leg is priced in your favour."""
    return true_p / american_to_implied(odds)


def parlay_report(legs, corr=None, trials=200000):
    """legs: list of dicts with keys true_p and odds.

    Returns payout, independent and correlated hit probability, EV per
    dollar, and the compounded edge. EV uses the correlated probability
    because that is the one that pays.
    """
    probs = [l["true_p"] for l in legs]
    odds = [l["odds"] for l in legs]
    dec = parlay_decimal(odds)
    indep = independent_probability(probs)
    if corr is None:
        corr = [[1.0 if i == j else 0.0 for j in range(len(legs))]
                for i in range(len(legs))]
    joint = joint_probability(probs, corr, trials=trials)
    ev = joint * dec
    compounded = 1.0
    for l in legs:
        compounded *= edge_ratio(l["true_p"], l["odds"])
    return {
        "n_legs": len(legs),
        "decimal": dec,
        "american": decimal_to_american(dec),
        "p_independent": indep,
        "p_correlated": joint,
        "correlation_lift": (joint / indep - 1.0) if indep > 0 else 0.0,
        "ev_per_dollar": ev,
        "compounded_edge": compounded,
        "breakeven_p": 1.0 / dec,
    }


# ------------------------------------------------------ kelly and stake

def kelly_fraction(p, dec):
    """Full Kelly for a binary bet. b = dec - 1."""
    b = dec - 1.0
    if b <= 0:
        return 0.0
    f = (p * b - (1.0 - p)) / b
    return max(0.0, f)
