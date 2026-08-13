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

# 13. APP SHELL (Phase 1). One nav, five pages: nav.js is the single source
#     of truth, every link target exists, every page includes it exactly once
#     with a distinct active key, and on the draft room the include lives
#     OUTSIDE the engine sentinels so regeneration can never touch it.
navp = os.path.join(ROOT, "out", "nav.js")
ok(os.path.exists(navp), "nav.js exists (single source of truth)")
if os.path.exists(navp):
    navsrc = open(navp).read()
    nav_items = re.findall(r'\["(\w+)",\s*"[^"]+",\s*"([^"]+)"\]', navsrc)
    ok(len(nav_items) == 5, "nav defines exactly five items", f"{len(nav_items)}")
    missing = [href for _, href in nav_items
               if not os.path.exists(os.path.join(ROOT, "out", href))]
    ok(not missing, "every nav link target resolves to a real file",
       "; ".join(missing))
    PAGES = {"draft_room.html": "draft", "players.html": "players",
             "teams.html": "teams", "ff-hub.html": "findings",
             "home.html": "hub"}
    seen_keys = []
    for fname, want in PAGES.items():
        psrc = open(os.path.join(ROOT, "out", fname)).read()
        tags = re.findall(r'<script src="nav\.js" data-active="(\w+)"[^>]*\bdefer\b[^>]*></script>', psrc)
        ok(tags == [want], f"{fname} includes the shared nav once, active={want}",
           str(tags))
        seen_keys += tags
        # the old ad-hoc navs must be gone - one navigation system per page
        ok('<nav class="small">' not in psrc,
           f"{fname} carries no second navigation system")
    ok(sorted(seen_keys) == sorted(k for k, _ in nav_items),
       "each active key is used exactly once across the five pages")
    dr = open(os.path.join(ROOT, "out", "draft_room.html")).read()
    tag_at = dr.index('src="nav.js"')
    ok(tag_at < dr.index('<script id="engine-data"'),
       "draft room nav include sits OUTSIDE (before) the engine sentinels")
    ok("nav.js" in open(os.path.join(ROOT, ".github", "workflows", "pages.yml")).read(),
       "pages workflow deploys nav.js")

# 14. APP SHELL (Phase 2). Token, layout, and header consistency: one dark
#     family (#0b1120, ff-hub's), one container width, one kicker treatment -
#     and the semantic verdict colors did not move.
ALL_PAGES = ["draft_room.html", "players.html", "teams.html", "home.html",
             "ff-hub.html"]
_tokened = ["draft_room.html", "players.html", "teams.html", "home.html"]
for fname in ALL_PAGES:
    psrc = open(os.path.join(ROOT, "out", fname)).read()
    ok("#0A0E1A" not in psrc and "0a0e1a" not in psrc.lower()
       or fname not in _tokened,
       f"{fname}: old dark background family fully retired")
    ok("max-width:1100px" in psrc, f"{fname}: shared 1100px container")
    ok('class="kick"' in psrc, f"{fname}: kicker header treatment present")
for fname in _tokened:
    psrc = open(os.path.join(ROOT, "out", fname)).read()
    ok("--bg:#0b1120" in psrc, f"{fname}: dark bg aligned to #0b1120")
    ok("--go:#34D399" in psrc and "--stop:#F87171" in psrc
       and "--warn:#FBBF24" in psrc,
       f"{fname}: semantic verdict colors did not move")
ok(".kick{" in open(navp).read(), "kicker style lives in nav.js (single source)")

# 15. APP SHELL (Phase 3). Polish stays inside its fence: reveals are opt-in
#     per page and the draft room never opts in; hover is a border-color lift
#     only; reduced-motion turns everything off.
navsrc2 = open(navp).read()
ok("data-reveal" not in open(os.path.join(ROOT, "out", "draft_room.html")).read(),
   "draft room NEVER carries the reveal attribute")
