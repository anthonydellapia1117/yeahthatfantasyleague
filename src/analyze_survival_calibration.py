#!/usr/bin/env python3
"""Item 5 follow-up: the survival recalibration PROPOSAL. Evidence only -
no frozen function changes, nothing wired. The exact diff Anthony would
approve ships as ADR text, not code.

THE DIAGNOSIS QUESTION
The frozen sd curve is already fitted on this league's own history
(2,039 picks carry adp_differential), so the observed overconfidence
about removal cannot be a scale problem. The hypothesis: it is a SHAPE
problem. The model removes players NORMALLY around ADP; if the true
differential distribution is right-heavy (fallers keep falling), a
normal with the right sd still kills the late tail too fast - exactly
the observed miscalibration. Tested here on both ADP frames (FFC and
the archive differentials) via standardized quantiles vs the normal.

TWO CANDIDATE FIXES, FIT 2013-2022, EVALUATED 2023-2025 (walk-forward,
same pair frame as the item-5 calibration: every FFC-listed player
available at one of Anthony's picks, predicted to his next)

  A  empirical-tail survival: replace the normal CDF with the
     Kaplan-Meier survival of the standardized differential
     z = (pick - adp) / sd_for(adp), censoring undrafted players at the
     year's final pick. Uses the frozen sd_for READ-ONLY; would ship as
     a parallel function, frozen originals untouched.
  B  isotonic calibration layer: pool-adjacent-violators over 20
     prediction bins, mapping the frozen cond_survival output to a
     calibrated probability. A monotone lookup table - trivially
     mirrored in the room's JS, applied AFTER the frozen math,
     kill-switchable, frozen bytes untouched.

DECISION METRICS
Holdout Brier + reliability (esp. the sub-50% bucket where the defect
lives), and the draft-day consequence: pairs where the frozen model says
TAKE NOW (pred < 0.6, the room's WAIT threshold) but the candidate says
WAIT (>= 0.6) - how many calls flip, and how often the player was
actually still there (the flip's empirical win rate).

Writes out/data/survival_recalibration.json.
"""
import csv
import datetime
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_recency as base
import engine_2026 as eng                 # frozen - read-only

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "data", "survival_recalibration.json")
SKILL = ("QB", "RB", "WR", "TE")
ME = "Antdell & Ernie"
SEASONS = range(2013, 2026)
TRAIN_MAX = 2022
WAIT_THRESHOLD = 0.6
NBINS = 20


def load_years():
    """Per year: FFC universe with adp, taken_by, my pick list, last pick."""
    picks = list(csv.DictReader(open(os.path.join(ROOT, "out", "picks.csv"))))
    years = {}
    for Y in SEASONS:
        yr = sorted([r for r in picks if int(r["season"]) == Y],
                    key=lambda r: int(r["overall"]))
        taken_by = {(base.norm(r["player_name"]), r["pos"]): int(r["overall"])
                    for r in yr}
        ffc = {}
        for p in json.load(open(os.path.join(base.HISTORY, f"ffc_ppr_{Y}.json")))["players"]:
            if p["position"] in SKILL:
                ffc[(base.norm(p["name"]), p["position"])] = float(p["adp"])
        mine = sorted(int(r["overall"]) for r in yr if r["member_name"] == ME)
        years[Y] = {"ffc": ffc, "taken_by": taken_by, "mine": mine,
                    "last_pick": int(yr[-1]["overall"])}
    return years


def gen_pairs(years, y_lo, y_hi):
    """(year, adp, pred_frozen, observed) - identical frame to item 5."""
    out = []
    for Y in range(y_lo, y_hi + 1):
        d = years[Y]
        for k0, k1 in zip(d["mine"], d["mine"][1:]):
            for key, adp in d["ffc"].items():
                if d["taken_by"].get(key, 10**9) < k0:
                    continue
                pred = eng.cond_survival(adp, k1, k0)
                out.append((Y, adp, pred,
                            1 if d["taken_by"].get(key, 10**9) >= k1 else 0))
    return out


def km_curve(years, y_lo, y_hi):
    """Kaplan-Meier survival of z = (pick - adp)/sd_for(adp); undrafted
    players censored at the year's final pick."""
    events = []                             # (z, is_event)
    for Y in range(y_lo, y_hi + 1):
        d = years[Y]
        for key, adp in d["ffc"].items():
            sd = eng.sd_for(adp)
            taken = d["taken_by"].get(key)
            if taken is not None:
                events.append(((taken - adp) / sd, 1))
            else:
                events.append(((d["last_pick"] - adp) / sd, 0))
    events.sort()
    zs, surv = [], []
    at_risk, s = len(events), 1.0
    i = 0
    while i < len(events):
        z = events[i][0]
        deaths = censored = 0
        while i < len(events) and events[i][0] == z:
            if events[i][1]:
                deaths += 1
            else:
                censored += 1
            i += 1
        if deaths and at_risk:
            s *= (1 - deaths / at_risk)
            zs.append(z)
            surv.append(s)
        at_risk -= deaths + censored
    return zs, surv


