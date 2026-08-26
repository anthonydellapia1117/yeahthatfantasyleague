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
    # The guard that matters: players inside the real draft window must
    # match. The window is ADP < 200 (the league drafts 12x15 = 180 picks;
    # 200 leaves margin) - the old ADP < 250 window broke the cron for four
    # straight days in late August when Sleeper's deepening preseason pool
    # pushed camp bodies with ADP 237-249 past the 2% budget, players
    # nflverse does not carry and no page renders. A normalizer regression
    # still trips this instantly: it would unmatch names across the whole
    # window, not just the fringe.
    matched_ids = set(xw["matched"])
    window = [p for p in adp["players"]
              if (p.get("adp_sleeper") or 999) < 200 and p["pos"] != "DEF"]
    un_window = [p["name"] for p in window if p["player_id"] not in matched_ids]
    ok(len(un_window) <= max(2, len(window) * 0.02),
       "draft-window players (ADP < 200) match at >=98% (suffix-normalized)",
       f"{len(un_window)}/{len(window)}: {un_window[:5]}")
    # The 200-249 fringe may legitimately miss (Sleeper lists camp bodies
    # nflverse lacks), but the law stands: unmatched is LOGGED, never
    # silently dropped.
    fringe = [p for p in adp["players"]
              if 200 <= (p.get("adp_sleeper") or 999) < 250 and p["pos"] != "DEF"]
    logged = {r["name"] for r in rec.get("unmatched", [])}
    un_fringe = [p["name"] for p in fringe if p["player_id"] not in matched_ids]
    ok(all(n in logged for n in un_fringe),
       "every unmatched fringe player (ADP 200-249) is logged in reconciliation",
       f"unlogged: {[n for n in un_fringe if n not in logged][:5]}")
    # the diacritic fold stays in the normalizer (the Estime/Estimé miss)
    bp = open(os.path.join(ROOT, "src", "build_pages_data.py")).read()
    ok("unicodedata.normalize(\"NFKD\"" in bp and "unicodedata.combining" in bp,
       "crosswalk normalizer folds diacritics (Estime/Estimé class)")

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

# 8b. P0 PICK CLOCK LAW: the clock derives from the draft's own settings
#     and anchors to Sleeper's last_picked - never a hardcoded duration,
#     never poll-detection time. The 2x silent-clock defect stays dead.
_room = open(os.path.join(ROOT, "out", "draft_room.html")).read()
ok("pick_timer" in _room and "last_picked" in _room,
   "P0: the room reads pick_timer and last_picked from the draft")
ok("two minutes" not in _room and ">2:00<" not in _room,
   "P0: no two-minute language or hardcoded 2:00 anywhere in the room")
ok("120 - Math.floor" not in _room and "clockStart" not in _room,
   "P0: the hardcoded duration and the poll-anchored clock are gone")
ok("clock unavailable - use Sleeper" in _room,
   "P0: absent clock data renders an honest absence, not a plausible number")
ok("LiveState.pickTimer = (draft.settings && Number(draft.settings.pick_timer)) || null" in _room,
   "P0: the duration is captured from settings on every fetch")

# 8d. RESPONSE VALIDITY AND FRESHNESS (review P1-C): a resolved fetch is
#     not current data. The room must cache-bust, check response.ok,
#     validate shape, refuse to move the board backwards, and show source
#     age beside fetch time.
ok('"?cb=" + Date.now()' in _room and '"/picks?cb=" + Date.now()' in _room,
   "P1-C: both draft fetches are cache-busted per poll")
ok("Array.isArray(picks)" in _room,
   "P1-C: picks must be an array before the board renders from them")
ok("picks.length < LiveState.lastPickCount" in _room,
   "P1-C: an older cached board is refused - the room never moves backwards")
ok("data \" + Math.max" in _room or "- data " in _room,
   "P1-C: source age renders beside fetch time")
