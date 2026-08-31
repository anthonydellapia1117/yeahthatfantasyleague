# Self-audit and defect record - 2026-08-26

Written at Anthony's direction ahead of an agent handoff to Codex. Parts 1 and 2
are the empirical record and the predicted-defect hunt. Parts 3 and 4 (tacit
knowledge, forward work) follow in this document; the migration spec is
`docs/AGENT_HANDOFF_SPEC.md`.

Method: reconstructed from `git log` (100 commits), `CHANGELOG.md` (35 entries),
`docs/AUDIT_3B_2026-08-12.md`, `docs/AUDIT_SURVIVAL_2026-08-12.md`, the findings
pages, and direct inspection of the working tree. Every claim below that says
"confirmed" was executed in this session; claims that are inference are labelled.

---

## PART 1: THE DEFECT RECORD

### 1.1 The table

Discovery channels: **SELF-PRE** (caught before committing), **SELF-POST** (caught
by me auditing already-committed work, almost always because Anthony
commissioned the audit), **GUARD** (an automated test caught it), **ANTHONY**,
**REVIEWER** (external independent review or a PR reviewer).

| # | Defect | Found by | Age before discovery | Shipped live? | Class |
|---|---|---|---|---|---|
| 1 | Every DEF under-scored by the 10-pt shutout bonus (`pts_` prefix filter too broad) | SELF-POST (3B audit, hand-validation) | ~1 day | yes | over-broad filter |
| 2 | 168/168 reconciliation did not reproduce (lowercase-only name match) | SELF-POST (3B audit) | ~1 day | yes | **NAME-NORM (1)** |
| 3 | `lineup_efficiency.csv` had no generator - two scripts each pointed at the other | SELF-POST (3B audit) | ~2 commits | yes | **SILENT PIPELINE BREAK** |
| 4 | `REFERENCE.md` led with superseded figures, self-contradicting table | SELF-POST (3B audit) | ~1 day | yes | **DOC/ARTIFACT DIVERGENCE (1)** |
| 5 | Headline correlations (+0.055 / -0.124) had no committed generator | SELF-POST (3B audit) | ~1 day | yes | **REPRODUCIBILITY GAP (1)** |
| 6 | One statistic, two bases, in three families of figures | SELF-POST (3B audit) | ~1 day | yes | basis drift |
| 7 | ADP_SD step function: adjacent-ADP survival differed 8,284x at pick 48 | SELF-POST (adversarial review of an unrelated feature) | since first engine | yes | unvalidated model shape |
| 8 | Wait-or-reach used unconditional survival; pre-draft cards and live room disagreed | SELF-POST (same review) | since first engine | yes | **CONDITIONING FRAME (1)** + **TWO-SURFACES (1)** |
| 9 | Survival put mass below pick 1: consensus #1 read 50% available at pick 1 | GUARD (tests written after #7/#8) | hours | yes | boundary/domain assumption |
| 10 | sd extrapolated below the observed range (1.30 at ADP 1 vs lowest bin 3.73) | GUARD (same run) | hours | yes | extrapolation beyond fit |
| 11 | Lift ratios against near-zero base rates (DEF 4.30x on a 0.005 share) | GUARD (same run) | hours | yes | ratio-of-noise |
| 12 | The power-law sd **lost its own out-of-sample backtest** to the step it replaced | SELF-POST (survival audit) | ~1 day | yes | **ADOPTED WITHOUT OUT-OF-SAMPLE TEST** |
| 13 | JS `1-erf` saturates to hard 0 past z~6 while Python `erfc` keeps mass | SELF-POST (survival audit) | since first room | yes | **TWO-SURFACES (2)** |
| 14 | A single failed poll permanently replaced the live UI with the pre-draft view, under a forfeit clock | REVIEWER (gated v2 review) | within the v2 diff | no (caught pre-merge) | **FAIL-OPEN CONTROL (1)** |
| 15 | Quarantine guard 8 built its leak list and **never asserted it** | REVIEWER (gated v2 review) | since written | no (pre-merge) | **FAIL-OPEN GUARD (2)** |
| 16 | Nine further v2 defects (sim survival credit, mid-draft sim seeding, roster_id coercion, snake mapping triplicated, etc.) | REVIEWER (gated v2 review) | within the diff | no | mixed |
| 17 | Walter multiplier inverted judgment for the 29 negative-CVS players | REVIEWER (red-team, post-merge #28) | ~1 day | yes | **UNTESTED SIGN DOMAIN** |
| 18 | On your own clock the pick engine computed survival to the current pick (trivially 100%), zeroing scarcity | REVIEWER (red-team) | ~1 day | yes | **DEGENERATE-CASE ASSUMPTION** |
| 19 | Depth charts 9 days stale against a 7-day guard; shards had not rebuilt since 08-17 | GUARD (during a refresh) | ~8 days | yes | **SILENT CRON (1)** |
| 20 | Crosswalk collapsed Marvin Harrison onto Marvin Harrison Jr. | GUARD (98% floor) | ~1 day | yes | **NAME-NORM (2)** |
| 21 | Two tests hardcoded one day's data and failed on correct behavior | GUARD | ~1 week | n/a | data-dependent test |
| 22 | Test wrapper exit-code masking: a pipe/compound wrapper returned 0 around a crashing suite - **a false green was committed** | REVIEWER (PR #48 blocker, relayed by Anthony) | unknown, >=1 commit | yes | **FAIL-OPEN GUARD (3)** |
| 23 | Same WR recommended at picks 24 and 25 across a snake turn | **ANTHONY** (visually, live) | since forward cards | yes | **MULTI-PICK INDEPENDENCE (1)** |
| 24 | Naive max-VOR drafts duplicate elite TEs early | GUARD (M1 mock validation, built to catch this) | since first engine | yes | **MULTI-PICK INDEPENDENCE (2)** |
| 25 | VONA prune summed raw VOR - the objective M1 had already disproved | **SELF-PRE** (mid-build) | 0 | no | **MULTI-PICK INDEPENDENCE (3)** |
| 26 | Strict domination collapsed nearly every fork | SELF-PRE (mid-build) | 0 | no | threshold over-application |
| 27 | VONA invariant assertion fired on below-replacement pools | SELF-PRE (own assertion) | 0 | no | assertion scope |
| 28 | `.activef {display:flex}` beat the `hidden` attribute; the filter bar never hid | GUARD (new smoke) | 0 | no | CSS specificity |
| 29 | DRAFT MODE: `const API` never switched to MOCK_ID | GUARD (smoke scenario) | 0 | no | incomplete wiring |
| 30 | Gate sentinel false-positive on "FAILURES" inside a PASS label | SELF-PRE | 0 | no | sentinel brittleness |
| 31 | **Pick clock hardcoded 120s against a real `pick_timer` of 60, anchored to poll-detection not `last_picked`** | **REVIEWER** | since Draft Room v2 (~2 weeks) | **yes, live** | **HARDCODED SERVER-KNOWABLE VALUE** |
| 32 | VONA conditioning mismatch: E[now] unconditional vs E[next] conditional, 28% of nodes negative | **REVIEWER** | since the tree shipped | yes | **CONDITIONING FRAME (2)** |
| 33 | VONA ignored roster feasibility (three early TEs on a path) | **REVIEWER** | since the tree shipped | yes | **MULTI-PICK INDEPENDENCE (4)** |
| 34 | Room validated that Sleeper *answered*, not that the answer was *usable*; a shared cache served 118s-old picks read as fresh | **REVIEWER** | since first room | yes | **FAIL-OPEN FETCH** |
| 35 | pages-data cron: 8 of 14 scheduled runs failed, last four consecutively; live site served Aug-17 depth data for 6d 6h 58m 40s | **REVIEWER** | 6d 6h 58m 40s | **yes, live** | **SILENT CRON (2)** |
| 36 | BULLISH verdict automation statistically unsound (post-hoc MDE as equivalence test, six cells no multiplicity, sign-blind BEATS) | **REVIEWER** | ~1 day | yes | **AUTOMATING A JUDGMENT** |
| 37 | N.1 written to a docs file, on no page in the app | **REVIEWER** | ~1 day | n/a | **DOC/ARTIFACT DIVERGENCE (2)** |
| 38 | `paths.html` omitted from the Pages explicit copy list - live 404 | SELF-POST (deploy byte-compare) | ~1 hour | **yes, live** | **DEPLOY MANIFEST INCOMPLETENESS** |
| 39 | Crosswalk normalizer did not fold diacritics (Estime / Estimé) | SELF-POST (diagnosing #35) | ~2 weeks | yes | **NAME-NORM (3)** |
| 40 | V1 changelog reports 39 forks / 29 pruned / 15 coin flips, while the committed `04d3dd3` artifact records 53 / 49 / 28; counters include subtrees later removed by ancestor pruning | **REVIEWER** (PR #54 accounting) | since V1 shipped | n/a (repository record) | **DOC/ARTIFACT DIVERGENCE (3)** |
| 41 | pages-data refreshed `depth_charts.json` without rebuilding CVS; a correct rebuild moved 80/190 player records and two Walter reference scales | **REVIEWER** (PR #54 rebase) | ~2 hours | no - the token-authored commit never deployed | **SILENT CRON (4)** |
| 42 | Same-day engine and mock builds shared one date, so the linkage guard passed while 14 mock tier values were stale | **REVIEWER** (#56 dependency audit) | ~1 day | yes (deployed artifact) | **FAIL-OPEN GUARD (5)** |
| 43 | `LA/LAR` mismatch nulled both CVS context factors for every Ram; weight redistribution kept the live board plausible | **REVIEWER** (team-code audit) | since CVS factor launch | yes | **OPTIONAL DEGRADATION (4)** |
| 44 | The lucky-player control reproduced exactly from an all-week extract containing postseason weeks; the clean regular-season top-tier penalty was -14.34, not the reported -30.2 | **REVIEWER** (source-basis reproduction) | <1 day | no (analysis record) | **REPRODUCIBLE CONTAMINATED SOURCE** |
| 45 | Four RBs with no observed 2025 usage entered the BULLISH backfield percentile as `0.0`; the population was 50 instead of 46 and its median was 0.4986 instead of 0.5060 | **REVIEWER** (percentile-population sweep) | since C5 | yes | **MISSING OBSERVATION AS ZERO** |
| 46 | The advertised TE 2-of-2 gate was one varying on-field-dropback input times a constant 0.9 market-share input for all 19 veterans; Isaiah Likely's BAL-2025 share was ranked alone in his NYG-2026 group | **REVIEWER** (input-value audit) | since C5 | yes | **VACUOUS GATE + HISTORICAL PRODUCTION INSIDE CURRENT-ROSTER GROUPING (1)** |
| 47 | Corrected `ALL_R_CODE.R` said the RB export was regenerated, but the committed RB CSV still carried `target_volume` and 2,530 NA-subsetting junk rows | **REVIEWER** (script/artifact comparison) | <1 day | no (analysis artifact) | **DOC/ARTIFACT DIVERGENCE (4)** |
| 48 | The R forward-Vegas export inverted the verified home-spread convention in 224/224 team-games; 31/32 aggregates were wrong and rank correlation with the correct table was -0.437 | **REVIEWER** (source-sign verification) | <1 day | no (caught before app wiring) | **ANALYSIS SOURCE REGRESSION** |
| 49 | Fourteen Python and four browser name normalizers disagreed; consolidation removed 119 phantom replay identities and restored 16 current ADP joins | **REVIEWER** (normalizer inventory) | since the duplicated consumers diverged | yes | **NAME-NORM (4)** |
| 50 | The canonical quote fold covered curly U+2019 but not modifier-letter apostrophe U+02BC; the contract, not one observed spelling, was incomplete | **REVIEWER** (Unicode corpus audit) | latent | no known current player impact | **NAME-NORM (5)** |
| 51 | Forward Vegas read a committed `schedule_2026.csv` snapshot that no workflow refreshed, so its dynamic horizon would have stayed at Weeks 1-6 while live games priced further out | **SELF-PRE** (new-feature update-path audit) | 0 | no - caught before first stale build | **SILENT STALENESS (5)** |
| 52 | `backfield_share` grouped the existing all-week 2025 carry basis by each player's 2026 depth-chart team; David Montgomery's 158 DET carries moved into HOU, removing them from Gibbs's denominator. The aggregate usage shard also trimmed low-PPR backs and collapsed multi-team rows, so historical regrouping alone still left PHI/JAX denominators wrong | **REVIEWER** (RB input-denominator audit) | since C5 | yes | **HISTORICAL PRODUCTION INSIDE CURRENT-ROSTER GROUPING (2) + INCOMPLETE/COALESCED SOURCE** |
| 53 | `adj_vac` subtracts an incoming player only when he has 2025 NFL targets; a 2026 rookie therefore subtracts zero, overstating the destination team's open opportunity while producing a plausible value | **REVIEWER** (opportunity-input audit) | since C5 | yes | **HISTORICAL PRODUCTION INSIDE CURRENT-ROSTER GROUPING (3)** |
| 54 | At the actual slot-4 decision, PATHS rendered zero forks and labelled the root "not a decision" while its action space contained one unconditional representative per position: it could neither condition on Gibbs/Bijan/Chase being gone nor compare McCaffrey with Taylor inside RB. On the observed board it would still render Puka alone (WR VONA 45.83 vs RB 41.29, gap 4.54 above a recomputed 3.58 epsilon) even though the complete 4/21/28 policy placed McCaffrey only 2.08 lineup points above Puka, inside the artifact's 7.0 coin-flip band | **REVIEWER** (slot-4 decision audit) | since PATHS shipped | yes | **SURFACE ABSENCE AS FINDING** |
| 55 | Printable Sheet 4 took the engine's static median-availability checkpoints, stripped `p_available_now`, tier-cliff and coin-flip qualifiers, then labelled the remaining names "Board expects" and the unsolved `fallback` "Next best." Bijan entered the pick-4 pool at 50.3% while Gibbs missed it at 48.2%. The sheet was not sourced from the paired simulation at all; in the current committed Puka-path run Javonte appears at pick 28 in only 7.652% of states. Individual survival had silently become a joint-path forecast, and the fallback had never been re-solved through the marginal policy | **ANTHONY** (read the live printed surface) | since cheat sheet shipped | yes | **QUALIFIER LOSS / REPRESENTATIVE PATH AS FORECAST** |

### 1.2 Base rate: how often do I catch my own defects before committing?

**Roughly 1 in 10, and the honest number is probably worse.**

Of the 55 entries: 5 are SELF-PRE (#25, #26, #27, #30, #51) - **9.1%**. The first
four are flattering to me. #25 was caught only because M1 had *already* published
the finding that raw VOR sums are the wrong objective, so I was checking against a
known answer. #27 was caught by an assertion I wrote in the same sitting. #51 is
the first spontaneous instance: before shipping a newly wired input, I asked
whether its source could actually update and found that it could not.

The other categories: SELF-POST 12, GUARD 9, REVIEWER 27, ANTHONY 2.

The SELF-POST count is the one that needs the caveat. Every single SELF-POST find
came from an audit **Anthony commissioned** - the 3B audit, the survival audit, the
deploy byte-compare he made me institute, the P2 investigation he ordered. Not one
came from me spontaneously re-examining shipped work. So the accurate statement is
not "I catch about a third of my defects afterwards"; it is **"I catch defects when
someone tells me to go look, and almost never otherwise."**

Twenty-seven of 55 - the largest single share, and disproportionately the severe
ones - came from outside review. Of the eleven defects now known to have reached
the live site and stayed there for more than a day (#19, #31, #34, #35, #39,
#43, #45, #46, #52, #53, #54), **nine were found by someone other than me.**

### 1.3 Which classes recur, and why the first fix did not generalize

Seven classes have three or more occurrences. In every case the first fix was
applied at the **call site** rather than at the **rule**.

**MULTI-PICK INDEPENDENCE - 4 occurrences (#23, #24, #25, #33).**
The rule: any projection that solves more than one pick must consume its own prior
selections and respect roster feasibility. First fix (#24) patched the mock
simulator. Second (#23) patched the engine's slot cards. Third (#25) I caught in the
VONA tree only because M1 had documented it. Fourth (#33) the reviewer caught,
because `starter_caps` did not exist yet - `roster_caps` did, and the tree used
neither. **Why it did not generalize:** the fix was expressed as *code in one
consumer*, not as *a shared module every consumer must route through*. Only after
#33 does `src/forward_policy.py` exist as the single layer, and even now nothing
mechanically prevents a new consumer from re-implementing pick selection inline. The
guard added in P1-B checks the VONA tree's output specifically; it does not check
"every multi-pick artifact in `out/data/`."

**NAME NORMALIZATION - 5 occurrences (#2, #20, #39, #49, #50).**
Suffixes, father/son collisions, diacritics, eighteen divergent implementations,
then a quote-codepoint contract gap. The first three fixes each extended one
normalizer with the transformation the latest case needed. Match-rate tests said
something broke but never defined what the key must ignore or what identity must
preserve. #49 finally separated the blind comparison key from the collision-aware
identity resolver, routed every Python consumer through them, and held the four
necessary browser copies to Python with corpus parity. #50 then proved why the
contract corpus matters: current names used U+2019, while unobserved U+02BC still
split an otherwise identical name. The test now names the punctuation classes
instead of waiting for the next player to expose one.

**SILENT CRON / STALE PUBLICATION - 5 occurrences (#19, #35, P2-3's
draft-morning rebuild gap, #41, and #51).**
**Why it did not generalize:** after #19 the fix was a *guard inside the job* (a
7-day as-of check). That makes the job fail loudly - but a failing job is exactly
the state nobody was watching. The monitoring was pointed at the machine, not at the
deliverable. Only P2 (this session) moved the check to the published artifact on the
live site. Even then, #41 recurred in a second producer because the downstream
rebuild rule was copied into one workflow rather than enforced at the shared
publication boundary. The measured publication exposure behind #35 was not the
four-day shorthand first recorded: Pages served Aug-17 depth data for exactly
**6d 6h 58m 40s**.

#51 is the first occurrence caught before it became stale. Forward Vegas was
designed to extend as more schedule weeks priced, but `pages-data.yml` refreshed
HISTORY `games.csv` while the builder consumed a static committed snapshot that no
workflow updated. It would have kept answering the Weeks 1-6 question through draft
morning with current-looking tags. The repair synchronizes and validates the 2026
snapshot before consumers run, stages snapshot plus metadata atomically, records
source/snapshot/decision digests and explicit horizon events, and fails closed on a
contracted horizon. The distinctive lesson is prospective: inspect the update path
of a new feature before trusting its first correct build. Every earlier occurrence
was found only after the deliverable had already gone stale.

**FAIL-OPEN GUARD / CONTROL - 5 occurrences (#14, #15, #22, the SKIP hole in
Part 2, and #42).**
A failed poll dropped permanently into fallback (#14); a guard constructed evidence
and never asserted it (#15); a wrapper returned 0 around a crash (#22); a suite
printed ALL PASS after skipping a third of itself (Part 2, P2-1); and a linkage
guard compared date-only strings that necessarily collide for two same-day builds
(#42). **Why it did not generalize:** #22's fix (`run_gate.sh`) is excellent for
the shape it targets - exit codes and sentinels. But it validates the *envelope*,
never the *content*. The class is "a check that cannot fail in the state it exists
to detect." Engine linkage now uses a self-verifying canonical content digest,
and a same-day mutation fixture proves the digest changes while the date does not.

**PRESENCE-NOT-CORRECTNESS GUARD - one decision-input instance (P2-9), with
lower-stakes analogues.** The FLEX suite proves that the observed artifact exists;
that its independently supplied totals, shares, intervals, and allocation satisfy
basic bounds and sums; and that the same allocation reaches the engine. It never
recomputes those fields from one another or compares a truthy allocation with the
Sleeper starter data it claims to summarize. This is distinct from the fail-open
class above: the guard does fail on missing or falsy input, and the mandatory VOR
step blocks that fallback from the 06:00 workflow. It cannot fail on the harder
state - plausible, wrong data.

The repository audit found three other unbacked semantic shape checks:
`test_pages_data.py` requires top-50 Sleeper ADPs only to be truthy;
`test_ceiling.py` requires weekly replacement values only to be positive with the
expected keys; and `test_archetypes.py` requires thresholds to be positive and
verification samples to clear minimum `n`. The latter two are optional display
layers rebuilt daily; the ADP shard is live-refreshed rather than a frozen input.
FLEX is the only committed input whose presence/shape guard is relied upon to
exclude a silent fallback **and** whose unchecked value directly reprices draft
decision math. WS2 artifact pointers and the publication heartbeat are not members
of this class because existence is their stated contract. The mathdiff proof
compares function bodies, while engine lineage and the CVS/VONA/mock rebuild guards
compare content. Historical #42 is the closest repaired predecessor: its date-only
proxy had this shape until the digest repair.

**CONDITIONING FRAME - 2 occurrences (#8, #32).** Mixing conditional and
unconditional survival in one expression, four months apart, in two different
subsystems. **Why it did not generalize:** #8's fix routed three specific call sites
through `cond_survival`. No invariant was written down. #32 then did the opposite
mistake (conditional where unconditional was needed) in new code, and the artifact
advertised it - 28% of nodes had negative VONA, an impossibility - for as long as it
took an outsider to look.

**DOC/ARTIFACT DIVERGENCE - 4 occurrences (#4, #37, #40, #47).** The written record
can be internally stale (#4), absent from its consuming surface (#37), or disagree
with the committed artifact (#40). At `04d3dd3`, `CHANGELOG.md` reports 39
rendered forks, 29 dominated branches pruned, and 15 coin flips.
`out/data/vona_tree_2026.json` records 409 constructed nodes, 53 fork events, 49
directly pruned roots, and 28 coin-flip events. Recursing the completed roots gives
the actual visible surface: 259 nodes, 42 fork groups, and 21 visible coin-flip
nodes. The counters were incremented before ancestor pruning, so removed descendants
remained in the summaries. The correct fix is to compute visible node and fork
counts recursively after pruning is complete.

#47 is the same class at the producer boundary: corrected R source and prose said
the RB export had been regenerated, while the committed CSV retained the old
schema and 2,530 junk rows. Correct source code is not evidence that the artifact
was rebuilt. The contract is source **plus** regenerated bytes, verified together.

**MISSING OBSERVATION AS ZERO - one live instance (#45), after a full percentile
population sweep.** `dict.get(id, 0)` put players with no 2025 usage into a
backfield-share distribution as observed zeroes. The rule is narrower and stronger
than “drop zeroes”: a zero is valid only when a canonical identity and source row
show that zero; absence is null and excluded. The sweep found exactly one live
instance. Every other BULLISH percentile population was identity-clean. Bucky
Irving's 0-of-n inside-five share is a legitimate observed zero and remains in its
population. The discovery frame had 50 candidates and four absent observations;
after #65's fresh engine moved Jonah Coleman outside the 168-pick pool, the current
artifact has 49 candidates, 46 observations, and three explicit exclusions. The
median remains the corrected 0.5060; that frame change is recorded rather than
silently forcing the old count.

**VACUOUS GATE (#46).** A probabilistic matrix is not multi-criterion merely
because it has two keys. Every eligible veteran TE received the same 0.9
market-share probability, leaving only the on-field-dropback share to vary, and
that quantity includes pass blocks. The live TE rows are suspended and omitted;
the artifact keeps the five computed former rows plus a neutral explanation on
all three tag surfaces. Its provenance also records the independent grouping
error: Isaiah Likely's 2025 Baltimore share was ranked inside his one-player 2026
Giants group. Resumption requires two genuine, season-consistent criteria and a
new reviewed N.1 test.

**SURFACE ABSENCE AS FINDING - one live instance (#54).** An empty result can
look like negative evidence even when the system never represented the question.
PATHS deliberately branches among positions, not players, and starts from an
unconditional pre-draft pool. At slot 4 it therefore rendered zero forks and the
phrase "not a decision" while being structurally unable to compare McCaffrey with
Taylor or accept the observed Gibbs/Bijan/Chase-gone board. Conditioning only the
pool does not repair the action space: Puka's WR VONA is 45.83 versus McCaffrey's
RB VONA 41.29, a 4.54 gap above both the current 1.39 epsilon and the 3.58 epsilon
recomputed on that depleted board, so the page would still render Puka alone.
The complete adaptive 4/21/28 policy instead puts McCaffrey only 2.08 lineup
points above Puka, inside the artifact's own 7.0-point coin-flip band. This is the
same silence shape as optional-shard degradation, but the fetch and rendering
both succeeded: the omitted action space itself became a false finding. The rule
is that every zero-result surface must name the universe it actually queried and
must carry a behavioral fixture in which a known actionable state produces an
action. Held PR #54 changes the branch rule, ranking, and rendering, but still
exposes only one action per position and therefore does not repair the missing
question. For PATHS, the offseason repair is an explicit unavailable-player state,
player-level actions, and complete turn continuations through the shared forward
policy; changing epsilon cannot ask the missing question.

**HISTORICAL PRODUCTION INSIDE CURRENT-ROSTER GROUPING - 3 occurrences (#46,
#52, #53), plus one inverse gap.** Likely's BAL-2025 receiving share was ranked
among NYG-2026 TEs. RB shares rebuilt 2025 carry denominators from 2026 depth
charts, moving Montgomery's DET carries to HOU and inflating Gibbs; the first
repair attempt then exposed a second source defect because a trimmed one-row-per-
player shard could not represent Tank Bigsby's JAX/PHI split. Adjusted vacated
targets treats incoming rookies as zero because they have no 2025 NFL usage.

The historical RB repair now consumes an untrimmed player-team ledger: every
split row contributes to its historical team's denominator and a player with
positive carries on multiple teams receives a null individual share rather than
an invented single-team one. A same-build counterfactual reproduces the exact
retired calculation, then separates historical regrouping from the untrimmed
split ledger. The fixed 2025 parquet bytes and canonical 161-row ledger digest
are pinned, so a rebuilt artifact cannot silently truncate weeks, postseason, or
the long tail while remaining internally self-consistent.
It changes 13 RB gate scores, only Gibbs among displayed tags (84.0 to 69.0),
with no tag membership/status or non-RB movement.

The repair exposes the inverse omission without solving it: `backfield_command`
now applies the existing all-week 2025 carry-share basis consistently to
historical teams, but the RB matrix has no measure of carries opened by 2026
departures. `teams.html` displays thresholded raw departure/arrival rows from the
trimmed one-row-per-player shard; it does not compute a complete net signal from
the new ledger.
Vacated carries remains assessment-only until its ADP correlation and incremental
value are measured. A same-method carry signal would inherit the
rookie/no-prior-NFL-sample problem in `adj_vac`, so fix `adj_vac` and any carry
implementation under one rookie policy or do not wire carries. The rule is:
historical production stays keyed to its historical season/team; departures and
arrivals are computed separately and bidirectionally, with rookies explicit.

**REPRODUCIBLE CONTAMINATED SOURCE (#44).** Byte-identical reproduction proved the
arithmetic and still confirmed the wrong claim because the chosen extract included
postseason weeks. The top-tier lucky-player penalty moved from -30.2 to -14.34 on
the clean regular-season source. Reproducibility is necessary evidence about a
calculation; it is not evidence that the input population answers the question.

### 1.4 Silent versus loud

This is the sharpest split in the record, and it is the one that matters.

**LOUD failures (test goes red, page shows an error, script raises):** #9-#11, #20,
#21, #28, #29, #30, and every C-phase builder without its cache. All of these were
caught quickly, most within hours, several before merge. **Not one loud failure ever
reached Anthony.**

**SILENT failures (the system looks healthy and is wrong):** #1, #3, #7, #8, #13,
#15, #19, #22, #23, #31, #32, #33, #34, #35, #38, #39, #40, #41, #42, #43,
#44, #45, #46, #47, #48, #49, #52, #53, #54. Twenty-nine of 54, and
they include **every single defect that reached the live site and stayed.**

The pattern is unambiguous: **this project does not have a bug-finding problem, it
has a silence problem.** When something fails loudly the existing machinery catches
it fast. The defects that survive are, without exception, the ones that produce a
plausible-looking output: a clock that counts down (just wrong), a page that renders
(through a 6d 6h 58m 40s stale-publication interval), a guard that passes (having
asserted nothing), a tree of
recommendations (28% of which are mathematically impossible), a 200 OK (carrying a
two-minute-old cache).

The corollary I did not act on for two weeks: **every new feature should have been
asked "how would this look if it were broken?" and if the answer is "the same,"
that is a defect in the feature, not a monitoring gap.**

### 1.5 What the outside reviewer saw that I did not

Twenty-seven finds, including nine of the eleven long-lived live defects. The mechanism is
not "too close to it" - that is the comfortable answer. Three specific mechanisms,
each of which I can name from the record:

**(a) I verified against my own intent, the reviewer verified against the source of
truth.** The clock (#31) is the cleanest case. I wrote a two-minute countdown
because the build order said two minutes; I then tested that the countdown counted
down correctly from two minutes. Every test I wrote passed. What I never did was
`GET /v1/draft/{id}` and read `settings.pick_timer`. The reviewer did. The same
mechanism produced #34 (I checked that the fetch resolved, not that the payload was
fresh) and #35 (I checked that the workflow existed, not that it had succeeded).
The R Vegas export (#48) inverted home and away in every priced team-game; only
comparison with the app's existing formula, moneyline direction, and raw schedule
established the sign. **I test that the code does what I meant. I do not test that
what I meant is true.**

**(b) I do not look at my own output as evidence.** The VONA artifact (#32) shipped
with 57 of 204 nodes carrying negative VONA. That is not subtle - it is an
impossibility, printed in the file, in a field named `vona`. I generated that file,
wrote guards for its provenance and thresholds, and never once ran
`min(n["vona"] for n in nodes)`. The reviewer read the artifact. The TE audit
(#46) found nineteen identical 0.9 values in the advertised second criterion; the
R comparison (#47) found corrected code beside an unchanged CSV. **I write guards
about a file's structure and never interrogate its values or compare the producer
with the committed output.**

**(c) I accept a specification as a substitute for verification.** "Two minutes"
came from the build order. `TEAMS = 12` came from me knowing the league. The step-sd
bands (#7) came from a prior session. In each case a number entered the system as an
assertion by an author, and no step ever asked the server or the data whether it was
still true. **The reviewer's advantage is that they had no memory of the
specification, so the only thing they could check against was reality.**

### 1.6 Where Anthony's instructions contributed

Asked for directly, so stated directly.

**The "underpowered" reframe (#36).** The instruction was right: a non-significant
result from an underpowered design is not evidence of absence. What went wrong is
mine - I turned a *judgment about one result* into an *automated three-state rule*
applied to six cells, which introduced three new statistical errors that were not in
the instruction (post-hoc MDE used as an equivalence test, no multiplicity control,
a sign-blind BEATS branch). The generalizable lesson is mine to carry:
**a correction to a conclusion is not a mandate to build a classifier.** Anthony's
later correction ("report the verdict, do not compute it from post-hoc power") was
the right fix and I should have arrived at it myself.

**The LeagueLegacy coverage claim.** Anthony stated the pipeline read one file from
2016 forward. It reads seven files across all thirteen seasons. I checked, reported
the contradiction, and he withdrew it. That exchange cost roughly one work item and
is the system working correctly - it is listed here only because the audit asked for
completeness, not as a criticism.

**Deprioritizing the dual-root hazard.** Logged as "not draft-night critical" and
deferred - a joint call, and correct on draft-night grounds. Part 2 shows it has a
live consequence that neither of us checked for (P2-U1 below). The lesson: "not
draft-critical" answers *when* to fix, and we let it answer *whether* to look.

---

## PART 2: WHAT IS STILL WRONG THAT NOBODY HAS FOUND

Predicted from the recurrence patterns in 1.3, then hunted. Every item below was
confirmed by execution in this session unless labelled otherwise. Severity is
this-project severity; "draft-critical" means it can produce a wrong decision or a
dead surface on 2026-09-08.

### URGENT, not draft-critical

**P2-U1. The repo is PUBLIC and league members' personal and financial data is
committed in it. The `.gitignore` rule written to prevent exactly this is defeated
by the duplicate archive root.** RESOLVED in this pass - see the prune below.

Confirmed: `GET /repos/...` returned `"private": false, "visibility": "public"`, and
Anthony independently verified the files were fetchable with no auth.

`.gitignore` carries the rule *"Contains the league owner email address - excluded
from the public repo"* for
`made-resources/.../16_franchise/franchise_dashboard.json`. That path was indeed
untracked. **The byte-identical file under `LeagueLegacy-io/` was tracked** - the
exclusion was written for one root and defeated by the second.

**Precise scope, corrected.** An earlier draft of this document said
`finances_members.csv` exposed 23 members' emails and Discord ids. That was wrong
and the correction matters, because overstating an exposure is its own inaccuracy.
Verified by parsing the file: **24 rows**, with

| column | populated |
|---|---|
| `name` | 24/24 |
| `photo` (URLs) | 24/24 |
| `total_debits` / `total_credits` / `net` | 24/24 |
| `gender` | 14/24 |
| `email` | **0/24 - the column exists and is empty** |
| `discord_user_id` | **0/24 - the column exists and is empty** |

So what that file actually exposed is 24 real names, gender for 14, financial
balances for all 24, and photo URLs - not emails or Discord ids. Emails were exposed
elsewhere: **one** distinct address appeared across five files
(`franchise_dashboard.json`, `achievements.json`, `finances.json`,
`league_meta.json`, and a `user` blob inside `finances_members.csv` itself).

The prune also removed member data the original characterization had not found at
all: `00_league/members.csv`, `14_members/member_profiles.csv` and three siblings,
`08_finances/` (3 files), `16_franchise/franchise_stats.csv`, and the export's own
`members.csv`.

- Severity: **HIGH, now closed at HEAD.**
- Draft-critical: no.
- This is the dual-root hazard's realised cost. It had been logged as an
  architecture smell and deferred as "not draft-night critical"; that judgement
  answered *when to fix* and was allowed to answer *whether to look*.
- **History retention is deferred to after the draft, by Anthony's decision.** The
  files remain reachable in git history at and before `bd8aff7`. Three options,
  his call: (a) accept the history exposure and leave it, (b) rewrite history
  (`git filter-repo`, force-push, invalidates existing clones), (c) make the repo
  private - **rejected for now: GitHub Pages on a private repo requires Pro, and
  flipping visibility would take the app dark twelve days before the draft.**

**P2-U2. Half the analysis layer cannot be rebuilt by anyone, and five of its inputs
have no recorded source at all.** RESOLVED 2026-08-26: `fetch_history.py` now
covers all nine families. The five orphan URLs were identified from the cached
files' own schemas and each verified by downloading it and byte-comparing against
the cache that produced the committed artifacts - `pbp/play_by_play_2025.parquet`,
`pbp_participation/pbp_participation_2025.parquet`,
`ftn_charting/ftn_charting_2025.parquet`,
`pfr_advstats/advstats_week_rush_2025.parquet` (the `advstats_week_rush.parquet`
name 404s; it is year-partitioned), and `habitatring.com/games.csv` (a live file,
not a versioned release - a fresh pull differs by a few bytes as games are scored,
which is expected and now documented). A guard asserts every HISTORY filename any
`src/` module reads is a family the fetcher knows, so the gap cannot silently
reopen; it was verified to bite by deleting a download and watching it fail.

At discovery, seven builders copied the same ephemeral container path as the
canonical `analyze_recency.HISTORY`; `fetch_history` imported the canonical value.
The cache is 156MB, 59 files, in `/tmp/claude-0/.../scratchpad/history`, and dies
with this container. A later test copied the literal again while adding coverage
for this fix - the defect class reproducing inside its own guard. Resolved in #57:
every consumer imports `analyze_recency.HISTORY`, and an AST guard derives the
default from that assignment and asserts the literal occurs exactly once across
`src/` and `tests/`. The guard itself therefore cannot become the second copy.

`src/fetch_history.py` - committed in #36 explicitly so "anyone can rebuild that
cache and reproduce byte-for-byte" - downloads **four** families
(`ffc_ppr`, `spw`, `inj`, `roster`). The cache holds **nine**. The five it cannot
fetch are `pbp_2025.parquet`, `participation_2025.parquet`, `ftn_2025.parquet`,
`advrush_2025.parquet`, `games.csv`. Confirmed by execution:

```
build_bullish_inputs -> FileNotFoundError: /tmp/emptyhist/pbp_2025.parquet
build_ws2_audit      -> ... spw_2016.csv  (also reads games.csv at line 510)
```

Confirmed: **grep for `nflverse-data/releases/download` across `src/`, `docs/` and
`.github/` returns no URL for any of the five.** The artifact provenance says
"participation 2025" and "nflverse schedules" in prose, with no release name and no
URL. The knowledge of how those five files were obtained exists only in the session
context this handoff is meant to preserve.

- Severity: **HIGH for the handoff.** C5 (BULLISH inputs) is unreproducible today.
  C6 (WS2 audit) is partially unreproducible. The rest are recoverable but only by
  re-running a fetcher nobody has documented as a prerequisite.
- Draft-critical: no - the artifacts are committed and the draft-morning workflow
  does not rebuild them (see P2-3).
- Cheapest fix: extend `fetch_history.py` to all nine families and add a guard that
  every `HISTORY`-reading path in `src/` corresponds to a family the fetcher knows.
  I can derive four of the five URLs from `build_pages_data.py`'s `NV` pattern;
  `advrush` I would have to look up and should not guess.

### DRAFT-NIGHT RELEVANT

**P2-1. `run_gate.sh` cannot tell a fully-run suite from a half-skipped one.**
RESOLVED 2026-08-26 - see the measured coverage below.
FAIL-OPEN GUARD, occurrence 4.

Confirmed by execution:
```
HISTORY=/tmp/emptyhist sh tests/run_gate.sh python3 tests/test_analysis.py
  -> 5 SKIP lines, "ALL PASS", "GATE OK", exit 0
```
On every GitHub runner - including the draft-morning workflow - `test_analysis.py`
skips all five determinism reruns and reports success. The runbook says the reruns
"skip loudly"; they do print SKIP, but the gate's contract is exit-0 + sentinel, and
both hold. So the workflow step named "Analysis guards" is green on a suite that did
not run its guards.

- Severity: MEDIUM. No known defect is hiding behind it; the point is that one could
  be, indefinitely, and this is the fourth instance of the class.
- Draft-critical: indirectly - it is a draft-morning gate.
- Cheapest fix: have each suite print `RAN n GUARDS` and have `run_gate.sh` fail if
  a `SKIP` appears without `GATE_ALLOW_SKIP=1`.

**P2-2. Nothing reads `draft.type` or `settings.reversal_round`. The snake math is
assumed, and it is right only because the current settings happen to match.**
RESOLVED 2026-08-26: `src/preflight_draft.py`, wired into both the 2-hourly draw
watch and the draft-morning workflow.
This is the #31 shape exactly, predicted from it, and confirmed.

Live ground truth fetched this session:
```
type: snake | teams: 12 | rounds: 14 | pick_timer: 60 | reversal_round: 0
roster_positions: QB RB RB WR WR TE FLEX K DEF BN BN BN BN BN
```
`grep` confirms no code path reads `type` or `reversal_round` anywhere. If the
commissioner enables third-round reversal (a checkbox in Sleeper) or changes the
draft to linear, **every pick number the engine and the room compute becomes wrong,
silently, on draft night** - the board would still render, the up-next strip would
still name teams, and all of it would be off by a snake turn.

Also: `TEAMS = 12` and `ROUNDS = 14` are hardcoded module constants in
`src/engine_2026.py` and are never cross-checked against the `total_rosters` the
same program already fetches, nor against the draft's `settings.rounds` which it
never fetches at all. (The *room* is safe here - it derives `GEO` from the loaded
draft. The *engine* is not.)

- Severity: **HIGH if it ever changes, zero today.** Probability low; blast radius
  total.
- Draft-critical: **yes, conditionally.**
- Cheapest fix: a preflight assertion - fetch the draft, assert
  `type == "snake"`, `reversal_round in (0, None)`, `settings.teams == TEAMS`,
  `settings.rounds == ROUNDS`, and fail the build otherwise. Ten lines, and it
  converts a silent catastrophe into a loud stop. Recommend adding to
  `check_draft_order.py` (already scheduled every 2 hours) *and* to the
  draft-refresh workflow.

**P2-3. The draft-morning workflow rebuilds the engine but not the artifacts derived
from it, and no guard notices the divergence.** RESOLVED 2026-08-27: the workflows
rebuild their mapped downstream chains, and the shared publication guard verifies
canonical engine-content digests rather than calendar dates.

At discovery, `draft-refresh.yml` rebuilt exactly three things: `engine_2026.py`,
`build_cvs_inputs.py`, `build_cvs.py`. It did **not** rebuild
`vona_tree_2026.json`, `mock_drafts_2026.json`, `archetypes_2026.json`,
`ceiling_2026.json`, `bullish_2026.json`, or `base_rates.json`.

A previous refresh moved 259 ADP values. At discovery, a draft-morning board refresh
therefore would have left PATHS on yesterday's engine while still rendering it as a
nav-linked decision surface.

At discovery, only 2 of 30 artifacts recorded `engine_generated` at all
(`vona_tree`, `mock_drafts`). `test_mock.py` asserts the key **exists**; nothing
asserts it **matches**. `paths.html` displays the tree's own recorded engine date but
never fetched `engine_2026.json`, so the mismatch was invisible on the page. The
only warning then was in the draft room, for CVS versus engine.

Confirmed cost of the fix: `python3 src/build_vona_tree.py` takes **1.0s**, needs no
network and no `HISTORY`, and is byte-deterministic (zero diff on rebuild). The
others cannot go in the workflow because they need the `HISTORY` cache - which is
P2-U2, and which is *why* they were left out, a reason recorded nowhere.

- Severity: **MEDIUM-HIGH.**
- Draft-critical: **yes** for PATHS.
- Implemented fix: `draft-refresh` rebuilds CVS, VONA, mock, decision cards, the
  embedded room payload, and all five teaser pages from one engine object.
  `pages-data` rebuilds every declared shard consumer before an atomic commit.
  The engine carries a SHA-256 over canonical JSON with only the digest field
  omitted; six direct JSON derivatives record that digest. CVS, VONA, and mock are
  strict and refuse a mismatch. Ceiling and BULLISH are HISTORY-bound display
  layers: their lineage may lag the 06:00 engine until the 08:00 pages-data run,
  but the UI hides or neutralizes the stale state rather than presenting it as
  current. BULLISH inputs digest each committed source payload, tags digest the
  exact inputs payload, and pages-data runs a strict current-engine repair guard;
  two same-engine children therefore cannot hide a skipped rebuild. BULLISH was
  deliberately not added to the 25-minute draft-morning job: doing so would add
  pyarrow, a 156 MB cache, 59 cached source files, and a live games endpoint to the
  decision-critical path for a display-only tag.
- The same-day fixture is the essential regression: change an engine field while
  leaving `generated` unchanged and the digest must differ. The old date guard
  could not fail that test. On the pre-#56 snapshot it hid 14 stale mock tier
  values; BULLISH separately carried one stale Zay Flowers injury reason with no
  lineage oracle. In an isolated rebuild from base `da78b0c`, **0 substantive
  mismatches across all 13 direct, embedded, and static engine derivatives**.

**P2-4. Optional-shard fetch failures degrade silently.**
On `big_board.html`, `base_rates.json` / `ceiling_2026.json` / archetypes / bullish
are fetched in bare `try { ... } catch (e) { D.x = null; }` blocks. Critical shards
correctly `throw` and show a banner; the optional ones vanish without a word. If a
shard 404s in production, columns disappear and the page looks fine.

**Fourth confirmed instance, 2026-08-28 (#64): valid nulls hid a failed
cross-provider join.** nflverse keyed the Rams as `LA`; Sleeper and the engine used
`LAR`. All six Rams on the live CVS board therefore rendered with both
`team_context` and `surrounding_talent` null, confidence `0.65` instead of `0.83`,
and no visible error. The room separately omitted the Rams PROE chip and the team
page's canonical `#t=LAR` route fell back to the index. Restoring the missing
evidence moved **187 CVS values and 23 ranks** through positional z-score
recalculation; Kyren Williams moved **-3.03 CVS**, the largest absolute change.
This is the same optional-degradation shape as a table disappearing: a genuine
pipeline failure was rendered as ordinary absence. #64 canonicalized team codes at
provider boundaries. The follow-up guard discovers every committed output JSON/CSV
and fails if any NFL team-code field cannot resolve through the shared alias map,
so the invariant covers the next provider spelling rather than only `LA/LAR`.

- Severity: LOW-MEDIUM. Same silence class; small blast radius.
- Draft-critical: no.
- Cheapest test: a smoke scenario that serves the board with `base_rates.json`
  removed and asserts a visible "unavailable" notice. None exists today.

### NOT DRAFT-CRITICAL

**P2-5. Hardcoded 12-team geometry inside DRAFT MODE.** `sleeperListHtml()` bands are
`[1,36] [37,72] [73,120] [121,200]` and `simBand()` labels `rd11-14` - all derived
from 12 teams x 14 rounds. DRAFT MODE explicitly supports other shapes (a 10-team
15-round mock was verified live). In that mock the bands are wrong and the labels
lie. Same class as #31, smaller stakes. Cheapest fix: derive from `GEO`.

**P2-6. Two normalizers, one fixed.** The diacritic fold added in P2 exists in
`build_pages_data.norm_name`. `src/ingest.py:_norm_player` and `bullish_vs_adp.norm`
still strip only punctuation and suffixes. NAME-NORM occurrence 4 is pre-positioned.
Cheapest fix: one shared normalizer with a contract test, not a rate test.

**P2-7. Displayed numbers whose provenance is a typed constant.** The pick grade
(0-100, the headline number on the on-the-clock card) is a weighted sum with
`GRADE_W = {VALUE:30, MARKET:30, URGENCY:20, NEED:12, SCARCITY:8}`, and the pick
engine uses `PE = {NEED:12, FLEX:6, SCARCITY:8, PLAYOFF:3, HI:10, MED:4}`. These are
**judgment weights, never backtested against anything.** The M1 validation tested the
*marginal-lineup policy*, not these weights. The card does say it is a stated proxy,
which is honest, but the audit question was "can you trace every displayed number to
a computed source" and for the grade the answer is **no - it traces to a number I
chose.** Not a bug; an unearned precision. Listing it because the governance asks for
derived-not-typed and this is the largest surviving exception.

**P2-8. `renderPre(... || 7)`** - the pre-draft default seat is hardcoded 7 with the
comment "documented seat last year". It is labelled and switchable, and the live path
correctly resolves slot from `roster_id` (`draft_room.html:461`), so this is cosmetic.
But note `roster_id == 7` and `slot == 7` are the same integer by coincidence; if a
future edit conflates them the tests would not notice.

**P2-9. The FLEX guard validates presence and linkage, not the correctness of a
truthy observed allocation.** `tests/test_vor.py` proves
`flex_usage_2025.json` exists; checks basic bounds and sums on its separately
supplied counts, shares, intervals, and allocation; and proves that allocation is
linked into the engine. It does not rederive the observed counts from Sleeper's
2025 matchup starters, recompute shares and Wilson intervals from the counts, or
recompute the largest-remainder allocation from the shares. A missing or falsy
allocation activates the projection-greedy fallback, but the mandatory VOR gate in
the 06:00 `draft-refresh` workflow then fails, so that fallback cannot publish
through the scheduled path. A coordinated truthy-but-wrong artifact can satisfy
every current guard and render normally. Confirmed counterexample: changing the
allocation from RB4/WR8/TE0 to RB5/WR7/TE0, then rebuilding the dependent engine
fields, leaves all 32 relevant VOR predicates green. The derivation has a second
version of the same weakness: it stops at the first failed or empty matchup week,
while the guard accepts `n >= 150`; thirteen complete weeks produce `n=156`, so a
plausible partial season can also pass.

- Severity: **LOW before the draft.** The artifact is a frozen 2025 snapshot and
  no wrong committed value is known.
- Draft-critical: **no.** The realistic missing/falsy scheduled path already
  fails closed.
- Decision: no correctness guard now, by Anthony's direction nine days out.

**P2-10. The draft-order endpoint states were tested separately; the one-time
placeholder-to-confirmed transition was not.** RESOLVED on the 2026-08-31
transition branch before Sleeper published the order.

At 18:02 and again at 18:31 UTC the real draft still returned `pre_draft`,
`draft_order: null`, the exact identity roster map, and zero picks. Roster 3 was
ownerless. Historical Sleeper evidence from this league's 2024 shell and the live
2026 roster state show that a legitimate publication can therefore contain 11
`draft_order` users plus a complete 12-entry `slot_to_roster_id` permutation.
The resolver required 12 users and rejected that realistic payload as
`incomplete_draft_order`, before considering the complete roster evidence.

A second defect survived even under the idealized null-user-order/full-roster-map
fixture: the top banner advanced to confirmed, but `OrderHyp.active()` is always
false when an external report exists, so the already-rendered order card, gap
strips, active reference chip, and decision geometry were not repainted. Two green
fresh-load fixtures had proved both endpoint states while missing the broken seam.
The pre-fix same-page smoke removed `#ohyp-card` into a blocked state and exited 1.

The fix permits a well-formed partial user map only as corroboration for a complete
non-identity roster permutation. It still rejects partial+absent, identity,
incomplete, or malformed fallbacks; owner absence and any slot disagreement still
block. A confirmation-state change now repaints the pre-draft surface to slot 4 in
the same document. The regression starts on the exact captured placeholder, opens
slot 7 as a reference, switches to the realistic 11+12 payload, and proves all
labels, pick geometry, and the active chip advance together without a reload,
conflict, live clock, or transient slot-7 primary. This is automated transition
evidence, not a claim that the still-pending real server transition has occurred.

- Severity: **HIGH and draft-critical before the fix.** The first real order poll
  could have blocked or displayed a split state immediately before the draft.
- Defect class: **endpoint snapshots without transition coverage.** The question
  to ask is not only “do both states render?” but “does the same consumer move
  between them coherently?”

### Hunted and found clean (stated so the next agent does not redo it)

- **Injection.** `MOCK_ID` is sanitized at the source (`.replace(/\D/g,"")`) and
  escaped at render. Member-controlled Sleeper team names are `esc()`'d at every
  interpolation site checked. No unescaped network string found in an `innerHTML`
  template literal.
- **Secrets.** No API keys, tokens, or private keys in any tracked file
  (scanned `sk-`, `ghp_`, `AKIA`, PEM headers). The Yahoo OAuth scripts take
  credentials from env and hardcode none.
- **Deploy manifest for data.** `pages.yml` copies `out/data/*.json` by wildcard, so
  the #38 class cannot recur for shards - only for HTML pages, which guard 8c now
  covers for nav-linked pages (a non-nav-linked page would still slip).
- **Critical-shard fetch handling.** `if (!r.ok) throw` with a visible banner on all
  four content pages. Correct.
- **Frozen math.** `mathdiff` proof EMPTY at HEAD; the ten frozen function bodies are
  byte-identical to origin/main.

---

## PART 3: TACIT KNOWLEDGE INVENTORY

Most of this is now written into `docs/AGENT_HANDOFF_SPEC.md`, where it is useful
to the next agent rather than filed in an audit: governance rationale is §3,
rejected approaches §5, module map and non-obvious coupling §6, sequencing §6,
sharp edges §7, do-not-modify §6. What follows is the residue - things that are
true, undocumented, and did not belong in a spec.

**Why the architecture is the shape it is.** The static-site-plus-embedded-payload
design was not chosen for elegance. It was chosen because the draft is one evening,
on a phone, possibly on hotel wifi, and every moving part is a thing that can fail
at 8pm on 2026-09-08. No server means no server to be down. The engine payload is
*embedded* rather than fetched for the same reason: one fewer request between
Anthony and his board. The cost is that rebuilding the engine rewrites
`draft_room.html`, which surprises everyone once.

**Why so much is display-only.** Not caution for its own sake. Each display-only
decision has a specific dead backtest behind it (spec §5). The pattern to
internalise: this project has repeatedly found real, persistent effects that do not
predict - opponent tendencies are genuinely real and genuinely worthless in the
arithmetic (p=0.99). "Real" and "useful" came apart often enough that display-only
became the default landing place for anything that has not earned its way into a
number.

**Why the guards are adversarial.** `test_survival.py` runs the OLD model through
the cliff guard to prove the guard bites. That convention exists because a guard
that has never failed on the bug it was written for is decoration. When you add a
guard, break the code deliberately and watch it fail. I did this for the two new
guards in this pass, and the fetcher-coverage guard did NOT bite on the first
attempt - it was matching the fetcher's docstring rather than its downloads. Only
the deliberate break exposed that.

**What "verified" means in the docs.** Numbers in `docs/` are labelled by their
verification status and the labels are load-bearing. "Reproduced" means re-run this
session. "Documented-only" means it came from a session whose code was not
committed - the three dead-hypothesis p-values (0.252, 0.266, 0.197) are the
standing example and they have no generator. Do not promote a documented-only
number to a verified one by quoting it confidently.

**Anthony's working style, since it shapes what good work looks like here.** He
reads everything, checks numbers independently, and corrects both directions -
including withdrawing his own claims when the evidence goes the other way (the
LeagueLegacy coverage claim). He wants the harsh version. Hedging reads as evasion.
When he says "report the verdict, do not compute it", he means the automation is
the error, not the conclusion. When he asks for a checkpoint, stop and produce it.

**The one instruction-shaped failure to remember.** He corrected N.1 from "null" to
"underpowered", which was right. I then built a three-state classifier out of it,
which was wrong in three independent ways. The lesson is mine: **a correction to a
conclusion is not a mandate to build a classifier.**

---

## PART 4: WHAT SHOULD BE BETTER

Effort is a rough order of magnitude. "Draft-critical" means it can produce a wrong
decision or a dead surface on 2026-09-08.

### Done in this pass

| Item | Effort | Draft-critical |
|---|---|---|
| Geometry preflight (`draft.type`, `reversal_round`, teams, rounds) | S | **yes, conditionally** |
| VONA tree rebuilt with its engine + provenance guard on every derived artifact | S | **yes** |
| Skipped guards fail the gate; `RAN n GUARDS` on every run | S | no |
| Archive pruned, dual root collapsed, PII removed from HEAD | M | no |
| `fetch_history.py` extended to all nine families + coverage guard | M | no |

### Architecture

**The dual-source-root hazard is resolved** (one root, 165 files deleted). The
residual structural problem is that `src/` mixes three unrelated layers with no
boundary: the draft-night path (5 files), the analysis layer (14 files needing a
156MB cache), and one-off investigation scripts. A newcomer cannot tell which is
which. **Effort M, not draft-critical:** move analysis and investigation scripts
into `src/analysis/` and `src/research/`. Do this AFTER the draft.

### Test coverage - the honest gaps

**The live browser-to-Sleeper path has never been exercised, and it is the
draft-night path.** All 326 smoke scenarios stub the API. Every clock, freshness,
and DRAFT MODE guarantee is proven against a fixture that behaves the way I assumed
Sleeper behaves - the exact shape of failure mode §1.1. **Effort M, DRAFT-CRITICAL.**
The cheapest real coverage: one Playwright run against a live Sleeper mock draft
(publicly readable, already verified), asserting the clock tracks the real timer and
picks appear. Anthony currently covers this manually.

> **CORRECTION, 2026-08-27.** The paragraph above was true when written and is now
> wrong on its headline claim. Anthony exercised the live path the same night, from
> a real browser against live Sleeper draft `1388575351239606272` (19 teams):
> `sleeper 200 - 106ms - data 43s old`, a clock counting off that draft's **120s**
> `pick_timer` (proving the P0 fix is dynamic per draft, not a corrected constant),
> seat 13 auto-detected, the format-mismatch bar firing on all three differences,
> correct 19-team snake math, and every decision surface populated. Full record and
> the two caveats: `docs/AGENT_HANDOFF_SPEC.md` §11.
>
> What still stands from the paragraph: the AUTOMATED coverage is unchanged - all
> 326 scenarios remain hermetic, so this is a human-verified path rather than a
> regression-protected one, and the settings verified (19/120s/2 flex) are not the
> league's (12/60s/1 flex, drawn order). The "untested paths" list below is
> unaffected.
>
> The same run confirmed P2-5 in production rather than by prediction: the room
> rendered `rd11-14` band labels against that draft, those boundaries being 12-team
> arithmetic. Cosmetic, not draft-critical.
>
> Left as written above rather than rewritten, because this document is a dated
> record of what was known on 2026-08-26 and silently editing it would destroy the
> thing it is for.

**Untested paths that only fail in production:** a mid-draft Sleeper outage longer
than the poll interval; a pick payload that shrinks (the new refusal path is smoke-
tested, but not against a real cache); the wake-lock on a real phone; behaviour when
`last_picked` is stale but `status` is still `drafting`.

**Not covered anywhere:** the pick engine's grade weights (typed, never
backtested); optional-shard absence (silent); non-nav-linked page deploy coverage.

### Monitoring

Three silent failures in two weeks; the publication watch now covers the pages-data
cron. **Still unwatched:** `draft-refresh.yml` fires twice ever (08-28, 09-08) and
nothing alerts if a run fails - the 08-28 dry run is the only rehearsal and a
failure would be discovered by looking. **Effort S, draft-critical-adjacent:** point
the publication watch at the engine payload's `generated` date on the two refresh
dates. Also: the Pages deploy itself has no watch - `pages.yml` could fail after a
successful merge and the site would silently serve the previous build.

### Statistical rigor

**Where claims are still weaker than the governance requires:**
- The pick grade (0-100, the headline number on the on-the-clock card) is a weighted
  sum of typed constants. Never validated. Honest on its face, but it is the largest
  standing exception to derive-don't-type. **Effort M:** backtest against the replay
  harness that already exists, or relabel.
- The M1 mock validation shows the board beats ADP chalk from three slots
  (+51.7/+96.5/+71.0 starter points) against **one** opponent model - ADP chalk with
  an observed K/DEF window. That is a weak adversary. A board that beats chalk has
  not been shown to beat a competent human league.
- `flex_allocation` is derived from a **single** season (2025 observed starters).
  Correctly labelled `flex_source: observed_2025`, but one season of a 12-team
  league is a small sample to set positional caps from, and `TE: 0` is why the VONA
  tree can never propose a second TE.
- The C4 ceiling weighting **cannot be validated against league history** -
  `use_median_scoring` is 0 for every season through 2024, so the format it is
  tuned for did not exist before 2025.

### Complexity that has not earned itself

- `out/draft_room.html` is ~2,400 lines of HTML, CSS and JS in one file, and it is
  the most defect-dense file in the repo by a wide margin. Splitting it is correct
  and **must not happen before the draft.**
- At `04d3dd3`, the VONA guard emits **1,347 of the project's 2,089 non-browser
  checks**, but not because one assertion is repeated. Its 259 visible nodes receive
  five direct checks each (1,295 executions); another 52 checks cover aggregate,
  slot, and page properties. Report assertion executions together with structural
  coverage rather than deleting the suite from the denominator.
- **PR #54 PATHS render (`8a831a8`, held):** slot 10 renders 102 nodes and 26 fork
  groups. At 1280×720 the page is 11,158 px high (15.5 viewports); at 390×844 it
  is 19,908 px high (23.6 viewports), before any decision ledger is expanded. There
  is no horizontal overflow and individual rows are legible, but the decision
  surface is not. The full ledger can remain in the artifact; the initial page
  needs a rendering cap and progressive disclosure.
- `verify_yahoo.py` is ungated, needs an uncommitted `raw/yahoo/` input, and cannot
  run. It should be deleted or documented as historical.

### Security and data handling

Scanned clean: no API keys, tokens, or private keys in any tracked file; the Yahoo
OAuth scripts read credentials from env and hardcode none; `MOCK_ID` is
digit-stripped at the source and escaped at render; member-controlled Sleeper team
names are escaped at every interpolation site checked; critical shard fetches
`throw` with a visible banner.

The one real finding was P2-U1, now fixed at HEAD with history retention deferred.
The lesson generalises past this repo: **a `.gitignore` rule is a control with a
scope, and duplicating a tree silently moves data outside that scope.** Anything
excluded by path should be excluded by pattern across all roots - which the
rewritten rules now do, verified with `git check-ignore`.


---

## MEASURED COVERAGE (2026-08-26, after the P2-1 fix)

`run_gate` now reports `RAN n GUARDS` on every run, so coverage is a number
instead of an assumption. Measured across all fifteen suites, with and without the
HISTORY cache:

| | with cache | on CI (no cache) |
|---|---|---|
| checks that ran | 2,089 | 2,084 |
| checks skipped | 0 | **5** |

All five skips are in `test_analysis.py`; every other suite runs identically with
and without the cache. Numerically that is 0.24% of the battery - but the five are
precisely the determinism reruns that prove the analysis artifacts reproduce from
their inputs, so **the reproducibility guarantee is the one thing CI never
exercises.** The workflow now sets `GATE_ALLOW_SKIP=1` on that single step with the
loss named at the call site, rather than the skip being invisible.

One caveat on the headline number: at `04d3dd3`, `test_vona.py` contributes 1,347
of 2,089 checks. The completed tree contains 259 visible nodes, and five direct
assertions run on every node (1,295 checks). Negative VONA, roster feasibility, and
E[next] monotonicity are instead accumulated while walking and asserted only three
times total; they are among the remaining 52 slot/global/page checks. Therefore
**742 is merely 2,089 minus the entire VONA suite, not an estimate of distinct
coverage**, and the previous conclusion is withdrawn. Coverage reports should pair
executed assertions with nodes walked and invariant families exercised.