for fname in ("players.html", "teams.html", "home.html", "ff-hub.html"):
    ok("data-reveal" in open(os.path.join(ROOT, "out", fname)).read(),
       f"{fname} opts into the phase 3 polish")
ok("prefers-reduced-motion:no-preference" in navsrc2
   and "prefers-reduced-motion: reduce" in navsrc2,
   "every phase 3 animation is fenced behind motion preference")
ok("translateY(8px)" in navsrc2 and ".4s" in navsrc2,
   "reveal is the specified 8px rise at 400ms")
ok("box-shadow" not in navsrc2 and "scale(" not in navsrc2,
   "hover lift is border-color only - no shadows, no transforms")

# 16. DARK LOCK. The hub matches a dark-only design target and must never
#     repaint on an OS theme flip - least of all mid-draft at sunset. No page
#     may carry a color-scheme preference rule; every page declares dark to
#     the browser so form controls and chrome match.
for fname in ALL_PAGES:
    psrc = open(os.path.join(ROOT, "out", fname)).read()
    ok("prefers-color-scheme" not in psrc,
       f"{fname}: no color-scheme preference rule - dark always")
    ok("data-theme" not in psrc,
       f"{fname}: no theme-attribute escape hatch either")
    ok('<meta name="color-scheme" content="dark">' in psrc,
       f"{fname}: declares color-scheme dark to the browser")
ok("prefers-color-scheme" not in navsrc2,
   "nav.js carries no color-scheme preference rule")

# 17. CONTRAST GUARD (the white-card fix). WCAG ratios are COMPUTED here from
#     the committed token values, never hardcoded as expected numbers - if a
#     future token change breaks legibility this section fails loudly.
def _srgb_lum(hexcolor):
    h = hexcolor.lstrip("#")
    chans = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        chans.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * chans[0] + 0.7152 * chans[1] + 0.0722 * chans[2]

def _contrast(a, b):
    la, lb = _srgb_lum(a), _srgb_lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)

def _scope_tokens(src, marker="CARD SCOPE"):
    i = src.index(marker)
    block = src[src.index("{", i):src.index("}", i)]
    return dict(re.findall(r'--([\w-]+):\s*(#[0-9a-fA-F]{6})', block))

def _root_tokens(src):
    i = src.index(":root{")
    block = src[i:src.index("}", i)]
    return dict(re.findall(r'--([\w-]+):\s*(#[0-9a-fA-F]{6})', block))

for fname in ("draft_room.html", "players.html", "teams.html", "home.html"):
    psrc = open(os.path.join(ROOT, "out", fname)).read()
    card = _scope_tokens(psrc)
    page = _root_tokens(psrc)
    cs = card["s1"]
    bad = [f"--{t} {_contrast(card[t], cs):.2f}" for t in
           ("ink", "ink2", "ink3", "go", "stop", "warn", "info")
           if _contrast(card[t], cs) < 4.5]
    ok(not bad, f"{fname}: every card text and verdict token clears 4.5:1",
       "; ".join(bad))
    ok(_contrast(cs, page["bg"]) >= 3.0,
       f"{fname}: card surface vs page clears 3:1",
       f"{_contrast(cs, page['bg']):.2f}")
    dbad = [f"--{t} {_contrast(page[t], page['bg']):.2f}" for t in
            ("go", "stop", "warn")
            if _contrast(page[t], page["bg"]) < 4.5]
    ok(not dbad, f"{fname}: dark-context verdict colors clear 4.5:1 on the page",
       "; ".join(dbad))

_drsrc = open(os.path.join(ROOT, "out", "draft_room.html")).read()
_drcard = _scope_tokens(_drsrc)["s1"]
_pos = dict(re.findall(r'\.p(QB|RB|WR|TE|K|DEF)\{border-left-color:(#[0-9a-fA-F]{6})\}', _drsrc))
pbad = [f"{k} {_contrast(v, _drcard):.2f}" for k, v in _pos.items()
        if _contrast(v, _drcard) < 4.5]
