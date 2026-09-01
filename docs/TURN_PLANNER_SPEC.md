# Turn Planner - approved offseason replacement for PATHS

Status: **APPROVED DESIGN ONLY. DO NOT IMPLEMENT BEFORE THE 2026 DRAFT ON
SEPTEMBER 8.** The current production build remains stable. PR #54 stays parked
and is not an implementation base for this work.

Written 2026-08-31 after the confirmed slot-4 order exposed the difference
between the question PATHS answered and the player decision Anthony actually
faced. This document supersedes the replacement outline in section 8 of
`docs/VONA_TREE_SPEC.md` and the older PATHS open-item wording in
`docs/AGENT_HANDOFF_SPEC.md`.

The implementation may begin only after the draft. A future agent may not ship a
cheaper substitute by omitting the action-uncertainty study, copying the current
VONA band, showing fourteen independent recommendations, or relabelling the
existing tree.

## 1. Decision and product boundary

Replace the public PATHS page with a separate **Turn Planner**. It is an adaptive
one-turn decision surface over the actual draft state, not a draft tree and not a
global roster optimizer.

The page has two permanent layers:

1. A 14-pick rail for Anthony's confirmed slot-4 picks:
   `4, 21, 28, 45, 52, 69, 76, 93, 100, 117, 124, 141, 148, 165`.
2. One persistent player board. The board is ordered by engine VOR. Selecting a
   rail turn changes the availability evidence shown for that turn. It does not
   create another board.

The required, user-toggleable decision layer is named **Marginal Policy**, never
`optimizer`. When enabled on the next fully conditioned turn, it marks the output
of the canonical one-step marginal-lineup policy given the actual picks already
made. It never hides, filters, or reorders the base board.

The displayed pick numbers are confirmed facts, but the implementation derives
them from the reconciled `draft_order_context.primary_slot` and
`draft_order_context.primary_picks` on every build. It must never type the list
above into page logic. Rail cells are Anthony's scheduled owner turns, not actual
league-pick events; every actual league pick affects the shared board state.

Only the next fully conditioned Anthony turn receives a policy mark. In live
mode, a decision at Anthony pick `k` is fully conditioned only on a coherent
validated prefix containing exactly completed league picks `1..k-1`, including
every intervening opponent selection. In what-if mode it means the same complete
unavailable-player state before pick `k`, not merely Anthony's earlier selections.
Marking round 3 before rounds 1 and 2 and every intervening league pick exist
would recreate the fictional-path defect under a different interface.

## 2. Why fourteen boards are wrong

The current engine contains 417 players. Fourteen full boards would render 5,838
rows. Even restricting the display to the 80 positive-VOR skill players would
render 1,120 repeated rows, before K/DEF. More importantly, fourteen boards would
look like fourteen compatible future states even though each player's
availability is marginal and the intervening picks are unknown.

The rail is navigation over one decision state, not a row of projected drafts:

- During the live draft it selects Anthony's next pick automatically.
- Selecting a future turn changes the displayed survival horizon only, suppresses
  policy scores and marks, and labels the view `FUTURE MARGINAL AVAILABILITY -
  NOT A RECOMMENDATION`. Returning to the next live turn restores the mark.
- In prep mode a user may enter an explicit hypothetical Anthony selection and
  inspect how roster state and future availability evidence change. That alone
  does not condition the next turn. A new policy mark requires the complete
  intervening unavailable-player state ending immediately before the next
  Anthony pick.
- There is never a hidden representative path joining the rail entries.

`Prep mode` and `WHAT-IF mode` are the same explicit non-live state.

A completed rail turn is audit-only unless its coherent pre-pick snapshot and
score vector were retained. Selecting it must not rescore today's remaining pool
as though that were the old board.

The model state contains the complete remaining engine universe, including
negative-VOR players and K/DEF. Default board visibility is that full active
universe, ordered by engine VOR. `The list never shrinks` means the policy never
removes an option because of a
probability, threshold, score, position, or preference. Players actually drafted
by any team necessarily leave the active pool, but remain available in a
collapsed struck-through section of the same board, not a second board. Search
and position controls may change temporary visibility without changing model
state and always expose a clear-all control.

## 3. Canonical state and live transition

The planner consumes one coherent state object:

