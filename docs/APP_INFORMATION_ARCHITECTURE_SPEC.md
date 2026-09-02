# Application information architecture - post-draft specification

Status: **APPROVED PLAN. DOCUMENTATION ONLY BEFORE THE 2026-09-08 DRAFT.**

Written 2026-09-02 after a rendered review of all eight navigated surfaces. This
document governs the post-draft reorganization of the application. It does not
authorize a runtime, model, artifact, navigation, build, or deployment change
before the 2026 draft is complete. Midnight on September 8 does not end the freeze.
If a production defect is separately authorized before the draft, that authorization
must name the defect and does not authorize this broader work.

This document complements `docs/TURN_PLANNER_SPEC.md`. The Turn Planner document
continues to govern coherent live state, marginal-policy scoring, availability,
uncertainty calibration, and the replacement of PATHS. This document governs page
ownership, navigation, visual hierarchy, removal, grouping, and failure boundaries.

## 1. Decision and governing question

The app is a draft-decision product, not a catalog of everything that was
interesting to compute. Every public element must answer:

> What decision does this change?

If the answer is none, the element is removed from the operating surface, moved
behind evidence or audit disclosure, or deleted from the draft app. Work already
spent on an element is not a reason to retain it.

The current eight-peer navigation reflects implementation history. The approved
architecture has three top-level user jobs:

| Top-level section | Sticky sub-tabs | Job |
|---|---|---|
| **DRAFT** | **Live Room** / **RxR Prep** / **Print** | Make and execute Anthony's picks |
| **BOARD** | **CVS Board** / **Player** / **Team** | Compare players and inspect supporting evidence |
| **EVIDENCE** | **Data Health** / **Findings** | Decide whether the app and its methods are trustworthy |

The exact route ownership is:

| Section | Sub-tab | Existing file |
|---|---|---|
| DRAFT | Live Room | `out/draft_room.html` |
| DRAFT | RxR Prep | `out/rxr.html` |
| DRAFT | Print | `out/cheatsheet.html` |
| BOARD | CVS Board | `out/big_board.html` |
| BOARD | Player | `out/players.html` |
| BOARD | Team | `out/teams.html` |
| EVIDENCE | Data Health | `out/home.html` |
| EVIDENCE | Findings | `out/ff-hub.html` |

These are the eight navigated surfaces referenced by this document. `CVS Board`
is the existing Big Board route under its more accurate role label; it is not a new
ranking page. The wordmark and existing home/root entry continue to open Data
Health unless a later, separately reviewed route decision changes them.

The top-level link opens the first sub-tab. There are no intermediate section
landing pages: they would add a click without changing a decision.

The default public routes remain separate HTML files. The tab strip provides a
unified information architecture without pretending the pages share runtime state.
Existing URLs and useful hash/query deep links remain valid.
Because the same files remain in place, compatibility is not implemented through
redirects. Browser guards inventory every existing public URL and required deep link
before and after the navigation change.

## 2. Why this is not one application shell

Separate HTML files are intentional failure boundaries, not an implementation
shortcoming:

- `draft_room.html` owns the 60-second live cockpit, coherent Sleeper polling,
  freshness, clock, current pick, and recovery behavior.
- `rxr.html` is a synthetic pre-draft scenario surface. It does not own live
  polling, wake lock, audio, future recommendations, or a tie claim.
- `cheatsheet.html` is static, printable, and usable when the live application or
  network is unavailable.
- Board and evidence pages may lose an optional shard without taking the live room
  or printed fallback with them.

Combining these pages into one DOM, router, or shared application process would
make cosmetic unity responsible for larger correlated failures. In particular,
Draft Room polling must not share runtime fate with the printable sheet.

Shared implementation is allowed; shared runtime fate is not. `nav.js`, common
styles, a future canonical live-state module, and canonical pure scoring helpers
may be shared. Each HTML page must remain directly loadable and usable without
another page having loaded, without cross-tab coordination, and without another
page's local-storage state.

This preserves zero dependencies, vanilla JavaScript, static GitHub Pages, and the
repository's explicit deployment copy list. A literal single-document application
is rejected.

## 3. Navigation and sticky sub-tab contract

The shared global navigation renders only **DRAFT**, **BOARD**, and **EVIDENCE**.
The active section renders a second, sticky row immediately below the global bar.

The sub-tab row:

- remains fixed while the document scrolls;
- never wraps;
- scrolls horizontally on narrow viewports;
- keeps the active tab visible;
- preserves keyboard focus, visible focus state, and 44px mobile targets;
- identifies modes explicitly: `LIVE ROOM`, `RxR PREP`, and `PRINT`;
- does not imply that sibling pages share the same live snapshot; and
- leaves direct page URLs and deep links as release contracts.

Do not create duplicate global pills for a destination already in the active
section. One compact operational state indicator may link to Live Room, but it is a
status/control, not a ninth navigation item.

## 4. PATHS disposition

PATHS is **not** a navigated destination in any section. It receives no global link,
sub-tab, home tile, or fallback role.

In this document, `public destination` means a route exposed by navigation, a tile,
or a normal task flow. `paths.html` remains technically reachable on the public
Pages host by direct URL; that does not make it a supported decision destination.

This is deliberate. The current tree cannot compare same-position player actions,
cannot condition on an observed unavailable-player state, and rendered zero forks
for slot 4 where the actual player decision was unresolved. Its absence of output
read as a finding even though the question was never asked. `#54` remains parked
and does not repair that boundary because it remains position-level.

Until the full Turn Planner exists:

- `paths.html` may remain deployed at a direct URL solely for audit and
  reconstruction;
- its false-negative disclosure remains on the page;
- VONA JSON, builders, tests, and provenance remain internal evidence; and
- RxR Prep is the sole public successor under **DRAFT**.

When the complete Turn Planner passes `docs/TURN_PLANNER_SPEC.md`, it replaces or
extends RxR's public role. It does not add another peer beside RxR and PATHS. The
rendered PATHS page can then be retired unless human reconstruction still requires
it; the underlying VONA evidence can remain internal.

Documentation inventories must describe the real state as **eight public surfaces
plus one unlinked audit renderer** until this reorganization lands. They must not
resurrect PATHS to make an old eight-surface list appear consistent.

## 5. Primary slot and reference-slot access

Confirmed slot 4 is the default and the only normal operating path. Removing the
eleven alternate slots from Draft Room and Cheat Sheet's primary UI does not delete
the capability.

Reference views remain reachable through one deliberate path:

- **Draft -> Print** keeps a collapsed `Other slots - reference only` selector and
  the existing addressable `?slot=` behavior.
- Every alternate view carries a persistent `REFERENCE SLOT N - NOT PRIMARY`
  label and a one-action return to confirmed slot 4.
- Draft Room may retain alternate-seat access only in a collapsed
  diagnostics/spectator drawer. A stray click may not silently turn reference
  geometry into Anthony's operational answer.
- RxR Prep remains bound to the reconciled primary slot. Its rail is not an
  alternate-seat browser.
- Internal VONA/PATHS reconstruction may retain all twelve slots while that audit
  renderer exists.

If the official order changes, the canonical draft-order reconciliation and rebuild
change the primary slot. A user does not promote a reference view to primary by
clicking it.

`draft_order_context.primary_slot` is the authority for the primary route. A
reference query accepts only an integer slot in the reconciled `1..teams` domain.
An absent, malformed, or out-of-domain value fails visibly back to the canonical
primary slot; it never creates an unlabeled reference state. An official order
change requires the existing dependency-aware rebuild and publication verification
before any page claims the new primary slot.

## 6. Canonical decision hierarchy

The largest current product risk is not page count. It is multiple recommendation
producers rendered as peers under a 60-second clock, each individually disclosed:

1. engine VOR / board leader;
2. marginal roster-need guidance;
3. calibrated wait/take evidence;
4. an unbacktested 0-100 heuristic grade;
5. display-only signal and BULLISH chips; and
6. the configured-CVS Pick Engine.

The final live hierarchy is:

1. **Canonical action** - `forward_policy.score_candidates` for the current fully
   conditioned Anthony turn, once the complete Turn Planner contract permits it.
2. **Board leader - engine VOR** - a neutral reference, never an imperative
   substitute for the canonical action.
3. **Wait cost and two alternatives** - numeric timing evidence and alternatives
   from the same action producer/domain as the leader.
4. **Diagnostics** - configured CVS, grade components, historical context, and
   display-only tags behind details.

During migration, Draft Room may continue to lead with raw VOR only if the number
face says `BOARD LEADER - ENGINE VOR, SKILL`. It is not the final canonical action.

