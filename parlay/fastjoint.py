"""fastjoint.py - fast joint probability via a one-factor Gaussian copula.

Monte Carlo inside a combinatorial search is far too slow. The correlation
structure here is block diagonal by team, and inside a block it is well
approximated by a single common factor with a per-leg loading:

    X_i = lam_i * Z + sqrt(1 - lam_i^2) * e_i

which reproduces correlation lam_i * lam_j between legs i and j. Loadings
are signed, so a running back whose volume moves against his own team's
pass game gets a negative loading and correctly reduces the joint
probability of an all-overs stack.

The orthant probability then collapses to a one dimensional integral

    P(all hit) = integral phi(z) * product Phi((lam_i z - t_i)/sqrt(1-lam_i^2)) dz

evaluated by Gauss-Legendre quadrature over [-6, 6]. That is exact for a
one-factor model and roughly three orders of magnitude faster than
simulation.
"""
import math
from propmath import norm_cdf, norm_ppf

# Signed factor loadings by leg kind. lam_i * lam_j approximates the pairwise
# correlation inside a team block. A single factor cannot reproduce
# build.CORR exactly (the quarterback-to-receiver couplings it is fit to
# imply a receiver-receiver value above the matrix's 0.15), and opposing
# teams in the same game are treated as independent here where build.py
# gives them 0.12. The approximation was checked against the full copula on
# one-leg-per-player tickets and agreed to about 4 percent, which is why the
# search scripts use it only to rank and always verify finalists with
# propmath.joint_probability. The FanDuel pipeline takes no correlation
# credit at all.
LOADING = {"QBpass": 0.72, "QBcomp": 0.74, "WRrec": 0.70,
           "TErec": 0.52, "RBrush": -0.28}

_NODES = None

def _gauss_legendre(n=40, a=-6.0, b=6.0):
    """Nodes and weights by Newton iteration on the Legendre polynomial."""
    xs, ws = [], []
    for i in range(1, n + 1):
        x = math.cos(math.pi * (i - 0.25) / (n + 0.5))
        for _ in range(100):
            p0, p1 = 1.0, 0.0
            for j in range(1, n + 1):
                p2 = p1
                p1 = p0
                p0 = ((2 * j - 1) * x * p1 - (j - 1) * p2) / j
            dp = n * (x * p0 - p1) / (x * x - 1.0)
            dx = -p0 / dp
            x += dx
            if abs(dx) < 1e-14:
                break
        xs.append(x)
        ws.append(2.0 / ((1 - x * x) * dp * dp))
    half = (b - a) / 2.0
    mid = (a + b) / 2.0
    return [mid + half * x for x in xs], [half * w for w in ws]


def _nodes():
    global _NODES
    if _NODES is None:
        _NODES = _gauss_legendre()
    return _NODES


def joint_one_factor(legs):
    """P(all legs hit). Legs are grouped by team; groups multiply."""
    groups = {}
    for l in legs:
        groups.setdefault((l["game"], l["team"]), []).append(l)
    xs, ws = _nodes()
    total = 1.0
    for _, grp in groups.items():
        if len(grp) == 1:
            total *= grp[0]["p"]
            continue
        thr, lam = [], []
        for l in grp:
            thr.append(norm_ppf(1.0 - l["p"]))
            lam.append(LOADING.get(l["kind"], 0.0))
        acc = 0.0
        for z, w in zip(xs, ws):
            dens = math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
            prod = 1.0
            for t, la in zip(thr, lam):
                s = math.sqrt(max(1e-9, 1.0 - la * la))
                prod *= norm_cdf((la * z - t) / s)
                if prod < 1e-14:
                    break
            acc += w * dens * prod
        total *= acc
    return total