```
draft metadata + complete picks snapshot
    -> Anthony's resolved slot and actual roster
    -> genuinely remaining player pool
    -> selected Anthony turn
    -> engine and calibration lineage
```

The Draft Room's coherent refresh is currently inline page code, not an importable
module. Live mode must first extract one shared state module implementing the
existing concurrent, cache-busted `draft + picks` refresh, mismatch handling, and
atomic commit boundary. Both surfaces consume that module. Each page may
instantiate the canonical poller once; neither page may copy its logic or create a
second poller, cache, owner-slot resolver, or draft-state store inside the same
page. Picks, roster, remaining players, rail, availability, and policy marks on a
page repaint from one committed snapshot.

Separate browser tabs cannot be promised the same instant without a cross-tab
coordinator. This design does not require a `SharedWorker` or `BroadcastChannel`.
Every page instead shows coherent pick count and poll time, so a transient
cross-tab age difference is visible rather than presented as identical state.

The shared module must use canonical pick identity and resolved owner-slot evidence
to construct Anthony's roster. The current room reconstructs ownership partly
through array index and snake geometry; extraction must either replace that with
canonical evidence or prove exact equivalence across normal picks, undo, malformed
payloads, and every snake turn.

`Complete picks snapshot` is a validated prefix, not merely a JSON array. Explicit
pick numbers must be unique and contiguous `1..N`; player ids must be resolvable
and unique; each owner/slot assignment must reconcile with the confirmed draft
geometry. Missing, duplicate, reordered, or malformed pick/ownership evidence
holds the last coherent state visibly. An absent `pick_no` may not silently fall
back to array position in the extracted contract.

If either feed is unusable, the last coherent board remains visible with its
timestamp and a loud stale/desync state. The planner must not advance its turn,
roster, or recommendation from only one half of the feed. Unknown player ids,
unresolved owner state, and source conflicts leave the engine-VOR board visible
but block policy marks.

Manual input is allowed only in a visibly separate **WHAT-IF** mode. It cannot
silently override, supplement, or repair the live Sleeper state. Returning to
live mode discards the scenario ledger and rebuilds from the next coherent live
snapshot. Incoming live polls may update a visible source-age indicator while a
what-if is open, but cannot mutate its anchored snapshot. Undo/reset is explicit;
it never merges live and scenario picks.

The real started Sleeper feed remains unverified as of this specification. Real
`last_picked`, live cache timing, audio, wake lock, background-tab behavior, and
recovery can be observed only after the league starts drafting on September 8.
Do not rewrite that boundary as completed evidence.

## 4. Availability contract

Availability is evidence beside value. It never becomes a gate or a combined
score.

### 4.1 Current turn

At Anthony's current pick, availability is observed and binary: the player is
either in the coherent remaining pool or already drafted. Do not display a
modeled probability where the live board supplies the fact.

### 4.2 Future selected turn

For an undrafted player and a future owner pick `k`, display the adopted model's
numeric calibrated conditional-survival estimate from the current coherent pick
frame `c`:

```
P(player survives to k | player is available at c)
```

Show the numeric estimate and a continuous availability bar. State on the page
that the current function uses the player's ADP and the `c -> k` pick horizon; it
does not condition on the identities of other drafted players. It is one player's
marginal estimate, not a jointly possible board, selection frequency, tier,
cutoff, or forecast of who will be there together.

Create one canonical calibration evidence export tied by content digest to the
exact deployed 20-value lookup and its enabled/disabled state. It must carry the
observation count, survivor count, and Wilson interval for the evidence unit that
actually produced each mapped value - a raw fixed-width bin or an isotonic pooled
block, as applicable. These are calibration evidence, not an individual-player
probability interval. The engine currently exports calibrated values and parity
anchors, but not per-bin `n` and confidence intervals. Do not attach counts or
intervals from a different refit merely because it is called a calibration
artifact. Until exact lookup lineage exists, the UI may show the numeric estimate
with an explicit `calibration interval unavailable` state; it may not invent an
interval. The planner and Draft Room must consume the same calibration table,
digest, and kill-switch state or label the intentional difference on both
surfaces.

The observations are repeated player-by-consecutive-pick pairs within seasons,
not independent Bernoulli trials. Export distinct player and season counts and
state that clustering makes a pair-level Wilson interval narrower than the true
uncertainty. If an empty fixed-width bin inherits a mapped value from a preceding
or pooled block, link it to that donor block's counts and interval; never display
`n=0` beside an inherited nonzero estimate as though the empty bin estimated it.