def km_eval(zs, surv, z):
    """S(z) with S = 1 left of the first event; step function."""
    import bisect
    i = bisect.bisect_right(zs, z)
    return 1.0 if i == 0 else surv[i - 1]


def cand_a(zs, surv, adp, k1, k0):
    sd = eng.sd_for(adp)
    s0 = km_eval(zs, surv, (k0 - adp) / sd)
    if s0 <= 1e-9:
        return 0.0
    return max(0.0, min(1.0, km_eval(zs, surv, (k1 - adp) / sd) / s0))


def pav(train_pairs):
    """Isotonic (non-decreasing) calibration over NBINS prediction bins."""
    bins = [[0.0, 0] for _ in range(NBINS)]
    for _, _, p, o in [(0, 0, p, o) for _, _, p, o in train_pairs]:
        i = min(NBINS - 1, int(p * NBINS))
        bins[i][0] += o
        bins[i][1] += 1
    blocks = [[s, n] for s, n in bins if n]
    edges = [i for i, (_, n) in enumerate(bins) if n]
    merged = [[s, n, [e]] for (s, n), e in zip(blocks, edges)]
    i = 0
    while i < len(merged) - 1:
        if merged[i][0] / merged[i][1] > merged[i + 1][0] / merged[i + 1][1] + 1e-12:
            merged[i][0] += merged[i + 1][0]
            merged[i][1] += merged[i + 1][1]
            merged[i][2] += merged[i + 1][2]
            del merged[i + 1]
            i = max(0, i - 1)
        else:
            i += 1
    table = [None] * NBINS
    for s, n, es in merged:
        for e in es:
            table[e] = s / n
    last = 0.0
    for i in range(NBINS):                  # fill empty bins monotonically
        if table[i] is None:
            table[i] = last
        last = table[i]
    return table


def cand_b(table, pred):
    return table[min(NBINS - 1, int(pred * NBINS))]


def calib_stats(pairs, fn):
    preds = [(fn(x), x[3]) for x in pairs]
    m = len(preds)
    br = sum(o for _, o in preds) / m
    brier = sum((p - o) ** 2 for p, o in preds) / m
    brier_base = sum((br - o) ** 2 for _, o in preds) / m
    low = [(p, o) for p, o in preds if p < 0.5]
    return {"n": m, "brier": round(brier, 4),
            "skill_vs_base_rate": round(1 - brier / brier_base, 4),
            "low_bucket_lt50": {
                "n": len(low),
                "predicted_mean": round(sum(p for p, _ in low) / len(low), 3) if low else None,
                "observed": round(sum(o for _, o in low) / len(low), 3) if low else None}}


