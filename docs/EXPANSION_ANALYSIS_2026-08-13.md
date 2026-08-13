# Expansion Analysis - Platform Research Pressure-Test - 2026-08-13

**Desktop session review of docs/PLATFORM_RESEARCH_2026-08-13.md, per Anthony's brief: analyze all 13 sections, re-verify the register, record disagreements with evidence. This document is additive; the research doc is not modified.**

Verifier: Anthony. Companion documents: docs/RESEARCH_ADDENDUM_2026-08-13.md (bounded web extension), docs/EXPANSION_BUILD_ORDER_DRAFT.md (the gated plan). Nothing builds until the gate clears.

Housekeeping note: docs/2026_Platform_Insight_Data_Research.md is a byte-identical duplicate of the research doc (differs only by a trailing newline). Recommend deleting the duplicate and keeping the dated filename; awaiting the same gate.

---

## Part 1 - Section-by-section analysis

### Section 1 - Executive verdict

**Claims:** the decision engine has no market equal; the expansion opportunity is the insight surface (player/team/depth pages) on free verified data.
**Assessment: AGREE, and it matches independent evidence.** The v2 build order's own competitor research (run separately, before this doc existed) reached the same conclusion: FantasyPros Draft Intel is the only leaguemate product and it is tendency-display-only with a 5-year cap, no survival model, no backtest. Two independent research passes converging is worth noting.
**One scope caution:** "Sleeper-grade UX" is a benchmark for patterns, not a mandate to rebuild Sleeper. The doc's own pattern 12 (design for the repeat user - one user, Anthony) is the correct scope limiter and should govern.

### Section 2 - League platform landscape

**Claims:** platform capabilities and market moves; all display-context, none load-bearing for the build.
**Assessment: ACCEPT with one flag.** Claim #10 (NFL Fantasy shutdown, ESPN exclusivity) was REPORTED-only; the addendum upgrades or holds it (see companion doc). Nothing in the build depends on it either way.

### Section 3 - Draft tool landscape

**Claims:** verified pricing, capabilities, and the moat statement.
**Assessment: ACCEPT.** Prices are consistent with the v2 research where they overlap (Draft Sharks $96/yr mid-tier in both). The moat statement is not marketing: it is the tested difference between tendency display (what Draft Intel sells) and a survival model that survived a 12/13-season out-of-sample backtest (what shipped here).

### Section 4 - Player insight layer

**Claims:** seven converged primitives; metric families mapped to free sources; route data has no free in-season path; PlayerProfiler compliant paths only.
**Assessment: ACCEPT, all load-bearing probes reproduced** (see Part 2). Additions from this review:

1. **The xFP caveat must be a label, not a footnote.** ffopportunity's model is trained on 2006-2020 seasons (the doc flags this). Any xFP number on a player page carries "model calibrated through 2020" next to the number, house-style.
2. **FFC's per-player `stdev`/`high`/`low` partially fills primitive 5 honestly.** Verified live this session: FFC ships ADP dispersion across 6,160 real mocks. That is a MARKET band, not an outcome distribution - it can be displayed as "the market's range on him" without violating the no-invented-variance rule. The research doc lists FFC only as an ADP fallback; this is a real, free upgrade it missed.
3. **PlayerProfiler verdict endorsed and already precedented:** the v2 build order independently put PlayerProfiler-class usage metrics on its reject list for the same ToS reason. Door-open status re-confirmed by HEAD probe only; no data pulled.

### Section 5 - Team situation intel

**Claims:** 17 new play-callers; four computable instruments; evidence-discipline note (display only, probability never).
**Assessment: ACCEPT the instruments; one structural gap found.**

**The gap: play-caller-to-team-season mapping is not a dataset that exists anywhere free.** PROE-by-play-caller-across-stops requires knowing who called plays for which team in which season. nflverse pbp has no play-caller column. The research doc's own table was hand-compiled from trackers. That is the correct method - but the build order must make it an explicit, hand-curated, source-cited file (`data/playcallers.csv` with a source URL per row, staleness date, and a REPORTED tag rendered in the UI). Without that file being first-class and maintained, "career PROE by stop" silently becomes invented data the day a play-caller changes mid-season. This is the single biggest honesty risk in the whole expansion and it needs a named owner: Anthony confirms the table at build time and after any coaching news.

