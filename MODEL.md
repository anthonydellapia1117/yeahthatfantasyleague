# MODEL.md - The Big Board valuation system

Status: increment 2. The Walter guide is parsed and audited; nothing from it
moves any rank until Anthony approves the Evidence/Judgment classification
(stop condition 1). The CVS scoring function builds after that approval.

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

## CVS (builds after classification approval - design of record)

Composite Value Score per player: factor groups z-scored within position,
weighted from a single config (`data/cvs_weights.json`), tunable live in the
UI. Three outputs per player, never one: CVS (risk-neutral, 1-100 rank),
Confidence (share of factor weight backed by real data), Volatility
(floor-to-ceiling spread; feeds archetype labels and tier widening). Missing
data stays null; its weight redistributes across present factors; nothing is
imputed to look like a measurement. Provenance per factor per player: source,
retrieval timestamp, staleness.

Factor groups: baseline projection (VOR vs 12-team replacement), opportunity,
team context, coaching and scheme, surrounding talent, schedule (season SOS
plus separately weighted weeks 15-17), historical priors, volatility.

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
