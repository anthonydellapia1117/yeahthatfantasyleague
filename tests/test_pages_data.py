#!/usr/bin/env python3
"""Guards N2 + page-data schema for the expansion shards (Phase A).

Runs WITHOUT network: operates only on committed out/data/*.json.
Run: python3 tests/test_pages_data.py
"""
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "out", "data")
fails = []


def ok(cond, name, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "  -> " + detail))
    if not cond:
        fails.append(name)


def load(shard):
    p = os.path.join(D, f"{shard}.json")
    if not os.path.exists(p):
        return None
    return json.load(open(p))


SHARDS = ["adp", "crosswalk", "reconciliation", "depth_charts", "usage_2025",
          "team_proe_2025", "playcallers", "provenance"]

# 1. Every shard exists and carries provenance (guard N2)
for s in SHARDS:
    d = load(s)
    ok(d is not None, f"shard exists: {s}")
    if d is None:
        continue
    if s != "provenance":
        ok("provenance" in d, f"N2: {s} carries provenance",
           "missing provenance key")

# 2. ADP shard: source stamped, both sources present, band fields live
adp = load("adp")
if adp:
    prov = adp["provenance"]
    ok(prov.get("adp_source") in ("sleeper", "ffc"),
       "N2: adp_source stamped sleeper|ffc", str(prov.get("adp_source")))
    ok("ffc_attribution" in prov, "FFC attribution string present")
    top = adp["players"][:50]
    with_band = sum(1 for p in top if p.get("stdev") is not None)
    ok(with_band >= 35, "market bands present for most of the top 50",
       f"only {with_band}/50")
    ok(all(p.get("adp_sleeper") for p in top), "sleeper ADP present in top 50")

# 3. Crosswalk + reconciliation: unmatched logged, never dropped
xw, rec = load("crosswalk"), load("reconciliation")
if xw and rec and adp:
    n_matched = len(xw["matched"])
    n_unmatched = rec["unmatched_count"]
    total = len(adp["players"])
    ok(n_matched + n_unmatched >= total * 0.9 - 32,
       "crosswalk accounts for ADP players (matched + logged; DEF excluded)",
       f"{n_matched}+{n_unmatched} vs {total}")
    # The guard that matters: DRAFTABLE players (ADP < 250, non-DEF) must match.
    matched_ids = set(xw["matched"])
    draftable = [p for p in adp["players"]
                 if (p.get("adp_sleeper") or 999) < 250 and p["pos"] != "DEF"]
    un_draftable = [p["name"] for p in draftable if p["player_id"] not in matched_ids]
    ok(len(un_draftable) <= max(2, len(draftable) * 0.02),
       "draftable players match at >=98% (suffix-normalized)",
       f"{len(un_draftable)}/{len(draftable)}: {un_draftable[:5]}")

# 4. Depth charts: all 32 teams, as-of date fresh (within 7 days of build)
dc = load("depth_charts")
if dc:
    teams = {e["team"] for e in dc["entries"]}
    ok(len(teams) == 32, "depth charts cover 32 teams", f"{len(teams)}")
    as_of = dc["provenance"].get("as_of", "")[:10]
    try:
        age = (datetime.date.today() - datetime.date.fromisoformat(as_of)).days
        ok(age <= 7, "depth chart as-of within 7 days", f"{age} days ({as_of})")
    except ValueError:
        ok(False, "depth chart as-of parseable", as_of)

# 5. Usage: literal-column basis declared, shares are means of weekly cols
us = load("usage_2025")
if us:
    ok("literal columns" in us["provenance"].get("basis", ""),
       "usage shard declares its literal-column basis")
    top = us["players"][:100]
    ok(all(0 <= (p.get("target_share_mean") or 0) <= 1 for p in top),
       "share fields bounded in [0,1]")

# 6. PROE: plausible range (league PROE means sit within a few points of zero)
pr = load("team_proe_2025")
if pr:
    vals = [t["proe_2025"] for t in pr["teams"] if t["proe_2025"] is not None]
    ok(len(vals) == 32, "PROE for 32 teams", f"{len(vals)}")
    ok(all(-15 <= v <= 15 for v in vals), "PROE values in plausible band",
       f"range {min(vals)}..{max(vals)}")

# 7. Playcallers: curated file rendered with tags; count matches addendum
pc = load("playcallers")
if pc:
    ok(len(pc["callers"]) == 19, "19 play-caller rows per addendum",
       f"{len(pc['callers'])}")
    ok(all(r.get("tag") in ("VERIFIED-LIVE", "SOURCED", "REPORTED")
           for r in pc["callers"]), "every play-caller row tagged")
    ok(all(r.get("source_url") for r in pc["callers"]),
       "every play-caller row carries a source URL")

# 8. N1 (intel isolation, standing guard): no team-intel field name appears in
#    the engine's decision payload. The engine does not read out/data/; this
#    guard catches anyone wiring it in later.
eng_path = os.path.join(ROOT, "src", "engine_2026.py")
src = open(eng_path).read()
ok("build_pages_data" not in src and "team_proe" not in src and "playcallers" not in src,
   "N1: engine imports nothing from the pages-data layer")

# 9. Heartbeat exists (Actions keepalive)
ok(os.path.exists(os.path.join(D, "heartbeat.txt")), "heartbeat file present")