The primary stack never mixes a raw-VOR winner, grade-sorted alternatives, a CVS
winner, and a categorical wait verdict as though they were one reconciled answer.
Only one recommendation-sized element is visible in live clock mode.

`Same producer/domain` means the leader and alternatives are members of the same
legal candidate vector scored for the same coherent roster and remaining-player
snapshot. If only one legal alternative exists, show one. If none exists, say so.
Never backfill the visual quota from raw VOR, CVS, grade order, or an earlier poll.
Before canonical policy reaches Draft Room, raw-VOR leader and raw-VOR alternatives
may remain together as a clearly labelled reference stack; they may not use
imperative action language.

Configured CVS remains valuable as a decomposable reference lens and kill switch,
provided it never masquerades as engine VOR or canonical action. The heuristic grade
and configured Pick Engine are removed from the live answer stack. If retained for
reconstruction, they live under `Experimental lenses`, keep their unbacktested
labels, and use no leader, confidence, take, or wait language.

Personal DND and injury state may remain beside the action as explicit constraints.
TARGET, SLEEPER, BULLISH, Walter, and other display-only evidence never silently
reorder or replace the action.

## 7. Grouping contract by section

### 7.1 DRAFT

#### Live Room - above the fold

1. freshness/desync state and clock;
2. on-clock owner, pick, and up-next;
3. one source-labelled primary answer;
4. position, team, source-labelled value, injury, and personal DND;
5. one numeric wait-cost sentence;
6. two alternatives from the same producer; and
7. one compact roster-need or active-run warning.

#### Live Room - below the fold

- **Wait board:** next-pick survival, tier cliffs, best by position.
- **My draft:** roster, target queue, manual correction.
- **Draft context:** grid, ticker, relevant between-turn opponents, collapsed
  descriptive history.
- **Board:** the only complete available-player lookup in Draft Room.
- **Experimental lenses:** only if grade or Pick Engine is deliberately retained
  for audit.

#### RxR Prep

- compact boundary/mode strip;
- one 14-turn rail and scenario roster;
- one sticky state banner;
- one engine-VOR player board;
- Fill opponents, manual Record, search/filter, undo/reset; and
- one collapsed chronological scenario ledger.

It remains prep-only until the complete Turn Planner contract is met. Its player
list remains visible and its policy mark never filters or reorders the base board.

#### Print

- static primary-slot checkpoints;
- overall and positional backup rankings;
- repeated per-sheet engine and injury provenance; and
- print controls and the collapsed reference-slot path.

The checkpoint plan should be the first emergency-print side and visibly say
`PRE-DRAFT PLAN - NOT LIVE`. Print never polls or recomputes policy.

### 7.2 BOARD

#### CVS Board

The default row is action-first:

`rank | player + injury/tag | position/team/tier | CVS | engine VOR | ADP`

The page title and number face say `CVS BOARD - REFERENCE, NOT ENGINE VOR`.
Confidence, volatility, positional rank, playoff SOS, raw factors, ceiling evidence,
and historical rates move into Explain/Player rather than competing in the summary
row.

Signal vocabulary is limited to the existing user nouns `TARGET`, `AVOID`, and
`SLEEPER`, with a separate conflict marker. Producer/source details remain available.

#### Player

Player owns full-pool search and the dossier, not a second exhaustive rankings
product. It keeps player header, engine VOR/projection, ADP, injury, value-versus-
market evidence, collapsed raw usage, ceiling/availability evidence, and per-number
provenance.

#### Team

Team owns concise play-caller, pass-tendency/PROE, and depth context. Labels state
exactly what is computed and whether a value feeds configured CVS, engine VOR, or
neither. Full depth evidence is progressive disclosure.

#### Shared Board evidence

Board sub-pages share one visible source-status strip. An optional shard failure is
never represented by a vanished column, missing table, or apparently complete page.
Method and provenance live in one always-available drawer, not a first-screen essay.

### 7.3 EVIDENCE

#### Data Health

Data Health retains source ages, engine build date/timestamp as actually observed,
publication health, forward-Vegas horizon/attribution, and conditional alerts.
It is not a directory of all pages and does not repeat navigation.

#### Findings

Findings retains the exact artifact-backed N.1 **INCONCLUSIVE** verdict and a compact
dead-hypotheses ledger. Each row carries its own n, basis, and verification state.
Negative and null results remain public.

In-season efficiency work is archived for a future in-season surface rather than
occupying the draft application.

## 8. Explicit delete list

