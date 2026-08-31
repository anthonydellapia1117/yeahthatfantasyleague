# Draft Path Tree (VONA) - shipped positional spec; offseason redesign required

Status: **the position-level tree shipped, but the 2026-08-31 slot-4 decision
proved that zero rendered forks can be a false-negative.** The original three
decisions remain recorded in section 7. Section 8 records the required offseason
redesign; PR #54's Pareto branch does not supply it.

## 1. The objective function

VONA - Value Over Next Available. At a node, for each position:

    VONA(pos) = E[best available at THIS pick] - E[best available at MY NEXT pick]

The position with the largest expected loss is the one to take now. This
is the "QB dropoff is shallow so wait, RB dropoff R3 to R5 is severe so
do not" logic expressed as a number.

**How each term is computed, from existing repo machinery:**

- `E[best available at THIS pick]`: over the whole remaining positional pool,
  the survival-weighted expectation of the best VOR still on the board. The
  survival floor is presentation-only and never truncates the expectation.
  Concretely, order the position's pool
  by VOR descending and take
  `sum_i VOR_i * P(i available) * prod_{j<i} (1 - P(j available))` -
  the expected VOR of the top survivor, not the top name's VOR.
- `E[best available at MY NEXT pick]`: the same expectation computed with
  unconditional `survival(adp, next_pick)` from the **same pre-draft information
  frame**. Mixing unconditional now with conditional next made 28% of the first
  artifact's nodes negative; one frame makes `E[next] <= E[now]` structural for
  above-replacement pools. The frozen math is called, never reimplemented.
- Both terms are computed against the pool as the PATH left it: a node's
  ancestors' players are removed first. Shared `src/forward_policy.py` supplies
  roster feasibility and lineup-value pruning - the same layer that fixed the
  duplicate-pick bug. A tree that ignores its own path is the same defect one
  dimension up.

## 2. Structure

- **Input:** draft slot 1-12, rendered slot-conditional. The externally reported
  2026 draw makes **slot 4 primary** while Sleeper confirmation is pending; the
  other eleven slots remain selectable reference views. A later official order
  must reconcile exactly or fail loud. This changes the default and provenance,
  not the per-slot arithmetic.
