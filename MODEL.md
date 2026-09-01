# MODEL.md - The Big Board valuation system

Status: increment 2, wired. Anthony approved the Evidence/Judgment
classification on 2026-08-18 (stop condition 1 cleared); CVS is live on the
big board and the pick engine card is live in the draft room. The
with/without-guide backtest cannot run - no historical guide files exist -
so the guide layer is prospectively unvalidated: the 10% cap and the
`walter_enabled` kill-switch in `data/cvs_weights.json` are the risk bounds,
stated on the board itself.

## The routing rule (core principle, applies everywhere)

Every piece of guide content is classified into exactly one class:

| Class | What it is | How it enters | Weight |
|---|---|---|---|
| Evidence | Verifiable world-state: depth charts, signings and trades, coaching changes, scheme descriptions, rookie draft capital and landing spots, injury status, snap and target projections, Walter's stated rank/ceiling/floor figures | Feeds the factor groups directly, same as any other data source | Full weight |
| Judgment | Walter's calls: target, sleeper, do-not-draft, regression candidate, recency-bias target, strategy picks | The capped adjustment layer | Capped at +/-10% of CVS |

Ambiguity routes to Judgment. The classification appears in the Explain view
with the verbatim quote and its line reference. The cap lives in config and
does not rise without Anthony's explicit approval - never to make output look
better.

Conflict rule: if the guide contradicts a live data source (a depth chart
that has since changed, a player who moved), the live source wins and the
conflict is logged to `data/walter/conflicts.json`. A static document never
silently overwrites current data.

## The two Walter channels

- Channel A (per-player tags) - `data/walter/tags.json`. 11 tag types, each
  carrying the verbatim quote, section, line range, and explicit/inferred
  confidence. Judgment tags map to capped CVS deltas; every applied delta
  shows in Explain with its quote. Over-cap contradictions with the model go
  to the Model Conflict queue, never silently split.
- Channel B (structural knowledge) - `data/walter/structural.json`. Injury
  base rates by position, strategy definitions, scheme profiles. Feeds factor
  DEFINITIONS (coaching, historical priors, pick-engine conditioning) with
  attribution. Channel B may propose factor-weight changes with quote and
  backtest impact; it may never apply them.

Walter VORP and rank figures (`data/walter/walter_figures.json`) are a named
comparison series beside CVS - never blended into it. The guide in hand
carries ~19 sparse figures; the full-series correlation diagnostic runs when
the pending per-player export lands (ingestion contract open at
`data/walter/`).

Regression candidates are split: the stated mechanism (TD-rate 2025 vs 2026
projection) is Evidence routed to the baseline-projection factor; the call
itself ("overpriced/underpriced") is Judgment. No separate regression penalty
exists - the factor already prices the mechanism, so a second application
would double-count.

## Changelog as signal

`data/walter/changelog.json` stores, per player: `last_revised`,
`revision_direction` (up/down/neutral, subject-attributed with adjacency verb
detection), `revision_count`, and the entries verbatim. A player revised
twice in August carries different information than one untouched since June;
the UI exposes all three fields.

## Versioning

Every output carries the guide file's sha256. Re-parsing a changed guide
reports the previous hash and rewrites with a changed-flag - never a silent
overwrite. Name resolution: exact norm match, then a common-nickname pass,
then fuzzy at a 0.90 threshold; below threshold goes to
`data/walter/unresolved.json` for Anthony. Never guessed, never dropped.

## CVS (live - the anchor law)

Built by `src/build_cvs.py` from the engine payload, the committed shards,
three new input shards (`src/build_cvs_inputs.py`: volatility, TD rates, 2026
SOS - literal nflverse columns only), and the Walter layer. The anchor law:

    cvs_base = VOR + z_point_scale * sum(w_i / w_present) * z_i
    cvs      = cvs_base + ref_pos * capped_walter_pct / 100
    ref_pos  = within-position SD of cvs_base over the draftable pool

The percentage applies to a position-level reference magnitude, never the
player's own value (approved 2026-08-18, second revision of the walter
scale). History of the form, because each step was a real defect:

