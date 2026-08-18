#!/usr/bin/env python3
"""Guards on the CVS layer. Each pins a law from MODEL.md.

Run: python3 tests/test_cvs.py  (after src/build_cvs.py)
"""
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
spec = importlib.util.spec_from_file_location(
    "cvsmod", os.path.join(ROOT, "src", "build_cvs.py"))
cvsmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cvsmod)

fails = []


def ok(cond, name, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "  -> " + detail))
    if not cond:
        fails.append(name)


C = json.load(open(os.path.join(ROOT, "out", "cvs.json")))
cfg = C["config"]
players = C["players"]

# 1. z-score unit behavior: mean 0, unit spread, None passthrough, degenerate
zs = cvsmod.zscores([1.0, 2.0, 3.0, None, 4.0])
ok(zs[3] is None and abs(sum(z for z in zs if z is not None)) < 1e-9,
   "zscores: None passes through, present values center on zero")
ok(all(z == 0.0 for z in cvsmod.zscores([5.0, 5.0, 5.0, 5.0])),
   "zscores: degenerate spread collapses to zeros, never divides by zero")

# 2. the anchor law: cvs_base = VOR + sum of non-baseline contributions, and
#    cvs = cvs_base + ref_pos * capped_pct/100 where ref_pos is the
#    within-position SD of cvs_base (even authority across the range;
#    sign-safe because the reference is positive). The payload's echoed
#    references must match an independent recomputation.
import statistics
refs = {}
for pos in ("QB", "RB", "WR", "TE"):
    vals = [p["cvs_base"] for p in players if p["pos"] == pos]
    refs[pos] = max(statistics.pstdev(vals), 1.0) if len(vals) > 1 else 1.0
bad = [f"{pos}:{refs[pos]:.2f}!={C['walter_reference_points'][pos]}"
       for pos in refs
       if abs(refs[pos] - C["walter_reference_points"][pos]) > 0.25]
ok(not bad, "walter reference = within-position SD of cvs_base, echoed "
   "truthfully in the payload", "; ".join(bad))
bad = [p["name"] for p in players
       if abs(p["cvs_base"] - (p["vor"] + sum(
           f["contribution"] for f in p["factors"]
           if f["factor"] != "baseline_projection"))) > 0.1
       or abs(p["cvs"] - (p["cvs_base"] + refs[p["pos"]]
                          * p["walter"]["capped_pct"] / 100)) > 0.15]
ok(not bad, "anchor law: every CVS decomposes exactly into VOR + factor "
   "contributions, then the capped walter percentage of the positional "
   "reference", "; ".join(bad[:3]))
# sign safety directly: a positive capped pct never lowers cvs, a negative
# one never raises it
bad = [p["name"] for p in players
       if (p["walter"]["capped_pct"] > 0 and p["cvs"] < p["cvs_base"] - 1e-9)
       or (p["walter"]["capped_pct"] < 0 and p["cvs"] > p["cvs_base"] + 1e-9)]
ok(not bad, "walter sign safety: endorsements only raise, fades only lower",
   "; ".join(bad[:3]))

# 3. null handling: null factors contribute zero and confidence reports the
#    covered weight share exactly
W = cfg["factor_weights"]
wsum = sum(W.values())
bad = []
for p in players:
    nulls = [f for f in p["factors"] if f["raw"] is None]
    if any(f["contribution"] != 0.0 for f in nulls):
        bad.append(p["name"] + ":null-contrib")
    present = sum(f["weight"] for f in p["factors"] if f["raw"] is not None)
    if abs(p["confidence"] - present / wsum) > 0.002:
        bad.append(p["name"] + ":conf")
ok(not bad, "null factors contribute nothing; confidence equals the covered "
   "weight share", "; ".join(bad[:3]))

# 4. the cap is absolute: no capped delta beyond walter_cap_pct, and
#    was_capped implies the proposed total actually exceeded it
cap = cfg["walter_cap_pct"]
bad = [p["name"] for p in players
       if abs(p["walter"]["capped_pct"]) > cap + 1e-9
       or (p["walter"]["was_capped"]
           and abs(p["walter"]["proposed_pct"]) <= cap)]
ok(not bad, f"walter cap: no player moves more than {cap}% and was_capped is "
   "truthful", "; ".join(bad[:3]))

# 5. kill-switch honesty: with walter_enabled, every applied delta carries its
#    quote and line reference (a rank that moved must say why)
bad = [p["name"] for p in players for a in p["walter"]["applied"]
       if not a.get("quote") or not a.get("lines")]
ok(not bad, "every applied walter delta carries its quote and line reference",
   "; ".join(bad[:3]))

# 6. K and DST are excluded from CVS (their projections are floors)
ok(all(p["pos"] in ("QB", "RB", "WR", "TE") for p in players),
   "K and DST stay off the CVS board - floors are not comparable values")

# 7. signal precedence: personal BEAR always wins; consensus labels require
#    both sources; conflict flag set whenever opposing signals coexist
def whas(p, tag):
    return any(a["tag"] == tag for a in p["walter"]["applied"])