**Spot-check status:** six of the seventeen rows were independently re-verified via the addendum workflow (see companion doc for results). The table is a February compile; August camp news is exactly where it would rot.

### Section 6 - Conviction overlay

**Claims:** market numbers predict the market; conviction applies to value never availability; my_board.csv overlay; coin-flip tie-break; season-end scoring.
**Assessment: AGREE with the architecture - it is the correct generalization of the tendency lesson. Two spec ambiguities must be resolved before build:**

1. **The verdict subject problem.** "Re-sort within tiers by preference" can change which player is the displayed primary at a pick - which silently changes the SUBJECT of the wait-or-reach sentence. Resolution adopted in the build-order draft: **the model's primary remains the verdict subject, always.** The overlay renders YOUR CALL beside it with its own survival number ("your bull: 76% he lasts to pick 42"). The one sanctioned decision role stays the coin-flip tie-break, where the model has already declared indifference (within 8 VOR). Nothing else moves.
2. **The scoring rule must be pre-registered, now, before any call is made.** Choosing how to score calls after seeing season results is the one-sided/two-sided error this project already made once and corrected (AUDIT_SURVIVAL, STEP-vs-POWER p-value). The build-order draft therefore ships the scoring rule inside the my_board.csv schema on day one: each call is scored against ADP-implied positional finish, direction hit/miss plus a percentile magnitude, with the explicit small-n disclosure that 5-15 calls per season will not reach significance for years and the loop is discipline, not proof. Exact formula in the build-order draft, informed by the addendum's methods research.

### Section 7 - Data-source register and risk register

**Claims:** 14 register entries, 5 risks.
**Assessment: RE-VERIFIED 22/22 from this machine** (Part 2 table). One probe initially failed on an asset-name error in MY script, not in the register - pfr_advstats season files are combined across years; per-year granularity lives in `advstats_week_*_YYYY.parquet`. Register corrected detail worth carrying into the build: use the weekly files for per-season pulls.

**One addition to the risk register:** ADP source switching must be loud. The engine's survival input today is Sleeper ADP; FFC is the documented fallback. The two are different populations (league-mate market vs public mocks). Any build that can silently switch sources between runs must stamp the source into the payload (`adp_source: sleeper|ffc`) and render it in the provenance footer, so a fallback event is visible in the UI, not discovered in a discrepancy.

### Section 8 - The three prior repos

**Claims:** carry spec/patterns, not code, from Eagle-Draft-Hub and rork-tampr-pro; nothing from sports-ml-engine.
**Assessment: ACCEPT.** The verdicts import no code and no data, so they carry no verification burden. The Data Source Bar pattern (rork-tampr-pro) and the reconciliation-pipeline mental model (Eagle-Draft-Hub) are both already house practice here in other forms.

### Section 9 - Architecture

**Claims:** stay static; Pages + Actions cron; three trigger conditions for revisiting.
**Assessment: AGREE - it is the architecture already proven in production.** Two operational realities the doc does not state, added to the build-order draft:

1. **GitHub disables scheduled workflows after 60 days without repo activity.** In-season this never binds (daily data commits are activity); the risk window is the offseason. Mitigation: the cron job's own daily commit is the keepalive; if the data diff is empty, it still touches a heartbeat timestamp file.
2. **Daily data commits will accrete.** Mitigation: JSON shards live under `out/data/`, one commit per cron run, and shards are regenerated in place (no append-only growth). Repo size monitored by the workflow itself; alert threshold in the cron summary.

### Section 10 - Design pattern library

**Claims:** 14 patterns, brand continuity finding.
**Assessment: ACCEPT.** Two notes: pattern 6 (floor/ceiling bands) gains the honest FFC market-band path found in section 4 of this review. Pattern 4 (tap-any-number provenance) should be the FIRST pattern implemented on the new pages, not a polish item - it is quality rule 1 rendered as UI, and retrofitting provenance is always worse than building on it.

### Section 11 - Guards

**Claims:** seven guards unchanged.
**Assessment: VERIFIED against the repo's canonical values - every number matches** (nulls table, p=0.078 lead, r=+0.813 display-only tendencies with p=0.99 fold-in rejection, 12/13 p=0.0034 survival model, 22 guards + 42 anchors, K/DEF floors, bonus-exclusive era totals). The research doc's extension of the tendency law to NFL situation intel ("display and overlay evidence only, probability placement never, unless a backtest earns it") is the right generalization and is written into the build-order draft as a guard test.