1. `cvs_base * (1 + pct/100)` inverted the judgment for negative-CVS
   players - a red-team review caught it (an endorsement pushed 29
   deep-board players further down).
2. `|cvs_base| * pct/100` fixed the sign but made Walter's authority
   proportional to each player's distance from zero - near-replacement
   players got nothing, and sleepers are by definition near replacement.
   Walter's strongest call (Davante Adams, -9%) moved him -0.01 points.
   Anthony caught it.
3. The reference form gives even authority across the range: at the 10%
   cap no player moves more than 0.1 positional SD (QB 5.8, RB 7.7,
   WR 5.3, TE 4.1 points today) - less authority at the top than the
   original form, real authority at replacement level where tail rank
   gaps are 1.5-2 points. Sign-safe by construction. The references are
   echoed in the payload and re-derived independently by the guard.

Two operational controls on the layer (approved 2026-08-18):

- Live kill-switch: both boards ship server-ranked in cvs.json
  (`players[].no_walter` carries rank, pos rank, signal, and conflict with
  every walter source off, model flags recomputed from base ranks by the
  same precedence function). The WALTER LAYER toggle on the big board -
  localStorage key `ytfl_walter_live`, read by the pick engine too - swaps
  which variant renders, mid-draft, no rebuild. The page never re-derives
  a rank or a signal.
