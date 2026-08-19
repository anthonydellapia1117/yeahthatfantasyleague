#!/usr/bin/env python3
"""Guards on the analytical layer (items 2-5). Each pins a law from the
increment's commission: walk-forward honesty, seeded determinism, and
verdicts that follow their own intervals.

Run: python3 tests/test_analysis.py  (after the analysis scripts)
"""
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

fails = []


def ok(cond, name, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "  -> " + str(detail)))
    if not cond:
        fails.append(name)


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- item 2: manager-profile backtest
bp = load_mod("bp", "src/backtest_profiles.py")
B = json.load(open(os.path.join(ROOT, "out", "data", "manager_profiles_backtest.json")))

# 1. walk-forward honesty: train() must never see the evaluation season -
#    a poisoned future row changes nothing about the trained model
rows = [{"season": "2015", "round": "1", "pos": "RB", "member_name": "X"},
        {"season": "2015", "round": "1", "pos": "RB", "member_name": "Y"},
        {"season": "2014", "round": "1", "pos": "WR", "member_name": "X"}]
poison = rows + [{"season": "2016", "round": "1", "pos": "QB", "member_name": "X"},
                 {"season": "2020", "round": "1", "pos": "QB", "member_name": "X"}]
m_clean = bp.train(rows, 2016)
m_poison = bp.train(poison, 2016)
ok(m_clean[0] == m_poison[0] and dict(m_clean[1]) == dict(m_poison[1]),
   "item2: train() is blind to seasons at or after the evaluation season")

# 2. the coverage rule: under 2 prior drafts falls back to the league prior
probs, used = bp.predict(m_clean, "Y", "rd1-3")
ok(not used, "item2: a one-draft franchise falls back to league priors")

# 3. predictions are proper distributions
probs2, _ = bp.predict(m_clean, "X", "rd1-3")
ok(abs(sum(probs2.values()) - 1.0) < 1e-9 and all(v >= 0 for v in probs2.values()),
   "item2: predicted position probabilities are a proper distribution")

# 4. the verdict follows the interval - never the other way round
lo, hi = B["logloss"]["delta_ci95_season_bootstrap"]
v = B["verdict"]
ok((v == "profiles_beat_priors") == (lo > 0)
   and (v == "priors_beat_profiles") == (hi < 0),
   "item2: verdict is exactly what the bootstrap interval says", f"{v} [{lo},{hi}]")

# 5. seeded determinism: the committed payload reproduces from committed inputs
import io, contextlib
out_path = os.path.join(ROOT, "out", "data", "manager_profiles_backtest.json")
orig = open(out_path, "rb").read()
with contextlib.redirect_stdout(io.StringIO()):
    bp.main()
B2 = json.load(open(out_path))
open(out_path, "wb").write(orig)
a, b = dict(B), dict(B2)
a.pop("generated", None); b.pop("generated", None)
ok(json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True),
   "item2: backtest reproduces exactly from committed inputs (generated aside)")

# 6. isolation: the backtest script touches no engine code and no UI
src = open(os.path.join(ROOT, "src", "backtest_profiles.py")).read()
ok("import engine" not in src and "draft_room" not in src and "cvs" not in src.lower(),
   "item2: backtest imports no engine, touches no page, reads no CVS")

# ---- item 3: recency-bias coefficient
ar = load_mod("ar", "src/analyze_recency.py")
R = json.load(open(os.path.join(ROOT, "out", "data", "recency_bias.json")))

# 7. the verdict follows the interval, and the usage rule follows the verdict
lo, hi = R["b_late_ci95_season_bootstrap"]
ok(R["distinguishable_from_zero"] == (hi < 0 or lo > 0),
   "item3: distinguishable flag is exactly what the interval says")
ok(R["distinguishable_from_zero"] or R["direction"] == "none_established",
   "item3: no effect size, no direction claim - the usage rule holds")

