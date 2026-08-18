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
    cvs      = cvs_base + |cvs_base| * capped_walter_pct / 100

The percentage applies to the magnitude of cvs_base (sign-safe): an
endorsement always raises CVS and a fade always lowers it, including for
the 29 deep-board players whose cvs_base is negative. The naive multiplier
form inverted the judgment for those players; a red-team review caught it
and a dedicated guard in tests/test_cvs.py now pins the direction.

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

## Standing laws carried forward

The five frozen survival functions and the engine's verdict logic are out of
scope and byte-diff-proven at every merge. The conviction overlay's one
decision role stays the coin-flip tie-break. N1 and N2 stand.