- Tier-boundary flags: a delta that leaves a player inside his engine
  tier band changes nothing Anthony would act on; one that crosses a
  boundary is a real decision change. Crossings (own-delta, direction-
  consistent; shuffles caused by other players' deltas do not count) are
  flagged on the row and named in the CVS vs WALTER view - including
  "none at the current cap", stated rather than hidden. Well-defined
  because engine tiers are monotone in pure cvs_base order (verified,
  zero inversions).

VOR stays the anchor because points over replacement is the only scale
comparable across positions. Non-projection factors (opportunity, team
context, coaching, surrounding talent, schedule) are z-scored within position
over the draftable pool (QB30/RB60/WR70/TE30) and weighted from
`data/cvs_weights.json` - the single config. Three outputs per player, never
one: CVS, Confidence (covered weight share), Volatility (2025 weekly sd,
boom/bust, p90/p25). Nulls stay null, weight redistributes, confidence
reports it; `historical_priors` is null for every player today and says so.
K and DST are excluded: their projections are floors, not comparable values.
Guarded by `tests/test_cvs.py` (anchor decomposition, cap truthfulness,
null handling, signal precedence, isolation, determinism) at every merge.

## ADR: the pick engine objective (increment 2)

Decision: the pick engine card ranks by `CVS + need + tier-scarcity +
playoff-SOS tilt` - an explicit championship-lens proxy - rather than by a
title-odds simulation, and rather than replacing the VOR verdict.

- Championship probability is the mandated objective, but honest title odds
  require a validated season simulator that does not exist yet. Per stop
  condition 5 the card states on its face: "a schedule proxy for title odds,
  not a title-odds simulation".
- Weeks 15-17 SOS enters as its own tilt (PE.PLAYOFF x within-position z)
  above the season SOS already inside CVS - the mandated playoff weighting.
- The wait-or-reach verdict subject stays the audited VOR model. The card is
  additive and quarantined (PICKENGINE markers, reads cvs.json plus the
  read-only condSurvival, writes only its own card). If cvs.json is
  unreachable the card says so and the room runs exactly as before.
- Cost of waiting = P(gone by my next pick) x margin over the best
  alternate, from the frozen conditional survival model. Alternate
  conditions name the largest component where the alternate beats the pick.
- Constants (need 12, flex 6, scarcity 8, playoff 3/z, confidence bands
  10/4) print on the card. Ceiling/floor by slot from league history is NOT
  wired yet - deferred with the simulator, not silently approximated.

## Championship objective (pick engine - design of record)

The pick engine optimizes championship probability, not expected points:
weeks 15-17 SOS weighted above regular-season SOS in the recommendation
layer; ceiling valued over floor in roster slots where the league's own
13-season scoring history shows variance wins titles, floor over ceiling
where variance loses playoff berths. Honesty bound: full title odds require
a season simulator; until one is built and validated, the engine reports a
STATED PROXY (projected roster strength percentile against historical
playoff-make and title thresholds from this league's history) and labels it
as a proxy. Per stop condition 5, no number is presented that cannot be
defended.

## Analytical layer (items 2-5, reports first - nothing enters a rank or a
## UI without per-item approval)

Item 2 - manager profiles, validated: the simulator's per-franchise
positional profiles (shrunk lifts x band base rates) were backtested
walk-forward over 2016-2025 (1,766 picks; each season predicted from
strictly earlier drafts with the committed phase3i methodology). Profiles
beat the league-prior baseline on log-loss by +0.0081 (season-cluster
bootstrap 95% CI [+0.0049, +0.0112]) - real, small, and honest: about a
half-percent relative improvement, concentrated where tendencies actually
differ; top-1 hit rate is a wash because both models usually name the
modal position. The coverage rule (under 2 prior drafts falls back to
league priors, marked low-confidence) is enforced in code and guarded.
Payload: out/data/manager_profiles_backtest.json; guards in
tests/test_analysis.py. The simulator already consumes exactly these
profiles; this item's finding is that doing so is justified.

Item 3 - recency bias, REJECTED for use: across 1,677 skill picks in all
13 drafts (85% coverage; rookies and no-ADP picks excluded, stated),
regressing ln(pick paid) on the prior season's last-4-weeks points
(z within year) while controlling full-season points and ln(FFC ADP)
gives b_late = +0.0002, season-cluster bootstrap 95% CI
[-0.0203, +0.0178]. Not distinguishable from zero: whatever recency bias
exists in the market price, this league does not add to it. Per the
commission - no effect size, no usage - nothing recency-related enters
any factor, flag, or recommendation. Payload:
out/data/recency_bias.json.

Item 4 - injury pricing, NO INEFFICIENCY ESTABLISHED (with one flagged
candidate): two burden measures over 1,697 picks. By game-report
designations (Out/Doubtful weeks), the league pays UP slightly for
injury-history players vs market (b = -0.013, CI [-0.028, -0.001]) while
outcomes show no penalty at price (CI spans zero). By games actually
missed, the league tracks the market (CI spans zero) but outcomes DO
punish missed-time history at the same price (b = -0.084 SD per SD,
CI [-0.148, -0.025]). The measures disagree in pattern, so under the
pre-registered agreement rule nothing is used. FLAGGED for a follow-up
decision: the games-missed outcome signal is a candidate market-wide
fade (durability persistence) - investigating it (age confound, the
zero-game returners) is a separate approval. Payload:
out/data/injury_market.json.

Item 5 - replay backtest, honestly scoped (one-step deviations at actual
board states; live projections, the walter layer, and curated inputs
stated non-replayable, never approximated): over 169 of Anthony's actual
skill picks, his choices score +23.08 realized points per pick against
the blind ADP-best baseline, but the 95% CI crosses zero
[-0.44, +46.88]. The proxy replay engine (prior-season-points VOR,
rookies priced at zero) is +28.92 against ADP with a CI that also crosses
zero [-7.18, +67.15]. Anthony minus replay is -5.84, CI
[-46.15, +33.20]. Beat-or-report: neither Anthony nor the replay engine
establishes an advantage over the market-order baseline, and neither is
distinguishable from the other. #58's identity correction removed 119
alias player-pick identities from the replay frame and moved both
ADP-comparison intervals across zero; the earlier positive-interval
"both beat ADP" conclusion is retired. The frozen cond_survival,
evaluated on 16,949 player-pick pairs across 13 drafts, shows real skill
(24.66% Brier improvement over base rate) BUT is systematically
overconfident about removal: players it gives under 50% survival actually
survive 47.8% of the time, and the modern-era split (2023-2025:
predicted 0.319 vs observed 0.495 in that bucket) shows this is not an
old-era artifact. FLAGGED: the wait-or-reach card is
conservative - it says "reach" somewhat more often than the observed
history justifies. Recalibrating touches the frozen math and happens
only with explicit approval. Payload: out/data/replay_backtest.json.

Item 4 follow-up - durability fade, DROPPED: the games-missed outcome
signal survives the age control (-0.075), the points-per-game control
(-0.082), and both together (-0.073, CI [-0.146, -0.007]) - it is not an
age effect and not talent mismeasurement. It fails era stability, the
other half of the pre-registered rule: 2013-2018 shows nothing (+0.001,
CI [-0.109, +0.077]) and the entire effect lives in 2019-2025 (-0.143,
CI [-0.207, -0.081]). Position splits reinforce the instability (only
QB clears, n=241; RB/WR/TE all span zero), and the returner dummy is
noise. A signal that appears only in the era you would use it in is
exactly the pattern overfitting produces, so the rule says drop and it
is dropped. The 2026 season will test the modern-era hypothesis out of
sample for free; revisiting after that is a new decision, not this one.
Payload: out/data/durability_fade.json.

PRE-REGISTERED (2026-08-19, before the season, per Anthony): the
modern-era durability hypothesis and its decision rule, written before
the data exists. Hypothesis: the games-missed fade is a real 2019+
regime, not overfitting. Test: after the 2026 season completes, re-run
the full_ctrl spec (age + points-per-game controls, season-cluster
bootstrap) on 2019-2026 - eight seasons, one of them genuinely out of
sample relative to everything computed today. Decision rule: if the
2019-2026 coefficient's 95% interval excludes zero AND the sign is
negative AND the 2026-only contribution does not oppose it (the 2026
season's own coefficient point estimate is negative), the fade becomes
a CANDIDATE for a gated decision - display-only flag or CVS factor,
Anthony's call, nothing automatic. Any other outcome closes the
question permanently. No re-specification after seeing 2026 data;
this paragraph is the analysis plan.

## ADR (ADOPTED 2026-08-19): survival calibration layer

Status: ADOPTED by Anthony at scope (ii) full, with two conditions, both
met below. The five frozen functions are untouched - the calibration is
a monotone lookup applied AFTER them, kill-switchable at two levels
(payload flag + a one-tap live toggle in the room).

CURRENT LINEAGE CAVEAT (2026-08-31): the adopted lookup remains the exact
2026-08-19 approved constant. #58 later corrected player identity and regenerated
`out/data/survival_recalibration.json`; its modern-fit table now differs in 15 of
20 bins, by up to 0.0468. Retaining the approved model pending explicit reapproval
is deliberate. The regenerated proposal is no longer the exact evidence artifact
for that frozen constant, despite older text below and the engine comment naming
the path. Before any new calibration evidence is displayed, preserve the original
adopted fit by digest and explicitly review retention versus the corrected-identity
refit. Nothing in this note changes the deployed table.

ERA ANALYSIS (Anthony's question, rule registered before computing):
does the durability-style 2019 regime shift live in the calibration
table? YES. The all-years and modern (2019-2025) tables differ by up to
0.111 per bin, and bins 7-8 straddle the 0.6 verdict threshold between
them - the all-years blend imports the old era's fatter tails and
over-corrects exactly in the decision region. The 2019-2022 fit is not
worse on the 2023-2025 holdout (Brier 0.0597 vs 0.0598). Per the rule:
THE MODERN TABLE DEPLOYS; the all-years table is the documented
conservative fallback in out/data/survival_recalibration.json.

CONDITION 1 (the interval, on the record): Anthony's arithmetic on the
all-years lineage is confirmed exactly - 398 flips at 62.8%, binomial SE
0.024, CI95 [58.1%, 67.6%], one-sided z vs the 0.6 bar = 1.16. The
DEPLOYED lineage (2019-2022 fit, walk-forward on 2023-2025) is stronger:
292 flips at 65.8%, CI95 [60.4%, 71.2%], z = 2.09 - the lower bound
clears the bar. Caveat, stated not estimated: flips cluster within
players and draft years, so both intervals are somewhat narrow; three
holdout seasons are too few for a stable cluster interval.

CONDITION 2 (the switch and the delta): the room carries a one-tap
CALIBRATED SURVIVAL toggle (localStorage, like the Walter toggle), and
whenever the frozen and calibrated numbers land on opposite sides of the
0.6 verdict threshold on the current comparison, the card shows both -
only on those picks.

Scope notes: the live room's verdict comparison, survival tables, tier
cliffs, recs, and pick engine consume the calibrated value. The pick
grade's urgency input and the engine-baked pre-draft scenario verdicts
stay on the frozen number (not in the approved diff); draft-morning
regeneration refreshes the pre-draft cards anyway.

DIAGNOSIS (out/data/survival_recalibration.json): the frozen sd curve is
already fitted on this league's own history, so the overconfidence about
removal is a SHAPE defect, not scale. Removal around ADP is right-heavy
versus the normal the model assumes - the standardized differential's
q95 is 1.92 (FFC frame) and 1.90 (archive frame) against the normal's
1.645. Fallers keep falling; the normal kills the late tail too fast.

CANDIDATES, fit 2013-2022 and judged on held-out 2023-2025 (the same
pair frame as the item-5 calibration):

| Model | Brier | Skill vs base | Sub-50% bucket (pred vs obs) | TAKE NOW to WAIT flips | Flip win rate |
|---|---|---|---|---|---|
| frozen | 0.0648 | +21.8% | 0.32 vs 0.51 | - | - |
| A empirical-tail (KM) | 0.0576 | +30.5% | 0.35 vs 0.23 | 366 | 69.4% |
| B isotonic layer | 0.0598 | +27.8% | 0.42 vs 0.39 | 398 | 62.8% |

RECOMMENDATION: candidate B. It is monotone (never reorders any
decision, only rescales confidence), best calibrated in the bucket where
the defect lives, a 20-number lookup that mirrors trivially in the
room's JS, applied AFTER the frozen math, and kill-switchable. Candidate
A wins raw Brier but replaces the distributional form (a full parallel
survival function with its own JS mirror) and over-corrects its own low
bucket; it is documented as the alternative. B's flips clear the room's
own 0.6 WAIT threshold on held-out data (62.8% observed availability).

THE EXACT DIFF ANTHONY WOULD BE APPROVING (adoption table = the
all-years refit; the holdout numbers above are its out-of-sample
estimate):

    1. src/engine_2026.py - pure additions, zero existing lines change:
       SURVIVAL_CALIBRATION = [0.2749, 0.2749, 0.2749, 0.3559, 0.431,
         0.431, 0.4632, 0.5484, 0.5484, 0.6448, 0.6448, 0.6929, 0.7487,
         0.7487, 0.8062, 0.8834, 0.9182, 0.946, 0.9795, 0.9974]
       (AMENDED 2026-08-19 after the block was first written: the era
       rule selected the 2019-2025 modern fit as the deployed constant;
       the all-years table [0.3272, ..., 0.9964] this block originally
       quoted is the documented conservative fallback in
       out/data/survival_recalibration.json, not the shipped value)
       def calibrated_cond_survival(adp, to_pick, from_pick):
           p = cond_survival(adp, to_pick, from_pick)
           return SURVIVAL_CALIBRATION[min(19, int(p * 20))]
       plus payload keys survival_calibration (the table) and
       survival_calibration_enabled (the kill switch, true).
    2. out/draft_room.html - a JS mirror calCondSurvival() doing the
       same lookup over E.survival_calibration, falling back to the
       frozen condSurvival when the switch is off or the table absent.
       Two adoption scopes, Anthony picks one:
         (i)  display-only: survival percentages shown in the tables,
              recs, and pick engine read the calibrated value; the
              wait-or-reach VERDICT keeps the frozen number.
         (ii) full: the verdict threshold comparison also consumes the
              calibrated value - on holdout, 398 TAKE NOW calls become
              WAIT and are right 62.8% of the time, above the 0.6 bar.
    3. Guards: mathdiff still proves the five functions byte-identical
       (nothing touches them); new guards pin table monotonicity, the
       kill switch fallback, and JS/Python lookup parity.

Recommended scope: (ii) full, because the flips clear the threshold that
defines them; (i) is the cautious middle if Anthony prefers the verdict
untouched for one more season.

## Standing laws carried forward

The five frozen survival functions and the engine's verdict logic are out of
scope and byte-diff-proven at every merge. The conviction overlay's one
decision role stays the coin-flip tie-break. N1 and N2 stand.