The current repository does not yet satisfy that lineage contract. The adopted
engine lookup was frozen on 2026-08-19. The identity consolidation in #58 then
regenerated `survival_recalibration.json`; 15 of its 20 modern-fit values now
differ from the deployed lookup, by as much as 0.0468, while the engine comment
still cites that mutable file as the full evidence for its older table. Retaining
an explicitly approved model pending reapproval is deliberate and defensible;
claiming the regenerated proposal is its exact evidence is not. Before Turn
Planner availability ships, preserve the immutable adopted fit, rerun and review
the corrected-identity fit, and explicitly approve either retention or replacement.
Do not swap the live table as an incidental part of this feature.

`Calibration interval unavailable` is an honest development state only. The
public PATHS replacement cannot ship future survival estimates until the exact
deployed lookup has matching counts, hits, Wilson intervals, digest, and
kill-switch lineage.

### 4.3 Prohibited availability transformations

The planner must not:

- apply the engine checkpoint's `survival >= 0.5` filter;
- classify players as `likely` or `unlikely` with a binary threshold;
- multiply VOR, projected points, or marginal lineup gain by survival to create
  a single expected score;
- sort the base board by survival; or
- describe a list of high marginal probabilities as an expected board.

## 5. Marginal Policy contract

The canonical objective is the existing `forward_policy` one-step objective:

```
marginal_lineup_gain(player) =
    phantom_lineup_pts(actual_roster + player, baselines)
    - phantom_lineup_pts(actual_roster, baselines)
```

The primary ordering key is marginal lineup gain rounded to four decimals exactly
as the current policy rounds it. Engine VOR is the next key. If both keys are
exactly equal, current behavior keeps the first player in input order; the refactor
must preserve and fixture that final stability rule. Input-first stability is not
a tie or equivalence claim. This is not a multi-round
rollout, beam search, Monte Carlo opponent board, or full-roster optimum.

### 5.1 Required canonical API

Refactor the policy layer to expose:

```
score_candidates(pool, roster, baselines, caps) -> candidate score records
```

Each score record must include at least:

| Field | Meaning |
|---|---|
| `player_id`, `name`, `pos` | Sleeper player id plus display identity; names are never join keys |
| `marginal_lineup_gain_raw` | Unrounded change in projected starting-lineup points |
| `marginal_lineup_gain_key` | Four-decimal value used by the policy sort |
| `vor_tiebreak` | Engine VOR used only after equal rounded gain |
| `input_index` | Final stability key when rounded gain and VOR both tie |
| `eligible` | Whether the shared roster-cap and modeled-domain contract permits the action |
| `cap_reason` | Named cap or domain boundary when ineligible |
| `policy_rank` | Rank under the exact shared sort key |
| `raw_gap_from_leader` | Unrounded difference shown for audit, never as confidence |
| `policy_key_gap` | Difference between the rounded policy keys |

Candidate records remain in input order so the policy overlay cannot reorder the
base VOR board. Eligible skill candidates receive contiguous `policy_rank` values
under `(-round(marginal_lineup_gain_raw, 4), -vor_tiebreak, input_index)`;
ineligible candidates receive `policy_rank = null`. `pick_marginal()` becomes a
compatibility wrapper that returns the original `pool[input_index]` object at
`policy_rank == 1`, or `None`; it must not return a score record or copied player
dictionary because current callers rely on object identity. `raw_gap_from_leader` is
the signed value `leader.raw - candidate.raw`; it can be negative when equal
rounded gain lets VOR choose a leader with slightly lower raw gain.
`policy_key_gap` uses the rounded keys and is nonnegative. Neither field is
confidence. Both gap fields are null for ineligible records and whenever no
eligible skill leader exists; only eligible skill actions define the leader and
gaps.

The mock currently duplicates the same selection tuple rather than calling
`pick_marginal`; route every skill-action selection in both engine and mock
through `score_candidates`. Preserve the mock's separately labelled feasibility
fill that completes required K/DEF roster slots outside Marginal Policy; do not
present that forced fill as a scored recommendation.