# 10. PHASE C PLAYER PAGES. Acceptance: every number the page renders traces
#     to a real shard field. The page marks each one pv(value, shard, field);
#     this guard resolves every reference against the committed shards.
import re

pp = os.path.join(ROOT, "out", "players.html")
ok(os.path.exists(pp), "players.html exists")
if os.path.exists(pp):
    page = open(pp).read()
    # anchored on the trailing (shard, field) string args so pv() calls whose
    # value argument itself contains parentheses are still captured
    refs = set(re.findall(r',\s*"([A-Za-z0-9_]+\.json)"\s*,\s*"([A-Za-z0-9_]+)"\s*\)', page))
    ok(len(refs) >= 15, "page carries tappable provenance references",
       f"only {len(refs)}")
    # field universe per shard, from the committed files themselves
    fields = {}
    if adp:
        fields["adp.json"] = set().union(*(set(p) for p in adp["players"][:300]))
    if us:
        fields["usage_2025.json"] = set().union(*(set(p) for p in us["players"][:300]))
    if xw:
        fields["crosswalk.json"] = set().union(
            *(set(v) for v in list(xw["prospect"].values())[:300]))
    epath = os.path.join(ROOT, "out", "engine_2026.json")
    em = json.load(open(epath))
    fields["engine_2026.json"] = set().union(
        *(set(p) for p in em["players"][:300])) | {"vor_rank"}
    bad = [f"{s}:{f}" for s, f in refs
           if s not in fields or f not in fields[s]]
    ok(not bad, "every page-data reference resolves to a shard field",
       "; ".join(bad[:5]))
    ok("Provenance (guard N2)" in page, "provenance footer present")
    ok("ffc_attribution" in page, "FFC attribution rendered from the shard")
    ok("projection = floor" in page and "kdef_note" in page,
       "K/DST floor label and note wired")
    ok("no free in-season source" in page.lower()
       or "prior season - no free in-season source" in page,
       "route/usage metrics carry the prior-season honesty label")
    ok("Nothing on this page is estimated" in page,
       "absent blocks declared absent, not estimated")

# 11. PHASE D TEAM PAGES. Same acceptance as the player pages: every number
#     traces to a shard field, and every instrument shows its computation note.
tp_page = os.path.join(ROOT, "out", "teams.html")
ok(os.path.exists(tp_page), "teams.html exists")
if os.path.exists(tp_page):
    tpage = open(tp_page).read()
    trefs = set(re.findall(r',\s*"([A-Za-z0-9_]+\.json)"\s*,\s*"([A-Za-z0-9_]+)"\s*\)', tpage))
    ok(len(trefs) >= 8, "team page carries tappable provenance references",
       f"only {len(trefs)}")
    tfields = {}
    if pc:
        tfields["playcallers.json"] = set().union(*(set(r) for r in pc["callers"]))
    if pr:
        tfields["team_proe_2025.json"] = set().union(*(set(t) for t in pr["teams"]))
    if dc:
        tfields["depth_charts.json"] = set().union(*(set(e) for e in dc["entries"][:300]))
    if us:
        tfields["usage_2025.json"] = set().union(*(set(p) for p in us["players"][:300]))
    epath = os.path.join(ROOT, "out", "engine_2026.json")
    em2 = json.load(open(epath))
    tfields["engine_2026.json"] = set().union(*(set(p) for p in em2["players"][:300]))
    tbad = [f"{s}:{f}" for s, f in trefs if s not in tfields or f not in tfields[s]]
    ok(not tbad, "every team-page reference resolves to a shard field",
       "; ".join(tbad[:5]))
    ok(tpage.count("computation:") >= 4,
       "every instrument shows its computation note",
       f"only {tpage.count('computation:')}")
    ok("N1" in tpage and "p=0.99" in tpage,
       "team page states the N1 display-only rule with the backtest number")
    ok("Provenance (guard N2)" in tpage, "team page provenance footer present")
    ok("not zero" in tpage and "Nothing on this page is estimated" in tpage,
       "team page declares absent data absent")

# 12. PHASE E HOME PAGE. The action board: countdown from the payload (not a
#     second hardcode), staleness thresholds stated, overlay completeness from
#     the engine payload, trending attributed, all four surfaces linked, and
#     the history fact carried WITH its p-value caveat.
hp = os.path.join(ROOT, "out", "home.html")
ok(os.path.exists(hp), "home.html exists")
if os.path.exists(hp):
    hpage = open(hp).read()
    ok("E.league.draft_date" in hpage,
       "countdown reads the draft date from the engine payload")
    ok("Fresh under 36h" in hpage and "aging under 7 days" in hpage,
       "staleness thresholds stated on the board")
    ok(all(f'href="{s}"' in hpage for s in
           ("draft_room.html", "players.html", "teams.html", "ff-hub.html")),
       "home links every surface")
    ok("0 times in 13 seasons" in hpage and "p=0.323" in hpage
       and "not significant" in hpage,
       "history fact carries its p-value and the honesty caveat")
    ok("trending" in hpage and "never a projection" in hpage,
       "trending adds attributed and labelled non-projection")
    ok("25-call grading floor" in hpage or "25 calls" in hpage,
       "overlay completeness states the grading floor")
    ok("my_board" in hpage and "byte-identical" in hpage,
       "overlay card explains the empty-board guarantee")

print()
print(f"{len(fails)} FAILURES" if fails else "ALL PASS")
sys.exit(1 if fails else 0)