`Delete` means remove from the named navigated surface. Audit payloads may remain when
needed for reconstruction.

| Surface | Delete | Reason |
|---|---|---|
| Shared navigation | Eight peer destinations | Organized by implementation history, not user job |
| Shared navigation | Duplicate Draft Room destination/pill | One canonical route plus one operational status is sufficient |
| Shared shell | Content reveal animation | Decorative JavaScript must not be capable of hiding primary content |
| Home | Current Hub page as a product | Navigation repetition and low-action cards dominate its useful health data |
| Home | Countdown, surface directory, market heat, isolated history fact | None changes a pick |
| Draft Room | Eleven reference slots from normal use | Confirmed slot 4 is the operational path; reference access remains explicit elsewhere |
| Draft Room | Giant checkpoint card from live scroll | RxR and Print own pre-draft turn planning |
| Draft Room | Historical first-position table from primary flow | Descriptive tendency is null as prediction and should not imply authority |
| Draft Room | Heuristic grade dial from live answer | Visual verdict authority exceeds its actual role |
| Draft Room | Configured Pick Engine from live answer | It is a second recommendation producer |
| Draft Room | Separate `Also consider` panel | Merge with the two primary alternatives |
| Draft Room | Board Wall when Grid remains | Duplicate spatial view |
| Draft Room | Embedded second player board and sleeper list | Duplicate the dedicated Board screen |
| Draft Room | Simulator from clock flow | Prep scenario, not a live action |
| RxR | Separate current-pick explainer | State banner and rail already provide the state |
| RxR | Default current-round strip | Duplicate scenario-prefix representation |
| RxR | Default full snake board | Duplicate state and excessive width; retain one collapsed audit ledger |
| Cheat Sheet | Mandatory `What I Actually Took` side | Records a decision but changes none; make optional |
| Cheat Sheet | Eleven reference-slot buttons from primary view | Keep only in collapsed reference access |
| Big Board | Walter-comparison tab | Audit material, not a draft action |
| Big Board | Empty Conflicts tab | Render a conditional alert only when conflicts exist |
| Big Board | Standalone 60-row Ceiling table | Player dossier owns the evidence |
| Big Board | Repeated base-rate prose | One evidence table/drawer is enough |
| Big Board | Giant K/DST floor card | Print keeps a concise final-round floor note |
| Big Board | Current rookie filter | It is factually wrong; rebuild later from canonical draft year if still useful |
| Players | Exhaustive ranking-grid landing page | Duplicates the Board |
| Players | VOR color ramp | Order and numeric VOR already carry the information |
| Players | BULLISH/archetype/Your Call index filters | Cross-player tag filtering belongs to Board |
| Players | Separate Prospect, Your Call, and Not Wired cards | Fold draft capital into header; disclose method once |
| Teams | Current Vacated Opportunity panel | Typed cutoffs and incomplete incoming/outgoing accounting overclaim completeness |
| Teams | Repeated Not Wired card | One section-level disclosure is sufficient |
| Findings | Efficiency tab and hero efficiency statistics | In-season start/sit work, not draft support |
| Findings | Champion Drafts table | Anecdotal illustration of a null |
| Findings | Draft-versus-waiver franchise table | Condense to one negative result with n/CI |
| Findings | Mutable order/status sentence | Operational state does not belong in a frozen finding |
| Public app | PATHS destination | Confirmed false-negative surface; retain unlinked audit renderer only |

## 9. KEEP list - decisions not to delete

These were seriously considered for removal. Their reason for remaining is part of
the architecture contract.

| Keep | Why it earns its place |
|---|---|
| Static Cheat Sheet | Unique offline and paper fallback; no live page replaces it |
| RxR Prep | Unique complete-prefix scenario job while preserving the visible base board |
| Data Health | Determines whether every other answer is trustworthy |
| Forward-Vegas horizon and delta attribution | Distinguishes source-horizon movement from model movement |
| N.1 and compact dead-hypotheses ledger | Prevents negative evidence from disappearing and folklore returning |
| Configured CVS Board | Decomposable reference lens and kill switch, provided it never masquerades as engine VOR or canonical action |
| Player dossiers | Investigate a candidate after the shortlist is known |
| Collapsed raw usage, ceiling, and availability evidence | Can change confidence in a shortlisted player without bloating the default board |
| Team play caller, PROE, and depth context | Explains configured CVS/team environment once accurately labelled |
| Draft Room Grid and sole Board screen | Legitimate between-pick context and lookup jobs |
| Manual correction and target queue | Required recovery and user-state tools |
| Tier cliffs and next-pick survival | Directly change take-versus-wait reasoning |
| Concise K/DST floor disclosure | Honest last-round limitation without pretending to rank complete projections |
| Sleeper external recovery link | Independent path when the local room is stale or unavailable |
| Every honesty label, null, limitation, provenance line, verdict wording, and false-negative disclosure | Relocate or collapse; never remove or weaken |