ok("e.httpStatus" in _room and "badSchema" in _room,
   "P1-C: HTTP errors and unusable payloads are named, not swallowed")

# 8c. DEPLOY COMPLETENESS: pages.yml copies an explicit file list, which
#     silently omitted a brand-new page once (paths.html shipped to main,
#     every gate green, live site 404). Every page the shared nav links to
#     must appear in the deploy copy list.
_pgy = open(os.path.join(ROOT, ".github", "workflows", "pages.yml")).read()
_navsrc0 = open(os.path.join(ROOT, "out", "nav.js")).read()
import re as _re
_nav_hrefs = _re.findall(r'\["\w+",\s*"[^"]+",\s*"([^"]+)"\]', _navsrc0)
_missing_deploy = [h for h in _nav_hrefs if f"out/{h}" not in _pgy]
ok(not _missing_deploy,
   "every nav-linked page is in the pages.yml deploy list",
   "; ".join(_missing_deploy))

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

# 11b. BIG BOARD (CVS). The rank is the anchor law and nothing else; the cap
#      and kill-switch are stated on the page; all seven signals carry three
#      channels (container treatment + icon + text label) with a legend and
#      persistent filters; the payload itself is ordered by CVS.
bb_page = os.path.join(ROOT, "out", "big_board.html")
ok(os.path.exists(bb_page), "big_board.html exists")
cvs_path = os.path.join(ROOT, "out", "cvs.json")
ok(os.path.exists(cvs_path), "cvs.json exists")
if os.path.exists(bb_page) and os.path.exists(cvs_path):
    bpage = open(bb_page).read()
    ok("CVS = VOR + z_point_scale x weighted-z" in bpage,
       "big board declares the anchor law on its face")
    ok("walter_enabled" in bpage and "kill-switch" in bpage
       and "capped" in bpage,
       "big board states the cap and the kill-switch as the risk bounds")
    ok("REJECTED" in bpage and "p=0.99" in bpage,
       "big board states the rejected tendency fold with its number")
    ok("NOT WIRED, ON PURPOSE" in bpage,
       "unwired factors declared not wired, with the reason")
    ok("floors" in bpage and "off the CVS board" in bpage,
       "K and DST floors stated off the board, with the reason")
    ok('get("cvs.json")' in bpage, "board is driven by cvs.json")
    ok("Provenance (guard N2)" in bpage, "big board provenance footer present")
    # signal encoding: every signal has a container treatment, an icon, and a
    # text label; the legend and conflict marker render; filters persist
    SIGNALS = ["personal_dnd", "consensus_dnd", "single_dnd",
               "consensus_target", "single_target", "consensus_sleeper",
               "single_sleeper"]
    miss = [s for s in SIGNALS if f'.brow[data-sig="{s}"]' not in bpage]
    ok(not miss, "every signal state has a container treatment",
       "; ".join(miss))
    for lbl in ("MY DND", "DND x2", '"DND"', "TARGET x2", '"TARGET"',
                "SLEEPER x2", '"SLEEPER"'):
        ok(lbl.strip('"') in bpage, f"signal text label {lbl} present")
    ok("renderLegend" in bpage and "! CONFLICT" in bpage,
       "legend always visible, conflict marker in it")
    ok("signal_conflict" in bpage and "Conflicts view" in bpage,
       "conflicts stay visible with their own marker and view")
    ok("ytfl_bb2" in bpage and "localStorage" in bpage,
       "filter and view state persists across refresh")
    ok("ytfl_walter_live" in bpage and "WALTER LAYER" in bpage,
       "live kill-switch toggle present, shared-key persisted")
    ok("no_walter" in bpage and "cvs_base" in bpage,
       "kill-switch renders the server-ranked pure-model variant")
    ok("tier_move" in bpage and "tiermoves" in bpage,
       "tier-boundary crossings flagged on rows and named in the delta view")
    drp = open(os.path.join(ROOT, "out", "draft_room.html")).read()
    ok("ytfl_walter_live" in drp and "cvs_base" in drp,
       "pick engine reads the same kill-switch and pure-model variant")
    # the draft-order hypothesis: quarantined, persisted, and explicitly
    # subordinate to Sleeper's real draw
    ok("ORDERHYP-BEGIN" in drp and "ORDERHYP-END" in drp
       and "ytfl_order_hyp" in drp,
       "order hypothesis is marker-quarantined and persisted")
    ok("THE LIVE SOURCE WINS" in drp and "hypothesis is retired" in drp,
       "order hypothesis states that Sleeper's draw wins, and retires visibly")
    ok(drp.index("ORDERHYP-BEGIN") > drp.index("engine-data-end"),
       "order hypothesis code sits outside the engine sentinels")
    # the survival calibration layer (ADOPTED, scope ii): payload table is
    # the committed constant, monotone, kill-switchable; the room consumes
    # it through the wrapper with the frozen fallback and shows the delta
    # on threshold-straddling picks only
    _esrc = open(os.path.join(ROOT, "src", "engine_2026.py")).read()
    _m = re.search(r"SURVIVAL_CALIBRATION = \[([^\]]+)\]", _esrc)
    _tbl = [float(x) for x in _m.group(1).replace("\n", " ").split(",")]
    emb2 = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
    ok(emb2.get("survival_calibration") == _tbl,
       "calibration table in the payload equals the committed constant")
    ok(len(_tbl) == 20 and all(0 <= v <= 1 for v in _tbl)
       and all(_tbl[i] <= _tbl[i + 1] + 1e-9 for i in range(19)),
       "calibration table is a monotone 20-bin probability table")
    ok(isinstance(emb2.get("survival_calibration_enabled"), bool),
       "payload carries the calibration kill switch")
    ok("SURVCAL-BEGIN" in drp and "ytfl_survcal_live" in drp
       and "function calCondSurvival" in drp,
       "room carries the calibrated wrapper and its one-tap toggle")
    ok("|| !survCalOn()) return p" in drp.replace("  ", " ")
       or "!survCalOn()) return p" in drp,
       "wrapper falls back to the frozen number when any switch is off")
    ok("const s = calCondSurvival(comp.adp" in drp
       and "the calibration flips this call" in drp,
       "verdict consumes the calibrated number and shows both on straddles")
    ok(drp.index("SURVCAL-BEGIN") > drp.index("engine-data-end"),
       "calibration code sits outside the engine sentinels")
    ok("1 - condSurvival(p.adp, ctx.myNext" in drp,
       "grade urgency stays on the frozen number (not in the approved diff)")
    ok("CALIBRATED SURVIVAL UNAVAILABLE" in drp,
       "toggle label honors the payload kill switch, never claims ON falsely")
    _cref = emb2.get("calibration_reference") or []
    ok(len(_cref) >= 5 and all(0 <= r["cal"] <= 1 for r in _cref),
       "payload carries Python-computed calibration anchors for JS parity")
    ok("2019-2025 era" in drp,
       "the room's disclosure names the deployed era fit, not the rejected blend")
    ok("pre-draft verdicts use the frozen survival model" in drp,
       "the frozen/calibrated boundary is stated on the pre-draft surface")
    # signal encoding in the room: same seven states, three channels,
    # server-side precedence, walter-toggle aware, display only
    ok("SIGENC-BEGIN" in drp and "SIGENC-END" in drp
       and drp.index("SIGENC-BEGIN") > drp.index("engine-data-end"),
       "room signal encoding is marker-quarantined outside the sentinels")
    for lbl in ("MY DND", "DND x2", "TARGET x2", "SLEEPER x2"):
        ok(lbl in drp, f"room carries signal label {lbl}")
    for c in ("#b91c1c", "#b45309", "#047857", "#1e3a8a", "#1d4ed8"):
        ok(c in drp, f"room carries signal color {c} (contrast-proven set)")
    ok("peWalterOn() ? c : c.no_walter" in drp,
       "room signals honor the walter live toggle via the server variants")
    _pe_seg = drp[drp.index("function peScore"):drp.index("function peCondition")]
    _gr_seg = drp[drp.index("const GRADE_W"):drp.index("function renderRecs")]
    ok("sigOf" not in _pe_seg and "sigBadge" not in _pe_seg
       and "sigOf" not in _gr_seg and "sigBadge" not in _gr_seg,
       "signals are display only - never inside the score or the grade")
    _vb_seg = drp[drp.index("function renderValueBoard"):drp.index("function simGauss")]
    ok("sigAttr(" in _vb_seg and "sigBadge(" in _vb_seg and "sigLegend()" in _vb_seg,
       "the value board (best-available view) carries all three signal channels")
    # byte-identity with the big board: the SIG and ICON maps must never
    # drift between the two pages (labels, colors, icon assignment, SVGs)
    def _blk(src, name):
        i = src.index(f"const {name} = {{")
        return src[i:src.index("};", i) + 2]
    ok(_blk(drp, "SIG") == _blk(bpage, "SIG")
       and _blk(drp, "ICON") == _blk(bpage, "ICON"),
       "room SIG and ICON maps are byte-identical to the big board")
    # a novel cvs.json signal value must render nothing, never throw inside
    # the render loop (refresh() swallows render errors AFTER stamping the
    # freshness dot, so a throw here would freeze the room silently)
    _sb_seg = drp[drp.index("function sigBadge"):drp.index("function sigAttr")]
    _sa_seg = drp[drp.index("function sigAttr"):drp.index("function sigLegend")]
    ok('if (!s) return "";' in _sb_seg and "SIG[s0.sig]" in _sa_seg,
       "unknown signal keys are guarded in both channels (badge and data-sig)")
    # gone/taken rows never carry a signal - pin the suppression branches
    ok('${gone ? "" : sigAttr(p)}' in drp and '${gone ? "" : sigBadge(p)}' in drp,
       "value board gone rows are signal-free (both channels suppressed)")
    ok('${c.taken ? "" : sigAttr(c.p)}' in drp
       and '${c.taken ? "" : sigBadge(c.p)}' in drp,
       "a taken searched player in recs is signal-free (both channels suppressed)")
    # ordering is pinned by the exact comparators - the signal cannot reach
    # them without breaking these strings
    ok(".sort((a, b) => b.s.total - a.s.total)" in drp,
       "pick-engine alternatives order by score alone (comparator pinned)")
    ok(".sort((a, b) => b.g - a.g)" in drp,
       "recs order by grade alone (comparator pinned)")
    # C1 RUNDETECT: the position-run alert derives from the league's own base
    # rates, never a fixed count
    _rd_seg = drp[drp.index("function runDetect"):drp.index("function renderFeatures")]
    ok("pos_base_rates" in _rd_seg and "binomTail" in _rd_seg,
       "run detection is binomial surprise against the archive's base rates")
    ok("c[pos] < 3" in _rd_seg and "0.05" in _rd_seg,
       "run floor (k>=3) and significance convention (p<0.05) are stated in code")
    ok("the archive expects" in drp,
       "run banner shows the expected count, not just the observed one")
    # C1 FLEX: payload carries the derived allocation with its source
    ok('"flex_allocation"' in open(os.path.join(ROOT, "src", "engine_2026.py")).read(),
       "engine payload carries the derived flex allocation")
    # IDENT + UPNEXT: the Sleeper identity layer and the "am I next" strip
    ok("IDENT-BEGIN" in drp and "UPNEXT-BEGIN" in drp
       and drp.index("IDENT-BEGIN") > drp.index("engine-data-end"),
       "identity and up-next blocks are marker-quarantined outside the sentinels")
    # the room's link must be DERIVED from the polled draft id, never typed
    # in - in DRAFT MODE it derives from the loaded mock id the same way
    ok('"https://sleeper.com/draft/nfl/" +\n  (MOCK_MODE ? MOCK_ID : (E.league ? E.league.draft_id : ""))' in drp,
       "the room's Sleeper link is derived from the polled draft id")
    ok("https://sleeper.com/draft/nfl/1389" not in drp,
       "the room hardcodes no draft url - it cannot drift from the feed")
    ok('$("sleeper-link").href = DRAFT_URL;' in drp,
       "the header link is wired to the derived draft url")
    # team_name is display only and must never displace the history join key
    eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
    rs = eng["rosters"]
    ok(all("team_name" in r and "franchise" in r for r in rs),
       "every roster carries both the Sleeper team name and the franchise era")
    mine = [r for r in rs if r["roster_id"] == eng["league"]["anthony_roster_id"]]
    ok(len(mine) == 1 and mine[0]["handle"] == "antdell"
       and mine[0]["team_name"] == "Taylor Made",
       "Anthony's roster resolves to antdell / Taylor Made",
       str(mine and (mine[0]["handle"], mine[0]["team_name"])))
    ok(mine and mine[0]["franchise"] == "Antdell & Ernie",
       "the franchise era key is unchanged by the team-name work")
    _up = drp[drp.index("UPNEXT-BEGIN"):drp.index("UPNEXT-END")]
    ok("YOU ARE ON THE CLOCK" in _up and "UP IN " in _up and "before you:" in _up,
       "the up-next strip states the clock, the count, and who picks first")
    ok("teamLabel(" in _up, "the up-next queue names teams, not bare slot numbers")
    # display only: identity must not reach the score or the grade
    _pe2 = drp[drp.index("function peScore"):drp.index("function peCondition")]
    ok("teamLabel" not in _pe2 and "team_name" not in _pe2,
       "the Sleeper team name never enters the pick-engine score")
    for pg_ in ("big_board.html", "home.html"):
        _t = open(os.path.join(ROOT, "out", pg_)).read()
        ok(eng["league"]["draft_id"] in _t,
           f"{pg_} links to the live Sleeper draft")
    ok("${S(p).cvs_rank}" in bpage,
       "rows render the payload's server-ranked variant - no page-side re-rank")
    # the ordering lives in the payload: strictly ranked, CVS-descending
    cvsp = json.load(open(cvs_path))["players"]
    ok([p["cvs_rank"] for p in cvsp] == list(range(1, len(cvsp) + 1)),
       "cvs.json players arrive ranked 1..N in order")
    ok(all(cvsp[i]["cvs"] >= cvsp[i + 1]["cvs"] for i in range(len(cvsp) - 1)),
       "cvs.json order is CVS-descending - no hidden composite in the page")

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
           ("draft_room.html", "big_board.html", "players.html", "teams.html",
            "ff-hub.html")),
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
    ok(len(nav_items) == 7, "nav defines exactly seven items", f"{len(nav_items)}")
    missing = [href for _, href in nav_items
               if not os.path.exists(os.path.join(ROOT, "out", href))]
    ok(not missing, "every nav link target resolves to a real file",
       "; ".join(missing))
    PAGES = {"draft_room.html": "draft", "big_board.html": "board",
             "players.html": "players", "paths.html": "paths",
             "teams.html": "teams",
             "ff-hub.html": "findings", "home.html": "hub"}
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
       "each active key is used exactly once across the seven pages")
    dr = open(os.path.join(ROOT, "out", "draft_room.html")).read()
    tag_at = dr.index('src="nav.js"')
    ok(tag_at < dr.index('<script id="engine-data"'),
       "draft room nav include sits OUTSIDE (before) the engine sentinels")
    ok("nav.js" in open(os.path.join(ROOT, ".github", "workflows", "pages.yml")).read(),
       "pages workflow deploys nav.js")