ok(len(_pos) == 6 and not pbad,
   "draft grid position colors clear 4.5:1 on the card", "; ".join(pbad))

_ffsrc = open(os.path.join(ROOT, "out", "ff-hub.html")).read()
_ffcard = _scope_tokens(_ffsrc)
_ffpage = _root_tokens(_ffsrc)
_fcs = _ffcard["s1"]
fbad = [f"--{t} {_contrast(_ffcard[t], _fcs):.2f}" for t in
        ("t1", "t2", "t3", "teal", "red", "gold")
        if _contrast(_ffcard[t], _fcs) < 4.5]
ok(not fbad, "ff-hub: card text, accents, and darkened gold clear 4.5:1",
   "; ".join(fbad))
ok(_contrast(_fcs, _ffpage["bg"]) >= 3.0,
   "ff-hub: card surface vs page clears 3:1",
   f"{_contrast(_fcs, _ffpage['bg']):.2f}")
fdbad = [f"--{t} {_contrast(_ffpage[t], _ffpage['bg']):.2f}" for t in
         ("teal", "red")
         if _contrast(_ffpage[t], _ffpage["bg"]) < 4.5]
ok(not fdbad, "ff-hub: dark-context accents clear 4.5:1 on the page",
   "; ".join(fdbad))

# 18. TEASER LEAK GUARD. The shared build must give nothing away: redaction
#     happens at build time, so these are assertions about what the committed
#     teaser files CONTAIN, not about what CSS hides.
TEASER = os.path.join(ROOT, "out", "teaser")
_tfiles = ["index.html", "draft_room.html", "players.html", "teams.html",
           "ff-hub.html"]
ok(all(os.path.exists(os.path.join(TEASER, f)) for f in _tfiles),
   "teaser: all five pages built")
if all(os.path.exists(os.path.join(TEASER, f)) for f in _tfiles):
    em3 = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
    _pl = sorted(em3["players"], key=lambda p: -p["vor"])
    _top = lambda pos, n: [p["name"] for p in _pl if p["pos"] == pos][:n]
    allowed = set(_top("QB", 3) + _top("RB", 3) + _top("WR", 3)
                  + _top("TE", 1) + _top("K", 1) + _top("DEF", 1))
    handles = {r["handle"] for r in em3["rosters"] if r.get("handle")}
    franchises = {r["franchise"] for r in em3["rosters"] if r.get("franchise")}
    top150 = [p["name"] for p in _pl[:150]]
    for f in _tfiles:
        src_t = open(os.path.join(TEASER, f)).read()
        leaks = [t for t in ("engine_2026", "data/", "nav.js", "../",
                             "my_board", "n_eff", "prior", "survival(",
                             "0.0772", "88.55", "p=0.323", "2,039")
                 if t in src_t]
        ok(not leaks, f"teaser {f}: reaches no data, no shard, no real page",
           "; ".join(leaks))
        oleaks = [h for h in (handles | franchises) if h and h in src_t]
        ok(not oleaks,
           f"teaser {f}: nothing about how this league's teams draft",
           "; ".join(oleaks[:3]))
        nleaks = [n for n in top150 if n in src_t and n not in allowed]
        ok(not nleaks, f"teaser {f}: no player beyond the allowed subset",
           "; ".join(nleaks[:3]))
        ok("YTFL PRIVATE BUILD" in src_t and "blur(" in src_t,
           f"teaser {f}: watermark and blur present")
    psrc_t = open(os.path.join(TEASER, "players.html")).read()
    ok(sum(1 for n in allowed if n in psrc_t) == len(allowed) == 12,
       "teaser players: exactly the 12 allowed names, all present",
       f"{sum(1 for n in allowed if n in psrc_t)}/{len(allowed)}")
    ok("teaser" in open(os.path.join(ROOT, ".github", "workflows",
                                     "pages.yml")).read(),
       "pages workflow deploys the teaser")

print()
print(f"{len(fails)} FAILURES" if fails else "ALL PASS")
sys.exit(1 if fails else 0)
