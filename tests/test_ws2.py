#!/usr/bin/env python3
"""C6 guards: the Workstream-2 claims audit artifact.

Validates out/data/ws2_audit_2026.json (committed; the builder needs the
history cache and does not rerun here) and enforces the governance canary:
the report's cited numbers may appear in src/build_ws2_audit.py ONLY inside
the CLAIMS literal and the module docstring - never loose in computation.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "out", "data")
FAILS = []


def ok(cond, label):
    print(("PASS  " if cond else "FAIL  ") + label)
    if not cond:
        FAILS.append(label)


a = json.load(open(os.path.join(D, "ws2_audit_2026.json")))

# provenance and governance statements
prov = a["provenance"]
ok(all(k in prov for k in ("generated", "scoring", "window", "governance",
                           "workstream3")), "provenance block complete")
ok("6-pt pass TD" in prov["scoring"], "scoring basis is league-exact")
ok("methodology only" in prov["workstream3"],
   "workstream 3 adopted as methodology only, nothing imported")

# every audit block is shaped and verdicted
BLOCKS = ("rb_vs_wr_top12", "rb_2025_outlier", "rb1_curse", "elite_rb_gap",
          "overall_rb1_late", "first_time_wr1", "qb1_rush",
          "rb_band_conversion", "team_success_folklore")
ok(set(a["audits"].keys()) == set(BLOCKS), "all nine audit blocks present")
VERDICTS = {"agrees", "partial", "disagrees", "frame_differs", "unverifiable"}
for name, b in a["audits"].items():
    ok(all(k in b for k in ("claim", "computed", "basis", "verdict")),
       f"{name}: claim/computed/basis/verdict present")
    ok(b["verdict"] in VERDICTS, f"{name}: verdict in the allowed set")

# proportions carry n and Wilson CIs; the z-test is coherent
rw = a["audits"]["rb_vs_wr_top12"]["computed"]
for pos in ("RB", "WR"):
    c = rw[pos]
    ok(0 <= c["k"] <= c["n"] and len(c["ci95"]) == 2
       and c["ci95"][0] <= c["k"] / c["n"] <= c["ci95"][1],
       f"rb_vs_wr {pos}: k<=n and CI brackets the rate")
ok(0 <= rw["p_two_sided"] <= 1, "z-test p in [0,1]")
ok(rw["significant_at_05"] == (rw["p_two_sided"] < 0.05),
   "significance flag matches its own p")

# curse ledger internal consistency
cu = a["audits"]["rb1_curse"]["computed"]
with_next = [r for r in cu["rows"] if r["next_ppg"] is not None]
ok(cu["comparable"] == len(with_next), "curse: comparable == rows with a "
                                       "next-season PPG")
ok(cu["declined"] <= cu["comparable"], "curse: declines <= comparable")
ok(cu["declined"] == sum(1 for r in with_next
                         if r["next_ppg"] < r["ppg"]),
   "curse: declined count recomputes from the rows")

# elite gap CI brackets its mean
eg = a["audits"]["elite_rb_gap"]["computed"]
ok(eg["gap_ci95"][0] <= eg["mean_gap"] <= eg["gap_ci95"][1],
   "elite gap: CI brackets the mean")
ok(len(eg["per_season"]) == 10, "elite gap: ten seasons")

# band conversion rows
for r in a["audits"]["rb_band_conversion"]["computed"]["rows"]:
    ok(0 < r["n"] and 0 <= r["k"] <= r["n"] and len(r["ci95"]) == 2,
       f"band {r['band']}: k/n/CI coherent")

# cross-artifact: the curse tag target is our own computed 2025 RB1
late = a["audits"]["overall_rb1_late"]["computed"]["rows"]
rb1_2025 = next(r["rb1"] for r in late if r["year"] == 2025)
arch = json.load(open(os.path.join(D, "archetypes_2026.json")))


def norm(n):
    n = n.lower().replace(".", "").replace("'", "")
    return " ".join(w for w in n.split()
                    if w not in ("jr", "sr", "ii", "iii", "iv", "v"))


tagged = [p["name"] for p in arch["players"]
          if any(t["tag"] == "rb1_curse" for t in p["tags"])]
ok(len(tagged) == 1 and norm(tagged[0]) == rb1_2025,
   "the C3 rb1_curse tag sits on the league-scored 2025 RB1 this audit "
   "computes")

# already-adjudicated pointers reference artifacts that exist
for name, ptr in a["already_adjudicated"].items():
    ok(os.path.exists(os.path.join(D, ptr["artifact"])),
       f"pointer {name}: artifact {ptr['artifact']} exists")

# unverifiable entries carry reasons, and there are exactly the two known
ok(len(a["unverifiable"]) == 2 and
   all(e.get("reason") for e in a["unverifiable"]),
   "unverifiable claims logged with reasons")

# governance canary: cited numerals only inside CLAIMS or the docstring
src = open(os.path.join(ROOT, "src", "build_ws2_audit.py")).read()
body = re.sub(r'\A(#![^\n]*\n)?"""[\s\S]*?"""', "", src, count=1)
body = re.sub(r"CLAIMS = \{[\s\S]*?\n\}\n", "", body, count=1)
ok("CLAIMS = {" not in body, "canary: CLAIMS literal was stripped")
CITED = ("58.3", "44.0", "24.9", "15.1", "16.08", "26.6", "18.1", "13.3",
         "22.2", "8.75", "25.7", "27.4", "62%", "9.7", "350", "360", "4.2")
for tok in CITED:
    ok(tok not in body,
       f"canary: cited value {tok} confined to CLAIMS/docstring")

# workflow and runbook wiring
wf = open(os.path.join(ROOT, ".github", "workflows",
                       "draft-refresh.yml")).read()
ok("test_ws2.py" in wf, "workflow runs the WS2 audit guards")
rb = open(os.path.join(ROOT, "docs", "DRAFT_MORNING.md")).read()
ok("test_ws2.py" in rb, "runbook lists the WS2 audit guards")

if FAILS:
    print(f"\n{len(FAILS)} FAILURES")
    sys.exit(1)
print("\nALL PASS")