## 10. Eight visual hierarchy rules

1. **One recommendation-sized element per live view.** No peer headline producers.
2. **Name the producer on the number face.** Footer-only disclosure is insufficient.
3. **Method text may collapse; method meaning may not.** Exact verdict and limitation
   wording survives relocation.
4. **Optional failures are visible.** Missing evidence yields a source-status line,
   never an apparently complete surface.
5. **Sticky sub-tabs never wrap on mobile.** They scroll horizontally and keep the
   active tab visible.
6. **Audit material is visually subordinate to action.** No audit table, method
   paragraph, or secondary control row precedes the live primary stack.
7. **One responsive state representation by default.** Wide boards and duplicate
   ledgers are explicit audit views, not simultaneous primary content.
8. **Reserved verdict colors remain reserved.** Evidence, policy marks, descriptive
   archetypes, and uncertainty use distinct neutral treatments.

At 390x844 and 1280x720, Draft Room's complete primary stack should fit without
scrolling. RxR's full player universe remains inside a bounded internal scroller.
Polling causes no layout shift. Print sheets remain one Letter side each.

## 11. Four live correctness defects - independent first PR

These are wrong answers on shipped surfaces, not architecture cleanup. They are the
first implementation unit and remain independent of every reorganization phase.

1. **Big Board rookie classification.** `isRookie()` treats missing volatility as
   rookie evidence and currently classifies veterans including James Conner as
   rookies. Rebuild from canonical draft-year evidence or remove the filter.
2. **Players full-pool search.** The page advertises `search any player` but slices
   each position before search. Search the entire engine pool; cap only the default
   browse view.
3. **Big Board live availability.** The independent poll has no timeout,
   `response.ok`, freshness, or visible failure state. A first failure leaves the
   drafted set empty; a later failure retains an old set. Both can show a drafted
   player as available while the page looks healthy.
4. **Home engine age.** The engine carries a date, but Home appends a fabricated
   noon timestamp to publish fractional age. State `built on YYYY-MM-DD` until a
   real timestamp exists.

This work gets its own PR before navigation or page movement. If the reorganization
is delayed or cancelled, the fixes still land.

### 11.1 Draft-completion freeze boundary

No implementation lands before the 2026 draft is complete under this specification.
This is a state boundary, not a midnight boundary.

The Big Board defect is the only possible exception because it can materially offer
an already-drafted player. Read-only reproduction established both silent paths:

- after an initial picks failure, the availability filter can remain active with an
  empty drafted set; and
- after one successful poll, a later failure can retain the old drafted set while
  newer picks remain visible.

The defect is isolated to Big Board; it does not corrupt Draft Room, RxR, or the
engine. If Anthony treats Big Board as reference-only during the live draft and uses
Draft Room for availability, preserve the freeze. If Anthony intends to rely on Big
Board's `available only` filter while on the clock, authorize that defect explicitly
as a separate pre-draft hotfix PR. After the draft, the remaining three defects and
any necessary follow-through for the polling fix form the independent correctness PR
before architecture work. Do not smuggle the wider architecture work into either PR.

Post-draft, the long-term answer is not a third hand-written poller. Big Board either
becomes explicitly reference-only or consumes the one canonical coherent live-state
module defined by the Turn Planner work.

## 12. Additional correctness and claim work discovered by the review

The four-defect PR is intentionally narrow. The following are separate follow-ups:

- Team says its context is display-only even though PROE, play caller, and depth
  feed configured CVS; rewrite the scope accurately.
- Rename `Pace and tendency` to what is measured: 2025 pass tendency/PROE.
- Rename `Depth chart - ranked by value` to state that it is grouped by position
  and VOR-sorted within position.
- Optional Big Board and Players shards require one visible source-status strip.
- Findings carries mutable/stale order language and displayed values that need
  generated-artifact linkage rather than a stale embedded copy.
