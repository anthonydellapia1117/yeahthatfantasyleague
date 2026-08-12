#!/usr/bin/env python3
"""Guards on the survival model. Each encodes a bug that was live and shipped.

Run: python3 tests/test_survival.py
"""
import importlib.util, math, os, sys, csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
spec = importlib.util.spec_from_file_location("eng", os.path.join(ROOT, "src", "engine_2026.py"))
eng = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eng)

fails = []


def ok(cond, name, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "  -> " + detail))
    if not cond:
        fails.append(name)


# 1. CONTINUITY. The shipped 4-band step made ADP 24 vs 25 differ by 8,284x at
#    pick 48. No adjacent ADP pair may move survival by more than 5 points anywhere.
# The failure mode was a RATIO blowup from a step discontinuity, not a small
# absolute gap. Near the top of the board adjacent ADP slots legitimately differ by
# ~0.1 because sd is small there and the model is correctly confident. What must
# never happen is one ADP slot changing survival by a multiple.
def max_adjacent_ratio(surv):
    worst, where = 1.0, None
    for a in range(1, 200):
        for k in range(1, 169):
            lo, hi = surv(a, k), surv(a + 1, k)
            # Only where the number drives a decision. Deep in the Gaussian tail
            # every model has large ratios between tiny probabilities, and 0.0002
            # versus 0.0014 both read as "he is gone". At a 2 percent floor the
            # smooth model peaks at 2.5x and the old step function at 10.5x.
            if lo < 0.02 or hi < 0.02:
                continue
            r = max(hi / lo, lo / hi)
            if r > worst:
                worst, where = r, (a, k)
    return worst, where

worst, where = max_adjacent_ratio(eng.survival)
ok(worst < 4.0, "no ADP cliff: one ADP slot never multiplies survival",
   f"max {worst:.1f}x at ADP {where[0]}->{where[0]+1}, pick {where[1]}")

# And prove the guard actually bites: the shipped step function must fail it.
OLD = [(24, 5.46), (60, 13.63), (120, 24.01), (10 ** 9, 23.81)]
def old_survival(a, k):
    sd = next(s for hi, s in OLD if a <= hi)
    return max(0.0, min(1.0, 0.5 * math.erfc((k - a) / (sd * math.sqrt(2)))))
old_worst, _ = max_adjacent_ratio(old_survival)
ok(old_worst >= 4.0, "the guard would have caught the original step-function bug",
   f"old model max ratio only {old_worst:.1f}x")

# 1b. Nothing has been drafted at pick 1, so everyone is available.
ok(all(abs(eng.survival(a, 1) - 1.0) < 1e-9 for a in (1, 2, 5, 30, 150)),
   "survival at pick 1 is 1.0 for every player",
   f"ADP 1 gives {eng.survival(1, 1):.3f}")

# 2. sd is continuous and stays inside the observed range. It is NOT monotone -
#    that is INTERP's entire point: the empirical curve peaks near ADP 100 and
#    declines toward the end of the draft, which the audit showed a monotone
#    power law cannot express (docs/AUDIT_SURVIVAL_2026-08-12.md item C).
sds = [eng.sd_for(a) for a in range(1, 200)]
ok(max(abs(b - a) for a, b in zip(sds, sds[1:])) < 0.5, "sd has no jump")
lo = min(s for _, s in eng.ADP_SD_CURVE)
hi = max(s for _, s in eng.ADP_SD_CURVE)
ok(all(lo - 1e-9 <= s <= hi + 1e-9 for s in sds),
   "sd stays inside the observed bin range", f"range {min(sds):.2f}-{max(sds):.2f}")
ok(len(eng.ADP_SD_CURVE) == 12, "sd curve is the 12 audited bins")

# 3. MONOTONE + BOUNDED in the pick number.
ok(all(eng.survival(30, k) >= eng.survival(30, k + 1) - 1e-12 for k in range(1, 168)),
   "survival non-increasing in pick")
ok(all(0.0 <= eng.survival(a, k) <= 1.0 for a in (1, 30, 90, 150) for k in (1, 50, 168)),
   "survival stays in [0,1]")

# 4. DEEP TAIL. 1-erf collapses to exactly 0 past z~5 and trips the zero guard;
#    erfc keeps the real value.
ok(eng.survival(5, 60) > 0.0, "deep tail is positive, not a cancelled zero",
   f"got {eng.survival(5, 60)}")

# 5. CONDITIONAL form. Self-conditioning is identity; conditioning never exceeds 1.
ok(abs(eng.cond_survival(30, 40, 40) - 1.0) < 1e-9, "cond_survival(k,k) == 1")
ok(all(eng.cond_survival(a, k, 1) <= 1.0 + 1e-9 for a in (5, 30, 90) for k in (10, 60, 120)),
   "cond_survival never exceeds 1")
