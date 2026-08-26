# Draft Path Tree (VONA) - SPEC CHECKPOINT, not yet built

Status: **awaiting approval.** Nothing in this document is implemented.
Per the build order, the tree is the largest item and its spec is
checkpointed before any code. Everything below is either derived from
artifacts this repo already ships or flagged as an open decision for
Anthony.

## 1. The objective function

VONA - Value Over Next Available. At a node, for each position:

    VONA(pos) = E[best available at THIS pick] - E[best available at MY NEXT pick]

The position with the largest expected loss is the one to take now. This
is the "QB dropoff is shallow so wait, RB dropoff R3 to R5 is severe so
do not" logic expressed as a number.

**How each term is computed, from existing repo machinery:**

- `E[best available at THIS pick]`: over players at that position with
  `survival(adp, pick) >= FLOOR`, the survival-weighted expectation of
  the best VOR still on the board. Concretely, order the position's pool
  by VOR descending and take
  `sum_i VOR_i * P(i available) * prod_{j<i} (1 - P(j available))` -
  the expected VOR of the top survivor, not the top name's VOR.
- `E[best available at MY NEXT pick]`: the same expectation computed with
  `cond_survival(adp, next_pick, this_pick)` - the frozen, calibrated
  conditional survival already used by the room's wait-or-reach verdict.
  The math functions are the frozen five; the tree calls them, never
  reimplements them.
- Both terms are computed against the pool as the PATH left it: a node's
  ancestors' picks are removed first, using `src/forward_policy.py` -
  the same shared layer that fixed the duplicate-pick bug. A tree that
  ignores its own path is the same defect one dimension up.

## 2. Structure

- **Input:** draft slot 1-12, rendered slot-conditional (the order is
  undrawn; the tab defaults to a slot picker exactly like the room's
  pre-draft view).
- **Root:** the round-1 pick at that slot. When one option dominates -
  no rival within the branch threshold - render a SINGLE node and state
  why ("VONA gap 34.1 pts over the next position; not a decision").
- **Branch only at real decision points:** branch when two or more
  positions' VONA values sit within `BRANCH_EPS` of each other. A fake
  fork is worse than none.
- **Parallel roots:** for middle and late first-round slots, render the
  top-2 first-round constructions side by side (whatever they compute to
  be - typically RB-first vs WR-first, but the tree does not assume it)
  so the constructions compare directly.
- **Depth:** rounds 1 through 7. Beyond that, survival dispersion and
  projection error swamp the VONA signal; the page states the cutoff and
  the reason rather than rendering noise. (Open decision D1 below: 7 or
  8.)
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
- VONA at that node: what taking this position now saves versus waiting
  for the next turn, in projected points
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
   real decision points cluster.

## 7. Open decisions for Anthony

- **D1 - depth:** 7 rounds or 8? 7 is the conservative read of where
  survival dispersion overwhelms the signal; 8 covers one more turn for
  late slots. I recommend 7, with the cutoff stated on the page.
- **D2 - parallel roots scope:** "middle and late" slots was the ask.
  I propose parallel roots for slots 5-12 and a single root for 1-4
  (where round 1 is usually forced), unless you want them everywhere.
- **D3 - does the tree read the BULLISH tag?** Per the N.1 null test I
  propose NO - it stays display-only and out of any planning
  computation. Say the word if you want it shown on nodes as a chip
  (display-only, beside the numbers), which would be consistent with
  the room and board.
