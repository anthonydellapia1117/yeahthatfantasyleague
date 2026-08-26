# Changelog

## C1: VOR engine derives what it used to assume (2026-08-26)

Phase C component 1 of the research-integration pass - the draft-night
critical path. Three constants became derivations, each logged on the
findings page with n and CI:

- FLEX ALLOCATION: the 12 flex slots were split 6 RB / 6 WR by
  assumption. Observed behavior - all 216 flex starts of the 2025
  season, read from the slot-ordered starters arrays - says WR 8 / RB 4
  / TE 0 (WR 67.6% [61.1, 73.5]). Replacement ranks move to RB28/WR32,
  repricing the rounds-3-5 RB/WR boundary where the flex decision
  actually lives. The projection-greedy fill is the stated fallback;
  the assumed split is gone from the source.
- TIER BREAKS: the fixed 12.0 VOR gap cut QB nine times and WR once in
  the same forty players. Thresholds now derive per position (p90 of
  that position's own successive drops): five real tiers everywhere,
  and the room's tier-cliff math sees WR structure for the first time.
- RUN ALERTS: the 4-of-8 banner fired on the league's normal early RB
  diet and missed real anomalies. Detection is now exact binomial
  surprise against the archive's per-band base rates (p < 0.05, k >= 3,
  both stated); the banner shows observed vs expected and the p-value.
- tests/test_vor.py (26 assertions) gates the scoring table to the
  tenth of a point under 6-pt passing TDs and pins all three
  derivations; wired into the draft-refresh workflow and the runbook.

## Live-draft wiring: Sleeper link, team identity, up-next (2026-08-26)

Anthony asked for the app refreshed and pointed at the live draft, and to
know mid-draft when he is next and who goes before him.

- SLEEPER LINK on the draft room, big board, and hub. In the room it is
  DERIVED from the polled draft id, so the link can never point somewhere
  the room is not actually watching; a guard fails the build if anyone
  hardcodes a draft url there.
- TEAM IDENTITY, two names kept apart on purpose. The engine now carries
  each roster's Sleeper `team_name` (Anthony's is "Taylor Made"; six of
  twelve managers set one) alongside `franchise`, which stays the archive
  member name that joins 13 seasons of history and keys every prior. The
  room leads with the Sleeper name and keeps the franchise visible as
  provenance, so a dossier is still traceable to the history it came from.
  Guards pin both, and pin that the team name never reaches the score.
- UP NEXT strip in the live card: "UP IN 2 PICKS - your pick 7", who picks
  before you by team, and the pick after that. It turns amber inside three
  picks and green on the clock. No seat means it says so rather than
  guessing.
- REFRESH to today's live inputs: engine, CVS board, and the page-data
  shards. Two guards caught real problems on the fresh data rather than
  waving them through - see below.

### Two data defects the refresh exposed

- CROSSWALK, father onto son. The suffix strip that rescues "Kenneth
  Walker" vs "Kenneth Walker III" also collapses Marvin Harrison (1996,
  IND) onto Marvin Harrison Jr. (2024, ARI) - same name, same position,
  and `latest_team` cannot separate them because nflverse keeps the last
  team a retired player suited up for. Draftable match rate had fallen to
  97.5% against a 98% floor. Resolved by entry year, applied only when
  unique and only when every candidate has one: `draft_year` is None for
  the UNDRAFTED, not the old, so a son who went undrafted (Frank Gore Jr.)
  would otherwise resolve backwards onto his father. Twelve collisions now
  resolve, all of them modern-over-namesake, and every one is logged.
- STALE DEPTH CHARTS. The as-of date was nine days old against a
  seven-day guard; the shards had not rebuilt since 08-17.

### Two tests that hardcoded a day's data

Both failed on correct behavior and are now payload-driven, per the rule
written into the runbook: the coin-flip overlay named Ashton Jeanty, whose
VOR moved 99 -> 74 in this refresh and who is no longer the runner-up (it
derives the runner now); and the order-hypothesis options asserted one
franchise string, which the team names displaced (it now checks every
handle and every franchise era from the payload).

## Signal encoding live in the draft room (2026-08-19)

Anthony's question two: the seven-state signal encoding was board-only
(plus a pick-engine headline tag). Now it is live in the room's
available-player views, same precedence and same three channels as the
big board.

- THE SIGNAL is read, never re-derived: sigOf(p) takes the server-ranked
  cvs entry and picks the walter-on or walter-off variant with the same
  peWalterOn() precedence the pick engine already uses - so the one-tap
  walter toggle flips the room's signals exactly as it flips the board.
