# Expansion Build Order - DRAFT, gated on Anthony's approval

**Status: NOT APPROVED. Nothing here builds until Anthony says Approve.**

Scope: home page, player pages, team pages, depth charts, conviction overlay, Actions cron - on top of the existing engine, per docs/PLATFORM_RESEARCH_2026-08-13.md (sections 6 and 9), as pressure-tested in docs/EXPANSION_ANALYSIS_2026-08-13.md and extended in docs/RESEARCH_ADDENDUM_2026-08-13.md.

File scope (hard boundary): `src/` (build scripts), `out/` (pages + JSON shards under out/data/), `.github/workflows/` (cron), `tests/` (extend guards + parity; add page-data guards), `data/` (curated inputs: my_board.csv, playcallers.csv). **out/draft_room.html changes are limited to navigation links. The draft path is frozen until after 2026-09-08 except for its own regeneration flow.**

## Iron rules, carried forward plus two new

All existing guards (research doc section 11) stand. New, from this review:

- **N1 - NFL intel law:** team/situation intel renders in display and overlay-evidence surfaces only. A guard test asserts no team-intel field reaches verdict or survival arithmetic.
- **N2 - Provenance stamping:** every JSON shard carries source, fetch time, and (for ADP) `adp_source: sleeper|ffc`. Every page renders its provenance footer. A guard test asserts the stamps exist.

## Sequencing principle: draft-first, draft-frozen

The draft is 26 days out. Phases A-C are pre-draft deliverables. Phase D-E are buildable pre-draft but skippable without harm. Nothing destabilizes the draft room: the expansion is additive files plus nav links.

---

## PHASE A - Data plumbing (the foundation everything rides on)

**A1. `src/build_pages_data.py`** - one script, same pattern as engine_2026.py: fetches, computes, writes JSON shards to `out/data/`, byte-stable on re-run with unchanged inputs.
- Sleeper projections + ADP (existing path), FFC ADP (build-time fetch, attribution string in payload, per-player stdev/high/low retained as the market band)
- nflverse: depth_charts_2026, stats_player_week_2025, pbp 2025 (PROE aggregates only, not raw plays), pfr_advstats (use `advstats_week_*_YYYY` naming), snap_counts, combine, draft_picks, rosters, players (v2 naming), schedules
- ID reconciliation: Sleeper player_id <-> gsis_id via players.parquet crosswalk; unmatched players logged to a reconciliation report, never silently dropped

**A2. `data/playcallers.csv`** - the curated file the analysis mandates. 19 rows per the addendum (CAR and DEN added), columns: team, caller, role, first_time flag, source_url, source_date, confirmed_by. Rendered with a REPORTED badge and its source date on every surface. Review trigger: any coaching news, and a mandatory check draft week.

**A3. `.github/workflows/pages-data.yml`** - daily cron 12:00 UTC (after nflverse 7AM depth charts), plus manual dispatch. Runs A1, commits shards, Pages redeploys. Heartbeat file touched even on empty diffs (60-day disable guard). Cron summary reports shard sizes and staleness.

**Acceptance:** shards regenerate byte-stable; reconciliation report empty or explained; cron green two consecutive days; new guard tests pass (N2 stamps, schema presence, staleness thresholds).

## PHASE B - Conviction overlay (highest draft value)

**B1. `data/my_board.csv`** - schema per research doc 6.3 plus the pre-registered scoring block from the addendum:
`player, call (BULL|BEAR), move (+1 tier|-1 tier), reason, source, confidence (optional 0-1), date`
Scoring rule, fixed now, in the file header: primary = signed margin vs ADP-implied positional finish (slot version + FantasyPros 3-yr slot-to-points conversion); secondary = hit rate with n; optional Brier vs base rate for confidence-bearing calls; grades accumulate across seasons, ~25-call floor before a grade means anything.

**B2. Engine surfacing** - `engine_2026.py` reads my_board.csv: YOUR CALL chip beside model VOR on cards; coin-flip tie-break toward bulls (the one decision role); within-tier resort for display; survival of each bull to each of my picks.
**The verdict-subject rule (analysis doc, section 6):** the model's primary remains the wait-or-reach subject, always. The overlay never swaps it.

**B3. Guard test additions:** overlay fields reach no verdict/survival arithmetic except the sanctioned coin-flip branch; verdicts byte-identical with an empty my_board.csv.

**Acceptance:** with a populated board, cards show both numbers; with an empty board, output is byte-identical to today; guards green.

## PHASE C - Player pages (draft-prep families only, pre-draft cut)

**C1. `out/players/` static pages** (or one page + hash routing - build decision) from A1 shards:
- Header: name, pos, team, injury status, model VOR + tier, ADP (source-stamped), FFC market band ("the market's range on him: 24-41 across 6,160 mocks")
- Value block: VOR rank vs ADP gap (the market-disagreement number)
- 2025 usage/efficiency: target share, air yards share, WOPR, snap share, EPA-based efficiency (literal stats_player and pbp columns; no derived inventions)
- xFP block with the calibration label ("model trained through 2020")
- Prospect block: draft capital, combine, age (draft_picks + combine + players)
- YOUR CALL block when my_board.csv has a row, with the reason and source displayed
- Route metrics: 2025 values labeled "prior season - no free in-season source"; K/DEF pages carry the floor label

**Acceptance:** every number on the page traces to a shard field (guard: page-data references resolve); provenance footer on every page; tap-any-number provenance is pattern 1, built first.

## PHASE D - Team pages + depth charts (buildable pre-draft, skippable)

**D1. Team page per NFL team:** play-caller card (playcallers.csv + PROE by team-season from pbp aggregates; career-by-stop only where the curated file covers the stop), vacated opportunity (roster diff x prior-year usage shares), O-line proxies (yards before contact, pressure context) with attributed-study framing, pace/neutral tendencies.
**D2. Depth charts:** ranked-value grid (usage share + VOR order, official slot as metadata) from depth_charts + stats_player.

**Acceptance:** N1 guard proves no team-intel field reaches decision math; every instrument shows its computation note.

## PHASE E - Home page

Action-item dashboard (pattern 10): draft countdown, data staleness board (every shard's age), overlay completeness (calls without sources flagged), trending adds (attributed), the one display-worthy history fact (consensus #1 never won here), links to every surface. ff-hub.html stays the findings page; home links to it.

## Explicitly deferred (unchanged decisions)

In-season surfaces (start-sit, live scoring) - post-draft. RB start-sit tool - post-draft commission. Injuries feed integration - revisit after its first production run 2026-09-01 (addendum finding); until then, no injury data beyond Sleeper's status flag already in the engine.

## Test plan summary

Existing: 22 survival guards + 42-anchor parity suite + smoke scenarios - all untouched, all must stay green.
New: N1 intel-isolation guard, N2 provenance guard, overlay byte-identity guard (B3), page-data schema + reference-resolution guards, shard staleness guard, cron heartbeat check.

## Approval gate

Approve -> implementation begins at Phase A inside the stated file scope, tests green at every merge, draft path frozen.
Request changes -> revise this draft.
