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

print()
print(f"{len(fails)} FAILURES" if fails else "ALL PASS")
sys.exit(1 if fails else 0)
