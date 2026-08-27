# Draft Path Tree (VONA) - reviewed implementation contract

Status: **implemented and corrected after the 2026-08-26 cold review.** The
terminal horizon, rendering rule, branching rule, and shared-FLEX feasibility
below replace the original p25/floor specification.

## 1. The objective function

VONA - Value Over Next Available. At a node, for each position:

    VONA(pos) = E[best available at THIS pick] - E[best available at MY NEXT pick]

The larger the expected loss from waiting, the more urgent the position. VONA is
an opportunity-cost coordinate, not the whole draft objective. The tree pairs it
with expected marginal starting-lineup gain and reports every action that is not
locally dominated on those two coordinates.

Both expectations use one pre-draft information frame and the same unconditional
`survival(adp, pick)` function. The tree never mixes an unconditional current term
with a player-specific conditional next term.

For a VOR-descending positional pool, every positive-VOR player is a mutually
exclusive top-survivor state:

    P(player i is top) = P(i available) * product(P(higher-VOR j gone))

The remaining probability is the replacement state and is worth zero. The
expectation includes every positive-VOR player. There is no survival cutoff and no
negative-VOR contribution.

The independence assumption needed by that product is disclosed and measured
with a descriptive same-position adjacency diagnostic from the league's own
draft history. Each rate carries k, n, and a Wilson 95% interval. Adjacency does
not identify player-level survival correlation or its bias direction, so it is a
limitation, not a hidden correlation adjustment.

## 2. Structure

- **Input:** draft slot 1-12, rendered slot-conditional while the order is undrawn.
- **Display depth:** rounds 1 through 7, the seven skill-starter decisions. This is
  a display and roster-construction horizon, not a claim that value stops there.
- **Value lookahead:** every displayed node has a real next owner pick. In
  particular, round 7 is evaluated against the owner's round-8 pick. A terminal
  node never silently substitutes `E[next] = 0`.
- **Visible path state:** a modal-player event means that player is available and
  every higher-VOR player at the position is gone. The continuation removes that
  whole implied-gone set plus the drafted player. A modal replacement event
  removes every positive-VOR player at that position. This is a coherent
  representative scenario for reading a path, not an expectation over every
  future chance branch. The tree makes no terminal-value pruning or
  global-optimality claim from that modal transition.
- **Roster feasibility:** a seven-pick leaf must match one exact composition from
  `src/forward_policy.py`: the six fixed skill slots plus exactly one shared FLEX
  assigned to a position with nonzero observed 2025 FLEX starts. RB, WR, and TE
  all qualify; the source artifact reports 216 starts and Wilson intervals.
  Independent per-position caps are insufficient because they can consume two
  FLEX slots.

Depth seven deliberately represents starter construction. The actual draft has
14 rounds, so legal early-bench or delayed-QB/TE paths exist and are outside this
surface. That is a deliberate scope limit, not a claim that those strategies are
illegal.

## 3. The local branch rule

There is no `BRANCH_EPS` and no percentile quota.

For every feasible position, compute two coordinates:

1. VONA urgency.
2. Expected marginal lineup gain over the same top-survivor distribution:

       sum_state P(state) *
         [phantom_lineup(roster + state) - phantom_lineup(roster)]

The lineup function is the shared `forward_policy.phantom_lineup_pts` objective.
The replacement state contributes zero.

Render the Pareto frontier using the unrounded internal coordinates. An action is
removed at the node only if another action is at least as good on both coordinates
and strictly better on one. Multiple survivors are a local model tradeoff, not a
claim of statistical closeness, statistical equivalence, global optimality, or a
coin flip. One survivor is a forced node.

Every feasible sibling, both raw decision coordinates, its Pareto status, and its
exact dominance witnesses are serialized in `decision_set`. Display rounding is
never an implicit epsilon. The visible policy is recomputed locally at each modal
path state; it does not discard an action based on modal terminal lineup values.
Exceeding the render budget fails the build loudly instead of silently dropping a
path.

## 4. Node contents

Each player node shows only computed fields:

- player, position, VOR, ADP, and projection;
- current pick and the actual next owner pick used by VONA;
- `P(available at this pick)`;
- `P(this player is the top survivor)` and the probability no above-replacement
  player remains;
- VONA, `E[now]`, and `E[next]`;
- expected marginal lineup gain;
- expected available players in the displayed tier and `P(any tier player)`;
- the full feasible sibling decision ledger and modal continuation basis.

The user-facing page exposes that ledger at every node, including dominated
actions and their exact dominance witnesses; the aggregate action count is not a
substitute for the underlying evidence.

The displayed identity is the modal player state from the full distribution. If
the replacement state is modal, the node is an honest fallback-required state with
no invented player name, ADP, or availability percentage.

No BULLISH chip appears on a node. The tree is a decision surface, and finding N.1
does not establish incremental value over ADP.

## 5. Decision constants

There are no statistical thresholds in the branch or render rules.

| Constant | Meaning |
|---|---|
| `DEPTH = 7` | display and starter-construction horizon; round 8 remains the terminal value lookahead |
| `MAX_NODES = 120` | deliberate UI safety budget, checked only after the complete local Pareto policy is built; the current maximum is 102 nodes and the mobile smoke renders that full slot without page-level horizontal overflow |

The old `SURV_FLOOR = 0.40`, p25 VONA-gap epsilon, and p25 domination band are
removed. Reusing a typed room convention did not make the floor derived, and a
quartile of gaps guaranteed relative branching even when the board contained no
genuine decision boundary.

The 120-node budget is not a statistical cutoff and never changes which actions
are selected. It is an accepted fail-loud coupling: a future live board above 120
blocks the VONA build and therefore the linked refresh until the complete tree is
reviewed on mobile and the UI budget is deliberately revised. It must never
truncate a valid tree to make a build pass.

## 6. What it must never do

- No hardcoded player names or hand-authored paths.
- No new survival math. The frozen functions are called as-is and mathdiff stays
  EMPTY.
- No conditional/unconditional frame mixing.
- No independent multi-pick selection or local substitute for `forward_policy`.
- No silent terminal zero, budget truncation, fallback player, or omitted feasible
  sibling ledger.
- No terminal pruning or global-optimality claim from a modal representative path.
- No test that prescribes how many slots must fork. Honest forced trees are valid.
- No BULLISH input to a live verdict or to this planning surface.

## 7. Build and verification

1. Run `src/engine_2026.py`.
2. Run `src/build_vona_tree.py` in the same pass.
3. Run `tests/test_vona.py` through `tests/run_gate.sh`.
4. Run `tests/mathdiff.py` through the mandated EMPTY-sentinel gate.
5. Run the full browser smoke and inspect artifact values, especially every
   round-7 `next_pick`, recomputed `e_next`, VONA identity, leaf composition, and
   every decision-set witness.

The committed artifact reports displayed picks, lookahead picks, solved and
rendered node and decision-group counts, every feasible candidate and local
dominance witness, exact starter targets, correlation evidence, and all model
disclosures.