ok(eng.cond_survival(30, 40, 35) > eng.survival(30, 40) - 1e-9,
   "conditioning on availability raises survival, never lowers it")
ok(all(eng.cond_survival(30, k, 20) >= eng.cond_survival(30, k + 1, 20) - 1e-12
       for k in range(20, 168)),
   "cond_survival non-increasing in the target pick")
# Normalization invariance: the pick-1 normalization must cancel in every
# conditional ratio (it is a single S(1) factor on both sides).
ok(all(abs(eng.cond_survival(a, 60, 30)
           - (eng._raw_survival(a, 60) / eng._raw_survival(a, 30))) < 1e-9
       for a in (10, 25, 40) if eng._raw_survival(a, 30) > 1e-12),
   "conditional ratios are invariant to the pick-1 normalization")

# 5b. CALIBRATION BENCHMARK - the guard the power law showed was missing. The
#     shipped sd must beat the frozen step-function baseline on the conditional
#     decision quantity over the full historical pick table, evaluated
#     identically and deterministically. A future sd change that predicts worse
#     than the ORIGINAL model cannot ship. (In-sample eval; the leave-one-out
#     ordering that motivated INTERP is in docs/AUDIT_SURVIVAL_2026-08-12.md.)
def cond_brier(sdf):
    tot = n = 0.0
    for p in csv.DictReader(open(os.path.join(ROOT, "out", "picks.csv"))):
        d = p.get("adp_differential")
        if not d:
            continue
        try:
            d = float(d)
        except ValueError:
            continue
        y = float(p["overall"])
        adp = y - d
        c0 = 1
        while c0 <= min(y, 156):
            k = c0 + 12
            z1 = (c0 - adp) / (sdf(adp) * math.sqrt(2))
            zk = (k - adp) / (sdf(adp) * math.sqrt(2))
            s_from, s_to = 0.5 * math.erfc(z1), 0.5 * math.erfc(zk)
            pr = 0.0 if s_from <= 1e-12 else min(1.0, s_to / s_from)
            o = 1.0 if y >= k else 0.0
            tot += (pr - o) ** 2
            n += 1
            c0 += 4
    return tot / n

STEP_SD = lambda a: next(s for hi, s in OLD if a <= hi)
b_ship, b_step = cond_brier(eng.sd_for), cond_brier(STEP_SD)
ok(b_ship < b_step,
   "shipped sd beats the frozen step baseline on the decision quantity",
   f"shipped {b_ship:.5f} vs step {b_step:.5f}")

# 6. THE HARD GUARDRAIL. Franchise lift is display only and must reach no arithmetic
#    that touches a probability. Tested and rejected: pooled Brier got worse
#    (0.23030 -> 0.23050, p=0.9932). See out/tendency_backtest.json.
src = open(os.path.join(ROOT, "src", "engine_2026.py")).read()
body = src[src.index("def build_model"):]
bad = [ln.strip() for ln in body.splitlines()
       if ("gap_lift" in ln or "lift" in ln)
       and any(t in ln for t in ("survival(", "p_available", "p_gone", "vor *", "* lift"))]
ok(not bad, "franchise lift never enters a probability", "; ".join(bad[:2]))

# 7. The tendency table exists and its lifts are centred, not runaway.
tp = os.path.join(ROOT, "out", "positional_tendency.csv")
if os.path.exists(tp):
    lifts = [float(r["lift"]) for r in csv.DictReader(open(tp))]
    # K and DEF carry league base rates near 0.03, so honest ratios swing wider
    # there than for skill positions. Cambrias at 0.34 for DEF rd7-10 is 51 verified
    # picks, not noise. Bound the skill positions tightly and K/DEF loosely.
    skill = [float(r["lift"]) for r in csv.DictReader(open(tp))
             if r["pos"] in ("QB", "RB", "WR", "TE")]
    allv = lifts
    # Bounds set from what shrinkage actually produces on this data, not a guess.
    # The extremes are real and well sampled: Cambrias wait on QB (0.63, n=39,
    # their first-QB round is 8.26, latest in the league) and Pung & Tralie reach
    # for one (1.68, n=39). A runaway would be a shrinkage failure, not a habit.
    ok(0.5 < min(skill) and max(skill) < 2.0, "skill-position lifts stay plausible",
       f"range {min(skill):.2f}-{max(skill):.2f}")
    ok(0.25 < min(allv) and max(allv) < 3.0, "no runaway lift anywhere",
       f"range {min(allv):.2f}-{max(allv):.2f}")

print()
print(f"{len(fails)} FAILURES" if fails else "ALL PASS")
sys.exit(1 if fails else 0)