- THREE CHANNELS on every surface, verbatim from big_board: the
  [data-sig] container treatment (3px border-left + tint), the inline
  SVG icon, and the text label (MY DND / DND x2 / DND / TARGET x2 /
  TARGET / SLEEPER x2 / SLEEPER), with the conflict marker when the
  walter-off signal disagrees.
- SURFACES: the on-the-clock card (name + comparison chips), the two
  runner chips, the by-position minis, the watch-queue board (with a
  legend), the recs cards (with a legend), the pick-engine
  alternatives, and the Board tab's best-available view - overall and
  per-position rows both, with the legend at the top.
- DISPLAY ONLY, guarded: pages guards prove the signal never enters
  peScore or the grade path, the maps match big_board byte-for-byte,
  and the smoke test asserts badges/containers/legends render and that
  toggling walter changes the rendered signals.

## Survival calibration ADOPTED at scope (ii), era-informed table (2026-08-19)

Anthony adopted candidate B with two conditions, both met, and asked
whether the 2019 regime shift lives in the calibration table. It does.

- ERA ANALYSIS (rule registered before computing): the all-years and
  modern (2019-2025) tables differ by up to 0.111 per bin and straddle
  the 0.6 verdict threshold in bins 7-8; the modern-era fit is not worse
  on the 2023-2025 holdout (0.0597 vs 0.0598). THE MODERN TABLE DEPLOYS;
  the all-years table is the documented conservative fallback.
- CONDITION 1: Anthony's interval arithmetic confirmed exactly (398
  flips, 62.8%, CI [58.1%, 67.6%], z=1.16 - all-years lineage). The
  deployed lineage is stronger: 292 walk-forward flips at 65.8%,
  CI [60.4%, 71.2%], z=2.09 - the lower bound clears the 0.6 bar.
  Clustering caveat stated, not estimated.
- CONDITION 2: one-tap CALIBRATED SURVIVAL toggle in the live room
  (localStorage, like the walter toggle); when frozen and calibrated
  straddle the verdict threshold, the card shows both numbers - only on
  those picks.
- THE WIRING (approved diff, verbatim): SURVIVAL_CALIBRATION constant +
  calibrated_cond_survival wrapper + two payload keys in the engine
  (pure additions); calCondSurvival JS mirror with frozen fallback;
  verdict comparison, survival tables, tier cliffs, board survival,
  recs, and pick engine consume the calibrated number. The pick-grade
  urgency and engine-baked pre-draft verdicts stay frozen (not in the
  approved diff, stated in the ADR). The ten frozen function bodies
  remain byte-identical - mathdiff proves it.
