# Independent assessment: gemini_player_value_analysis.md

Written 2026-08-26, from a cold read of `docs/research/gemini_player_value_analysis.md`
alone. `docs/bullish_algorithm_review.md` was NOT opened before or during this
assessment - the reconciliation against it happens in Phase B, after this file is
committed. Every factual verification below was made against current data (the repo's
shards and history cache, live Sleeper API, live nflverse releases), never from memory;
each computed check was independently replicated by a second pass before being stated
here as fact.

Verdict up front: the document's 2026 roster geography is accurate and two of its core
ideas (TPRR-style target earning for WRs, route share for TEs) point in a sound
direction. But its narrative and its embedded implementation prompt specify two
different algorithms; its "predictive" evidence is largely same-season circular
correlation; its thresholds are asserted, not derived, and at least one would blank an
entire position; every sleeper it nominates fails its own gates; and several inputs it
requires cannot be built from any source we can reach. Nothing in it should ship as
written. Its salvageable content is a shortlist of criteria DIRECTIONS whose thresholds
must be re-derived from our own data.

---

## 1. Internal consistency: the narrative and its embedded prompt disagree

The report presents a criteria matrix in prose ("The 'BULLISH' Identification
Algorithm") and then an executable prompt ("Implementation Blueprint"). They are not
the same algorithm.

| Position | Narrative says | Embedded prompt says | Effect |
|---|---|---|---|
| Gate (RB/WR) | at least 4 of 5 criteria | ALL of 4 criteria (no "at least" language) | different qualification logic entirely |
| RB volume | >60 targets/17g pace | HVT (receptions + inside-10 carries) > 4.5/g | different metric; the doc itself argues targets > receptions, then uses receptions |
| RB goal line | >65% of team inside-10 attempts | absent | committee backs can qualify under the prompt |
| RB capital | NFL Draft R1-2 AND years 1-4 | fantasy ADP Rounds 1-2 | conflates NFL draft capital (a talent proxy) with fantasy ADP (a market price); tenure filter vanishes |
| WR | 5 criteria incl. xYPRR 80th pct and "Vegas alignment" | drops both, ADDS NFL Draft R1-2 (which the narrative assigns to RBs, not WRs) | prompt outright excludes every NFL R3+ WR - including the doc's own sleeper, Jalen McMillan (2024 R3) |
| QB | rush FP/g AND pass TD/g AND top-10 Vegas | drops the Vegas condition | one of three conjunctive legs vanishes |
| TE | route participation AND top-2 receiving YMS | drops YMS | the doc calls YMS "the second-most predictive stat" for the position, then deletes it |

Additional internal contradictions:

- HVT is defined twice: three buckets in the narrative (pass-catching, goal-line,
  explosive), two in the prompt (receptions + inside-10 carries). The MISSION block
  advertises "highly stable" HVT; the body never establishes the prompt's version.
- Phase 1 computes xYPRR that Phase 2 never consumes - dead computation left over from
  the dropped narrative criterion.
- Vegas totals are "a critical cross-check against public fantasy sentiment" in one
  section and "absolute truth" in the prompt. The latter is indefensible; the former is
  the usable framing.
- The Kenneth Walker penalty is "dynamically penalize" in the narrative and a flat,
  underived 15% constant in the prompt. The injury itself is a foot issue in the body
  text while the citation anchoring the penalty sentence headlines a back issue - the
  doc's own sources disagree about the injury it builds a rule on.
- **The DeVonta Smith case contradicts the doc's own table.** Smith is presented as an
  "automatic mathematical target" because of the A.J. Brown vacuum - four lines below a
  table scoring Philadelphia at **-108 net adjusted vacated targets, the most negative
  shown**. The section argues in raw-vacated terms immediately after declaring raw
  vacated targets "a flawed methodology." Under the doc's own WR criterion 4 (>75
  adjusted), Smith fails.
- The GROUND TRUTH block misstates our league: "1 QB, 2 RB, 2 WR, 1 TE, 1 FLEX" omits
  K, DEF, and the bench, and never mentions the 6-point passing TD - a setting the
  doc's own QB section says "heavily dictate[s]" quarterback value.
- The prompt references repo structures that do not exist: a standard "target" tag it
  claims to supersede (the deployed system is a seven-state signal encoding with
  server-side precedence), and a `franchise_id` key on player objects (franchise is a
  roster/manager join key; player objects never carried it).

## 2. Statistical validity of the cited numbers

Labeled and sorted. The pattern: the genuinely predictive claims are the two blog-post
stability numbers; nearly everything else labeled as a big correlation is same-season
and mechanically circular.

**Same-season, circular - descriptive, not predictive** (the stat generates the points
it "predicts"):
- "Implied touches ... 92% correlation to PPR fantasy points" - touches ARE point
  events in PPR.
- "Total touchdowns maintain a 0.6115 correlation to PPR points" - a TD is 6 of the
  points.
- "80.7% of RBs who score a TD finish top-24 that week" - same-week tautology.
- "Raw target volume correlates at 0.82 with fantasy output (50+ targets)" - targets
  become receptions become points; plus survivorship in the 50+ filter.
- "Passing TDs 0.881 correlation"; "passer rating correlates at 0.80" - same-season.