Canonical Sleeper player id must also replace `name|pos` as the de-duplication
identity inside `phantom_lineup_pts`, roster state, and mock `taken` state. Today’s
payload is collision-free, so current sequences and artifacts must remain exact;
a synthetic same-display-name, same-position fixture must prove that two distinct
ids remain distinct actions and one id cannot be drafted twice.
Before any new consumer ships, preserve every current selected-player sequence and
keep generated artifacts byte-identical apart from declared volatile provenance.

Availability does not enter `score_candidates` at the live current turn because
the remaining pool is observed. At an unconditioned future rail turn, display
survival evidence only - no candidate policy scores and no leader. A future score
vector at pick `k` requires the explicit validated prefix `1..k-1`.

### 5.2 Roster and domain boundaries

Use the shared `roster_caps` contract. Its flex eligibility is derived from the
observed allocation, but it also adds one stated `+1` injury-spare convention for
each skill position; that convention is policy rather than league roster geometry
and must be visible in provenance. Require a complete cap map for every modeled
skill position and fail loud on a missing or unknown position instead of inheriting
the current permissive default. `count == cap` and `count > cap` are ineligible;
`count == cap - 1` remains eligible. If every candidate is capped, render a loud
`MARGINAL POLICY OUTSIDE DEFINED ROSTER DOMAIN` state and leave the base board
usable. Do not silently rerun uncapped as the current static checkpoint producer
does.

K and DEF remain projection floors. They stay visible on the complete board but
are domain-ineligible for `score_candidates`, carry
`cap_reason = projection_floor`, and receive null marginal-gain keys, policy rank,
and leader gaps until those positions have a validated objective. Their engine
VOR floor may remain visible as board evidence but cannot act as a policy
tiebreak or mark. Do not
infer a K/DEF-only state from round number, and do not let a generic fallback
bypass this rule.

If more than one boundary applies, `projection_floor` takes precedence over a
position cap. An unknown position or incomplete cap map is a state error, not a
candidate-level `cap_reason`. `Every candidate is capped` means every otherwise
objective-valid skill candidate in the remaining pool is ineligible.

### 5.3 Re-solving and runtime

This is an `O(number of remaining candidates)` one-step rescore over fixed lineup
geometry, not a path search. Recompute after every coherent pick snapshot and
after every explicit what-if state change. Do not cache a score vector across a
roster, pool, baseline, cap, or engine-digest change.

Before release, benchmark the full remaining universe on the real 60-second room
fixture and mobile browser. Publish run count plus p50 and p95 state-commit-to-mark
latency. If it is too slow for the observed clock budget, optimize the canonical
scorer; do not substitute a precomputed path or heuristic.

## 6. Action uncertainty - mandatory study, honest null allowed

### 6.1 The 7.0 VONA value is not uncertainty

The current VONA artifact's `narrow_band = 7.0` is the p25 of **71 positive
strict-domination margins** generated by the current all-slot position-tree probe,
which is itself subject to the tree's 80-node-per-slot construction budget. It
describes internal, budget-conditioned spread among this board's position actions.
It is not derived from held-out forecast error, action-value residuals,
calibration coverage, or historical decision accuracy.

Therefore 7.0 must never be used or described as:

- model uncertainty;
- a player-equivalence or tie band;
- confidence in one action over another;
- a forecast-error tolerance; or
- the threshold for a Turn Planner mark.

The nominal complete 4/21/28 comparison placed McCaffrey 2.08 projected lineup
points above Puka. The repository previously described that result as a model tie
because 2.08 was inside 7.0. That conclusion was stronger than the evidence. The
correct model statement is: **McCaffrey is the deterministic nominal leader by
2.08; player-action uncertainty has not been calibrated.** Anthony's durability
choice remains an external owner override, not a model output.

### 6.2 Required calibration work

Before the Turn Planner may display a tie, equivalent set, confidence mark, or
separated winner, it must attempt a held-out player-action error study:

1. Reconstruct historical draft states with the roster already selected, the
   players actually available, the preseason projection basis, and league-exact
   lineup geometry.
2. Score every eligible action through the canonical `score_candidates` contract.
3. Compute realized marginal lineup-value differences for candidate pairs under
   one consistent future-value basis.
4. Define paired action error as realized pairwise difference minus predicted
   pairwise difference.
5. Hold out complete seasons. No observation may calibrate the same fold on which
   it is evaluated.