# 14. APP SHELL (Phase 2). Token, layout, and header consistency: one dark
#     family (#0b1120, ff-hub's), one container width, one kicker treatment -
#     and the semantic verdict colors did not move.
ALL_PAGES = ["draft_room.html", "big_board.html", "players.html",
             "teams.html", "home.html", "ff-hub.html"]
_tokened = ["draft_room.html", "big_board.html", "players.html", "teams.html",
            "home.html"]
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
for fname in ("big_board.html", "players.html", "teams.html", "home.html", "ff-hub.html"):
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

for fname in ("draft_room.html", "big_board.html", "players.html", "teams.html", "home.html"):
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

# the seven signal colors are load-bearing (names must stay legible inside
# every signal treatment) - verify each against the big-board card surface
_bbsrc = open(os.path.join(ROOT, "out", "big_board.html")).read()
_bbcard = _scope_tokens(_bbsrc)["s1"]
_sigcolors = set(re.findall(r'\.brow\[data-sig="[a-z_]+"\]\{border-color:(#[0-9a-fA-F]{6})', _bbsrc))
sbad = [f"{c} {_contrast(c, _bbcard):.2f}" for c in _sigcolors
        if _contrast(c, _bbcard) < 4.5]
ok(len(_sigcolors) == 5 and not sbad,
   "all five signal colors clear 4.5:1 on the big-board card",
   f"{len(_sigcolors)} colors; " + "; ".join(sbad))

