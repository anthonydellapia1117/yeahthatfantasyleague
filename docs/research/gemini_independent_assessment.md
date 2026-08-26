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
