# YeahThatFantasyLeague - Full Handoff

**Written 2026-08-11 for a successor session. The research record below is
self-contained: read this plus `out/`, no chat history needed.**

Verifier: Anthony DellaPia. Draft is **2026-09-08**.

---

## LIVE BATON - update this block, last writer owns it

**THE CONVENTION: whoever writes last updates this block, in the same commit as
the work.** Not afterwards, not "when things settle". If this block disagrees with
`git log`, the block is wrong and the next agent has been misled.

| | |
|---|---|
| **Last touched** | 2026-08-28 by Codex - excluded absent RB observations from the live BULLISH percentile, suspended the vacuous TE matrix with visible provenance, reran N.1 in its honest RB/WR scope, and activated raw-schedule forward Vegas only for QB environment and WR opportunity. |
| **Next agent** | Wait for Anthony's review of `codex/bullish-input-integrity`; do not merge it unilaterally. Keep #54 OPEN, ON HOLD, and untouched. After this branch is resolved, follow the remaining `docs/ffopportunity/FFOPPORTUNITY_HANDOFF.md` integration order, preserving the display/shadow/offline/do-not-wire boundaries. |
| **Branch** | `codex/bullish-input-integrity`, based on `main` at `242ae6b` (#65); review and merge only through its PR |
| **Live site** | https://anthonydellapia1117.github.io/yeahthatfantasyleague - #65 is merged and live at `242ae6b`; the Pages run was green, all 48 deployed files were byte-identical, all seven surfaces returned 200, `PAGES DATA FRESH - published 2026-08-28T02:16Z (9h ago)`, and `PREFLIGHT OK - snake, 12 teams, 14 rounds, 60s timer, no reversal`. The BULLISH input-integrity branch is not live pending review. |
| **Draft order** | UNDRAWN as last checked 2026-08-28 (`status pre_draft`). A Routine checks every 2h and self-retires on the draw. |
| **Live draft geometry** | snake, 12 teams, 14 rounds, 60s pick timer, no third-round reversal - asserted by `src/preflight_draft.py` |
| **Live path** | PARTIALLY VERIFIED 2026-08-26 against real Sleeper draft `1388575351239606272`: 19 teams / 120s / 2 flex. It has **NOT** been verified against this league's real 12 teams / 60s / 1 flex with a drawn order. See `AGENT_HANDOFF_SPEC.md` §11. |

### What was done in the last session

1. **#53 and #55 through #65 are merged; #65 is live.** #53 records the human
   live-path exercise and its limits. #55 fixed the round-7 VONA lookahead by
   comparing against real round 8 and published the reviewed N.1
   **INCONCLUSIVE** finding on `ff-hub.html`. #63 made the red paint and beep share
   one boundary, fixed BULLISH UTC provenance, replaced data-dependent collision
   assumptions with deterministic fixtures, corrected digest-mismatch diagnosis,
   and removed transient team-name assertions. #64 fixed the live `LA/LAR` joins;
   #65 completed the Unicode quote contract and added the repository-discovered
   output team-code guard. Its Pages deployment is 48/48 byte-identical and
   healthy. Do not confuse the unmerged BULLISH branch with a stale deploy.
2. **#58 consolidated player identity.** One Python comparison key plus the
   collision-aware identity resolver replaced fourteen Python definitions; four
   browser copies are held to Python by corpus parity. Replay survival pairs fell
   17,068 -> 16,949 by removing 119 phantom alias identities; Brier improved
   0.0745 -> 0.0710 and skill 0.1960 -> 0.2466. Sixteen current players recovered
   ADP fields. The known Leon Johnson wrong-era mapping remains logged and out of
   scope.
3. **#60-#62 hardened the 60-second room and seat resolution.** The clock is
   server-anchored; draft and picks fetch in parallel; the board cannot lag behind
   a fresh clock; a confirmed commissioner undo recovers visibly; freshness and
   amber/red/blink stages scale with `pick_timer`. #61 resolves the BULLISH overlay
   from a complete drawn-order permutation, preserves all twelve pre-draw windows,
   and fails loudly on unresolved drawn state. #62 removed the unsafe optional
   `teams=None` resolver interface. #63 made red paint and the urgent beep consume
   one `redStage` predicate.
4. **#56-#57 closed the daily dependency and same-day lineage gaps.** pages-data
   rebuilds every declared downstream consumer after shard refresh. Engine
   derivatives link by a canonical whole-payload SHA-256 rather than a date, and
   same-day mutation fixtures prove the guard bites. Strict artifacts fail closed;
   BULLISH/ceiling remain display-only and visibly stale during the intentional
   06:00-08:00 lag instead of burdening the draft-morning workflow with HISTORY.
5. **#64-#65 fixed team-code and player-quote contracts without rewriting
   provider shards.** One canonical Python helper maps `LA->LAR`, `JAC->JAX`,
   `WSH->WAS`, and `ARZ->ARI`; every changed Python consumer imports it. Matching
   browser boundary logic now lets the team and room pages join provider-native
   `LA` rows to canonical `LAR`. Before the fix, all six Rams on the CVS board had
   null team context and surrounding talent, the room omitted the Rams PROE chip,
   and `teams.html#t=LAR` fell back. Source-derived guards cover all four team-keyed
   shards and browser smoke exercises the LAR route. BULLISH tags and the engine/VOR
   payload are unchanged. U+2019 was already folded and the claimed Wan'Dale loss
   did not reproduce. Exhaustive
   committed-source inventory found ten real U+2019 player-name uses, zero U+02BC,
   U+00B4, or U+2018 uses, and zero U+0060 backticks embedded in a player name.
   Pre-#65 main nevertheless failed U+02BC and U+0060 comparison and split the
   U+00B4 search token. One pre-NFKD fold now covers ASCII plus U+2019, U+02BC,
   U+0060, U+00B4, and U+2018 in Python and JavaScript while exact-name collision
   evidence remains untouched. Walter's capture regex imports the same contract.
   A dynamic guard scans every committed output JSON/CSV, including scalar fields,
   code-keyed maps, and unlabelled pair domains; unknown codes fail while aliases
   and the explicit `FA` non-team state pass.
6. **The current branch makes BULLISH inputs honest before adding signal.** The
   percentile sweep found exactly one live contaminated population: absent 2025
   RB usage was coerced to observed zero. The discovery frame changed 50 entries
   to 46 observations; after #65's fresh engine moved Jonah Coleman outside the
   168-pick pool, the committed frame is 49 candidates = 46 observations + three
   explicit null exclusions. The upper-middle median is 0.5060, Jacory
   Croskey-Merritt and Tyler Allgeier move from criterion probability 0.75 to 0.50,
   and Bucky Irving's real 0-of-n inside-five result remains a legitimate zero.
   Every percentile now carries observation and exclusion accounting.
7. **The live TE gate is suspended, not cosmetically relabelled.** All 19 eligible
   veterans received the same 0.9 market-share value, so the advertised 2-of-2
   matrix was one varying on-field-dropback input times a constant. McBride,
   Warren, Pitts, Kelce, and Henry are omitted from live tags and retained in a
   top-level evidence ledger. All three tag surfaces render the same neutral
   suspension explanation. The ledger also records Isaiah Likely's 2025 Baltimore
   share being ranked alone in his 2026 Giants group. The historical TE extract is
   regenerated to 6,730 identified rows with no fake route alias or NA-subsetting
   junk; the still-dirty RB/WR R exports remain explicitly unconsumed.
8. **N.1 remains INCONCLUSIVE after the honest scope change.** RB/WR tags are 22/35
   (62.9%) versus 86/164 (52.4%), +10.4pp, 95% CI [-7.3, +28.2], p=0.261. Removing
   the non-discriminating TE criterion reduced the point estimate and widened the
   interval from 31.0pp to 35.5pp; it did not rescue the result. The approved
   verdict is artifact-backed on `ff-hub.html`, and all tags remain display-only.
9. **Forward Vegas is live only in the two approved consumers.** The builder reads
   raw `schedule_2026.csv`, validates 272 regular-season games / 32 canonical teams
   / 17 games per team, verifies the home-spread sign independently, and derives
   the maximal contiguous fully priced horizon every build. Current scope is Weeks
   1-6, 93 games, 186 team-games; Week 7 is 7/14 priced. The top environments are
   LAR, DET, BAL, BUF, and SF. Gains are Brock Purdy and Jordan Love; losses are
   Caleb Williams, Jalen Hurts, Justin Herbert, Kyler Murray, and Trevor Lawrence;
   Mahomes promotes to BULLISH and Ja'Marr Chase demotes to WATCH. The replacement
   feeds only QB environment and WR opportunity. All ten RB tag records are
   object-identical in the same-build counterfactual because RB expected-TD equity
   remains on its separate Week-1 source. The horizon, priced-game counts, source
   SHA, and activation delta are permanent provenance.
10. **Source-quality defects are recorded separately from app truth.** The
   lucky-player penalty reproduces from the contaminated all-week file but changes
   materially in the clean regular-season control. The R forward-Vegas export has
   the opposite sign in 224/224 team-games, while the app's existing Week-1 formula
   was already correct. Corrected R source also claimed an RB regeneration whose
   committed CSV still carries `target_volume` and 2,530 junk rows. Reproducible
   arithmetic, corrected source, and regenerated artifact bytes are three distinct
   claims.
11. **Full battery green on the current branch.** The
   gate-runner self-test plus fourteen gated suites ran
   16/70/22/50/70/17/16/79/63/47/45/1211/23/363/38 checks (2,130 total). All five analysis
   determinism reruns executed from the complete HISTORY cache: 38 guards, zero
   skips. Browser smoke ran 363; `MATH DIFF PROOF: EMPTY` for all ten frozen
   function bodies. The ceiling artifact was rebuilt against #65's exact engine
   lineage before the BULLISH chain: weekly replacements are unchanged; 140 ADPs
   moved with the fresh engine, and only Kyler Murray and Tyler Allgeier moved in
   projection/availability-adjusted projection.

### In flight / nothing blocked

The current BULLISH input-integrity branch is green and awaits Anthony's review; it
must not merge without that review. PR #54 remains OPEN, ON HOLD, and untouched at
remote head `4bd541e`; its mergeability is currently unresolved against moving
`main`. Its PATHS
policy is still the data-derived R1-2 / R3-4 / R5-7 coverage-valid bands with the
conditional spread floor. Do not rebase, resolve, or merge it until the order is
drawn and Anthony asks to inspect his actual slot. The `docs/ffopportunity/` R export
is an analysis source, not app truth: the app's Week-1 Vegas sign was already
correct, and the shipped QB table did not inherit the R file's `-2` interception
error. Do not consume unreviewed local regenerated exports. The forward-Vegas and
TE items named in the old queue are complete on this branch; do not repeat them.

### The three things the next agent most needs to know

1. **Do not replace content checks with timestamps, presence checks, or today's
   payload.** Human dates are provenance, never identity. Strict consumers fail
   closed; display-only lag is visibly neutral. Behavioral laws need deterministic
   fixtures even when a live integration scan is retained.
2. **The browser-to-Sleeper live path is only partially verified.** Anthony ran the
   deployed room against a real 19-team Sleeper draft (`1388575351239606272`) on
   2026-08-26. It proved server-derived geometry at 19 teams / 120s / 2 flex, seat
   detection, format warnings, and populated surfaces. It did **not** exercise the
   league's real 12 teams / 60s / 1 flex with a drawn order. Automated smoke is
   hermetic. Do not promote the partial run into evidence for the untested case.
3. **PII is out of HEAD but still in git history.** Retention is Anthony's call,
   deferred to after the draft. Do not act on it unilaterally.

---

---

## THE HEADLINE, and it contradicts the brief

**There is no draft-day roadmap. Every draft-day hypothesis tested is null.**

That is not a failure to find one. It is a finding, on 156 franchise-seasons and 13 champions, and it is the single most valuable thing in this document because it stops the successor spending days looking for a pattern that is not there.

| Hypothesis | Result | Verdict |
|---|---|---|
| Champions draft a distinctive rounds 1-5 archetype | No sequence reaches n=5. Max n=7 | **Underpowered, untestable** |
| Champions wait on QB | 6.46 vs 5.92, permutation **p=0.252** | **Folklore** |
| Champions avoid QB in rounds 1-5 | 62% vs 48%, permutation **p=0.266** | **Folklore** |
| Champions load RB early | 2.15 vs 2.01 RB in rounds 1-5 | **Noise** |
| Champions load WR early | 2.00 vs 2.03 WR | **Noise** |
| Draft slot matters | Champions spread 2,2,4,5,5,5,8,10,10,11,12,12,12. Mean 7.5 vs 6.5 expected | **No pattern** |
| Draft-day composition predicts finish | corr RB -0.013, WR -0.049, QB +0.110 | **All ~zero** |
| Drafted-vs-acquired share predicts winning | corr champion +0.043, rank -0.101 | **Dead** |
| Champions draft the consensus #1 player | **0 of 13.** But p=0.323 under random | **Striking, not significant** |

## THE FAAB SIGNAL IS ALSO DEAD

Tested 2026-08-11. **Permutation p = 0.197**, n=118 franchise-seasons 2016-2025, 10 champions, 50,000 shuffles. Champions mean bid 46.8 versus pool 35.7. Max single bid: champions 91.4 versus pool 91.2, p=0.465.

**Not significant. Do not build on it.**

## THE STRONGEST SURVIVING CANDIDATE, and it is marginal

**Lineup efficiency: started points as a percentage of optimal.**

| | Champions | Field | p |
|---|---|---|---|
| Lineup efficiency | **89.75%** | 88.44% | **0.078** |

One canonical test: `src/phase3_lineup.py`, 50,000 shuffles, seed 20260811, n=156 franchise-seasons and 13 champions, written to `out/efficiency_test.json` and read by the dashboard rather than recomputed. Quote it as 0.078 - a fourth digit implies precision a 50,000-shuffle test does not have.

**An earlier draft reported 89.96 / 88.68 / p=0.0697; that figure is stale and does not reproduce.** All efficiency percentages in this document are ratio-of-sums, the standardized basis per the accepted 3B audit.

Closest to significance of anything tested and still above 0.05 at n=13. Direction is consistent and the mechanism is plausible, which is more than any draft-day hypothesis managed. Treat as a lead, not a finding.

**Per-franchise, and this is the personally actionable part:**

| Franchise | Efficiency | Pts left/wk | Per season | Titles |
|---|---|---|---|---|
| John Juliano | 90.41% | 12.47 | 175 | 0 |
| **Phil Baldino** | **89.97%** | **13.65** | **191** | **3** |
| **Cambrias** | **89.67%** | **14.40** | **202** | **3** |
| Frank & Julian | 89.24% | 13.72 | 192 | 0 |
| Mike Long | 88.82% | 14.12 | 198 | 0 |
| Ronnie | 88.77% | 14.90 | 209 | 2 |
| **Antdell & Ernie** | **88.55%** | **15.14** | **212** | **0** |
| Nolan & Vinny | 88.53% | 15.22 | 213 | 0 |
| Pung & Tralie | 88.47% | 15.08 | 211 | 0 |
| Team JoeBa | 88.46% | 14.73 | 206 | 0 |
| Richie | 88.43% | 15.24 | 213 | 1 |
| Chris & Dom | 88.14% | 16.35 | 229 | 2 |
| LFTLR | 87.71% | 15.40 | 216 | 0 |
| Rob & GregBo | 87.42% | 16.72 | 234 | 1 |
| GaTTa | 85.33% | 19.54 | 274 | 1 |

Ratio-of-sums per `src/phase3_lineup.py`. Anthony ranks **7th of 15 by efficiency, 9th of 15 by points left per week**. An earlier draft said 11th of 15; that does not reproduce under either ranking. Both three-time champions sit above him either way.

**Positional decomposition of the gap to Baldino (phase 3A): RB is 80 percent of it.** RB capture 86.9 percent versus his 90.7. QB is a strength, not a leak: 93.5 percent capture versus his 89.6, worth 1.06 pts/wk in Anthony's favour. The raw "WR is the biggest leak" reading is an artifact of WR carrying the most starter slots.

**Gap to Baldino: 1.49 points per week, 21 points per season. The 2025 championship was lost by 12.44.**

That is not proof of causation, and Chris & Dom won twice at 88.21% while John Juliano leads the league with zero titles. But it is the only lever found in this entire project that is measurable, controllable, and larger than the margin that actually beat him.

---

## PART 1 - SETTLED. Do not re-derive.

### The league
12 teams, snake, full PPR, 13 completed seasons 2013-2025. Yahoo 2013-2024, Sleeper 2025-2026.
2026 league `1389378429505241088`, draft `1389378429505241089`, **order NOT set**.
Anthony is roster 7 "Taylor Made", co-owner ernie706.
2026 scoring: `rec 1.0, pass_td 6.0, pass_yd 0.04, pass_int -1.0, rush_td 6, rec_td 6, fum_lost -2.0`.
Starters `QB RB RB WR WR TE FLEX K DEF` + 5 bench.
**EXCLUDE** Sleeper `1092592577628426240`: empty trial shell, 0 picks, 0 transactions.

### Champions, all 13 verified
2013 Ronnie | 2014 GaTTa | 2015 Chris & Dom | 2016 Chris & Dom | 2017 Richie | 2018 Phil Baldino | 2019 Cambrias | 2020 Ronnie | 2021 Rob & GregBo | 2022 Cambrias | 2023 Phil Baldino | 2024 Phil Baldino | 2025 Cambrias

Titles: **Cambrias 3, Phil Baldino 3**, Chris & Dom 2, Ronnie 2, Richie 1, Rob & GregBo 1, GaTTa 1.
**Antdell & Ernie: 0 in 13 seasons.** Runner-up 2025, lost by 12.44.

### Every champion's rounds 1-5 sequence
```
2013 Ronnie        QB WR RB RB WR      2020 Ronnie        RB RB QB WR WR
2014 GaTTa         TE WR TE WR RB      2021 Rob & GregBo  WR RB QB WR RB
2015 Chris & Dom   WR TE RB QB RB      2022 Cambrias      RB RB WR RB RB
2016 Chris & Dom   WR WR WR RB TE      2023 Phil Baldino  WR RB RB RB WR
2017 Richie        WR RB RB WR WR      2024 Phil Baldino  WR RB WR QB TE
2018 Phil Baldino  RB WR RB WR RB      2025 Cambrias      RB RB TE RB WR
2019 Cambrias      RB WR RB WR WR
```
**No two are the same.** That is the point.

### The #1 board player, every season
| Yr | #1 on board | Pos | Drafted by | Champion took him |
|---|---|---|---|---|
| 2013 | Jamaal Charles | RB | Team JoeBa | no |
| 2014 | LeSean McCoy | RB | Cambrias | no |
| 2015 | Antonio Brown | WR | LFTLR | no |
| 2016 | Antonio Brown | WR | Antdell & Ernie | no |
| 2017 | David Johnson | RB | LFTLR | no |
| 2018 | Todd Gurley | RB | Frank & Julian | no |
| 2019 | Saquon Barkley | RB | Frank & Julian | no |
| 2020 | Christian McCaffrey | RB | Team JoeBa | no |
| 2021 | Christian McCaffrey | RB | Nolan & Vinny | no |
| 2022 | Jonathan Taylor | RB | Rob & GregBo | no |
| 2023 | Justin Jefferson | WR | Chris & Dom | no |
| 2024 | Christian McCaffrey | RB | John Juliano | no |
| 2025 | Ja'Marr Chase | WR | Richie | no |

9 RB years, 4 WR years, **0 for 13**. Expected 32% of the time by chance. Report it as descriptive colour, never as a rule.

### Franchise versus person - critical
The archive labels franchises with **current** names applied retroactively. `member_name` is a continuity key, **not** who managed that season. `out/franchise_eras.csv` has 20 eras / 15 franchises.

| Franchise | Split | Kind | Treatment |
|---|---|---|---|
| Richie | 2021: Lefty & Long (Nolfi + Mike Long) to Nolfi solo | behavioural | **split** |
| Rob & GregBo | 2015: Rob solo to Rob + Gregory DellaPia | behavioural | **split** |
| Nolan & Vinny | 2017: Nolan solo to Nolan + Vincent Gatta | behavioural | **split** |
| Antdell & Ernie | 2015: Three Amigos (3) to Two Amigos (2) | behavioural | **split** |
| Ronnie | 2024: Harry joined, **silent partner** | nominal | **pool** |

Effective Phase 4 unit count: **19, not 20**.

Three champions invisible at franchise level: **Vincent Gatta** won 2014, now drafts for Nolan & Vinny. **Mike Long** shares the 2017 title, his solo franchise shows 0. **Gregory DellaPia** left Antdell & Ernie in 2015 and won 2021 with Rob & GregBo.

### Verified data
2,339 picks 2013-2025, 12 franchises every season, no survivorship gaps. 37,106 weekly roster rows with `started`/`points`. 3,938 transactions 2014-2025; 2013 has none. **52 assertions pass, 0 fail.** 2025 archive draft reconciles to Sleeper **168 of 168**. Identity map **12 of 12** verified by overall-pick join, zero name similarity used. 2018 overall pick 38 is a **forfeit** under rule 3.2's 2-minute clock, not a gap.

### Phase 2 result
**League-wide DRAFTED share of starter points: 68.9%.** Range 60.2 to 76.2. Basis: 2014-2025, the twelve seasons with transaction data (G-003 excludes 2013 from the acquisition split).
**It does not predict winning.** Cambrias 64.9% with 3 titles. Antdell & Ernie 64.5% with **0**. Rob & GregBo 82.4%, highest in league, 1 title.

### Two champions, two mechanisms
| | Actual W% | All-play W% | Gap | Drafted share | Titles |
|---|---|---|---|---|---|
| Cambrias | .606 | .606 | **0.000** | 64.9 | 3 |
| Phil Baldino | .596 | .563 | **+.033** | 72.3 | 3 |
| Antdell & Ernie | .484 | .489 | -.005 | 64.5 | **0** |

Cambria wins on raw strength. Baldino outperforms his all-play. **Anthony has not been unlucky.** Baldino also has the better rate: 3 in 9 seasons vs 3 in 13.

---

## PART 2 - DEAD ENDS. Cost real time. Do not repeat.

1. **Yahoo Fantasy API is CLOSED.** Fantasy Sports scope no longer exists in Yahoo's developer console. A valid OAuth token returns `oauth_problem="additional_authorization_required"`. Verified on two apps, screenshot-confirmed. No Python wrapper routes around it. Yahoo now requires written application and review.
2. **The 5% bonus gap is ACCEPTED.** Six 40-yard long-play bonuses, Yahoo 2013-2024 only, 6.14 pts/team-week, present in team totals, absent from per-player rows. Flips 47 of 1,128 games (4.17%). The Phase 2 ratio is unaffected - both sides bonus-exclusive. Owner confirmed these were a **deliberate rule change to raise difficulty**. Keep as a product idea for a rules-evolution feature; not an analysis blocker.
3. **Rule 3.3 (draft order = reverse prior finish) is NOT FOLLOWED.** 17 of 141 slot assignments match, 12.1% vs 8.3% random. Slot is unpredictable until it posts.
4. **Browser scraping Yahoo works but rate-limits** at ~50 fetches with HTTP 999.
5. **Quarantined fields**, no traceable derivation: `value`, `adp_consensus_score`, `adp_differential_pct`, `risk_tolerance`, and LeagueLegacy's `scoring_format` (says half-ppr for all 14 seasons; Sleeper says `rec=1.0` full PPR).
6. **`adp_effective_pick` is NULL on all 2,339 rows.** ADP is recoverable only as `overall_pick - adp_differential`, valid on 2,039 of 2,339.

---

## PART 3 - REMAINING WORK

**A. Significance-test the FAAB finding.** 46.8 vs 34.7 is the only live signal. Permutation test it. If it holds, it is the answer to "what do champions do."

**B. In-season, not draft-day.** Every draft-day door is closed. Look at: waiver timing (early-week vs late), start-sit accuracy versus `is_optimal`, points-left-on-bench, and streaming behaviour at QB/TE/DEF.

**C. Cambria vs Baldino.** They win differently. Cambria 35.0 tx/season, Anthony 36.2 - **near-identical volume, opposite outcomes**. Volume is not it. Test bid size, timing, and target quality.

**D. Anthony's actual leak.** Not draft position, not drafted share, not luck. Candidates: start-sit, FAAB sizing, roster construction late.

**E. Phase 5 simulator.** All 12 slots, since order is unknown. Survival probability, run probability, opportunity cost, per-slot decision cards.

---

## PART 4 - FILES

| Path | Contents |
|---|---|
| `out/picks.csv` | 2,339 picks, all seasons |
| `out/pick_value.csv` | picks joined to realized starter production, VOR, vs-expected, hit/bust |
| `out/drafted_vs_acquired.csv` | 156 franchise-seasons, the central number |
| `out/champions.csv` | 13 seasons |
| `out/franchises.csv` | 15 franchises, spans, titles, active |
| `out/franchise_eras.csv` | 20 eras, people, titles, confidence |
| `out/franchise_lineage.md` | person-vs-franchise reasoning, era rules |
| `out/identity_map.csv` | 12 of 12 verified mappings |
| `out/assertions.csv` | 52 checks, 0 failures |
| `out/gap_register.md` | G1-G7, open and closed |
| `out/gap_report_2026-08-11.md` | 18 confirmed gaps, scrape list |
| `src/ingest.py` | Phase 1, re-runnable |
| `src/phase2_value.py` | Phase 2, re-runnable |

Sources: `made-resources/YeahThatFantasyLeague_LeagueLegacy_Archive_2013-2026/` (71 files) and `LeagueLegacy-io/leaguelegacy_YeahThatFantasyLeague_full_export/` (33 files). Archive A wins for picks and weekly rosters; export B wins for transaction items.

---

## CONSTRAINTS

Never backfill a pick, roster, transaction, or result. Never merge manager identities on name similarity. Every derived table carries source, source_ref, fetched_at, confidence. Every 2013-2024 figure carries the bonus-exclusive basis note. Hyphens only, no em dashes, no emojis. Tables over bullets. Lead with the answer. Report confidence and sample size beside every claim.

**With 13 champions, most comparisons will not reach significance. That has already proven true for every draft-day hypothesis. Do not manufacture a clean recipe to satisfy the framing of a question.**


## Draft Room v2 - shipped 2026-08-12

Live app: https://anthonydellapia1117.github.io/yeahthatfantasyleague/out/draft_room.html
(local `out/draft_room.html` is the offline fallback; same embedded model).
Six gated phases per docs/DRAFT_ROOM_BUILD_ORDER.md: broadcast-grade design
system, live pick-clock mode (duration from draft settings), sixteen features (roster-need-aware
recommendation first), the quarantined league-mate simulator, GitHub Pages
deployment via the gh-pages workflow, and this review. Draft-morning production
uses the mapped, gated `.github/workflows/draft-refresh.yml` chain in
`docs/DRAFT_MORNING.md`; an engine-only commit is invalid.
The survival math is frozen: 41 Python guards + 350 browser guards, including 42
JS parity anchors, plus the calibration benchmark gate every merge.

## Draft-day features + conviction overlay - shipped 2026-08-13

Four draft-day surfaces on top of v2, math untouched (the five survival
functions are byte-identical to the pre-feature main; the diff proof runs at
every merge):

- Pick grade: 0-100 gear beside the live answer. Presentation, not decision -
  named weights in code (GRADE_W), three bands carry the message (red 0-39
  not at this price, amber 40-69 defensible, green 70-100 take him). Guard 9
  proves the grade reads no banned field and no verdict reads the grade;
  six pinned anchors including the monotone Dak curve gate every merge.
  Evidence chips (play-caller REPORTED + date, team PROE, FFC band) sit
  beside the gear and never enter the number.
- Recommendations panel: on WAIT or COIN FLIP, 2 alternatives by default
  (toggle 3/4/5, search appends one, max 6), each with its own gear.
- Draft grid: 12 team columns x 14 rounds, position-coded, live feed.
- Value board: overall top 50/100 + positional top 5/10/20 with FLEX and
  DST, drafted auto-remove/grey-out toggle, K/DST floor labels.

Conviction overlay (Expansion Phase B): `data/my_board.csv` - schema and the
pre-registered scoring rule live in the file header. The engine applies it
AFTER build_model as a pure transform (apply_overlay): YOUR CALL chips beside
model VOR on every surface, survival of each bull to the slot-7 picks in the
MY BOARD markdown section, within-tier resort on positional panels (display),
and its ONE decision role - the coin-flip tie-break toward bulls. The model
primary is always the wait-or-reach subject; guard 10 (10 checks) proves the
overlay reaches no other arithmetic and that an empty board is byte-identical
to no overlay. The shipped board is empty - populate it with your calls and
regenerate.

## Expansion Phases C-E - shipped 2026-08-13

Three shard-fed pages beside the draft room, all on the same design system,
all with tap-any-number provenance (tap a number, see its shard, field,
source, and fetch time):

- out/players.html - hash-routed player pages: value vs market with the FFC
  band and attribution, literal 2025 nflverse usage columns, draft capital,
  YOUR CALL block, K/DST floor labels. Absent blocks (combine, snap share,
  EPA, xFP, routes) are declared absent, never estimated.
- out/teams.html - all 32 teams: curated play-caller card (19 confirmed
  rows; uncurated teams say so), PROE with its measurement basis, vacated
  opportunity (departed vs arrivals with the computation note), depth chart
  ranked by value with the official slot as metadata.
- out/home.html - the action board: draft countdown from the payload, data
  staleness board, overlay completeness, attributed trending adds, the one
  history fact (consensus #1, 0-for-13, p=0.323 - colour, not strategy),
  links to every surface.

Guards: test_pages_data.py sections 10-12 resolve every on-page number
reference against the committed shard fields and assert every honesty label.
Smoke scenarios 10-12 run the pages on a hermetic local server. N1 stands:
the engine reads nothing from this layer.

## App shell - shipped 2026-08-13

out/nav.js is the single chrome source: the fixed bar (gold hairline, YTFL
HUB wordmark, countdown/LIVE pill reusing the draft room's own state, mobile
drawer), the kicker header style, and the phase 3 polish (opt-in reveals and
border-lift hovers, reduced-motion aware). All five pages share the #0b1120
dark family, an 1100px container, and the same header treatment; semantic
verdict colors are guard-asserted unmoved. The draft room include sits
outside the ENGINE-DATA sentinels (regeneration verified byte-identical), the
bar collapses to 36px in live mode, and a smoke guard keeps the answer, gear,
and verdict above the fold at 390px. Guards: test_pages_data sections 13-15;
smoke scenario 13.

## Big Board - shipped 2026-08-13

out/big_board.html - the pre-draft master list. The rank is VOR and nothing
else (the guard asserts the sort expression in code); tiers render as cliff
breaks under the position filters. Every factor Anthony asked for sits on the
row as a LABELLED evidence chip with tap-provenance - market band and bye
(FFC), 2025 workload (nflverse), depth slot (ESPN), play-caller with its
source tag, PROE - and the factor ledger at the top states where each factor
lives: decision input (VOR, survival timing), displayed evidence (coaching,
team context - N1, rejected as probability input p=0.99), or not wired on
purpose (schedule/competition - no stamped source, SOS approximations on the
reject list). No hidden composite, ever. Guards: pages-data section 11b; smoke
scenario 15 (on-screen order proven equal to payload VOR order).