# 8. unit behavior of the estimator: zscore centering and a known OLS solve
zs = ar.zscore([1.0, 2.0, 3.0])
ok(abs(sum(zs)) < 1e-9 and abs(zs[2] - (-zs[0])) < 1e-9,
   "item3: zscore centers and is symmetric")
beta = ar.ols([[1.0, 0.0], [1.0, 1.0], [1.0, 2.0]], [1.0, 3.0, 5.0])
ok(abs(beta[0] - 1.0) < 1e-9 and abs(beta[1] - 2.0) < 1e-9,
   "item3: OLS recovers a known line exactly")

# 9. every league draft season is in the sample and coverage is reported
ok(R["seasons"] == list(range(2013, 2026))
   and all(str(y) in R["coverage_by_year"] for y in range(2013, 2026)),
   "item3: all 13 draft years covered with per-year exclusion accounting")

# 10. determinism (only when the fetched history cache is present - the raw
#     downloads are not committed)
if os.path.exists(os.path.join(ar.HISTORY, "spw_2012.csv")):
    out_path = os.path.join(ROOT, "out", "data", "recency_bias.json")
    orig = open(out_path, "rb").read()
    with contextlib.redirect_stdout(io.StringIO()):
        ar.main()
    R2 = json.load(open(out_path))
    open(out_path, "wb").write(orig)
    a, b = dict(R), dict(R2)
    a.pop("generated", None); b.pop("generated", None)
    ok(json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True),
       "item3: regression reproduces exactly from cached inputs (generated aside)")
else:
    print("SKIP  item3 determinism rerun - history cache absent (fetch with "
          "src docs; committed payload guards above still ran)")

# ---- item 4: injury market inefficiency
I = json.load(open(os.path.join(ROOT, "out", "data", "injury_market.json")))

# 11. the agreement rule: a verdict other than "none" requires both burden
#     measures to agree AND at least one relevant interval excluding zero
def dirs(r):
    A, B = r["league_response"], r["outcome_justification"]
    a = "fades" if A["distinguishable"] and A["b"] > 0 else \
        "pays_up" if A["distinguishable"] else "follows_market"
    b = "justified" if B["distinguishable"] and B["b"] < 0 else \
        "outperform_at_price" if B["distinguishable"] else "no_outcome_signal"
    return a, b
d1, d2 = dirs(I["results"]["inj_desig"]), dirs(I["results"]["games_missed"])
ok(I["burden_measures_agree"] == (d1 == d2),
   "item4: the agreement flag matches the two burden measures")
if I["verdict"] != "no_inefficiency_established":
    ok(d1 == d2, "item4: a positive verdict requires burden-measure agreement")
else:
    ok(True, "item4: verdict is no-inefficiency (agreement rule or null results)")

# 12. every distinguishable flag matches its own interval
bad = [f"{m}.{k}" for m, r in I["results"].items() for k, v in r.items()
       if v["distinguishable"] != (v["ci95"][1] < 0 or v["ci95"][0] > 0)]
ok(not bad, "item4: distinguishable flags follow their intervals", "; ".join(bad))

# 13. the zero-game veterans (season-long absentees) are IN the sample -
#     they are the most injury-discounted players and must not be dropped
kept = sum(c["zero_game_veterans_kept"] for c in I["coverage_by_year"].values())
ok(kept > 0, "item4: season-long absentee veterans retained in the sample",
   str(kept))

# 14. determinism (cache-gated like item 3)
sys.path.insert(0, os.path.join(ROOT, "src"))
import analyze_recency as _base
if os.path.exists(os.path.join(_base.HISTORY, "inj_2012.csv")):
    import analyze_injury as ai
    out_path = os.path.join(ROOT, "out", "data", "injury_market.json")
    orig = open(out_path, "rb").read()
    with contextlib.redirect_stdout(io.StringIO()):
        ai.main()
    I2 = json.load(open(out_path))
    open(out_path, "wb").write(orig)
    a, b = dict(I), dict(I2)
    a.pop("generated", None); b.pop("generated", None)
    ok(json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True),
       "item4: analysis reproduces exactly from cached inputs (generated aside)")