- Home must never infer precision from a date-only field.
- Descriptive archetypes must not reuse reserved verdict colors.

These do not justify weakening or deleting their existing honesty disclosures.

## 13. Effort and impact order

| Order | Implementation unit | Estimate | Impact |
|---:|---|---:|---|
| 1 | Four independent live correctness defects | 1-2 days | Highest correctness; separate PR |
| 2 | Three-section navigation and sticky sub-tabs | 1-2 days | Highest navigation gain |
| 3 | Draft Room canonical-answer hierarchy and operating-path reduction | 2-4 days | Highest draft-night safety gain |
| 4 | Big Board action-first rows and evidence consolidation | 2-3 days | Very high |
| 5 | Remove Players/Teams as top-level products while preserving dossiers | 2-4 days | High |
| 6 | Data Health/Findings pruning and linkage corrections | 0.5-1 day | Medium-high |
| 7 | RxR duplicate-state cleanup | 0.5-1.5 days | Medium |
| 8 | Shared visual tokens, neutral evidence scale, and accessibility polish | 2-3 days | Medium |
| Reject | Literal single-document application | 5-8 days alone | Correlated risk without proportional benefit |

A cohesive post-draft pass is approximately **9-14 focused development days**,
including the test rewrites required by deletions. The first three units deliver
most of the safety and navigation value in approximately **4-7 days**. These ranges
overlap; they are planning estimates, not additive invoices.

The complete live Turn Planner retains its separate 9-14-day estimate and held-out
uncertainty calibration critical path in `docs/TURN_PLANNER_SPEC.md`. Decluttering
the current pages does not make that model work cheaper.

## 14. Required test changes

Current tests encode some of the hierarchy being removed. Implementation must change
the contract deliberately rather than preserve a bad layout to keep an old test
green.

At minimum, post-draft work adds or updates guards for:

- exactly three global sections and the correct sticky sub-tabs;
- direct independent loading of every retained HTML page;
- exactly one visible primary action in live clock mode;
- producer labels for policy, engine VOR, survival, grade, and CVS;
- same-producer leader and alternatives;
- primary-stack visibility at 390x844 and 1280x720;
- a full-pool Players search fixture below the default browse cap;
- canonical rookie evidence, including a veteran without volatility;
- Big Board poll timeout/HTTP/error/stale behavior if live availability remains;
- explicit unavailable states for optional shards;
- hidden-but-addressable reference slots with an unmistakable reference label;
- malformed/out-of-range reference queries visibly returning to the canonical slot;
- RxR's single default state representation and complete-prefix policy boundary;
- Cheat Sheet remaining static with no poller; and
- page content remaining visible when navigation or reveal enhancement fails.

The primary action is mechanically identified with one DOM contract such as
`data-decision-role="primary"`; live mode permits exactly one visible match. At the
guarded 390x844 and 1280x720 viewports, its complete stack—including the longest
normal producer label and a visible stale/error banner—fits between the sticky
navigation and viewport bottom without document scrolling. Tests also exercise
browser text enlargement and mobile safe-area padding. Subjective words such as
`compact` or `subordinate` are not acceptance criteria by themselves.

Before repeated disclosures are removed, implementation creates a disclosure
inventory mapping each approved wording to its canonical on-face location and its
expandable full-text location. A deletion test proves every verdict, null,
limitation, provenance statement, and false-negative warning still has an accessible
canonical instance.

`tests/run_gate.sh` remains the only valid suite invocation. Browser deletion tests
must be additive until the old hierarchy assertions are explicitly superseded.

## 15. Non-goals and do-not-build list

This architecture does not authorize:

- a framework, package dependency, backend, or client-side router;
- a single-document app;
- shared cross-page mutable state or a page that depends on another tab;
- a new PATHS variant or resurrection of PR #54;
- presenting RxR Prep as the completed live Turn Planner;
- another independent live poller;
- a new combined score, threshold, verdict, or uncertainty band;
- promotion of configured CVS, grade, BULLISH, Walter, research, or owner preference
  into canonical policy;
- deletion, paraphrase, or weakening of an approved verdict, provenance line,
  method disclosure, limitation, null, or false-negative warning; or
- runtime implementation before September 8 without a new explicit authorization
  for a named production defect.

The implementation standard is not `everything still exists somewhere`. It is:
the next decision is fast to find, every visible claim names its authority, and
removing clutter never strengthens a claim by hiding its limitation.