- Pre-registered alongside (Anthony's item-2 follow-up): the modern-era
  durability hypothesis and its 2026 decision rule, written into
  MODEL.md before the season.

## Draft-order hypothesis card (2026-08-19)

- Pre-draft draft room: Sleeper's lobby has no draw yet, so a new card
  lets Anthony assign the 12 real franchises (name + sleeper handle,
  from the engine payload) to slots and preview seat context under that
  order. Assignment SWAPS, so the order is always a permutation; state
  persists in localStorage (ytfl_order_hyp); the scenario view follows
  his hypothesized seat.
- THE LIVE SOURCE WINS: the moment Sleeper's real draw exists, the
  hypothesis retires visibly and the drawn order labels everything -
  automatically, per the standing conflict rule. Live mode never reads
  the hypothesis at all.
- Honesty boundaries stated on the card: verdicts and survival numbers
  are pure pick geometry and never depend on seat order; only seat
  labels and their tendency lifts remap (lifts recomputed per franchise
  from the payload, since a label without its own lift would mislead);
  engine-built urgency lines keep the build order until regeneration.
- ORDERHYP marker quarantine outside the engine sentinels; guards pin
  the markers, persistence key, live-wins language, and sentinel
  placement; smoke covers the 12x12 selects, swap-no-duplicates, seat
  follow, strip relabeling, reload persistence, and the drawn-order
  retirement path.

## Survival recalibration PROPOSAL - evidence merged, nothing adopted (2026-08-19)

- Diagnosis (src/analyze_survival_calibration.py): the frozen sd curve is
  already league-fitted, so the overconfidence about removal is a SHAPE
  defect - removal around ADP is right-heavy vs the assumed normal
  (standardized q95 = 1.92 FFC frame / 1.90 archive frame vs 1.645
  normal). Fallers keep falling; the normal kills the late tail too fast.
- Candidates fit 2013-2022, judged on held-out 2023-2025: A empirical-
  tail KM (Brier 0.0576, flips right 69.4%) vs B isotonic layer (Brier
  0.0598, best sub-50% calibration, flips right 62.8%); frozen reference
  0.0648 with the known low-bucket defect. RECOMMENDED: B - monotone
  (never reorders a decision), a 20-number lookup applied AFTER the
  frozen math, kill-switchable, trivially mirrored in JS.
- The ADR in MODEL.md carries the exact gated diff (pure additions, two
  adoption scopes: display-only or full wait-or-reach) and the all-years
  adoption table. STATUS: PROPOSED, NOT ADOPTED - the frozen functions
  are untouched and mathdiff still proves it.
- Guards: proposal status pinned, read-only frozen import, table
  monotonicity, flip accounting, shared holdout frame, cached-input
  determinism.

## Durability-fade investigation: dropped under the pre-registered rule (2026-08-19)

- src/analyze_durability.py on the shared injury frame (refactored
  analyze_injury.build_sample, payload byte-identical): the fade survives
  age and points-per-game controls (full_ctrl b=-0.073, CI excludes
  zero) but fails era stability - nonexistent 2013-2018 (+0.001), entire
  effect in 2019-2025 (-0.143). Only QB clears the position split (thin
  n); the zero-game returner class is noise.
- VERDICT: confounded_or_unstable; recommendation DROP. An effect that
  only exists in the era it would be deployed in is the signature of
  overfitting. 2026 tests the modern-era hypothesis out of sample for
  free; revisiting after that is a new decision.
- Guards: verdict recomputes from its own rule, flags follow intervals,
  age coverage stated (0 players without birth dates), cached-input
  determinism (roster-gated).

## Reproducibility: the history fetcher is now committed (2026-08-19)

- src/fetch_history.py: idempotent fetcher for the analysis layer's data
  cache - FFC PPR ADP 2013-2025, nflverse weekly 2012-2025, injuries
  2012-2025 (gz and plain fallbacks), rosters 2013-2025 (birth dates for
  the durability age control). Cache path via the HISTORY env var, same
  resolution the analysis scripts use.
- PROOF: a cache rebuilt from scratch into a fresh directory reproduces
  every committed analysis payload exactly - tests/test_analysis.py ran
  end-to-end against the rebuilt cache, ALL PASS including the
  determinism reruns.

## Item 5 - replay backtest: drafter holds, survival skilled but conservative (2026-08-19)

- src/replay_backtest.py, two honestly-scoped parts. Part 1 (value core,
  one-step deviations at actual board states, 169 skill picks): Anthony
  beats blind ADP-best by +35.6 realized pts/pick (CI excludes zero); the
  proxy replay engine beats ADP by +42.7 but does NOT distinguishably
  beat Anthony (CI [-47.2, +32.2]). The proxy prices by prior-season
  points only and values rookies at zero - stated, not hidden; it bounds
  the replay from below and does not measure the 2026 engine.
- Part 2 (frozen cond_survival verbatim, 17,068 pairs): +19.6% Brier
  skill over base rate, with systematic overconfidence about removal in
  the sub-50% buckets (predicted 0.03 observed 0.33 at the extreme;
  modern era 2023-2025 confirms: 0.32 predicted vs 0.51 observed below
  50%). FLAGGED: wait-or-reach is conservative; recalibration is frozen-
  math territory and gated on explicit approval.
- Guards: honesty pins (non-replayable list, rookie caveat), delta/mean
  consistency, calibration arithmetic, decile and era partitions,
  read-only frozen import, cached-input determinism.

## Item 4 - injury market inefficiency: none established, one flag (2026-08-19)

- src/analyze_injury.py: two regressions x two burden measures over 1,697
  ADP-matched skill picks. A: does the league discount injury history
  beyond market price? B: do outcomes justify a discount at price?
  Season-long absentee veterans stay in the sample (the item-3 frame
  dropped exactly the most injury-discounted players); rookies stay out.
- FINDINGS: designations say the league pays UP slightly vs market
  (A b=-0.013, CI excludes zero) with no outcome penalty; games-missed
  says the league tracks market but outcomes punish missed-time history
  at price (B b=-0.084, CI [-0.148, -0.025]). The two disagree in
  pattern; under the pre-registered agreement rule the verdict is
  no_inefficiency_established and NOTHING is used.
- FLAGGED, not wired: the games-missed outcome signal is a candidate
  market-wide durability fade; investigating it is a separate approval.
- Guards: agreement rule, flags-follow-intervals, absentee retention,
  cached-input determinism.

## Item 3 - recency-bias coefficient: no effect, not used (2026-08-19)

- src/analyze_recency.py: ln(pick paid) ~ z(last-4-weeks points) +
  z(full-season points) + ln(FFC ADP) + position dummies, all 13 drafts,
  1,677 skill picks (85% coverage; rookies and no-ADP picks excluded and
  counted per year). League scoring applied to prior-season stats
  (PPR + 6-pt pass TD). Late window anchored to each season's final four
  REG weeks.
- FINDING: b_late = +0.0002, season-cluster bootstrap 95% CI
  [-0.0203, +0.0178] - not distinguishable from zero. At the median
  selection a +1 SD hot finish moves this league +0.01 picks, i.e.
  nothing. The market control (ADP) absorbs market-wide recency bias;
  the league adds none of its own.
- CONSEQUENCE (the commission's rule): no effect size, no usage - nothing
  recency-related is wired anywhere. Guards: verdict-follows-interval,
  usage rule, estimator unit tests, coverage accounting, cached-input
  determinism.

## Item 2 - manager-profile backtest (2026-08-19)

- src/backtest_profiles.py: walk-forward backtest (2016-2025, 1,766 picks,
  never any future data in a train window) of the simulator's franchise
  positional profiles against league band priors, using the committed
  phase3i methodology (half-life 6, method-of-moments shrinkage).
- VERDICT: profiles beat priors on log-loss, delta +0.0081, season-cluster
  bootstrap 95% CI [+0.0049, +0.0112]. Small and real. Top-1 hit rate is a
  wash (both models name the modal position). The simulator's existing use
  of these profiles is therefore justified; no wiring changed.
- tests/test_analysis.py: walk-forward blindness, coverage-rule fallback,
  proper distributions, verdict-follows-interval, seeded reproducibility,
  engine/UI isolation.

## Walter layer: reference scale, live kill-switch, tier flags (2026-08-18)

Anthony approved the shipped increment and directed three changes:

- WALTER SCALE, second revision: Anthony caught that the sign-safe
  `|cvs_base| * pct` form made the layer's authority proportional to each
  player's own magnitude - structurally weakest on sleepers (near
  replacement, near zero), strongest on elites. Davante Adams' -9%, the
  strongest call in the guide, moved him -0.01 points. The law now scales
  against the within-position SD of cvs_base: even authority across the
  range, at most 0.1 positional SD of movement at the 10% cap (less than
  the original form allowed at the top). References echoed in the payload,
  re-derived independently by the guard.
- LIVE KILL-SWITCH: both boards ship server-ranked in cvs.json
  (players[].no_walter - ranks, signals, conflicts with every walter
  source off, one shared precedence implementation). The WALTER LAYER
  toggle on the big board flips mid-draft with no rebuild; the pick
  engine reads the same localStorage key and says so on its card.
- TIER-BOUNDARY FLAGS: walter deltas that cross an engine tier band are
  flagged on the row and named in the CVS vs WALTER view (own-delta,
  direction-consistent crossings only). Currently: none at the current
  cap - stated on the page, not hidden.
- walter_enabled stays true by Anthony's decision: the impossible
  backtest is absence of evidence, not evidence against; the cap, the
  two kill-switches, full attribution, and the conflict views are the
  bounds for an unvalidated but fully inspectable layer.

## Red-team pass on the pick engine and CVS (2026-08-18, after merge of #28)

Adversarial review (general-purpose agent standing in for the named
red-team subagent, which does not exist in this environment). Two HIGH
findings, both real, both fixed same-day:

- SIGN INVERSION (HIGH): the walter multiplier `cvs_base * (1 + pct/100)`
  inverted the judgment for the 29 players with negative cvs_base - an
  endorsement pushed them further down. Now sign-safe:
  `cvs = cvs_base + |cvs_base| * pct/100`; a dedicated direction guard
  pins it (test_cvs "walter sign safety").
- ON-THE-CLOCK DEGENERATE (HIGH): on your own pick the card computed
  survival to the current pick (trivially 100%), zeroing scarcity and the
  cost of waiting exactly at decision time. The card now targets your NEXT
  turn (mirrors the verdict card's isMe index); a new on-the-clock smoke
  fixture pins it.
- MED fixes: cost-of-waiting relabelled "score margin at risk (composite
  scale, not projected points)" and suppressed when degenerate; the
  single-candidate case no longer invents a 99-point margin; the card
  warns when cvs.json and the engine payload carry different generated
  dates; determinism guard no longer rewrites cvs.json or fails across
  midnight; adp_pos_rank keyed by (name, pos).
- Accepted (LOW, noted not fixed): numeric payload fields interpolated
  unescaped (builder-controlled, guarded); drafted-player joins by
  normalized name rather than sleeper_id (page-wide pre-existing
  convention, follow-up candidate).

## Increment 2 - CVS wired, signal encoding, pick engine (2026-08-18)

Classification approved by Anthony (stop condition 1 cleared); the guide
layer is live, capped, and kill-switchable.

- New input shards (`src/build_cvs_inputs.py`, literal nflverse columns
  only): `volatility_2025.json` (511 players - weekly PPR mean/sd, boom/bust,
  p90/p25), `td_rates_2025.json` (193 players - TD per opportunity with
  positional outlier deciles), `sos_2026.json` (2026 schedule x 2025 points
  allowed by position, season + weeks 15-17 slices).
- `src/build_cvs.py` + `data/cvs_weights.json`: the CVS anchor law
  (cvs_base = VOR + weighted within-position z of five wired factors;
  Walter judgment as a capped percent multiplier, 10%, never raised without
  approval). 190 players; nulls redistribute and confidence reports the
  covered share; K/DST excluded as floors. Every applied Walter delta
  carries its verbatim quote and line reference into the Explain view.
- Big board rewritten as the CVS board: seven signal states, three channels
  each (container treatment + icon + text label, WCAG-verified colors),
  precedence personal > consensus > single with conflicts kept visible;
  views BOARD / CVS vs WALTER (sparse figure deltas + regression cross-map)
  / CONFLICTS (model conflict queue - live: Jayden Daniels); filters with
  localStorage persistence; live drafted-removal poll.
- Pick engine card in the draft room (additive, PICKENGINE-quarantined):
  the pick + two alternates with conditions, three-line why, cost of
  waiting from the frozen survival model, confidence band, weeks 15-17
  tilt labelled "a schedule proxy for title odds, not a title-odds
  simulation". The wait-or-reach verdict stays the audited VOR model.
- Verification: `tests/test_cvs.py` (12 guards), pages guard suite extended
  (CVS board section, signal-color contrast, cvs teaser leak tokens), smoke
  scenarios 15 (CVS board) and 16 (pick engine) - all suites ALL PASS;
  five frozen survival functions byte-identical to main; engine regen
  touches only its sentinel payload (proven).
- HONESTY: the with/without-guide backtest cannot run - no historical guide
  files exist. The cap and the walter_enabled kill-switch are the risk
  bounds, stated in MODEL.md and on the board.

## Increment 2 - guide integration groundwork (2026-08-18)

- Ingested `data/Walter Ai-2026_Advanced_Fantasy_Guide.md` (sha-stamped) and
  built `src/parse_walter.py`: Evidence/Judgment extraction with verbatim,
  line-referenced quotes; 167 tags across 9 types; 19 Walter rank/ceiling/
  floor figures as a comparison series; Channel B structural knowledge
  (injury base rates, strategy definitions); change-log revision signals per
  player (last_revised, revision_direction, revision_count, subject-attributed).
- Name resolution: exact + nickname + fuzzy(0.90) against the ADP shard;
  0 unresolved, 0 guide-vs-live team conflicts on this parse.
- Extraction audit: 51.0% of the top 200 by ADP carry at least one tag
  (floor: 40%); 50 evidence / 117 judgment; quote fidelity mechanically
  verified against source line ranges (0 mismatches on prose quotes).
- Wrote MODEL.md: routing rule, channel caps, changelog signals, CVS and
  championship-objective designs of record.
- NOT DONE by design: nothing from the guide touches any rank. Gated on
  Anthony's approval of the classification sample (stop condition 1).

## Prior increments (summary)

- Phase 0 discovery: repo map, data inventory, factor availability, change
  contract (reported in-session, gated).
- Existing shipped surfaces: audited VOR engine + frozen survival math, draft
  room, big board (VOR + evidence chips), players/teams/hub pages, conviction
  overlay, teaser build, app shell. See docs/HANDOFF.md.