else:
    print("SKIP  item4 determinism rerun - history cache absent")

# ---- item 5: replay backtest
P = json.load(open(os.path.join(ROOT, "out", "data", "replay_backtest.json")))

# 15. the honesty pins: what cannot be replayed is stated, and the proxy
#     carries its caveat on its face
ok(len(P["not_replayable_stated"]) >= 3
   and "rookie" in P["part1_value_core"]["proxy_caveat"],
   "item5: non-replayable inputs stated; proxy caveat names the rookie hole")

# 16. internal consistency: the reported deltas equal the reported means
m5 = P["part1_value_core"]["mean_realized_pts"]
d5 = P["part1_value_core"]["deltas_per_pick"]
ok(abs(d5["actual_minus_adp_best"]["mean"] - (m5["actual"] - m5["adp_best"])) < 0.02
   and abs(d5["actual_minus_replay_vor"]["mean"] - (m5["actual"] - m5["replay_vor"])) < 0.02,
   "item5: deltas equal their means; nothing hand-adjusted")
ok(all(v["ci95"][0] <= v["mean"] <= v["ci95"][1] for v in d5.values()),
   "item5: every point estimate sits inside its own interval")

# 17. calibration arithmetic: skill is exactly 1 - brier/base, deciles
#     account for every pair
c5 = P["part2_survival_calibration"]
ok(abs(c5["skill_vs_base_rate"]
       - (1 - c5["brier"] / c5["brier_always_base_rate"])) < 1e-3,
   "item5: survival skill score recomputes from its own briers")
ok(sum(d["n"] for d in c5["reliability_by_decile"]) == c5["n_pairs"],
   "item5: reliability deciles account for every evaluated pair")
ok(sum(e["n_pairs"] for e in c5["by_era"].values()) == c5["n_pairs"],
   "item5: era splits partition the pairs exactly")

# 18. the frozen functions are consumed read-only: the replay never assigns
#     into the engine module or refits its curve
rsrc = open(os.path.join(ROOT, "src", "replay_backtest.py")).read()
ok("import engine_2026" in rsrc and "eng." in rsrc
   and "ADP_SD_CURVE =" not in rsrc
   and not any(l.strip().startswith("eng.") and "=" in l.split("#")[0]
               and "==" not in l for l in rsrc.splitlines()),
   "item5: frozen survival consumed read-only, never reassigned or refitted")

# 19. determinism (cache-gated)
if os.path.exists(os.path.join(_base.HISTORY, "ffc_ppr_2013.json")):
    import replay_backtest as rb
    out_path = os.path.join(ROOT, "out", "data", "replay_backtest.json")
    orig = open(out_path, "rb").read()
    with contextlib.redirect_stdout(io.StringIO()):
        rb.main()
    P2 = json.load(open(out_path))
    open(out_path, "wb").write(orig)
    a, b = dict(P), dict(P2)
    a.pop("generated", None); b.pop("generated", None)
    ok(json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True),
       "item5: replay reproduces exactly from cached inputs (generated aside)")
else:
    print("SKIP  item5 determinism rerun - history cache absent")

# ---- item 4 follow-up: durability-fade investigation
D = json.load(open(os.path.join(ROOT, "out", "data", "durability_fade.json")))

# 20. the pre-registered verdict rule recomputes from the payload's own
#     numbers - full_ctrl must exclude zero AND both era signs negative
fc = D["specs"]["full_ctrl"]
eras_neg = all(e["b"] < 0 for e in D["eras_full_ctrl"].values())
want = ("durability_fade_real"
        if fc["distinguishable"] and fc["b"] < 0 and eras_neg
        else "confounded_or_unstable")
