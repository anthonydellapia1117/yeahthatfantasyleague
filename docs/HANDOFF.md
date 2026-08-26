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
| **Last touched** | 2026-08-26 by Claude (this session, ending - Anthony's Fable 5 budget is exhausted until 08-31) |
| **Next agent** | **Codex.** Read `docs/AGENT_HANDOFF_SPEC.md` FIRST, sections 1 and 2 before touching anything. |
| **Branch** | `claude/chat-migration-desktop-ruannr`, based on `main` |
| **Live site** | https://anthonydellapia1117.github.io/yeahthatfantasyleague - byte-verified against `main` as of `49e3ea9` |
| **Draft order** | UNDRAWN as of 2026-08-26 22:12Z. A Routine checks every 2h and self-retires on the draw. |
| **Live draft geometry** | snake, 12 teams, 14 rounds, 60s pick timer, no third-round reversal - asserted by `src/preflight_draft.py` |

### What was done in the last session

1. **P0** - the pick clock (hardcoded 120s against a real 60s `pick_timer`, anchored
   to poll-detection). Server-anchored or honestly absent. Merged, deployed.
2. **P1 A/B/C/F** - VONA one-frame conditioning (28% of nodes had negative VONA),
   VONA starter feasibility via the shared `forward_policy` layer, room response
   validity vs freshness, and the BULLISH-vs-ADP verdict changed from an unsound
   automated rule to reviewed reported text. Merged (#51), deployed.
3. **P2** - pages-data cron verified dead for 4 days (8 of 14 scheduled runs failed);
   root-caused to a crosswalk guard and a missing diacritic fold; fixed, and the
   alert moved to the published artifact (`src/check_publication.py`).
4. **Self-audit** - `docs/SELF_AUDIT_2026-08-26.md`. 39 defects classified; 4 caught
   pre-commit (~10%); five recurring classes; a predicted-defect hunt that found
   the items below.
5. **Archive prune** - the repo is public and member finance/profile data was
   tracked under a duplicate root that defeated the `.gitignore` rule. 165 files
   deleted, roots collapsed to one, nothing functional changed (verified
   byte-for-byte).
6. **Draft-critical fixes** - geometry preflight; the VONA tree now rebuilds with
   the engine it derives from; skipped guards now fail the gate.
7. **`fetch_history.py` extended** from four data families to nine. The five it did
   not know about had no URL recorded anywhere, which left the C5 BULLISH inputs
   unreproducible by anyone. All five URLs verified byte-identical to the cache.

### In flight / nothing blocked

Nothing is half-finished. Every change above is committed, gated, and either merged
or on the branch with a green battery.

### The three things the next agent most needs to know

1. **`docs/AGENT_HANDOFF_SPEC.md` §1** - the three failure modes that produced this
   project's live defects. More useful than the module map.
2. **The live browser-to-Sleeper path has never been tested.** 326 smoke scenarios,
   all hermetic. It is the draft-night path. Anthony tests it manually.
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
deployment via the gh-pages workflow, and this review. Draft-morning flow:
`python3 src/engine_2026.py && git commit -am "draft morning rebuild" && git push`.
The survival math is frozen: 21 Python guards + the smoke suite with 42 JS
parity anchors + the calibration benchmark gate every merge.

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
