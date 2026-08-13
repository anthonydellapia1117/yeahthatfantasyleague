# Research Addendum - 2026-08-13

**Bounded web extension of docs/PLATFORM_RESEARCH_2026-08-13.md, run by the desktop session the same day. Five topics, five agents, primary sources first, every claim tagged and dated. This document is additive; the research doc is not modified. Read with docs/EXPANSION_ANALYSIS_2026-08-13.md.**

## The four things that change the research doc

### 1. Claim #10 UPGRADES: REPORTED -> VERIFIED-LIVE, with one wording correction

The NFL no longer operates a season-long fantasy game as of 2026; ESPN Fantasy is the **official** fantasy game of the NFL; league import (settings, members, history) is live at espn.com/importnfl. Confirmed on two primary ESPN Press Room pages:

- Joint ESPN/NFL migration FAQ, 2026-07-16 - VERIFIED-LIVE - espnpressroom.com/feature/nfl-fantasy-is-moving-to-espn-fantasy-your-questions-answered/
- ESPN press release, 2026-08-03 - VERIFIED-LIVE - espnpressroom.com/press-release/espn-fantasy-football-celebrates-being-named-official-fantasy-game-of-the-nfl-...
- Underlying deal: ESPN acquired NFL Network + NFL Fantasy for a 10% equity stake, announced 2025-08-05 - SOURCED - espnpressroom.com

**Wording correction:** primary sources say "official," not "exclusive." Yahoo, Sleeper, and CBS still run season-long games; they are simply not NFL-official. The research doc's phrasing "exclusive season-long partner" is secondary-press language (CordCuttersNews) and should not be quoted externally.

### 2. Claim #6 RESOLVES: the injuries conflict was documentation lag, not a data contradiction

The full story, from nflverse's own repos (VERIFIED-LIVE, github.com + nflreadr docs, 2026-08-13):