6. Report `n`, missingness, position/round coverage, and an appropriate paired
   prediction interval. Any rate or coverage statement carries its Wilson
   interval.
7. Test whether a single pooled interval is defensible. If position, draft depth,
   or roster state changes the error distribution and the sample supports the
   split, publish the supported strata. Do not type strata or collapse sparse
   cells merely to obtain a mark.

The preregistered study must also define the realized-value horizon, replacement
and missed-game treatment, dependence among candidate pairs from one state,
fold aggregation, interval coverage, supported-stratum rule, and multiple-action
procedure before examining the 2026 decisions. Cross-position comparisons use a
supported joint stratum or receive no uncertainty mark.

Tie-set construction is leader-referenced, not transitive closure. Compare each
eligible candidate with the deterministic Marginal Policy leader using
simultaneous paired-error intervals at the preregistered coverage. Mark the leader
and every candidate whose leader-relative interval contains zero as the complete
`UNRESOLVED` set. Call the leader separated only when every simultaneous interval
excludes zero in its favor. Pairwise A-B and B-C overlap does not pull C into the
set when the leader-C interval separates them.

The calibration implementation must preregister its outcome and interval rules
before inspecting the 2026 target decisions. A same-board gap quantile, visual
closeness rule, rounded-score equality, in-sample residual, or VONA-derived band
does not satisfy this requirement.

### 6.3 Honest null

Attempting calibration is mandatory. A future agent may not skip it to ship a
smaller product.

If the historical corpus cannot support an action-error interval, record that
negative result with `n`, missingness, season/position/depth coverage, every
source searched, reconstruction yield, dependence diagnostics, and the
preregistered failure criterion. That feasibility report requires review before
the UI work can use the honest-null path. The planner may then publish the
deterministic policy ordering with a visible `ACTION UNCERTAINTY NOT CALIBRATED`
state and no tie or confidence claim. A UI needing a band is not evidence that a
band exists.

## 7. Marking and presentation

The Marginal Policy layer may add columns and neutral marks only:

- exact marginal lineup gain;
- exact gap from the deterministic leader;
- cap/domain status;
- action-uncertainty evidence when calibration supports it; and
- provenance identifying `ENGINE VOR`, `SURVIVAL - MARGINAL`, and
  `FORWARD_POLICY - ONE STEP`.

It does not change the engine-VOR row order. If a calibrated interval leaves
multiple actions unresolved, mark the complete unresolved set rather than a
single winner. If the interval separates one action, state the measured action
and interval evidence without borrowing a reserved verdict color. Use neutral
ink, outline, bracket, and text; reserved verdict colors remain off limits.

Every displayed noun must match the producer:

- `board leader` means raw maximum engine VOR;
- `Marginal Policy leader` means the shared one-step policy output;
- `unresolved` requires held-out action-error evidence; and
- `available at pick k` always means one marginal conditional-survival estimate.

| Allowed label | Required evidence |
|---|---|
| `board leader` | Maximum engine VOR on the observed remaining board |
| `Marginal Policy leader` | Deterministic `policy_rank == 1`; no uncertainty claim |
| `UNRESOLVED` | Applicable held-out simultaneous interval contains zero |
| `separated` | Every applicable simultaneous interval excludes zero in the leader's favor |
| `ACTION UNCERTAINTY NOT CALIBRATED` | Reviewed honest-null feasibility artifact |

## 8. Draft Room recommendation conflict

The current Draft Room headline sorts a round-filtered domain by raw VOR: it
excludes K/DEF before the last two rounds, then excludes skill players in those
last two rounds. Roster geometry appears only as an advisory line, and its
separate Pick Engine is a configured CVS heuristic. A Turn Planner powered by
`forward_policy` can therefore disagree with both.

The Turn Planner may not ship while two unlabeled surfaces can present different
answers under the 60-second clock. Before release, choose and test one of these:

1. Feed the canonical `score_candidates` result into the Draft Room's actionable
   recommendation; or
2. Keep the raw-VOR headline but label its domain on the number's face, for
   example **BOARD LEADER - ENGINE VOR, SKILL** or **K/DEF FLOOR LEADER**, with
   the Marginal Policy result separately and consistently named.

Do not silently replace the existing room answer, and do not reuse the room's
configured CVS `Pick Engine` as the Marginal Policy.

## 9. League history