**Labeled year-over-year (the real predictive claims - to be recomputed in Phase C):**
- Y/T YoY R² = 0.08 vs TPRR YoY R² = 0.41 (hobbyist blog; plausible; priority queue).
- xYPRR stability 0.67 vs YPRR 0.51 (SumerSports; plausible; the supporting personnel
  example is COLLEGE data - "Power Four 2023-2025" - deployed for an NFL adjustment).
- YAC/rush stability 0.1894 - r vs R² never stated.
- "Route participation and target share ... correlating around 0.70" - unlabeled: r?
  R²? stability or same-season? Which metric?

**Suspicious or demonstrably mis-scaled:**
- "First downs per route run: 0.729 correlation with NEXT-season fantasy PPG" - if
  real at face value this would rival or beat every known single predictor; no sample,
  era, or r-vs-R² given. Priority-queue verification before any use.
- "RBs score a TD on ~42% of touches inside the 10" - our own play-by-play cache puts
  league-wide RB TD rates per carry inside the 10 at roughly 20-27%; ~40%+ is
  characteristic of inside-the-5. The figure looks like an inside-5 rate promoted to
  the inside-10 zone, roughly doubling the claimed goal-line equity. (Phase C's
  inside-5 vs 6-10 split adjudicates.)
- "88.1% of explosive rushing yards came on plays with >=3.0 YBC" - near-tautological;
  explosive runs mostly have big yardage before contact by construction.
- **The >3.0 YBC criterion conflates a per-play share with a season average.** The
  doc's own 27.8%-of-attempts stat is per-play; the criterion demands a season AVERAGE
  above 3.0. Computed from open 2025 data (pfr_advstats, 100+ carries, replicated):
  exactly **8 of 52 qualifiers exceed 3.0 YBC/att - and three are quarterbacks**
  (Corum 3.51, Gibbs 3.47, Hurts 3.31, Maye 3.25, Swift 3.21, Allen 3.18, Henderson
  3.05, Cook 3.03; median 2.42). Applied literally, RB criterion 5 blanks the tag for
  virtually the entire position.
- Hit-rate tables quoted to 2-4 decimal places (40.54%, 25.53%, 53.57%) with no n and
  no intervals; several reconstructed denominators are tiny.
- The dead-zone study is 1,455 fantasy drafts from a Reddit sample of OTHER leagues -
  market behavior, not player-performance law, with "league-winning" never defined.
  The prompt then treats its fantasy-round conclusions as if they were the NFL-draft
  capital findings.
- "Analyzing 13 years of historical league data reveals..." precedes hit-rate figures
  that come entirely from public sources, not our archive. (Also "tracked since 2014"
  vs our actual 13-season archive - off by one.)
- The 2.55x target:carry ratio is scoring-dependent and must be recomputed
  league-exact (priority queue) before use anywhere.
- Source quality: the load-bearing stability numbers trace to two blog posts; four
  citations are Reddit threads, one is YouTube, one is a newsletter, one is the user's
  own chat log, and the pressure-rate claims cite an SEO-spam storefront URL. The DST
  formula's weights cite NBC Sports but appear there uncited and unbacktested.

## 3. Criterion-level soundness

**RB.** Criterion 5 (trailing-season YBC) measures LAST YEAR'S offensive line and
scheme, not the player - non-portable across a team change. The doc's own flagship case
breaks it: Walker's 2025 YBC was earned behind Seattle's line, and he is now in Kansas
City. The doc argues environment dominates, then uses a trailing-environment stat as a
player criterion. Criteria 1-2 consume projections as inputs (projected targets,
projected goal-line share), importing whatever model produced them. Missing entirely:
availability/durability (the doc's own Walker discussion proves it matters - no
criterion), backfield competition (narrative-only), CURRENT-team line quality, and
schedule. Its two showcased elite RBs (Barkley: year 9; Walker: year 5) both fail the
doc's own years-1-4 criterion.

**WR.** TPRR and xYPRR are the soundest gates in the document - stable, skill-like,
consistent with public research. First-read share is a QB/coordinator-owned role stat
that the doc's own scheme-change section says gets reshuffled by new coordinators.
"Vegas alignment" is operationally undefined ("aligns efficiently") - not
implementable as stated. **A rookie WR can never pass the matrix**: TPRR, xYPRR
percentile, and first-read share all need a prior NFL season, while the doc's hit-rate
section urges aggressively targeting NFL R1-2 rookie WRs. No rookie path exists.

**QB.** The AND-gate (>5.0 rush FP/g AND >2.0 pass TD/g [AND top-10 Vegas, narrative
only]) is calibrated for 4-point-passing-TD formats. This league pays 6; pocket
volume passers are exactly what the format revalues, and the gate excludes them by
construction. The doc's own Josh Allen prop (24.5 season pass TDs = 1.44/g) fails its
own 2.0/g bar. Projected TD/g is also the least stable QB input; stable alternatives
(rush att/g, implied total, prior-season passing efficiency) exist and should replace
it.

**TE.** Route share + receiving YMS is the right direction and matches known research.
The 53.57% one-year-wonder volatility claim is left unused - no age/recency element is
built from it. The prompt halves the gate.