def main():
    years = load_years()

    # ---- diagnosis: standardized differential quantiles vs the normal, on
    # both ADP frames
    def quantiles(zvals):
        zvals = sorted(zvals)
        q = lambda p: round(zvals[int(p * (len(zvals) - 1))], 3)
        return {"n": len(zvals), "q50": q(.50), "q75": q(.75),
                "q90": q(.90), "q95": q(.95)}
    ffc_z = []
    for Y in SEASONS:
        d = years[Y]
        for key, adp in d["ffc"].items():
            t = d["taken_by"].get(key)
            if t is not None:
                ffc_z.append((t - adp) / eng.sd_for(adp))
    arch_z = []
    for r in csv.DictReader(open(os.path.join(ROOT, "out", "picks.csv"))):
        dv = (r.get("adp_differential") or "").strip()
        if not dv:
            continue
        try:
            dv = float(dv)
        except ValueError:
            continue
        adp = int(r["overall"]) - dv
        arch_z.append(dv / eng.sd_for(adp))
    normal_q = {"q50": 0.0, "q75": 0.674, "q90": 1.282, "q95": 1.645}
    diagnosis = {
        "hypothesis": "shape, not scale: removal is right-heavy vs the normal",
        "ffc_frame": quantiles(ffc_z), "archive_frame": quantiles(arch_z),
        "normal_reference": normal_q,
    }

    # ---- candidates: fit on train years, evaluate on holdout
    train = gen_pairs(years, 2013, TRAIN_MAX)
    hold = gen_pairs(years, TRAIN_MAX + 1, 2025)
    zs, surv = km_curve(years, 2013, TRAIN_MAX)
    table = pav(train)

    def fz(x):
        return x[2]
    def fa(x):
        Y, adp, _, _ = x
        return None
    # candidate A needs (adp, k0, k1) - regenerate holdout with them attached
    hold_full = []
    for Y in range(TRAIN_MAX + 1, 2026):
        d = years[Y]
        for k0, k1 in zip(d["mine"], d["mine"][1:]):
            for key, adp in d["ffc"].items():
                if d["taken_by"].get(key, 10**9) < k0:
                    continue
                hold_full.append((Y, adp, eng.cond_survival(adp, k1, k0),
                                  1 if d["taken_by"].get(key, 10**9) >= k1 else 0,
                                  k0, k1))
    models = {
        "frozen": lambda x: x[2],
        "A_empirical_tail": lambda x: cand_a(zs, surv, x[1], x[5], x[4]),
        "B_isotonic_layer": lambda x: cand_b(table, x[2]),
    }
    evaluation = {name: calib_stats(hold_full, fn) for name, fn in models.items()}

    # ---- the draft-day consequence: TAKE NOW -> WAIT flips on holdout
    flips = {}
    for name in ("A_empirical_tail", "B_isotonic_layer"):
        fn = models[name]
        fl = [x for x in hold_full
              if x[2] < WAIT_THRESHOLD <= fn(x)]
        flips[name] = {
            "n_flips": len(fl),
            "of_holdout_pairs": len(hold_full),
            "observed_still_available": round(
                sum(x[3] for x in fl) / len(fl), 3) if fl else None,
            "note": f"pairs where frozen < {WAIT_THRESHOLD} <= candidate - the "
                    "room's WAIT threshold; observed rate is how often waiting "
                    "would have worked"}

    # ---- era stability of the calibration itself (Anthony's question,
    # 2026-08-19). THE RULE, REGISTERED BEFORE COMPUTING:
    #   fit M on 2019-2022 only, evaluate on the same 2023-2025 holdout as
    #   the 2013-2022 fit. Deployment candidates: T_all (fit 2013-2025) and
    #   T_modern (fit 2019-2025). "Meaningfully different" means max bin gap
    #   >= 0.05 over bins occupied in both, OR any bin straddling the 0.6
    #   verdict threshold between the tables. Decision: meaningful AND the
    #   modern-era fit is not worse on holdout -> deploy T_modern with T_all
    #   as the conservative fallback; meaningful but modern fits worse ->
    #   deploy T_all and flag the tension; not meaningful -> T_all stands
    #   with more confidence than before.
    modern_train = gen_pairs(years, 2019, TRAIN_MAX)
    table_m = pav(modern_train)
    eval_modern_fit = calib_stats(hold_full, lambda x: cand_b(table_m, x[2]))
    t_all = [round(v, 4) for v in pav(gen_pairs(years, 2013, 2025))]
    t_modern = [round(v, 4) for v in pav(gen_pairs(years, 2019, 2025))]
    gaps = [abs(a - b) for a, b in zip(t_all, t_modern)]
    straddle = [i for i, (a, b) in enumerate(zip(t_all, t_modern))
                if (a >= WAIT_THRESHOLD) != (b >= WAIT_THRESHOLD)]
    meaningful = max(gaps) >= 0.05 or bool(straddle)
    modern_not_worse = eval_modern_fit["brier"] <= evaluation["B_isotonic_layer"]["brier"]
    era_choice = ("deploy_modern" if meaningful and modern_not_worse
                  else "deploy_all_flag_tension" if meaningful
                  else "all_years_stands")
    # walk-forward flips for the DEPLOYED lineage: the 2019-2022 fit is the
    # honest out-of-sample analog of the modern deployment table
    flm = [x for x in hold_full
           if x[2] < WAIT_THRESHOLD <= cand_b(table_m, x[2])]
    modern_flips = {"n_flips": len(flm), "of_holdout_pairs": len(hold_full),
                    "observed_still_available": round(
                        sum(x[3] for x in flm) / len(flm), 3) if flm else None}
    if flm:
        p_hat = modern_flips["observed_still_available"]
        se = (p_hat * (1 - p_hat) / len(flm)) ** 0.5
        modern_flips["win_rate_ci95_binomial"] = [round(p_hat - 1.96 * se, 4),
                                                 round(p_hat + 1.96 * se, 4)]
        modern_flips["one_sided_z_vs_threshold"] = round(
            (p_hat - WAIT_THRESHOLD) / se, 3)

    era_analysis = {
        "modern_fit_flips_holdout": modern_flips,
        "rule_registered_before_computing": (
            "meaningful = max bin gap >= 0.05 or any bin straddling the 0.6 "
            "threshold; deploy modern iff meaningful and the 2019-2022 fit "
            "is not worse on the 2023-2025 holdout"),
        "holdout_brier_2013_2022_fit": evaluation["B_isotonic_layer"]["brier"],
        "holdout_brier_2019_2022_fit": eval_modern_fit["brier"],
        "holdout_low_bucket_2019_2022_fit": eval_modern_fit["low_bucket_lt50"],
        "table_all_years": t_all,
        "table_modern_2019_2025": t_modern,
        "max_bin_gap": round(max(gaps), 4),
        "bins_straddling_threshold": straddle,
        "meaningfully_different": meaningful,
        "modern_fit_not_worse_on_holdout": modern_not_worse,
        "decision": era_choice,
    }

    # ---- the flip win-rate interval (Anthony's adoption condition 1).
    # Independence-assumption binomial CI exactly as he computed it, plus
    # the honest caveat: flips cluster (same player across consecutive pick
    # gaps, same draft year), so the true interval is somewhat wider; with
    # only three holdout seasons a cluster interval is too unstable to
    # quote, so the clustering is stated rather than estimated.
    fb = flips["B_isotonic_layer"]
    if fb["n_flips"]:
        p_hat = fb["observed_still_available"]
        se = (p_hat * (1 - p_hat) / fb["n_flips"]) ** 0.5
        fb["win_rate_ci95_binomial"] = [round(p_hat - 1.96 * se, 4),
                                        round(p_hat + 1.96 * se, 4)]
        fb["one_sided_z_vs_threshold"] = round((p_hat - WAIT_THRESHOLD) / se, 3)
        fb["ci_caveat"] = ("binomial CI assumes independent flips; flips "
                           "cluster within players and draft years, so the "
                           "true interval is somewhat wider - stated, not "
                           "estimated (3 holdout seasons is too few for a "
                           "stable cluster interval)")

    payload = {
        "generated": datetime.date.today().isoformat(),
        "status": "PROPOSAL - evidence only; frozen functions untouched; any "
                  "adoption requires Anthony's approval of the exact diff in "
                  "the ADR",
        "era_analysis": era_analysis,
        "diagnosis": diagnosis,
        "fit_window": f"2013-{TRAIN_MAX}",
        "holdout_window": f"{TRAIN_MAX + 1}-2025",
        "isotonic_table_20bin": [round(v, 4) for v in table],
        "isotonic_table_adoption_all_years": [
            round(v, 4) for v in pav(gen_pairs(years, 2013, 2025))],
        "adoption_note": ("the adoption table refits on all 13 years; the "
                          "holdout numbers above are the honest out-of-sample "
                          "estimate of how such a table behaves"),
        "evaluation_holdout": evaluation,
        "wait_or_reach_flips_holdout": flips,
        "provenance": {"pairs_frame": "item 5 replay frame (Anthony's "
                       "consecutive picks x FFC-listed availables)",
                       "frozen_functions": "engine_2026 sd_for/cond_survival, "
                                           "read-only",
                       "km_censoring": "undrafted censored at the year's final "
                                       "pick"},
    }
    json.dump(payload, open(OUT, "w"), indent=1)
    print("diagnosis (standardized differential quantiles, drafted players):")
    print(f"  ffc frame    q75 {diagnosis['ffc_frame']['q75']} q90 "
          f"{diagnosis['ffc_frame']['q90']} q95 {diagnosis['ffc_frame']['q95']}")
    print(f"  archive      q75 {diagnosis['archive_frame']['q75']} q90 "
          f"{diagnosis['archive_frame']['q90']} q95 {diagnosis['archive_frame']['q95']}")
    print(f"  normal ref   q75 0.674 q90 1.282 q95 1.645")
    for name, s in evaluation.items():
        lb = s["low_bucket_lt50"]
        print(f"{name:>18}: brier {s['brier']} skill {s['skill_vs_base_rate']:+.1%} "
              f"low-bucket pred {lb['predicted_mean']} obs {lb['observed']} (n={lb['n']})")
    for name, f in flips.items():
        print(f"{name:>18}: {f['n_flips']} TAKE NOW -> WAIT flips, "
              f"observed available {f['observed_still_available']}")


if __name__ == "__main__":
    main()