- The OLD injuries scrape died in August 2025 (its workflow's final scheduled runs, Aug 3-7 2025, all failed; zero runs since). The stale "source died after 2024" notice on the data-schedule page describes that pipeline.
- The complete 2025 file exists because maintainer mrcaseb **backfilled it on 2026-03-18 from a new source** (nflapi::nflapi_injuries), and the rewritten workflow merged to main on 2026-08-06.
- The new workflow is cron-scheduled daily 07:00 UTC, September through February. **First production run: 2026-09-01. It has never run in-season.**

**Risk register update:** downgrade from "source may be dead, 2026 unknown" to "restored via new source; zero in-season production runs yet; upstream is the same class of NFL API that died once before." The mitigation (degrade to "no data" gracefully, staleness badge) stands unchanged.

### 3. Claim #8 CORRECTS: 19 teams, not 17

All six spot-checked rows confirmed on team-site primary sources (ATL Rees 2026-01-28, CLE Monken 2026-01-28, NYG Nagy under HC John Harbaugh Feb 2026, PIT McCarthy calling plays per steelers.com 2026-06-16, TEN Daboll under Saleh 2026-01-27, WAS Blough first-time 2026-02-20). But the table is undercounted:

- **ADD CAR: Brad Idzik, first-time caller** - VERIFIED-LIVE - panthers.com, 2026-02-24
- **PROMOTE DEN: Davis Webb confirmed primary caller** - Payton's first year not calling since 2006 - VERIFIED-LIVE - denverbroncos.com, 2026-02-24. The doc's single-source watch item is resolved and deletes.
- First-time-caller list grows to six: Blough, Mannion, Doyle, Fleury, **Webb, Idzik**.
- NEW watch item - JAX: Udinski calling preseason plays - REPORTED only.

**The count is 19 of 32, and the table's February vintage showed measurable rot by August. This validates the analysis doc's requirement: playcallers.csv must be a curated, source-cited, dated file with a review step, not a static compile.**

### 4. Section 6.4 REFINES: the call-scoring rule, pre-registered

The methods research (FantasyPros accuracy methodology VERIFIED-LIVE; Good Judgment Open Brier FAQ VERIFIED-LIVE; Gneiting & Raftery 2007 on strictly proper scoring SOURCED; PunditTracker method REPORTED) lands on:

- **Binary "did bulls beat ADP" is statistically toothless at n=5-15:** beating a coin at p<0.05 in one season needs 9 of 10 hits. It cannot be the primary score.
- **Primary score: signed margin.** Call margin = ADP-implied positional finish minus actual positional finish (positive = bull was right), reported per call and averaged. A points version converts finish slots to points via rolling 3-year average production of the slot (the FantasyPros conversion), so a +3-slots call on a WR1 counts more than on a WR5.
- **Secondary: binary hit rate** (display honesty: reported with its n).
- **Optional: Brier score** only for calls that carry a stated confidence, against a base-rate reference (Brier Skill Score) - strictly proper, so honest confidence is the only winning strategy.
- **Accumulation across seasons is mandatory** - PunditTracker's floor of ~25 graded calls implies 2-3 seasons before a grade means anything. The overlay schema states this up front.

## Findings that change nothing but belong on the record

| Finding | Tag | Source, date |
|---|---|---|
| Underdog acquired by IG Group, up to ~$1.3B, closing late 2026/early 2027 | VERIFIED-LIVE | iggroup.com press release, 2026-07-30 |
| Yahoo launched college fantasy football for 2026 (Big Ten/SEC/Big 12/ACC + ND) | VERIFIED-LIVE | sports.yahoo.com, 2026-07-09 |
| Sleeper launched Kalshi-powered prediction markets under CFTC oversight | SOURCED | Business Wire, 2026-02-06 |
| FFC attribution is "requested," not strictly required; free incl. commercial | SOURCED | help.fantasyfootballcalculator.com, 2026-08-13 |
| docs.sleeper.com shows no API changes/deprecations dated 2025-2026; undocumented endpoints remain community-known-unstable | SOURCED / UNVERIFIED | docs.sleeper.com; community threads, 2026-08-13 |
| nflreadr 1.5.1 (2026-04-13): qs file type dropped (use parquet); most_recent_season() flips to 2026 in week 1 | SOURCED | nflreadr news, 2026-04-13 |
| nflreadr 1.5.0 (2025-09-02): players data moved to v2 (breaking renames); player stats moved to new files - consistent with the register's "stats_player replaced dead player_stats naming" | SOURCED | nflreadr news, 2025-09-02 |
| 2026 cadences confirmed unchanged: pbp/stats nightly, snap counts + ftn_charting 4x daily, depth charts daily 7AM UTC | SOURCED | nflverse data schedule, 2026-08-13 |
| Route-data gap stands for structured data; two free display sites (sticktothemodel.com, statrankings.com) claim weekly YPRR with unverified provenance and no export - eyeball only, never pipeline | REPORTED | bounded search, 2026-08-13 |

## Claims register final deltas (combining endpoint re-verification + this addendum)

| # | Final status | Delta |
|---|---|---|
| 1-4 | CONFIRMED by 22/22 endpoint probes from this machine | None |
| 5 | HELD (structured-data gap real; display-site caveat added) | Caveat only |
| 6 | **RESOLVED** - documentation lag; feed restored, first in-season run 2026-09-01 | Risk downgraded, mitigation unchanged |
| 7 | CONFIRMED (HEAD-only probe; ToS respected) | None |
| 8 | **CORRECTED: 19 teams, not 17**; 6 rows spot-verified; JAX watch added | Count + 2 rows |
| 9, 11, 12, 13 | ACCEPTED at original tags | None |
| 10 | **UPGRADED to VERIFIED-LIVE**; "exclusive" corrected to "official" | Tag + wording |
| 14 | ACCEPTED; persistence stays attributed-consensus, never a constant | None |

*Prepared by the desktop session, 2026-08-13. Five research agents, 88 tool calls, primary sources first, two-search stop rule per topic.*