League history remains description only. The tendency backtest is null
(`p=0.9932`) and continues to prohibit any manager adjustment to survival,
availability, policy scores, order, or marks.

An optional collapsed `BETWEEN YOUR TURNS` drawer may show, for known historical
franchises only:

- seats that pick before the next Anthony turn;
- observed first-position timing summaries;
- raw `n`, range, and basis; and
- slots 3 and 7 as unresolved with no inherited history.

This drawer is secondary prep context and stays collapsed in live clock mode. It
never creates a probability or recommendation.

## 10. Page and artifact disposition

Build a new `out/turn_planner.html` after the draft. Keep Cheat Sheet Sheet 4
static and printable. A future print/export button may snapshot the planner's
current explicit state, but the cheat sheet must not become a polling live app.

After the Turn Planner passes source parity, calibration disposition, live-state,
mobile, and browser tests:

- replace PATHS in public navigation;
- retain the old PATHS page only as an unlinked audit artifact if reconstruction
  still needs it; and
- keep VONA internal for positional cost-of-wait diagnostics, invariant testing,
  survival research, and artifact reconstruction.

VONA is not a player-action generator. PR #54 remains parked and must not be
rebased or repurposed as the Turn Planner implementation.

## 11. Cross-language and provenance contract

Python remains canonical. GitHub Pages cannot import it, so live evaluation needs
one shared JavaScript mirror of the score-vector contract. Hold that mirror to
Python with a Python-computed reference corpus spanning:

- empty, partial, flex-filled, bench-heavy, and capped rosters;
- all modeled positions;
- exact rounded-gain ties and VOR tie-breaks;
- values immediately below, at, and above fifth-decimal half boundaries;
- the observed slot-4 roster geometry; and
- cap-exhausted and K/DEF boundaries.

Add a mutation test that changes one scoring term and proves parity fails. A
parity test that has never failed is not sufficient evidence.
`marginal_lineup_gain_key` uses Python's actual `round(x, 4)` behavior, including
binary-float and ties-to-even edge cases. JavaScript must reproduce the
Python-computed key corpus; `Math.round()` or `toFixed()` alone is not the
contract.

Every rendered state carries:

- engine content digest and generated time;
- calibration artifact digest and sample basis;
- live poll time and coherent pick count;
- selected owner pick and actual/scenario mode; and
- explicit source labels for every decision column.

No Copilot document, R export, owner preference, BULLISH tag, Walter input, CVS
grade, research-document threshold, or typed heuristic weight may enter the base
order, availability, score vector, uncertainty, or marks.

The producer allowlist is closed: engine VOR orders the board, the adopted
survival model supplies future marginal availability, `forward_policy` supplies
one-step candidate scores, the held-out action-error artifact supplies uncertainty,
and reconciled Sleeper draft/pick state supplies the live pool and roster. Adding
any other producer requires a separately reviewed spec change.

## 12. Required behavior tests

At minimum, the implementation PR must make these fail before the feature and
pass after it:

1. The rail derives from the reconciled primary slot, equals Anthony's 14 current
   confirmed picks, and selects the next live turn without a typed slot-4 list.
2. Only one persistent player board exists; changing rail turns changes evidence,
   not the board instance.
3. The policy toggle changes no row order and hides no undrafted player.
4. With Gibbs, Bijan, and Chase unavailable, McCaffrey, Puka, and Jonathan Taylor
   all remain sibling player actions; same-position players are not collapsed.
5. A fixture containing an arbitrary actual Anthony selection outside every prep
   path plus the complete actual league-pick prefix ending immediately before
   Anthony's newly current turn produces a newly solved score vector without
   reload or path repair.
6. A future turn with any unknown intervening league pick displays marginal
   availability but no policy score or leader.
7. Current-pick availability is observed; future-pick availability is marginal,
   numeric, and unthresholded.
8. Cap exhaustion is loud and never triggers an uncapped fallback; cap-minus-one
   is eligible, while cap and over-cap are ineligible.
9. K/DEF rows carry the floor label and no marginal-gain key, policy eligibility,
   gap, rank, or Marginal Policy mark at any round.
10. A failed half-refresh preserves one coherent board and visibly blocks marks.
11. Python/JavaScript parity covers every score field and the mutation test bites.
12. No tie/equivalence marker can render without a linked held-out calibration
    artifact, `n`, and interval evidence.