**DST/K.** The DST composite multiplies incompatible units with invented weights
(pressure x1.5 + turnover x2 - opp EPA) and no backtest; streaming direction is fine,
formula is decoration until backtested (priority queue). Kickers get narrative
treatment and no criteria at all, despite the league starting one.

**The gate itself.** 4-of-5 equal weighting contradicts the doc's own evidence that
its criteria differ enormously in predictive strength (TPRR R² 0.41 vs an undefined
Vegas-alignment check, counted equally). Knife-edge no-rounding cliffs ("a 23.9% TPRR
does NOT receive the tag") maximize sensitivity to measurement noise in the same
paragraph that claims the matrix "insulates against random variance."

**The sleeper contradiction.** Every player the document markets as a sleeper fails
its own algorithm: McMillan (NFL R3) fails the WR prompt's R1-2 gate; Ward and Shough
fail the QB AND-gate. And because the prompt gates RBs on fantasy ADP Rounds 1-2, the
tag can only endorse players the market already prices at the top - the "asymmetric
draft value" the introduction promises is definitionally unreachable.

## 4. 2026 factual claims - verification ledger

Everything below was checked against current data (depth_charts.json as-of 2026-08-25,
live Sleeper players API fetched 2026-08-26, nflverse draft_picks and 2025 weekly
stats, our playcallers shard), then independently re-verified. Nothing was accepted
from memory.

**CONFIRMED (all ~36 player-team claims, two sources agreeing on every one):**
Walker->KC (RB1), A.J. Brown->NE, Wicks->PHI, Makai Lemon->PHI, Eli Stowers->PHI,
DeVonta Smith->PHI WR1, Barkley/Hurts/Goedert->PHI, Kraft/Reed->GB, Jennings->MIN,
Bourne->ARI, McCaffrey/Kittle->SF, Evans->SF (gone from TB), Demercado->KC RB2,
Emmett Johnson->KC RB3, Charbonnet->SEA, McMillan->TB, Egbuka->TB, Godwin->TB,
Tate->TEN, W. Robinson->TEN, Shough->NO, Ward->TEN, McConkey/Johnston->LAC,
LaPorta/J. Williams->DET, and the 2026 draft-pick claims (Lemon, Stowers). A.J.
Brown's "120 elite regular-season targets" is real (actual: 121). The GB vacated row
recomputes from our own cache to within 2 targets (172 vs 170), and SF's raw figure
nearly matches (143 vs 139) - the table descends from real data.

**CONTRADICTED:**
- **Cam Ward is not a rookie in 2026.** Sleeper: years_exp=1; our cache: 17 games and
  540 attempts for TEN in 2025. The Titans narrative leans on a rookie-development
  frame a year out of date.
- "Mannion's offense utilized 12-personnel on 33.76% [in Green Bay]" - our own
  curated playcallers shard marks Mannion a FIRST-TIME playcaller in 2026 (PHI OC,
  replacing Patullo). The GB rate belongs to GB's prior caller, not "Mannion's
  offense." The Goedert argument leans on this loose attribution.

**Coaching hires: 6 of 7 confirmed** by our playcallers shard (Mannion-PHI,
McDaniel-LAC, Petzing-DET, Robinson-TB, Kubiak-LV, Daboll-TEN). **Eric Bieniemy (KC)
appears nowhere in our data** - and it anchors the doc's single most developed BULLISH
case (Walker). Must be independently confirmed before "elite environment under
Bieniemy" is treated as an input.

**Omissions that cut against the doc's own cases:** Kraft (GB, a named beneficiary)
carries an ACL injury tag in current data; Charbonnet is on PUP with an ACL tag
(relevant to the Walker-timeshare framing); McMillan has his own current calf flag.

**UNVERIFIABLE from anything we can reach** (listed, not trusted): every Vegas figure
(all implied totals incl. DET 26.35 / NYJ 18.56 / KC 24.50, the +5.08/+4.04 deltas,
SB odds, SOS ranks), all player props (Allen 24.5, Montgomery 7.5, JSN 1,324.5), the
adjusted rows of the vacated-targets table (external model), 12-personnel rates,
tush-push/scheme color, Walker's itemized 2022-24 injury history, Godwin's YPRR 1.36
and PFF 68.8, McMillan's 86th-percentile RAS, Shough's 3.9 xRushTD ("nine rookie
starts" also unsupported), and every correlation/stability coefficient and hit-rate
table in the document.

## 5. Data feasibility (verified against live sources, with year coverage)

| Input the algorithm needs | Buildable? | Source and caveat |
|---|---|---|
| Inside-10/inside-5 carries, goal-line share, red-zone work, HVT actuals | YES | pbp, already in our cache 2013-2025 |
| Target share, air yards, receiving YMS, QB rush points, passer-efficiency components | YES | already in cache/shards |
| YBC per attempt | YES | pfr_advstats weekly, 2018+ (verified 2017 absent) |
| NFL draft capital + tenure | YES | draft_picks release, 2026 rookies included |
| Adjusted vacated targets | YES | our 2025 targets x current rosters - the CORRECT form of the doc's static table, recomputed on every roster move |
| Pressure rate, EPA/play (DST) | YES | participation + pfr_advstats + pbp |
| First-read target share | YES, 2022-2025 only | free FTN charting (read_thrown), joinable to pbp; ~340 first-read throws per team-season so per-player shares are noisy; 2022 encodes non-reads differently than 2025 |
| Routes run / TPRR / route participation | PROXY ONLY | participation data 2016-2025: routes proxied as on-field membership on dropbacks; the proxy counts pass-block snaps as routes (deflates TE route participation and TPRR vs the PFF-calibrated 24%/80% thresholds). No per-player route counts exist in open data - the participation `route` column names only the targeted receiver's route |
| xYPRR (personnel-adjusted) | PARTIAL | homegrown version possible from participation personnel fields; will NOT reproduce PFF/Sumer numbers - thresholds must be re-percentiled on OUR distribution |
| PFF grades, RAS | NO | paid constructs; criteria referencing them cannot ship |
| Season-long Vegas implied PPG | NO | verified: 2026 schedules carry per-game lines for only 112/272 games (41%), skewed to Weeks 1-6. Week-1 implied totals (16/16 complete) are the cleanest available proxy; the 23.5 threshold must be re-derived against whatever proxy is adopted |
| Season-long player props | NO | no reachable source; WR "Vegas alignment" and Phase 1 step 1 cannot ship as written |

Consequence: any threshold the doc states in PFF units (24% TPRR, 80% route
participation, 80th-pct xYPRR) is not portable to our proxies. Thresholds must be
re-derived as percentiles of OUR computed distributions, never copied.

## 6. Repo-integration conflicts (independent of any critique)

- "Supersedes the standard target tag": the deployed signal encoding is seven states,
  server-computed, displayed verbatim under a one-tap Walter toggle, with guards
  pinning that pages never re-derive it. A new tag enters as a new server-computed
  layer beside it, or not at all.
- Monte Carlo "championship probability" validation: the repo backtested folding
  manager tendencies into probabilities and REJECTED it (p=0.99, tendency_backtest);
  the mock simulator is quarantined display-only by guard. As specified the sim is
  also circular - it would validate BULLISH weighting using the same projections that
  generated the tags. "Exploit the historical tendencies of the other 11 managers" as
  a tagging input contradicts the same standing evidence.
- Bright-green highlighting violates the repo color law (verdict palette reserved;
  contrast-proven set only).
- "Do not use 2024 or 2025 ADPs as current values" - already repo law; current ADP
  refreshes live. Agreed and already true.
- GROUND TRUTH boost/penalize/"volume modifier" directives have no defined operation
  in a binary pass/fail tag system - there is no score to modify. Any adoption must
  first define what a modifier acts on.

## 7. What survives, if re-derived

Worth carrying into Phase C as DIRECTIONS with our own computed thresholds and
uncertainty handled honestly: TPRR-style target earning (proxy-based, re-percentiled);
route share for TEs; goal-line share with the inside-5/6-10 split adjudicated from our
pbp; vacated targets computed live from rosters; NFL draft capital as a rookie/year-2
input with hit rates recomputed with n and CI; implied totals as ONE environment input
from a real, dated source (never "absolute truth"); DST streaming direction pending a
backtest. Rejected as specified: every hardcoded threshold, the receptions-based HVT,
trailing YBC as a player criterion, the QB AND-gate in a 6-pt league, hard cliffs, the
prop-alignment criterion, the Monte Carlo validation, and the bright-green UI.

---
---

# PHASE B ADDENDUM - reconciliation against the external critique

Appended 2026-08-26, AFTER the assessment above was committed (git 7813b25 proves the
cold-read provenance; nothing above this marker was edited). This section reconciles
three inputs: the Phase A assessment, `docs/bullish_algorithm_review.md` (opened for
the first time for this section), and Anthony's 2026-08-26 settings correction.

## B.0 Settings correction - verified live before use

Every value in the correction was checked against the live Sleeper API for BOTH league
ids (2025: 1245905122328846336, 2026: 1389378429505241088) before being accepted:

- **Scoring table: verified EXACT on both leagues**, including pass_td 6.0, the full
  K distance/miss schedule, the DST points-allowed tiers, and the ST-player values
  (Sleeper keys `def_st_td`/`def_st_ff`/`def_st_fum_rec` = +6/+1/+1). No key in the
  live settings deviates from the correction's table.
- **Median game confirmed**: `league_average_match = 1` on both leagues. The critique's
  "behind a flag until confirmed" prescription (its Section 4.5) is hereby satisfied
  and superseded: C4 ships ENABLED.
- **Zero IR confirmed** (`reserve_slots = 0`, taxi 0): availability becomes a REAL
  computed criterion in C5, a ceiling penalty term in C4, and an archetype cost flag
  in C3 - not a narrative note.
- **FAAB $100 confirmed** (`waiver_type = 2`); the daily-window schedule and the
  "Waiver Time: None" interaction stay UNVERIFIED mechanics until checked against
  observed 2025 transaction timestamps - in-season module, never displacing C1-C5.
- **Commissioner lefty3 (Rich Nolfi) confirmed** (`is_owner`); draft order still
  undrawn (checked live: `draft_order: None`) - everything stays slot-parameterized.
- K/DST weights derive from the actual scoring table above - this supersedes the
  critique's offer to backtest the Gemini formula's invented coefficients (its
  Section 3 DST verdict). We derive; we do not launder the invented weights.

## B.1 Reconciliation table

Verdict key: AGREE (both found it, resolutions compatible) / CRITIQUE MISSED /
ASSESSMENT MISSED (critique found it, I did not) / DISAGREE (I contest the critique's
prescribed resolution - argued in B.2).

| # | Finding | Critique | Phase A assessment | Verdict / resolution |
|---|---|---|---|---|
| 1 | Narrative vs prompt define two different algorithms | S1, four-row conflict table; prescribes: implement 5-criterion 4-of-5 matrices, never the prompt | Same, plus: WR criteria swaps, RB capital domain switch (NFL round vs fantasy ADP), HVT double definition, dead xYPRR computation, ground-truth league errors | AGREE on both finding and resolution; assessment's extra rows fold into the spec |
| 2 | r/R-squared unlabeled; recompute all on nflverse with n | S2.1 | Same, same examples | AGREE |
| 3 | Same-season circular correlations sold as predictive | S2.2 | Same list independently | AGREE; only YoY-stability and next-season classes admissible |
| 4 | Top-3 finishes are the wrong calibration target; "mathematically guaranteed" banned | S2.3 | Flagged overclaim language but not the calibration-target point | ASSESSMENT MISSED (credit); adopt "elite-range probability" framing |
| 5 | RB >60-target pace: keep | S3 "Sound. Keep." | Flagged: it consumes a PROJECTION as an input - whose? | CRITIQUE MISSED the projection-source hole; resolution: volume input computed from OUR trailing usage + role deltas, never an imported projection |
| 6 | Goal-line + Vegas binaries -> expected-TD equity (team implied TDs x inside-5 share); 42% figure is inside-5-flavored | S3 | Same 42% mis-scaling found independently with our pbp range (20-27% inside-10) | AGREE; construct is also the mission baseline; inside-5 vs 6-10 split computed with n + CI |
| 7 | Draft capital demoted to years-1-2 tiebreak | S3 | Showcased RBs fail the doc's own years-1-4 filter | AGREE (mission baseline too) |
| 8 | YBC >3.0 replaced by current-team line quality | S3 "weakest criterion" | Same verdict PLUS the empirical kill: 8/52 qualifiers over 3.0 (three are QBs), median 2.42; per-play share conflated with season average | AGREE on resolution; CRITIQUE MISSED the magnitude (it would blank the position outright) |
| 9 | RB availability + backfield-competition missing | S3 + S5 taxonomy | Same, independently | AGREE; zero-IR now makes availability a first-class computed criterion |
| 10 | WR TPRR/decomposition sound | S3 "keep" | Same - soundest part of the Gemini doc | AGREE, with proxy re-percentiling (B.2.1) |
| 11 | WR first-read share: "sound, keep" | S3 | Coordinator-owned role stat the doc's own scheme section destabilizes; FTN-only 2022-2025; ~340 first-read throws/team-season = noisy shares | DISAGREE with unqualified "keep" - see B.2.2 |
| 12 | WR rookie path | absent | Rookies can never pass the matrix; doc simultaneously urges targeting R1-2 rookies | CRITIQUE MISSED; resolution in spec: rookies cap at WATCH via draft-capital base rates + situation; BULLISH requires observed NFL usage |
| 13 | QB projected-TD input -> stable inputs (rush att/g, implied total, prior EPA) | S3 | Same direction | AGREE (mission baseline); but see #14 |
| 14 | QB 6-pt-passing-TD calibration | absent | AND-gate excludes pocket passers this format revalues; Allen's own prop fails the doc's bar | CRITIQUE MISSED; settings correction now governs: derive the rushing-vs-pocket gap under exact scoring, log with n + CI; do NOT inherit any 4-pt-era rushing-QB conclusion (including the research director report's) |
| 15 | TE pair (route share + YMS) keep; TE1-TE3 gap conflicts with director report | S3 | Same pair endorsed; cross-doc conflict not visible in Phase A (director report out of scope) | AGREE; adjudicate TE scarcity from 2023-2025 with n + CI, log |
| 16 | DST formula arbitrary | S3: backtest 2023-2025 or ship as labeled heuristic | Same finding; formula weights uncited | AGREE on finding; resolution SUPERSEDED by settings correction: derive weights from actual scoring (fumble +1FF/+2REC structure, nonlinear PA tiers); a backtest may validate the DERIVED weights, never the invented ones |
| 17 | Vegas repricing-delta (21-day) | S4.1 new construct | Not in scope of Phase A | ASSESSMENT MISSED as design; but see B.2.3 - we hold no Vegas history, so it activates only after snapshotting begins |
| 18 | Edge x survival product | S4.2 | - | AGREE with construct; wording correction in B.2.4 (uses our frozen+calibrated survival, never "manager-tendency survival") |
| 19 | Trap-player routing via per-manager reach profiles | S4.3 | - | AGREE as display-only intel (repo law: tendencies never enter verdict math - backtested and rejected, p=0.99) |
| 20 | Props as third ensemble member | S4.4 | Feasibility: season-long props unreachable from any source we have | DISAGREE as shippable - see B.2.5; inert until a source exists |
| 21 | Median-game amplifier behind flag | S4.5 | - | Superseded: confirmed, ships enabled (B.0) |
| 22 | Backtest gate: preseason implied totals vs prior-year points, 2016-2025 | S4.6 | - | AGREE and FEASIBLE: historical Week-1 closing lines exist in nflverse schedules; run before trusting the layer, log result |
| 23 | Tag state machine, no cliffs, Wilson-based criterion probability, WATCH near-misses, event taxonomy, 72h TTL, T-minus protocol | S5 | Cliff critique found independently; machine design is the critique's | AGREE in full; the +/-2pp TPRR sampling-error quantification is the critique's (credit); adopt |
| 24 | Hardcode nothing; teams at compute time; fresh lines with provenance | S4/S6 | Same + governance | AGREE |
| 25 | Monte Carlo championship-probability validation phase | absent | Circular as specified; conflicts with repo's rejected tendency-probability evidence; sim is quarantined display-only | CRITIQUE MISSED; resolution: no championship-probability claims; validation = the findings-page verification queue + backtest gates |
| 26 | Fact errors: Cam Ward "rookie"; "Mannion's offense" GB attribution; Bieniemy-KC unsupported; Kraft/Charbonnet/McMillan current injury tags omitted | absent | All found and verified in Phase A | CRITIQUE MISSED; consequence: coaching claims enter only via our curated playcallers shard; player-narrative claims never enter at all |
| 27 | Feasibility ledger (routes proxy, FTN coverage, Vegas 112/272, PFF non-portability) | assumed inputs exist | Verified item by item | CRITIQUE MISSED (it prescribes recomputing PFF-unit metrics without noting the units are not portable); all thresholds re-percentile on OUR distributions |
| 28 | Gemini doc fairness: roster geography all-verified; GB vacated row recomputes within 2 targets | absent | Phase A | Both docs should carry this: the Gemini report's data layer is real; its statistics layer is the problem |

## B.2 Contested resolutions (presented, not silently chosen)

1. **PFF-unit thresholds (TPRR 24%, route participation 80%, xYPRR 80th pct).** The
   critique says "recompute all stability coefficients on nflverse" but keeps the
   thresholds' units. Our routes are a participation-based PROXY that counts
   pass-block snaps as routes, so our TPRR reads lower than PFF's and 24% is not a
   portable number. Resolution I will implement unless overruled: every threshold is
   a PERCENTILE of our computed distribution (e.g. top-quintile TPRR-proxy among
   qualifying WRs), with the percentile choice logged and the PFF-unit number recorded
   as provenance only.
2. **First-read share.** Critique: "sound, keep." My evidence: role stat owned by the
   coordinator (the doc's own scheme-change section reshuffles it), free data covers
   2022-2025 only, and ~340 first-read throws per team-season makes per-player shares
   noisy. Resolution I will implement unless overruled: keep as ONE input with wide
   uncertainty (Wilson on small n), reset-on-coordinator-change per the playcallers
   shard, and never as a sole qualifying criterion.
3. **21-day repricing delta.** We hold no Vegas history; nflverse carries current
   lines, not snapshots. Resolution: begin daily line snapshotting NOW (T-13d) with
   provenance timestamps; the feature activates when two or more snapshots exist and
   is labeled by its actual window (which will be <21 days by draft night).
4. **"Manager-tendency survival model."** The critique's edge-x-survival construct is
   right, but this repo's survival is pick-geometry + ADP based, frozen, with the
   adopted era calibration; folding manager tendencies into survival probabilities was
   backtested and REJECTED (p=0.99). The product is edge x calCondSurvival, and
   tendency intel stays display-only.
5. **Props ensemble.** No reachable source carries season-long props. The construct is
   sound; it ships INERT behind a source-exists check, and the findings page records
   it as unavailable rather than silently dropping it.

## B.3 The reconciled Phase C spec (governs implementation on approval)

Component order per the mission (C1 first, draft-night critical path). All thresholds
computed, percentile-based, uncertainty-carrying; nothing imported from either
document; every disagreement between computed values and either report's citations
logged on this page with n and CI.

- **C1 VOR + tier-break engine**: exact roster QB/RB/RB/WR/WR/TE/FLEX/K/DEF/5BN, 12
  teams, 14 rounds, EXACT scoring table (B.0, pulled live from Sleeper at compute
  time); replacement levels derived for this lineup incl. FLEX; tier breaks from
  gap statistics; positional-run alerts in the draft room. QB baselines reflect 6-pt
  passing TDs by construction.
- **C2 Base-rate columns**: top-12/top-24 hit and bust rates by ADP band x position,
  nflverse 2016-2025 + league history, n and Wilson 95% CI on every cell.
- **C3 Archetype tagger**: rules-based tags from computed usage thresholds per the
  research director report's archetype lists (methodology only, no player constants);
  post-injury-discount archetypes carry an explicit zero-IR cost flag.
- **C4 Ceiling weighting**: ENABLED (median confirmed); weekly-ceiling weighting for
  the two-results format; penalty term for projected games missed weighted by the
  bench-slot opportunity cost of a 5-bench/zero-IR roster.
- **C5 BULLISH engine** (4-of-5 probabilistic matrices, tag state machine per critique
  S5, TTL 72h wired to the freshness board, T-7d/T-24h/T-2h protocol, event taxonomy):
  - RB matrix: (1) receiving-volume input from our computed trailing usage + role
    deltas; (2) expected-TD equity = team implied TDs (Week-1 lines, dated) x
    inside-5 carry share, split adjudicated from pbp; (3) current-team line quality
    (returning starters + computed line metrics); (4) availability (games-played
    rate + derivable soft-tissue history); (5) backfield-competition delta. Draft
    capital: years-1-2 tiebreak only.
  - WR matrix: (1) TPRR-proxy percentile; (2) YPRR/xYPRR-proxy percentile (personnel
    adjustment where participation data allows); (3) first-read share (FTN, wide
    uncertainty, coordinator-change reset); (4) adjusted vacated targets computed
    live from rosters x prior targets OR top-implied-offense primary role; (5)
    route-participation proxy. Rookies cap at WATCH (draft-capital base rates +
    situation); BULLISH requires observed NFL usage.
  - QB: stable inputs only (rush att/g, team implied total, prior-season EPA-based
    efficiency), calibrated to exact 6-pt scoring; rushing-vs-pocket value gap
    computed and logged with n + CI before any archetype preference ships.
  - TE: route-participation proxy + top-2 receiving YMS; scarcity adjudication
    (TE1/TE3/TE6/TE12 PPG gaps 2023-2025) logged against both reports.
  - DST/K: weights DERIVED from the exact scoring table (nonlinear PA tiers, +3
    forced-and-recovered structure; K distance tiers + miss penalties); derived
    weights may be validated by backtest; invented coefficients never enter.
- **C6 Workstream 2 metrics** as computed features; Workstream 3 methodology only -
  the engine derives its own board; no player opinions imported as constants.
- **Vegas layer across components**: Week-1 implied totals as the environment input
  with provenance timestamps; snapshotting starts immediately for the repricing
  delta; the S4.6 backtest gate (Week-1 lines vs prior-year points, 2016-2025) runs
  before the layer influences any tag; edge x calibrated-survival ranking; trap
  routing display-only.
- **Findings verification queue** (union of governance + critique S6): TPRR and
  target-share YoY stability; xYPRR vs YPRR (r vs R-squared declared); first-downs
  -per-route-run predictiveness; inside-5 vs 6-10 conversion split; league-exact
  target-vs-carry ratio; TE scarcity adjudication; WR/RB draft-capital hit-rate
  curves; DST derived-weight validation; preseason-implied-totals backtest gate;
  rushing-vs-pocket QB gap under 6-pt scoring.

---

# PHASE C FINDINGS LEDGER

Running log of computed-vs-cited adjudications and source resolutions, per governance.
Each entry states what was computed, from what, with n and CI where applicable.

## C.0.1 What the p=0.99 tendency backtest actually tested (checkpoint note 1)

Verified from `src/phase3i_backtest.py` and `out/tendency_backtest.json`: the target
was **next-pick survival**, not championship outcome. For each season S from 2016,
the tendency table is built from seasons before S only, then predicts - for every
real pick in S - whether each still-available player survives to that team's NEXT
PICK. Scored by Brier and log loss against what happened, paired permutation over
10 seasons: base Brier 0.23030 vs adjusted 0.23050, adjusted better in 3 of 10
seasons, p = 0.9932. So the rejected claim is precisely "manager tendencies improve
next-pick survival probabilities out-of-sample." Tendency-to-championship was never
tested. Per the checkpoint directive this question is not reopened before the draft;
display-only stands either way, and edge-x-survival multiplies by the frozen +
calibrated survival model.

## C.0.2 Participation coverage window (checkpoint note 2)

Resolved live 2026-08-26 against the nflverse pbp_participation release, superseding
the cold-read draft's "coverage ended" belief: files exist for **2016 through 2025
inclusive** (2015 is 404). The 2025 file carries 45,184 rows with `offense_players`
populated on every row (0 nulls) and `offense_personnel`, `was_pressure`,
`nflverse_game_id`/`play_id` join keys present. The committed Phase A feasibility
table already stated 2016-2025 after workflow audit; this entry re-verifies it
directly and closes the question: the WR route-based criteria (TPRR proxy, route
participation proxy) ARE shippable on the on-field-dropback proxy through 2025, with
the stated weakness (pass-block snaps counted as routes) carried into their
uncertainty. The target-share/air-yards fallback is not needed.

## C.1 VOR + tier-break engine (Phase C component 1)

Three assumed constants replaced by derivations; the exact-scoring path verified by a
new committed suite (tests/test_vor.py, 26 assertions, gating the draft-refresh
workflow and the morning runbook at step 7b).

**C.1.1 Flex allocation - observed behavior replaces the 50/50 assumption.**
draft_board.py allocated the 12 FLEX slots as 6 RB / 6 WR by assumption ("flex splits
roughly half RB, half WR in PPR"). Computed from every 2025 matchup week of this
league (src/derive_flex.py -> out/data/flex_usage_2025.json; the 2024 shell excluded
per standing rule): n = 216 flex starts over 18 weeks - WR 146 (67.6%, Wilson 95%
[61.1%, 73.5%]), RB 63 (29.2%, [23.5%, 35.6%]), TE 7 (3.2%, [1.6%, 6.5%]).
Largest-remainder allocation: WR 8 / RB 4 / TE 0. The projection-greedy fill (the
theoretical optimum, kept as the fallback when the artifact is absent) says WR 12/12
- WR36 projects 177.3 vs RB25 at 171.0, a robust 6.3-point margin - so observed
behavior sits between the old assumption and the optimum, and is what replacement
actually means in this league. Effect: replacement ranks RB30->RB28, WR30->WR32;
baselines RB 160.2->169.0, WR 195.4->186.2; every RB VOR -8.8, every WR +9.2. The
repricing concentrates in ranks 30-60 (mid RBs fall ~14 VOR ranks, mid WRs rise
~10-13; the top-24 mix moves by one player), exactly the rounds where the flex
decision is live.

**C.1.2 Tier breaks - per-position derived thresholds replace gap=12.0.**
A single absolute gap cut QB nine times and WR once across the same forty draftable
players (QB drop p90 = 35.5, WR p90 = 9.0 - different scales, one constant). tiers()
now derives each position's threshold as the p90 of its own successive-VOR-drop
distribution (p90 is the stated convention; the values are computed): QB 24.1, RB
11.5, WR 8.6, TE 15.0 on today's payload, giving five real tiers per position where
WR previously collapsed into two. Tier-cliff math in the room inherits real WR tiers
for the first time. Fewer than eight draftable players never claims tier structure.

**C.1.3 Positional-run alerts - binomial surprise replaces the 4-of-8 constant.**
The room's run banner fired at any 4-of-last-8 position count. Against the archive's
own base rates (pos_base_rates, 2,339 picks by round band) that rule fires on the
league's NORMAL early diet (RB base 44.9% in rounds 1-3: even 6-of-8 RBs is only
p = 0.087) and misses genuine anomalies (3 QBs in 8 early picks is p = 0.022).
runDetect now computes the exact binomial tail against the current band's base rate:
alert at p < 0.05 with a k >= 3 floor (both stated in code), banner shows observed
vs expected count and the p-value. Smoke covers the positive (QB burst fires), the
negative (6 early RBs stays silent), and the base-rate-normal case.

**Scoring exactness** - score() verified to the tenth of a point against the
live-verified league table (6-pt passing TDs, PPR, K distance tiers and miss
penalties, DEF points-allowed tiers, ST-player keys), with Sleeper's precomputed
pts_ppr and adp_ fields proven excluded. The QB rushing-vs-pocket value gap under
this scoring lands with C5's findings entry, per the checkpoint directive.

## C.2 Base-rate columns (Phase C component 2)

Artifact: out/data/base_rates.json (src/build_base_rates.py). Two computed tables,
2016-2025, outcomes scored under the exact league table (6-pt passing TDs, full
PPR), positional finish by season total: MARKET (FFC positional-ADP bands, 1,140
joined player-seasons + 17 zero-point seasons counted as busts) and LEAGUE (this
league's own archive picks by round band, 1,448 joined + 26). Every cell carries n
and a Wilson 95% interval; definitions (hit12/hit24/bust36) are stated in the
artifact and repeated on the board. Rendered as per-player band chips on the big
board rows (from adp_pos_rank) plus a full reference table, labeled "History, not a
projection." Display-only, guarded (tests/test_baserates.py; gates at workflow +
runbook 7c).

Adjudications the tables settle or inform:

- **RB dead-zone shape replicates in OUR league; the cited numbers do not carry
  over.** League RB hit12 by round: rd1-3 50% [43,58] n=165 -> rd4-6 15% [10,23]
  n=117 -> rd7-10 9% [5,15] n=138. The cliff after round 3 is real here. The Gemini
  doc's 33%/37%/14%/5% "league-winning" ladder used an undefined metric on other
  leagues' mock drafts; our numbers are the ones the board shows.
- **Waiting on QB has not cost this league QB1 production (the 6-pt effect,
  observed).** League QB hit12: rd1-3 68% [46,85] n=19, rd4-6 72% [58,83] n=47,
  rd7-10 50% [37,63] n=50 - the rounds-4-6 QB pool hits as often as the early one.
  First observed input to the C5 rushing-vs-pocket derivation; the value question
  (points over replacement) stays with the C1 VOR board.
- **Elite TE has paid here**: league TE rd1-3 hit12 83% [63,93] n=23, with bust36
  0% [0,14] - the first data point for the TE-scarcity adjudication (the full
  TE1/TE3/TE6/TE12 PPG-gap computation stays in the C5 queue).
- **The Gemini WR hit-rate table is frame-incompatible, not wrong**: its "40.54% of
  Rd1 WRs deliver a WR1 season" is a CAREER rate by NFL draft round; our 60%
  [47,71] for pos1-6 ADP WRs is a per-season rate by market price. Logged as
  non-comparable; the draft-capital career curves belong to the C5 queue.
- Method note: a drafted player-season with zero recorded points joins as a bust
  rather than dropping out (17 market / 26 league cases) - dropping them would
  survivorship-bias every bust rate downward.