### Section 12 - Claims register

**Assessment:** delta table in Part 2. Bottom line: no claim failed. Two upgraded, one corrected in detail, three remain at their original tag pending external events.

### Section 13 - Source register

**Assessment: ACCEPT.** Primary-source discipline is consistent with what the addendum workflow could and could not confirm.

---

## Part 2 - Claims register #1-14: re-verification deltas (this machine, 2026-08-13)

| # | Claim (abbreviated) | Doc status | Re-verified today | Delta |
|---|---|---|---|---|
| 1 | Sleeper state/trending/projections live; projections undocumented, carries adp_ppr + pts_ppr | Session probe | 200/200/200; 3,300 players; adp_ppr and pts_ppr present | **CONFIRMED** |
| 2 | Sleeper ACAO:*; FFC no CORS header | Session probe | ACAO=* from the Pages origin; FFC ACAO=None | **CONFIRMED** |
| 3 | FFC documented, free w/ attribution; 6,160 drafts Aug 6-13 | VERIFIED-LIVE | 200; exactly 6,160 drafts, 2026-08-06..08-13; stdev/high/low/bye present | **CONFIRMED exactly** |
| 4 | depth_charts_2026 same-day fresh; stats_player naming; pbp xpass/pass_oe | VERIFIED-LIVE | depth_charts last-modified 2026-08-13 08:15 UTC (same-day); stats_player 200; pbp 200 (19.9 MB) | **CONFIRMED** (col-level fields previously verified; sizes consistent) |
| 5 | No free in-season route data for 2026 | SOURCED | Addendum workflow probed for refutation | See addendum - **HELD** unless refuted there |
| 6 | injuries conflict: docs say dead post-2024, 2025 file exists | Conflict flagged | injuries_2025.parquet 200, 95 KB, last-modified 2026-03-18 (consistent with a completed 2025 season file) | **CONFIRMED as flagged** - 2026 in-season reliability remains unknown; addendum researched the feed's fate |
| 7 | PlayerProfiler API open, undocumented; ToU bans scraping; $45 package | Probe + SOURCED | HEAD 200 (door open - no data pulled, per ToU) | **CONFIRMED** at status level |
| 8 | 17 new play-callers incl 4 first-time | SOURCED | Six rows spot-checked via addendum workflow | See addendum |
| 9 | BeerSheets discontinued | SOURCED | Not re-probed (display-context only) | ACCEPTED as SOURCED |
| 10 | NFL Fantasy shutdown; ESPN exclusive | REPORTED | Addendum sought primary confirmation | See addendum |
| 11 | Tool prices as tabled | SOURCED | Overlap-checked against independent v2 research; consistent | **CONSISTENT** |
| 12 | Draft Intel only leaguemate product, 5-yr cap | SOURCED | Matches independent v2 competitor research | **CONSISTENT** |
| 13 | 4for4 O-line r=0.462; PA +0.06 EPA | REPORTED (their n) | Not re-derivable without their data; attributed-only status is correct | ACCEPTED as REPORTED |
| 14 | Play-caller persistence: analyst consensus, no coefficient | REPORTED/UNVERIFIED | Correctly tagged; the build treats persistence exactly as the in-league tendency lesson dictates | ACCEPTED |

**Register detail corrected:** #14a-style per-year pfr_advstats pulls use `advstats_week_*_YYYY.parquet`; the season-level files are all-years combined. My probe error, not the doc's.

---

## Part 3 - What this review changes

1. **FFC market bands are in** (new, free, honest primitive-5 path on the market axis).
2. **playcallers.csv becomes a first-class curated file** with per-row sources and a REPORTED badge in the UI - the largest honesty risk named and contained.
3. **Verdict-subject rule fixed in spec:** model primary stays the wait-or-reach subject; overlay decides coin flips only.
4. **Scoring rule pre-registered** in the overlay schema before the first call is recorded.
5. **ADP source stamping** added to the payload and provenance footer.
6. **Two Actions-cron operational realities** (60-day disable, shard hygiene) written into the plan.

Everything else in the research doc survives pressure-testing unchanged. It is a strong document; its strongest property is that its architecture section and its overlay section both correctly generalize lessons this project already paid for.