ok(D["verdict"] == want, "durability: verdict recomputes from its own rule",
   f"{D['verdict']} vs {want}")
ok((D["verdict"] == "durability_fade_real") == ("gated decision" in D["recommendation"]),
   "durability: recommendation follows the verdict")

# 21. every spec interval matches its flag; age coverage is accounted
bad = [k for k, v in D["specs"].items() if "ci95" in v
       and v["distinguishable"] != (v["ci95"][1] < 0 or v["ci95"][0] > 0)]
ok(not bad, "durability: distinguishable flags follow their intervals",
   "; ".join(bad))
ok("players_without_birth_date" in D,
   "durability: age-control coverage stated")

# 22. determinism (cache-gated on the roster files)
if os.path.exists(os.path.join(_base.HISTORY, "roster_2013.csv")):
    import analyze_durability as ad
    out_path = os.path.join(ROOT, "out", "data", "durability_fade.json")
    orig = open(out_path, "rb").read()
    with contextlib.redirect_stdout(io.StringIO()):
        ad.main()
    D2 = json.load(open(out_path))
    open(out_path, "wb").write(orig)
    a, b = dict(D), dict(D2)
    a.pop("generated", None); b.pop("generated", None)
    ok(json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True),
       "durability: reproduces exactly from cached inputs (generated aside)")
else:
    print("SKIP  durability determinism rerun - roster cache absent")

# ---- item 5 follow-up: survival recalibration proposal
S = json.load(open(os.path.join(ROOT, "out", "data",
                                "survival_recalibration.json")))

# 23. proposal status is explicit and the frozen functions are consumed
#     read-only by the proposal script
ok(S["status"].startswith("PROPOSAL"),
   "calibration: payload states PROPOSAL - nothing adopted")
csrc = open(os.path.join(ROOT, "src", "analyze_survival_calibration.py")).read()
ok("import engine_2026" in csrc and "ADP_SD_CURVE =" not in csrc
   and not any(l.strip().startswith("eng.") and "=" in l.split("#")[0]
               and "==" not in l for l in csrc.splitlines()),
   "calibration: frozen survival consumed read-only")

# 24. both isotonic tables are monotone non-decreasing in [0, 1]
for key in ("isotonic_table_20bin", "isotonic_table_adoption_all_years"):
    t = S[key]
    ok(len(t) == 20 and all(0 <= v <= 1 for v in t)
       and all(t[i] <= t[i + 1] + 1e-9 for i in range(19)),
       f"calibration: {key} is a monotone probability table")

# 25. flip accounting is internally consistent
for name, f in S["wait_or_reach_flips_holdout"].items():
    ok(f["n_flips"] <= f["of_holdout_pairs"]
       and (f["n_flips"] == 0 or 0 <= f["observed_still_available"] <= 1),
       f"calibration: {name} flip accounting consistent")

# 26. all three models evaluated on the same holdout pairs
ns = {v["n"] for v in S["evaluation_holdout"].values()}
ok(len(S["evaluation_holdout"]) == 3 and len(ns) == 1,
   "calibration: frozen and both candidates share one holdout frame")

# 27. determinism (cache-gated)
if os.path.exists(os.path.join(_base.HISTORY, "ffc_ppr_2013.json")):
    import analyze_survival_calibration as asc
    out_path = os.path.join(ROOT, "out", "data", "survival_recalibration.json")
    orig = open(out_path, "rb").read()
    with contextlib.redirect_stdout(io.StringIO()):
        asc.main()
    S2 = json.load(open(out_path))
    open(out_path, "wb").write(orig)
    a, b = dict(S), dict(S2)
    a.pop("generated", None); b.pop("generated", None)
    ok(json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True),
       "calibration: reproduces exactly from cached inputs (generated aside)")
else:
    print("SKIP  calibration determinism rerun - history cache absent")

print()
print(f"{len(fails)} FAILURES" if fails else "ALL PASS")
sys.exit(1 if fails else 0)