- **Root:** the round-1 pick at that slot. When one option dominates -
  no rival within the branch threshold - render a SINGLE node and state
  why ("VONA gap 34.1 pts over the next position; no position-level fork
  under this rule").
- **Branch only at position-level fork candidates:** branch when two or more
  positions' VONA values sit within `BRANCH_EPS` of each other. A fake
  position fork is worse than none. This is not evidence that no
  player-level decision exists.
- **Parallel roots:** NOT gated on slot number. A slot cutoff would
  hardcode an assumption the data should decide. The tree branches
  wherever the top two options fall within the VONA threshold, at ANY
  slot: slot 1 renders single-root naturally because one option
  dominates, and slot 4 branches if the last elite RB and the first
  elite WR are genuinely close. The artifact reports the threshold used
  and the branch count produced per slot, so the shape is observable
  rather than assumed.
- **Display depth:** rounds 1 through 7, on a STRUCTURAL boundary rather than a
  noise argument. The starting lineup is exactly seven skill slots -
  QB, RB, RB, WR, WR, TE, FLEX - so depth 7 covers starting-lineup
  construction completely and stops where the lineup is full. K, DEF and
  bench depth are separate problems the board already handles; extending
  the tree past the lineup would add rounds whose decisions are not what
  the tree is for. This display boundary is not a value boundary: every
  round-7 node computes `E[next]` at that owner's real round-8 pick. It never
  substitutes zero merely because no round-8 child is rendered.
- **Pruning:** cap total rendered nodes at `MAX_NODES`; prune dominated
  branches (a branch whose best leaf VONA is worse than another branch's
  worst leaf by more than `BRANCH_EPS`) and print the pruned count -
  "14 dominated branches pruned" - never silently.

## 3. Node contents

Each node shows, all computed:

- Player, position, VOR, ADP
- `P(available at this pick)` from the frozen survival model - the
  "realistic yet optimistic" requirement. A node whose survival is below
  `SURV_FLOOR` is not rendered at all.
- NO BULLISH chip, not even display-only. The tree is a decision
  surface, and a visual marker pulls the eye regardless of its label; at
  92.1% top-band concentration in the current RB/WR finding N.1; it would only re-mark
  players the board already ranks highly. All nudge, no information. The
  tag stays on the Players tab, where it is informational rather than
  prescriptive.
- VONA at that node: what taking this position now saves versus waiting
  for the next turn, in projected points; the current and next owner picks
  are both named, including the round-7 to round-8 lookahead
- Tier state: which tier the player is in and how many of that tier
  remain above the survival floor at this pick

## 4. Thresholds - all derived, none hand-picked

Every constant is computed from the same board the tree renders and
labeled on the page with its derivation:

| Constant | Derivation |
|---|---|
| `SURV_FLOOR` | the survival value at which the room already flags "going, going" (0.40, the existing shipped convention) - reused, not reinvented |
| `BRANCH_EPS` | p25 of the absolute VONA gaps between the top two positions across all nodes at that depth - i.e. a branch fires when the gap is in the narrowest quartile of gaps actually observed |
| `MAX_NODES` | render budget, not a statistical choice: stated as a UI constraint |

`BRANCH_EPS` is the one that matters and it is deliberately
self-calibrating: it means "these options are close by the standard of
this board", not "these options are within N points" where N was typed
by hand.

## 5. What it must never do

- No hardcoded player names, no hand-authored paths, no narrative
  branches. Every node comes from the artifacts.
- No new survival math. The frozen five are called as-is; mathdiff must
  stay EMPTY across this work.
- If survival data cannot support a branch, the node says so rather than
  inventing one.
- The tree is a PLANNING surface, not a verdict path: like the
  simulator and the BULLISH tag, it never feeds the room's live
  recommendation.

## 6. Build plan (on approval)

1. `src/build_vona_tree.py` -> `out/data/vona_tree_2026.json`: all twelve
   slots, computed offline so the page renders instantly and the numbers
   are gate-checkable.
2. `tests/test_vona.py`: no duplicate player on any path, every node
   above the survival floor, thresholds present and derived, pruned
   counts reported, tree depth honored, and a cross-check that the
   forward-pick law holds along every path.
3. New tab wired into `nav.js` and the smoke.
4. Findings-page entry with whatever the tree reveals about where the
   rendered position-level fork candidates cluster.

## 7. Decisions, resolved

- **D1 - display depth: 7**, on a structural rationale rather than the
  noise argument originally proposed. The starting lineup is exactly
  seven skill slots (QB, RB, RB, WR, WR, TE, FLEX), so depth 7 covers
  lineup construction completely and stops at a principled boundary
  instead of an arbitrary one. Round 7 remains valued against the owner's
  real round-8 pick; stopping the display never means comparing against
  nothing.
- **D2 - branching: data-driven at every slot**, neither of the two
  options proposed. No slot-number gating; the threshold decides, and
  the artifact reports the threshold and the per-slot branch count so
  the resulting shape can be checked against the assumption it replaced.
- **D3 - BULLISH on nodes: no chip at all**, not even display-only. A
  marker on a decision surface nudges regardless of its label, and the
  N.1 concentration means it would re-mark only what the board already
  ranks highly.

## 8. 2026-08-31 false-negative and offseason redesign

The actual slot-4 premise was Gibbs, Bijan Robinson, and Ja'Marr Chase gone,
leaving McCaffrey, Puka, and Jonathan Taylor. The complete adaptive 4/21/28
marginal-lineup comparison produced McCaffrey 290.75, Puka 288.67, and Taylor
272.05: McCaffrey's nominal +2.08 over Puka sits inside the same artifact's
derived 7.0-point coin-flip band. Anthony therefore correctly read the first two
as tied and made a separately labelled durability override to Puka.

PATHS rendered zero forks because it had never represented that question:

- actions are positions, so McCaffrey and Taylor can never be siblings;
- the root accepts no explicit unavailable-player state, so the observed first
  three selections cannot condition it; and
- even deleting those three players by hand gives Puka/WR VONA 45.83 and
  McCaffrey/RB 41.29. The 4.54 gap exceeds both the shipped 1.39 round-one
  epsilon and the 3.58 epsilon recomputed on the depleted board, so the page
  would still render Puka alone and say there was no decision.

This is **SURFACE ABSENCE AS FINDING**: zero forks looks like "no decision here"
but meant "the player-level, observed-board question was never asked." It is
worse than a loud unsupported state because a successful empty result reads as
evidence. PR #54 replaces the branch rule with a Pareto frontier but retains one
action per position and therefore does not fix this defect. It stays parked for
the 2026 draft.

The offseason replacement is a redesign, not an epsilon patch:

1. accept an explicit unavailable-player board state at the root;
2. expose player-level actions among actual survivors;
3. evaluate each action through the owner's complete next-turn continuation
   (slot 4 means picks 4, 21, and 28) using shared `forward_policy` lineup value;
4. retain VONA as an urgency/position-loss diagnostic coordinate, not the sole
   branch generator; and
5. add a behavior fixture for this exact observed board that must render the
   McCaffrey/Puka tie and Taylor as the separated third option.