bad = []
for p in players:
    if p["personal"] == "BEAR" and p["signal"] != "personal_dnd":
        bad.append(p["name"] + ":personal")
    if p["signal"] == "consensus_dnd" and not (
            whas(p, "do_not_draft") and p["model_flags"]["do_not_draft"]):
        bad.append(p["name"] + ":consensus")
    neg = p["personal"] == "BEAR" or whas(p, "do_not_draft") \
        or p["model_flags"]["do_not_draft"]
    posv = (whas(p, "target") or whas(p, "sleeper")
            or whas(p, "recency_bias_target") or whas(p, "strategy_pick")
            or p["model_flags"]["target"] or p["model_flags"]["sleeper"]
            or p["personal"] == "BULL")
    if (neg and posv) != p["signal_conflict"]:
        bad.append(p["name"] + ":conflict-flag")
ok(not bad, "signal precedence and conflict flags hold for every player",
   "; ".join(bad[:3]))

# 7b. the no-walter board: server-ranked, ordered by cvs_base, no consensus
#     states possible, conflicts from personal + model sources only
nw = sorted(players, key=lambda p: p["no_walter"]["cvs_rank"])
ok([p["no_walter"]["cvs_rank"] for p in nw] == list(range(1, len(nw) + 1))
   and all(nw[i]["cvs_base"] >= nw[i + 1]["cvs_base"] for i in range(len(nw) - 1)),
   "no-walter ranks are a strict cvs_base ordering (kill-switch is a "
   "display swap, never a client rerank)")
bad = [p["name"] for p in players
       if (p["no_walter"]["signal"] or "").startswith("consensus")]
ok(not bad, "no-walter board carries no consensus signal - walter is truly off",
   "; ".join(bad[:3]))
bad = []
for p in players:
    nm = p["no_walter"]["model_flags"]
    neg = p["personal"] == "BEAR" or nm["do_not_draft"]
    posv = nm["target"] or nm["sleeper"] or p["personal"] == "BULL"
    if (neg and posv) != p["no_walter"]["signal_conflict"]:
        bad.append(p["name"])
ok(not bad, "no-walter conflicts recompute from personal + model only",
   "; ".join(bad[:3]))

# 7c. tier moves: only players with a live delta, from != to, direction
#     consistent with the delta sign, and the named list matches the flags
tm_names = {(m["name"], m["pos"]) for m in C["walter_tier_moves"]}
bad = []
for p in players:
    mv = p["walter"].get("tier_move")
    if mv:
        if not p["walter"]["capped_pct"] or mv["from"] == mv["to"]:
            bad.append(p["name"] + ":shape")
        d = p["walter"]["delta_points"]
        if (d > 0) != (mv["to"] < mv["from"]):
            bad.append(p["name"] + ":direction")
        if (p["name"], p["pos"]) not in tm_names:
            bad.append(p["name"] + ":unlisted")
ok(not bad and len(tm_names) == sum(1 for p in players if p["walter"].get("tier_move")),
   "tier-boundary moves are own-delta, directional, and named in the list",
   "; ".join(bad[:3]))

# 8. crossmap agreement values are directionally sound
valid = {"agree", "disagree", "disagree_strong", "no_data"}
bad = []
for x in C["regression_crossmap"]:
    if x["agreement"] not in valid:
        bad.append(x["name"])
    if x["agreement"] == "agree":
        okdir = ((x["walter_direction"] == "negative"
                  and x["model_says"] == "high_outlier")
                 or (x["walter_direction"] == "positive"
                     and x["model_says"] == "low_outlier"))
        if not okdir:
            bad.append(x["name"] + ":dir")
ok(not bad, "regression crossmap agreements are directionally verified",
   "; ".join(bad[:3]))

# 9. isolation: the CVS builder never touches the engine or the frozen math,
#    and the engine never reads CVS
src = open(os.path.join(ROOT, "src", "build_cvs.py")).read()
ok("import draft_board" not in src and "engine_2026 import" not in src
   and "survival(" not in src,
   "build_cvs imports no engine code and computes no survival")
esrc = open(os.path.join(ROOT, "src", "engine_2026.py")).read()
ok("cvs" not in esrc.lower(),
   "the engine (verdict source of truth) never reads CVS")

# 10. determinism: a rebuild reproduces the payload from committed inputs.
#     The generated stamp is the one date-of-run field, so it is excluded;
#     the original file bytes are restored afterwards - a guard must never
#     leave the working tree changed.
import io, contextlib
cvs_path = os.path.join(ROOT, "out", "cvs.json")
orig_bytes = open(cvs_path, "rb").read()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    cvsmod.main()
C2 = json.load(open(cvs_path))
open(cvs_path, "wb").write(orig_bytes)
a, b = dict(C), dict(C2)
a.pop("generated", None); b.pop("generated", None)
ok(json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True),
   "rebuild is deterministic from committed inputs (generated stamp aside)")

print()
print(f"{len(fails)} FAILURES" if fails else "ALL PASS")
sys.exit(1 if fails else 0)