# the players-page VOR ramp is a CONTINUOUS scale, so every interpolated
# color between the anchors must clear 4.5:1 on that card - not just the
# three anchors. It is also a DISTINCT scale: the ramp must not reuse the
# reserved verdict hexes (--go / --stop / --warn) in that card scope.
_plsrc = open(os.path.join(ROOT, "out", "players.html")).read()
_plcard = _scope_tokens(_plsrc)["s1"]
_anchors = re.search(
    r"const VOR_LO = \[(\d+), (\d+), (\d+)\], VOR_MID = \[(\d+), (\d+), (\d+)\],"
    r" VOR_HI = \[(\d+), (\d+), (\d+)\]", _plsrc)
ok(bool(_anchors), "players page declares the three VOR ramp anchors")
if _anchors:
    _n = [int(x) for x in _anchors.groups()]
    _lo, _mid, _hi = tuple(_n[0:3]), tuple(_n[3:6]), tuple(_n[6:9])
    _hex = lambda c: "#%02x%02x%02x" % c
    _ramp = []
    for _a, _b in ((_lo, _mid), (_mid, _hi)):
        for _i in range(21):
            _t = _i / 20
            _ramp.append(tuple(round(_a[j] + (_b[j] - _a[j]) * _t)
                               for j in range(3)))
    _rbad = [f"{_hex(c)} {_contrast(_hex(c), _plcard):.2f}" for c in _ramp
             if _contrast(_hex(c), _plcard) < 4.5]
    ok(not _rbad, "every interpolated VOR ramp color clears 4.5:1 on the card",
       "; ".join(_rbad[:3]))
    _pltok = _scope_tokens(_plsrc)
    _reserved = {_pltok[t].lower() for t in ("go", "stop", "warn") if t in _pltok}
    ok(not ({_hex(c) for c in (_lo, _mid, _hi)} & _reserved),
       "the VOR ramp is a distinct scale - no reserved verdict hexes reused",
       str(_reserved))
# the scale must be database-wide and median-anchored, both stated in code
ok("D.engine.players.map(p => p.vor)" in _plsrc,
   "VOR scale anchors are computed across the whole player database")
ok("right-skewed" in _plsrc and "median" in _plsrc,
   "the median-not-mean midpoint choice is stated on the page")
ok(".idxrow{display:flex;justify-content:flex-start" in _plsrc,
   "player rows are tight-packed, not space-between")
ok("grid-template-columns:repeat(3,minmax(0,1fr))" in _plsrc,
   "position groups render three across")

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
                             "0.0772", "88.55", "p=0.323", "2,039",
                             "cvs", "walter", "Walter")
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