13. Current engine and mock selected-player sequences remain exact after the
    score-vector refactor, and generated artifacts are byte-identical apart from
    declared volatile provenance.
14. Draft Room and Turn Planner cannot expose two differently sourced answers
    without their producer labels on the number's face.
15. Selecting a completed rail turn without a retained coherent snapshot cannot
    rescore today's remaining pool as a historical recommendation.
16. Calibration counts and Wilson intervals cannot load unless their evidence
    digest matches the exact deployed lookup and kill-switch state.
17. Absent, duplicate, gapped, or reordered explicit pick numbers and
    unreconciled ownership are rejected; the last coherent state remains visible.
18. Two same-name, same-position players with different Sleeper ids remain
    distinct actions, while the same id cannot enter roster or taken state twice.

All existing gates remain additive. Use `tests/run_gate.sh` without piping through
`head` or `tail`; all fifteen suites, browser smoke, analysis determinism, and
`MATH DIFF PROOF: EMPTY` remain release requirements.

## 13. Explicit do-not-build list

Do not build any of the following:

- fourteen duplicated player boards;
- a renamed, restyled, or player-labelled version of the existing PATHS tree;
- a player decision tree, representative draft path, beam search, or hidden
  multi-round optimizer;
- policy scores or marks for future turns with any unknown intervening league
  pick;
- a `survival >= 0.5` or any other binary availability cutoff;
- availability tiers that imply a categorical boundary;
- VOR, projected points, or lineup gain multiplied by availability;
- a fabricated expected board or joint-board frequency from marginal survival;
- a tie, equivalence, confidence, or uncertainty badge using the 7.0 VONA band,
  another board-spread quantile, visual closeness, or rounded equality;
- an uncapped policy fallback;
- a K/DEF policy recommendation while their inputs remain floors;
- manager-tendency probability or opponent-specific survival adjustment;
- BULLISH, CVS, Walter, R-export, Copilot, research-document, or owner-preference
  input to value, availability, policy, or marks;
- copied poller logic, a second poller inside one page, or a second owner-slot
  resolver;
- an interactive rewrite of the printable Cheat Sheet;
- a public Turn Planner that omits the calibration attempt merely to reduce
  scope; or
- any implementation, scaffold, feature flag, shadow production path, workflow,
  or migration before the September 8 draft is complete and its started-feed
  evidence has been recorded.

## 14. Effort and sequencing

Estimated effort is **9 to 14 focused engineering days**, assuming the historical
corpus can support the action-error reconstruction.

| Work | Estimate | Exit condition |
|---|---:|---|
| Canonical score vector and compatibility wrapper | 2-3 days | Existing policy outputs byte-identical; parity corpus bites |
| Held-out action-error feasibility and calibration | 3-5 days | Supported interval with `n`, or an evidence-backed honest null |
| Shared coherent live state and Turn Planner UI | 2-3 days | One rail/board state, live and what-if boundaries proven |
| Browser, mutation, mobile, provenance, and docs | 2-3 days | Full additive battery and source-labelled surfaces |

**Uncertainty calibration is the critical path.** UI work must not redefine or
skip it. If the corpus yields an honest null, the no-uncertainty state is part of
the completed product rather than a reason to invent a band.

No phase begins merely because the calendar reaches September 8. Implementation
requires the draft to be complete and the actual started-feed evidence from draft
night to be added to the live-state requirements first.

## 15. Separate deferred automation gap

The confirmed-order incident exposed a different dependency edge: the draw watch
detected `pending -> agrees`, but no process compared that live state with the
committed engine and dispatched a rebuild. A human noticed, initiated the full
dependency-aware rebuild, and the manual path deployed cleanly.

The recorded future shape is an idempotent watcher that:

1. reconciles the live official order;
2. compares it with the committed engine order state;
3. dispatches the existing `draft-refresh.yml` with `dry_run=false` only when live
   says `agrees` and committed state is still pending; and
4. alerts without dispatching on conflict, malformed, partial, or unresolved
   evidence.

It must reuse the existing strict rebuild workflow rather than duplicate its
dependency chain. **This automation is logged only. No Turn Planner PR may add a
watcher, trigger, dispatch, runtime logger, or workflow change, regardless of
date.** It requires separate approval and is not part of the Turn Planner scope.
