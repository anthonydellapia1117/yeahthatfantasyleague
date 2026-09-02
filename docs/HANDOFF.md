# YeahThatFantasyLeague - Full Handoff

**Written 2026-08-11 for a successor session. The research record below is
self-contained: read this plus `out/`, no chat history needed.**

Verifier: Anthony DellaPia. Draft is **2026-09-08**.

---

## LIVE BATON - update this block, last writer owns it

**THE CONVENTION: whoever writes last updates this block, in the same commit as
the work.** Not afterwards, not "when things settle". If this block disagrees with
`git log`, the block is wrong and the next agent has been misled.

| | |
|---|---|
| **Last touched** | 2026-09-02 by Codex - #79 is squash-merged at `c2a8931`; PR #80 is rebased behind it and documents the approved post-draft information architecture in `docs/APP_INFORMATION_ARCHITECTURE_SPEC.md`. #80 changes no runtime, model, artifact, navigation, build, or deployed byte. |
| **Next agent** | Preserve the runtime freeze until the 2026 draft is complete unless Anthony separately authorizes the named Big Board polling hotfix. After the draft, the four shipped correctness defects in the architecture spec are the first implementation unit, separate from reorganization. Then implement the three-section navigation, then the Draft Room competing-answer hierarchy. Do not touch #54. |
| **Branch** | PR #80, `codex/app-information-architecture-spec`; rebased documentation commits followed only by this resolved baton commit. #79's full battery remains recorded in item 27. #80's fresh-reader test recovered all ten governing decisions and its documentation diff check is clean. No runtime suite was invoked for #80 because executable, test, model, and artifact bytes are unchanged. |
| **Live site** | https://anthonydellapia1117.github.io/yeahthatfantasyleague - #79 is live from main `c2a8931`: Pages completed successfully, deployed `rxr.html` is byte-identical, drafted rows hide by default, and `Show drafted players` restores the same row struck through. PR #80 is repository documentation only and has no Pages byte to publish. |
| **Draft order** | SLEEPER CONFIRMED: Anthony is **slot 4**, roster 7, picks **4, 21, 28, 45, 52, 69, 76, 93, 100, 117, 124, 141, 148, 165**. Complete slot-to-roster permutation: `{1:10, 2:11, 3:1, 4:7, 5:6, 6:9, 7:3, 8:2, 9:8, 10:5, 11:4, 12:12}`. Both `draft_order` and `slot_to_roster_id` resolve slot 4 and `src/check_draft_order.py` reports agreement. |
| **Live draft geometry** | snake, 12 teams, 14 rounds, 60s pick timer, no third-round reversal - asserted by `src/preflight_draft.py` |
| **Live path** | PRE-DRAFT STATE VERIFIED against this league's real 12 teams / 60s / 1 flex and confirmed order for slot resolution, order provenance, gap strips, and history isolation. Same-page repaint is controlled no-reload coverage against the captured before/after payloads; no browser was demonstrably left open through the real publication moment. The only started-draft browser exercise remains the 2026-08-26 real Sleeper draft `1388575351239606272` at 19 teams / 120s / 2 flex. This league's actual started feed is **NOT** verified until September 8. See `AGENT_HANDOFF_SPEC.md` §11. |

### What was done in the last session

1. **#53 and #55 through #65 are merged; #65 is live.** #53 records the human
   live-path exercise and its limits. #55 fixed the round-7 VONA lookahead by
   comparing against real round 8 and published the reviewed N.1
   **INCONCLUSIVE** finding on `ff-hub.html`. #63 made the red paint and beep share
   one boundary, fixed BULLISH UTC provenance, replaced data-dependent collision
   assumptions with deterministic fixtures, corrected digest-mismatch diagnosis,
   and removed transient team-name assertions. #64 fixed the live `LA/LAR` joins;
   #65 completed the Unicode quote contract and added the repository-discovered
   output team-code guard. Its Pages deployment is 48/48 byte-identical and
   healthy. Do not confuse the unmerged BULLISH branch with a stale deploy.
2. **#58 consolidated player identity.** One Python comparison key plus the
   collision-aware identity resolver replaced fourteen Python definitions; four
   browser copies are held to Python by corpus parity. Replay survival pairs fell
   17,068 -> 16,949 by removing 119 erroneous replay player-pick pairs; Brier improved
   0.0745 -> 0.0710 and skill 0.1960 -> 0.2466. Sixteen current players recovered
   ADP fields. The known Leon Johnson wrong-era mapping remains logged and out of
   scope.
3. **#60-#62 hardened the 60-second room and seat resolution.** The clock is
   server-anchored; draft and picks fetch in parallel; the board cannot lag behind
   a fresh clock; a confirmed commissioner undo recovers visibly; freshness and
   amber/red/blink stages scale with `pick_timer`. #61 resolves the BULLISH overlay
   from a complete drawn-order permutation, preserves all twelve pre-draw windows,
   and fails loudly on unresolved drawn state. #62 removed the unsafe optional
   `teams=None` resolver interface. #63 made red paint and the urgent beep consume
   one `redStage` predicate.
4. **#56-#57 closed the daily dependency and same-day lineage gaps.** pages-data
   rebuilds every declared downstream consumer after shard refresh. Engine
   derivatives link by a canonical whole-payload SHA-256 rather than a date, and
   same-day mutation fixtures prove the guard bites. Strict artifacts fail closed;
   BULLISH/ceiling remain display-only and visibly stale during the intentional
   06:00-08:00 lag instead of burdening the draft-morning workflow with HISTORY.
5. **#64-#65 fixed team-code and player-quote contracts without rewriting
   provider shards.** One canonical Python helper maps `LA->LAR`, `JAC->JAX`,
   `WSH->WAS`, and `ARZ->ARI`; every changed Python consumer imports it. Matching
   browser boundary logic now lets the team and room pages join provider-native
   `LA` rows to canonical `LAR`. Before the fix, all six Rams on the CVS board had
   null team context and surrounding talent, the room omitted the Rams PROE chip,
   and `teams.html#t=LAR` fell back. Source-derived guards cover all four team-keyed
   shards and browser smoke exercises the LAR route. BULLISH tags and the engine/VOR
   payload are unchanged. U+2019 was already folded and the claimed Wan'Dale loss
   did not reproduce. Exhaustive
   committed-source inventory found ten real U+2019 player-name uses, zero U+02BC,
   U+00B4, or U+2018 uses, and zero U+0060 backticks embedded in a player name.
   Pre-#65 main nevertheless failed U+02BC and U+0060 comparison and split the
   U+00B4 search token. One pre-NFKD fold now covers ASCII plus U+2019, U+02BC,
   U+0060, U+00B4, and U+2018 in Python and JavaScript while exact-name collision
   evidence remains untouched. Walter's capture regex imports the same contract.
   A dynamic guard scans every committed output JSON/CSV, including scalar fields,
   code-keyed maps, and unlabelled pair domains; unknown codes fail while aliases
   and the explicit `FA` non-team state pass.
6. **The current branch makes BULLISH inputs honest before adding signal.** The
   percentile sweep found exactly one live contaminated population: absent 2025
   RB usage was coerced to observed zero. The discovery frame changed 50 entries
   to 46 observations; after #65's fresh engine moved Jonah Coleman outside the
   168-pick pool, the committed frame is 49 candidates = 46 observations + three
   explicit null exclusions. The upper-middle median is 0.5060, Jacory
   Croskey-Merritt and Tyler Allgeier move from criterion probability 0.75 to 0.50,
   and Bucky Irving's real 0-of-n inside-five result remains a legitimate zero.
   Every percentile now carries observation and exclusion accounting.
7. **The live TE gate is suspended, not cosmetically relabelled.** All 19 eligible
   veterans received the same 0.9 market-share value, so the advertised 2-of-2
   matrix was one varying on-field-dropback input times a constant. McBride,
   Warren, Pitts, Kelce, and Henry are omitted from live tags and retained in a
   top-level evidence ledger. All three tag surfaces render the same neutral
   suspension explanation. The ledger also records Isaiah Likely's 2025 Baltimore
   share being ranked alone in his 2026 Giants group. The historical TE extract is
   regenerated to 6,730 identified rows with no fake route alias or NA-subsetting
   junk; the still-dirty RB/WR R exports remain explicitly unconsumed.
8. **N.1 remains INCONCLUSIVE after the honest scope change.** RB/WR tags are 22/35
   (62.9%) versus 86/164 (52.4%), +10.4pp, 95% CI [-7.3, +28.2], p=0.261. Removing
   the non-discriminating TE criterion reduced the point estimate and widened the
   interval from 31.0pp to 35.5pp; it did not rescue the result. The approved
   verdict is artifact-backed on `ff-hub.html`, and all tags remain display-only.
9. **Forward Vegas is live only in the two approved consumers.** The builder reads
   the committed `schedule_2026.csv` snapshot, validates 272 regular-season games / 32 canonical teams
   / 17 games per team, verifies the home-spread sign independently, and derives
   the maximal contiguous fully priced horizon every build. Current scope is Weeks
   1-6, 93 games, 186 team-games; Week 7 is 7/14 priced. The top environments are
   LAR, DET, BAL, BUF, and SF. Gains are Brock Purdy and Jordan Love; losses are
   Caleb Williams, Jalen Hurts, Justin Herbert, Kyler Murray, and Trevor Lawrence;
   Mahomes promotes to BULLISH and Ja'Marr Chase demotes to WATCH. The replacement
   feeds only QB environment and WR opportunity. All ten RB tag records are
   object-identical in the same-build counterfactual because RB expected-TD equity
   remains on its separate Week-1 source. Daily pages-data now refreshes live
   `games.csv`, validates and atomically snapshots its 2026 rows before any
   consumer, and stages the snapshot plus metadata with every derivative. Current
   provenance is `UNCHANGED`, Weeks 1-6, 93 games / 186 team-games, pulled
   `2026-08-28T13:40:39+00:00`; raw source bytes moved but the decision-input digest
   did not. `HORIZON_EXTENDED`, `REPRICED`, `CONTRACTED`, and `UNCHANGED` are
   separately attributed; contraction fails before replacing either snapshot file.
   Home and Draft Room expose the current and last material event. A synthetic
   Week-7 completion fires `HORIZON_EXTENDED` at 93 -> 107 games / 186 -> 214
   team-games. The consumer independently rederives transition metadata, requires
   two finite canonical 32-team maps, keeps model-only movement out of the
   schedule-only delta, and rejects ambiguous mixed material frames.
   This is silent-staleness occurrence five and the first one found prospectively:
   the update path of a new feature was audited before that feature could freeze.
10. **Source-quality defects are recorded separately from app truth.** The
   lucky-player penalty reproduces from the contaminated all-week file but changes
   materially in the clean regular-season control. The R forward-Vegas export has
   the opposite sign in 224/224 team-games, while the app's existing Week-1 formula
   was already correct. Corrected R source also claimed an RB regeneration whose
   committed CSV still carries `target_volume` and 2,530 junk rows. Reproducible
   arithmetic, corrected source, and regenerated artifact bytes are three distinct
   claims.
11. **The RB historical-team denominator repair is isolated and attributable.**
   `usage_2025.json` now carries an untrimmed 161-row / 154-identity player-team
   carry ledger over all 32 teams and 12,399 carries, with REG+POST explicit. The
   exact nflverse parquet bytes and canonical ledger digest are pinned. The live
   population remains 46 observed + 3 honest nulls; p50/p75/p80 move from the
   retired current-roster frame's 0.5060/0.7342/0.7632 to
   0.5072/0.6538/0.6946. Forty-three RB inputs and 13 full gate scores move, but
   tag membership and status do not; Gibbs is the only displayed score change,
   84.0 to 69.0. The same-build attribution assigns 12 score moves to historical
   regrouping and three to replacing the trimmed/coalesced source with the
   untrimmed split ledger. All 16 non-RB tag records are object-identical in that
   counterfactual. Montgomery is on HOU in the current depth chart; his 158 carries
   correctly remain in DET's 2025 denominator.
12. **Full battery green on the RB branch.** The gate-runner self-test plus
   fourteen gated suites ran
   16/70/22/50/70/17/16/105/63/47/48/1211/23/366/38 checks (2,162 total).
   Every cache-backed analysis determinism check executed: 38 guards, zero skips.
   Browser smoke ran 365; `MATH DIFF PROOF: EMPTY` for all ten frozen function
   bodies. `src/preflight_draft.py` remains green at 12 teams / 60 seconds / one
   flex, but that is configuration validation, not a live drawn-order room test.
13. **Slot 4 is the one primary planning seat; all eleven alternatives remain
    references.** `data/draft_order_2026.json` records the complete externally
    reported order, exact snake picks, and the Sleeper-sourced start epoch
    (2026-09-08 20:00:25 ET). The engine, room, PATHS, VONA provenance, mock drafts,
    nav/countdown, doctrine, morning runbook, and operator docs consume that
    context. Main had no selected engine overlay seat while Sleeper was undrawn:
    its actual bad default was the room's pre-draft slot 7 render; PATHS defaulted
    to slot 1. #69 originally repeated the conflation by using roster id 7 as the
    printable sheet's slot; after #71 merged, the rebased page now consumes the
    shared engine `draft_order_context.primary_slot` and labels every non-primary
    selection as a reference. The engine uses 156 raw
    franchise-seasons from `out/positional_timing.csv`, byte-linked by SHA-256 and
    independently reconciled to `out/picks.csv`; history is displayed with n and
    never enters survival or a verdict. Slots 3 and 7 remain null rather than being
    guessed. The branch battery ran the gate-runner self-test, all fifteen gated
    suites at 114/0/22/51/70/17/16/105/63/173/48/1818/23/373/38 guards, all five
    deterministic analysis reruns with zero skips, browser smoke at 378 guards,
    and `MATH DIFF PROOF: EMPTY`. A final attribution audit caught the first
    BULLISH rebuild using a local Week-1 HISTORY file pulled 2026-08-28, older than
    main's 2026-08-30 input. The branch did not ship that mixed state: it refreshed
    HISTORY to 2026-08-31, resynced the forward schedule, rebuilt the full lineage,
    and reran the entire battery. The horizon stays Weeks 1-6 / 93 games and is
    honestly labelled `REPRICED`. Slot selection itself changes no player value or
    tag; the fresh-feed delta versus main is separately attributable (Kyren
    Williams WATCH -> BULLISH and Sam Darnold newly WATCH).
14. **The pick-4 model result is a narrow deterministic CMC lead; the owner
    decision is an external override.** Under the stated Gibbs/Bijan/Chase-gone board, paired complete
    4/21/28 policy simulation scores McCaffrey 290.75, Puka 288.67, and Jonathan
    Taylor 272.05. McCaffrey's nominal +2.08 over Puka is the deterministic
    ordering. The tree's 7.0 value is p25 of 71 current-tree strict-domination
    margins, not held-out player-action error, so it cannot establish equivalence
    or materiality. The documented survival-calibration sensitivity reverses the
    result to Puka +0.15, which establishes rank instability rather than a
    calibrated tie. Anthony will take Puka because CMC is age
    30, missed 13 of 34 games, carried 450 touches in 2025, and the league has
    zero IR slots. This is deliberately absent from generated decision cards and
    BULLISH data: it is an owner override after a narrow, uncalibrated model gap.
    If Puka is still not practicing by September 5, the override is withdrawn.
    The core board itself uses Sleeper's 2026 raw-stat projections scored under
    league-exact rules; 2025-on-2026 limitations describe auxiliary risk,
    ceiling, usage, archetype, and opportunity evidence.
15. **PATHS' empty result is a live false-negative, and #54 does not repair it.**
    The slot-4 tree has nine nodes and zero rendered forks, but it accepts neither
    an explicit unavailable-player state nor same-position player actions. Even
    after removing Gibbs/Bijan/Chase by hand it would render Puka alone: WR VONA
    45.83 versus RB 41.29, a 4.54 gap above a recomputed 3.58 epsilon. Zero forks
    therefore meant the player-level question was never asked, not that no
    decision existed. `docs/TURN_PLANNER_SPEC.md` now defines the approved
    offseason replacement: a 14-pick rail plus one player board, exact observed
    state, and a one-step Marginal Policy mark only for the next fully conditioned
    turn. VONA becomes an internal diagnostic, not an action generator.
16. **Puka-first leaves pick 21 unchanged and makes the second RB at 28 fully
    valuable.** A 100,000-state paired run (seed 20260831, Gibbs/Bijan/Chase gone,
    Puka forced, raw conditional survival, common uniforms) chose the same player
    at 21 as CMC-first in 99,997 states. Puka-path pick 21 was Bowers 40.337%,
    Chase Brown 24.889%, Derrick Henry 11.952%, Achane 8.429%, Kenneth Walker
    5.975%, and Nico Collins 3.813%; those six account for 95.395%. At 28 the
    position mix was WR 34.242%, RB 32.833%, TE 25.993%, QB 6.932%; Nico was the
    most frequent name at 23.500%, followed by Walker 10.321%, Henry 10.082%,
    Bowers 9.809%, McBride 8.713%, Javonte 7.652%, and Loveland 7.471%.
    Frequencies are availability descriptions, not priority: consume pick 21 and
    rerun `pick_marginal`. Puka + one RB leaves RB2 open, so a second RB receives
    full RB replacement value; CMC + RB prices a third RB against the higher FLEX
    baseline. An exploratory two-turn stochastic lookahead changed pick 21 in
    26.228% of states, mainly Bowers to a scarcer RB, and added 0.686 expected
    lineup points. No held-out player-action error interval exists, so that number
    cannot be labelled material, immaterial, tied, or separated. It is offseason
    redesign evidence, not a new draft-night verdict.
17. **The post-audit merge battery is green, including the coverage that first
    failed for environmental reasons.** The first analysis run correctly failed
    the gate at 33 guards plus five skips because no local HISTORY cache existed.
    `src/fetch_history.py` then populated all 59 files in an isolated `/tmp`
    cache; the rerun passed 38/38 with zero skips and all five determinism rebuilds.
    The full counts are gate-runner 16, then
    114/0/22/51/70/17/16/105/63/173/48/1818/23/373/38 across the fifteen gated
    suites including an empty mathdiff proof. Browser smoke passed 378 guards on
    the workflow-installed Chromium. No test or analysis run changed a committed
    artifact.
18. **The one-time order transition is now tested as a transition, not inferred
    from two fresh loads.** The real endpoint was captured twice before Rich
    entered the order: `pre_draft`, `draft_order: null`, exact identity
    `slot_to_roster_id`, and `picks: []`. Roster 3 appeared ownerless before
    publication, and this league's 2024 shell already demonstrates Sleeper's
    possible 11-user/12-roster shape. The real publication instead supplied a
    complete 12-user/12-roster mapping; keep the ownerless branch because it is
    correct rehearsal coverage for a state that can still occur.
    Pre-fix main rejected the realistic payload as `incomplete_draft_order`; the
    smoke then lost `#ohyp-card` to the blocked surface and exited 1. Independently,
    the pre-draft repaint was gated on a local hypothesis that cannot exist once
    the external report is committed, so an idealized confirmation could update
    the banner while leaving pending labels and a selected slot-7 reference.
    The repaired contract accepts a well-formed partial user order only beside a
    complete non-identity roster permutation, requires Anthony in both, and blocks
    disagreement. The same-page regression opens slot 7, transitions to the exact
    expected 11+12 payload via the public focus-return refresh, and proves slot 4,
    picks 4/21/28, confirmation provenance, all twelve reference chips, no clock,
    no conflict, no reload, and zero page errors. The full battery is gate-runner
    16 plus 120/0/22/51/70/17/16/105/63/173/48/1818/23/373/38 guards across the
    fifteen suites (2,937), analysis 38 with zero skips, browser smoke 385, and
    `MATH DIFF PROOF: EMPTY` for all ten frozen functions.
19. **Printable Sheet 4 is a qualified checkpoint ledger, not a draft forecast.**
    It reads `engine_2026.json.slots[primary_slot]`. At each owner pick that engine
    keeps players with at least 0.5 individual modeled survival, consumes its
    earlier listed anchors, and runs the shared marginal-lineup policy. It neither
    runs `mock_draft.py` nor samples opponent boards. Bijan's ADP 2.2 yields
    50.319% survival at pick 4, while Gibbs is 48.226%; that is why Bijan barely
    becomes the highest-VOR eligible anchor. Javonte's printed 69.0% is his
    individual survival to pick 28, not the frequency of the complete
    Bijan/Bowers/Javonte path and not the paired simulation's modal result. The
    old page stripped those qualifiers, called the path "Board expects," and
    called a VOR-sorted, non-marginal `fallback` "Next best." #72 prints the
    method boundary, exact availability, tier/injury/coin-flip cues, and live
    re-solve instruction; the unsolved fallback is omitted. A synthetic coin-flip
    browser fixture prevents the new guard from passing vacuously after ADP moves.
    A source-boundary audit found zero production use of Copilot/R analysis
    exports. The sole production path under `docs/ffopportunity/` is the
    machine-refreshed schedule snapshot, independently priced in Python and used
    only by display-only BULLISH QB environment and WR opportunity. It never
    enters VOR, survival, PATHS, the cheat selection, or the audited room verdict.
    Big Board and the additive room pick engine still carry their older explicit
    CVS/Walter layer and typed proxy coefficients; do not describe those complete
    surfaces as engine-only.
20. **#73 carries producer semantics and score provenance onto every affected
    surface.** The Sheet 4 defect was one under-specified producer contract across
    three renderers, not an isolated printable-page typo. Draft Room pre-draft
    cards and `decision_cards_2026.md` now call the sequence median-availability
    checkpoints, state that opponent boards are not simulated, scope instructions
    to the anchor path, and omit the raw `fallback`. The field remains in engine
    JSON as descriptive audit residue but no actionable renderer displays it. A
    payload-independent synthetic fixture injects that field into any primary row
    and proves both renderers ignore it. PATHS now says `rendered position-level
    forks`; zero output is explicitly not evidence that no player-level decision
    exists. Its artifact wording changed only in `why`: recursively removing that
    field makes the before/after trees identical, so #54's parked model is neither
    imported nor repaired here. The VONA spec and guard use the same bounded noun.

    The provenance follow-up required no layout or scoring restructure. Big Board
    puts `CONFIGURED CVS, NOT ENGINE VOR` beside its scores, names Walter ON plus
    the configured cap, and says factor weights remain when Walter is OFF; the old
    `pure model` claim is gone. Every 0-100 Draft Room grade carries `HEURISTIC
    GRADE - judgment weights, not backtested`; its title names VALUE 30, MARKET 30,
    URGENCY 20, NEED 12, SCARCITY 8, the 39/69 bands, and the limited role ordering
    only `Also consider`. The Pick Engine carries `HEURISTIC COMPOSITE`, PE weights
    NEED 12 / FLEX 6 / SCARCITY 8 / PLAYOFF 3, Walter state, and 10/4
    composite-margin cutoffs. `confidence` was itself too strong for that typed
    score gap and is gone from the band label. Neutral ink/line chips carry this
    provenance; no reserved verdict color was reused.
21. **#74 rebuilds every dependent after the real order publication and records
    the missing event edge.** Sleeper published a complete non-identity roster
    permutation and both order sources resolve Anthony as slot 4. The previous
    deployment was byte-correct and digest-coherent but stale about the mutable
    world state, because the draw watch could report the transition but nothing
    dispatched a rebuild. This is silent-staleness occurrence six. The smallest
    durable follow-up is an idempotent watch edge that dispatches the existing
    strict `draft-refresh.yml` only when live order status moves from unresolved
    to `agrees`; conflicts and unresolved states stay loud and never dispatch.

    The full strict plus HISTORY-dependent chain moved engine lineage and display
    provenance together. Slot-4 picks, VONA values, and mock decisions are
    unchanged. Slots 3 and 7 remain honestly unresolved across all 132 gap-seat
    observations: the actual 12/12 payload did not cause slot 3 to inherit Richie's
    history or slot 7 to inherit Mike Long's. That resilience came from keying
    opponent evidence to the reported history mapping instead of the live roster
    occupant, so an unforeseen payload shape was absorbed without contamination.
    Week 1-6 forward Vegas remains 93 priced games; one source refresh repriced
    four team values but produced zero BULLISH tag/status/score changes in the
    same-build counterfactual. Three live injury states moved. Browser smoke also
    caught and fixed a split-state repaint where a confirmed built artifact plus
    a placeholder first live response could mix pending and confirmed labels.
22. **Turn Planner is an approved offseason specification, not pre-draft work.**
    `docs/TURN_PLANNER_SPEC.md` replaces the earlier PATHS redesign outline with
    one persistent complete engine-VOR board and a 14-turn rail derived from the
    confirmed slot. Only the next Anthony decision with a validated league-pick
    prefix exactly `1..k-1` may receive a one-step Marginal Policy mark; future
    turns show marginal availability only. The canonical scorer must preserve the
    current rounded-gain/VOR/input-order contract and original-object return,
    replace `name|pos` state identity with Sleeper id, fail loud at cap/domain
    boundaries, and keep K/DEF outside the policy while preserving their separate
    feasibility fill. One coherent poller implementation is extracted from the
    room and instantiated once per page; cross-tab age differences remain visible.

    The action-uncertainty study is mandatory and is the 9-14 day effort's critical
    path. The VONA tree's 7.0 is p25 of 71 positive strict-domination margins from
    the current budget-conditioned position probe. It is not held-out error and
    cannot create a tie badge. If the historical corpus cannot support simultaneous
    leader-relative error intervals, the completed product publishes the reviewed
    honest null `ACTION UNCERTAINTY NOT CALIBRATED` and a deterministic order.
    PR #54 remains parked; VONA becomes internal. No phase begins before the draft
    is complete and real started-feed evidence is recorded.
23. **The Turn Planner source audit found a pre-existing calibration evidence-link
    defect; the live table did not change.** The lookup approved on 2026-08-19
    exactly matched that day's modern fit. #58 then repaired identity and rebuilt
    `survival_recalibration.json` from a 16,949-pair all-era frame; its 9,492-pair
    2019-2025 fit moves 15 of 20 bins by up to 0.0468. The engine correctly retained
    the explicitly approved constant pending reapproval, but its source comment and
    `MODEL.md` kept calling the mutable regenerated JSON the older table's full
    evidence. Separate guards prove both halves while never linking them. Freezing
    the model was deliberate; the false evidence link was not. Do not swap the
    table before the draft. Before Turn Planner availability work, preserve the
    adopted fit by digest, rerun/review corrected-identity evidence, and explicitly
    approve retention or replacement.
24. **The survival finding is one instance of a separate systemic dependency
    class.** An upstream correction can invalidate the evidence for a deliberately
    frozen downstream object even when that object correctly does not rebuild. This
    is not ordinary silent staleness: the accepted bytes remain intentionally fixed,
    while the claim supporting their approval moves. The repository-wide register
    in `docs/TURN_PLANNER_SPEC.md` §16 finds sixteen other dependency families,
    representing 32 accepted decisions, tables, or results. Seven have partial local
    checks, nine have none, and zero has complete immutable
    evidence-to-accepted-object lineage plus a mandatory re-review edge. Seven
    already show stale support or narrative; nine are latent.

    The material current divergence is analytical, not operational. After #58,
    actual-vs-ADP moved from +35.64, CI [+4.02, +69.44] to +23.08, CI
    [-0.44, +46.88], and replay-vs-ADP moved from +42.71, CI [+8.30, +76.89] to
    +28.92, CI [-7.18, +67.15]. Both intervals now cross zero. #77 corrects
    `MODEL.md` to the negative result: neither Anthony nor replay establishes an
    ADP advantage, and Anthony minus replay is -5.84, CI [-46.15, +33.20]. That
    analytical conclusion does not feed engine VOR, survival, the Cheat Sheet, or
    a draft-night verdict. The post-draft design is an evidence manifest that
    retains the frozen object and marks it `REVIEW REQUIRED` when its support
    digest moves; it must never auto-adopt a replacement. Do not build it before
    the draft.
25. **The 41 current-looking injury flags were one undated Sleeper field, not 41
    official designations.** `draft_board.py` copies only the season-projection
    row's nested `player.injury_status`; score, VOR and rank never consume it. The
    full 417-player engine snapshot contains 64 `Questionable`, 12 `IR`, three
    `PUP`, one `NA` and one `DNR`; the top-190 skill pool behind Anthony's count is
    39 `Questionable` plus one `NA` and one `IR`. The Cheat Sheet then had a second
    display defect: CSS rewrote every truthy status it rendered as `Q`. Current
    committed values match the live player payload for all 417 rows, recent generic
    `news_updated` timestamps and 2026 rookies refute universal untouched-2025
    carryover, but Sleeper exposes no injury-specific effective date/week or
    official-vs-camp discriminator. Retained 2025 draft payloads show the preseason
    population falling from 205/1,271 Questionable skill picks on Aug 20-26 UTC to
    72/1,029 on Sep 3-4 UTC (Sep 2-3 Eastern, before the opener). Exact 15-draft
    ids, counting rule and the absence of a committed immutable snapshot are in
    `docs/SELF_AUDIT_2026-08-26.md` entry #60. #77 preserves every raw status and
    all math, adds source/snapshot/scope on every surface, and pins non-Q rendering
    plus the live-room badge in smoke. Existing display-only BULLISH categorical
    injury handling is disclosed and unchanged.
26. **#78 is the bounded RxR Prep implementation, not the completed live Turn
    Planner.** Anthony explicitly superseded the pre-draft implementation freeze
    for this one surface on 2026-09-01. RxR derives the slot-4 rail and all 417
    rows from the engine, preserves engine-VOR order, records a complete manual or
    labelled ADP-chalk 12-team prefix, and runs the canonical one-step Marginal
    Policy only when that prefix reaches Anthony's next turn. Every row remains
    available in VOR order; #79 hides drafted rows by default and restores their
    struck-through audit treatment on demand. K/DEF are labelled unscored floors.
    The page carries `NOT A FORECAST`, `ONE STEP`, and `ACTION UNCERTAINTY NOT
    CALIBRATED` on its face. No future survival, tie, confidence, VONA, BULLISH,
    CVS/Walter, opponent-history probability or owner preference enters the mark.

    `forward_policy.score_candidates` is Python-canonical, keys all action state
    by Sleeper id, preserves the existing rounded-gain/VOR/input-order law, and
    fails on duplicate/overlapping ids, invalid domains, nonnumeric inputs and
    incomplete caps. The JavaScript mirror must exactly reproduce a 12-case
    engine-bound corpus plus six error cases; a stale corpus digest blocks the
    page. Draft-refresh rebuilds it immediately after the engine. A saved browser
    scenario is likewise engine-digest-bound and is removed when inputs move.

    On the current deterministic scenario, Gibbs/Bijan/Chase produce McCaffrey as
    the pick-4 one-step leader; choosing Puka and filling through pick 20 produces
    Bowers at 21; choosing Bowers and filling through pick 27 produces Javonte at
    28. These names are a reconstructable scenario, not an optimal-path claim.
    PATHS remains deployed for audit but is removed from public navigation; #54
    stays parked. Pre-merge visual review caught two walls before publication: the
    first mobile build was 31,623 px, and the 641-900px breakpoint later expanded
    to 26,018-31,192 px. Final pick-state ranges are 2.22-2.24 desktop screens,
    3.74-3.97 mobile screens, 2.55 at 768px and 2.65 at 900px, with the complete
    board inside an internal scroller and guards at every breakpoint.
27. **#79 changes only RxR drafted-row visibility.** The default unchecked state
    hides every drafted player while keeping all 417 rows in the DOM and their
    exact engine-VOR order; therefore the first visible row advances automatically
    to the best undrafted player. `Show drafted players` restores those same rows
    in place with the existing opacity and line-through audit treatment. The
    browser guard records Gibbs, Bijan, Chase and Puka, proves Puka hides and the
    next engine-VOR player rises to the top, restores Puka visibly struck through,
    hides it again, and then completes the conditioned pick-21/pick-28 path.
28. **PR #80 freezes the post-draft application architecture without changing the
    build.** The eight navigated pages become three user jobs with sticky
    cross-document sub-tabs: DRAFT (Live Room / RxR Prep / Print), BOARD (CVS
    Board / Player / Team), and EVIDENCE (Data Health / Findings). Separate HTML
    files remain intentional failure boundaries; Draft Room's poller may not share
    runtime fate with the printable sheet. PATHS remains a directly reachable but
    unlinked audit renderer and never returns to public navigation. Alternate slots
    remain available through a collapsed, visibly labelled Print reference path and
    an optional Draft Room diagnostics drawer; RxR stays on the reconciled primary
    slot.

    The central Draft Room repair is the competing-answer hierarchy: canonical
    marginal action, neutral engine-VOR board leader, numeric wait cost plus
    same-producer alternatives, then configured CVS/grade/history diagnostics
    behind details. Four shipped wrong-answer defects are explicitly a separate
    first PR after the draft: Big Board rookie classification, Players search
    truncation, Big Board's silent live-availability poll failure, and Home's
    fabricated noon timestamp. Read-only routed-failure testing proved the Big
    Board can show a drafted player as available without a warning. Preserve the
    freeze if Big Board is treated as reference-only; a pre-draft repair requires
    Anthony's explicit authorization for that defect alone.

### In flight / nothing blocked

Main is `c2a8931`; #79 is merged. PR #80 is rebased behind it and is the
documentation-only architecture freeze. #80 does not authorize the full live Turn
Planner or architecture implementation. All existing numeric artifacts remain
unchanged by #80. The real confirmed pre-draft endpoint is observed;
same-page repaint is regression-tested against the exact captured before/after
payloads. The actual started feed remains unverified. PR #54 remains OPEN, PARKED
THROUGH THE DRAFT, and untouched at remote head `4bd541e`; its
mergeability is unresolved against moving `main`. Its PATHS policy is still the
data-derived R1-2 / R3-4 / R5-7 coverage-valid bands with the conditional spread
floor, but its Pareto action space remains one action per position and cannot
answer the actual pick-4 question. Do not rebase, resolve, or merge it for this
draft. The separately specified draw-watch-to-rebuild edge is logged only and needs
separate approval regardless of date.

Post-draft backlog begins with the four independent shipped correctness defects in
`docs/APP_INFORMATION_ARCHITECTURE_SPEC.md`, then the approved three-section page
reorganization and Draft Room competing-answer hierarchy. The broader backlog also
includes the full live RxR Turn Planner with coherent Sleeper
polling and held-out action-uncertainty calibration, the frozen-evidence manifest and explicit review of its
seven current divergences, the three unenumerated `ALL_R_CODE` mislabels
(`route_participation_proxy`, `team_implied_total`, `prior_epa_proxy`), vacated-carries
assessment with the rookie gap handled jointly with `adj_vac`, team supply as
shadow/display only, the Turn Planner, and the adopted-survival evidence decision.
Do not consume unreviewed local R exports.

### The three things the next agent most needs to know

1. **RxR Prep is a bounded exception, not a waiver of the stable-build freeze.**
   Anthony explicitly authorized the scenario-only subset on September 1. Live
   polling, future-turn recommendations, survival, a tie band, uncertainty
   calibration, the draw-watch dispatch, the remaining R audit, vacated carries,
   and team supply all still wait until after the draft and separate authorization
   where stated. #54 stays parked.
2. **The browser-to-Sleeper live path is still only partially verified.** This
   league's real pre-draft 12-team / 60-second / 1-flex payload now verifies the
   confirmed seat, order provenance, and opponent-history isolation. Same-page
   repaint is controlled no-reload coverage against the exact captured before and
   after payloads, not evidence that a browser stayed open through publication.
   Anthony's only started-draft exercise remains the real 19-team Sleeper draft
   (`1388575351239606272`) on 2026-08-26 at 120 seconds / 2 flex. Real
   `last_picked`, pick-cache timing, audio, wake lock, background-tab behavior, and
   recovery on this league cannot be tested before the draft starts. Automated
   smoke is hermetic. Do not promote pre-draft confirmation into started-feed
   evidence.
3. **The adopted survival table is frozen, and its evidence-link problem is
   systemic.**
   Retaining the approved values pending reapproval appears deliberate. The current
   regenerated proposal is not their immutable evidence and cannot supply their
   future bin counts or Wilson intervals. Sixteen other frozen/review-approved
   families have the same dependency shape; none has complete evidence-to-approval
   detection, and seven already have stale support or narrative. Resolve them by
   explicit post-draft review, not an incidental feature diff or automatic rebuild.
   Separately, PII is out of HEAD but still in git history; retention is Anthony's
   call after the draft.

---

---

## THE HEADLINE, and it contradicts the brief

**There is no draft-day roadmap. Every draft-day hypothesis tested is null.**

That is not a failure to find one. It is a finding, on 156 franchise-seasons and 13 champions, and it is the single most valuable thing in this document because it stops the successor spending days looking for a pattern that is not there.

| Hypothesis | Result | Verdict |
|---|---|---|
| Champions draft a distinctive rounds 1-5 archetype | No sequence reaches n=5. Max n=7 | **Underpowered, untestable** |
| Champions wait on QB | 6.46 vs 5.92, permutation **p=0.252** | **Folklore** |
| Champions avoid QB in rounds 1-5 | 62% vs 48%, permutation **p=0.266** | **Folklore** |
| Champions load RB early | 2.15 vs 2.01 RB in rounds 1-5 | **Noise** |
| Champions load WR early | 2.00 vs 2.03 WR | **Noise** |
| Draft slot matters | Champions spread 2,2,4,5,5,5,8,10,10,11,12,12,12. Mean 7.5 vs 6.5 expected | **No pattern** |
| Draft-day composition predicts finish | corr RB -0.013, WR -0.049, QB +0.110 | **All ~zero** |
| Drafted-vs-acquired share predicts winning | corr champion +0.043, rank -0.101 | **Dead** |
| Champions draft the consensus #1 player | **0 of 13.** But p=0.323 under random | **Striking, not significant** |

## THE FAAB SIGNAL IS ALSO DEAD

Tested 2026-08-11. **Permutation p = 0.197**, n=118 franchise-seasons 2016-2025, 10 champions, 50,000 shuffles. Champions mean bid 46.8 versus pool 35.7. Max single bid: champions 91.4 versus pool 91.2, p=0.465.

**Not significant. Do not build on it.**

## THE STRONGEST SURVIVING CANDIDATE, and it is marginal

**Lineup efficiency: started points as a percentage of optimal.**

| | Champions | Field | p |
|---|---|---|---|
| Lineup efficiency | **89.75%** | 88.44% | **0.078** |

One canonical test: `src/phase3_lineup.py`, 50,000 shuffles, seed 20260811, n=156 franchise-seasons and 13 champions, written to `out/efficiency_test.json` and read by the dashboard rather than recomputed. Quote it as 0.078 - a fourth digit implies precision a 50,000-shuffle test does not have.

**An earlier draft reported 89.96 / 88.68 / p=0.0697; that figure is stale and does not reproduce.** All efficiency percentages in this document are ratio-of-sums, the standardized basis per the accepted 3B audit.

Closest to significance of anything tested and still above 0.05 at n=13. Direction is consistent and the mechanism is plausible, which is more than any draft-day hypothesis managed. Treat as a lead, not a finding.

**Per-franchise, and this is the personally actionable part:**

| Franchise | Efficiency | Pts left/wk | Per season | Titles |
|---|---|---|---|---|
| John Juliano | 90.41% | 12.47 | 175 | 0 |
| **Phil Baldino** | **89.97%** | **13.65** | **191** | **3** |
| **Cambrias** | **89.67%** | **14.40** | **202** | **3** |
| Frank & Julian | 89.24% | 13.72 | 192 | 0 |
| Mike Long | 88.82% | 14.12 | 198 | 0 |
| Ronnie | 88.77% | 14.90 | 209 | 2 |
| **Antdell & Ernie** | **88.55%** | **15.14** | **212** | **0** |
| Nolan & Vinny | 88.53% | 15.22 | 213 | 0 |
| Pung & Tralie | 88.47% | 15.08 | 211 | 0 |
| Team JoeBa | 88.46% | 14.73 | 206 | 0 |
| Richie | 88.43% | 15.24 | 213 | 1 |
| Chris & Dom | 88.14% | 16.35 | 229 | 2 |
| LFTLR | 87.71% | 15.40 | 216 | 0 |
| Rob & GregBo | 87.42% | 16.72 | 234 | 1 |
| GaTTa | 85.33% | 19.54 | 274 | 1 |

Ratio-of-sums per `src/phase3_lineup.py`. Anthony ranks **7th of 15 by efficiency, 9th of 15 by points left per week**. An earlier draft said 11th of 15; that does not reproduce under either ranking. Both three-time champions sit above him either way.

**Positional decomposition of the gap to Baldino (phase 3A): RB is 80 percent of it.** RB capture 86.9 percent versus his 90.7. QB is a strength, not a leak: 93.5 percent capture versus his 89.6, worth 1.06 pts/wk in Anthony's favour. The raw "WR is the biggest leak" reading is an artifact of WR carrying the most starter slots.

**Gap to Baldino: 1.49 points per week, 21 points per season. The 2025 championship was lost by 12.44.**

That is not proof of causation, and Chris & Dom won twice at 88.21% while John Juliano leads the league with zero titles. But it is the only lever found in this entire project that is measurable, controllable, and larger than the margin that actually beat him.

---

## PART 1 - SETTLED. Do not re-derive.

### The league
12 teams, snake, full PPR, 13 completed seasons 2013-2025. Yahoo 2013-2024, Sleeper 2025-2026.
2026 league `1389378429505241088`, draft `1389378429505241089`. Sleeper's complete
non-identity order map confirms Anthony at **slot 4**; `draft_order` and
`slot_to_roster_id` agree.
Anthony is roster 7 "Taylor Made", co-owner ernie706.
2026 scoring: `rec 1.0, pass_td 6.0, pass_yd 0.04, pass_int -1.0, rush_td 6, rec_td 6, fum_lost -2.0`.
Starters `QB RB RB WR WR TE FLEX K DEF` + 5 bench.
**EXCLUDE** Sleeper `1092592577628426240`: empty trial shell, 0 picks, 0 transactions.

### Champions, all 13 verified
2013 Ronnie | 2014 GaTTa | 2015 Chris & Dom | 2016 Chris & Dom | 2017 Richie | 2018 Phil Baldino | 2019 Cambrias | 2020 Ronnie | 2021 Rob & GregBo | 2022 Cambrias | 2023 Phil Baldino | 2024 Phil Baldino | 2025 Cambrias

Titles: **Cambrias 3, Phil Baldino 3**, Chris & Dom 2, Ronnie 2, Richie 1, Rob & GregBo 1, GaTTa 1.
**Antdell & Ernie: 0 in 13 seasons.** Runner-up 2025, lost by 12.44.

### Every champion's rounds 1-5 sequence
```
2013 Ronnie        QB WR RB RB WR      2020 Ronnie        RB RB QB WR WR
2014 GaTTa         TE WR TE WR RB      2021 Rob & GregBo  WR RB QB WR RB
2015 Chris & Dom   WR TE RB QB RB      2022 Cambrias      RB RB WR RB RB
2016 Chris & Dom   WR WR WR RB TE      2023 Phil Baldino  WR RB RB RB WR
2017 Richie        WR RB RB WR WR      2024 Phil Baldino  WR RB WR QB TE
2018 Phil Baldino  RB WR RB WR RB      2025 Cambrias      RB RB TE RB WR
2019 Cambrias      RB WR RB WR WR
```
**No two are the same.** That is the point.

### The #1 board player, every season
| Yr | #1 on board | Pos | Drafted by | Champion took him |
|---|---|---|---|---|
| 2013 | Jamaal Charles | RB | Team JoeBa | no |
| 2014 | LeSean McCoy | RB | Cambrias | no |
| 2015 | Antonio Brown | WR | LFTLR | no |
| 2016 | Antonio Brown | WR | Antdell & Ernie | no |
| 2017 | David Johnson | RB | LFTLR | no |
| 2018 | Todd Gurley | RB | Frank & Julian | no |
| 2019 | Saquon Barkley | RB | Frank & Julian | no |
| 2020 | Christian McCaffrey | RB | Team JoeBa | no |
| 2021 | Christian McCaffrey | RB | Nolan & Vinny | no |
| 2022 | Jonathan Taylor | RB | Rob & GregBo | no |
| 2023 | Justin Jefferson | WR | Chris & Dom | no |
| 2024 | Christian McCaffrey | RB | John Juliano | no |
| 2025 | Ja'Marr Chase | WR | Richie | no |

9 RB years, 4 WR years, **0 for 13**. Expected 32% of the time by chance. Report it as descriptive colour, never as a rule.

### Franchise versus person - critical
The archive labels franchises with **current** names applied retroactively. `member_name` is a continuity key, **not** who managed that season. `out/franchise_eras.csv` has 20 eras / 15 franchises.

| Franchise | Split | Kind | Treatment |
|---|---|---|---|
| Richie | 2021: Lefty & Long (Nolfi + Mike Long) to Nolfi solo | behavioural | **split** |
| Rob & GregBo | 2015: Rob solo to Rob + Gregory DellaPia | behavioural | **split** |
| Nolan & Vinny | 2017: Nolan solo to Nolan + Vincent Gatta | behavioural | **split** |
| Antdell & Ernie | 2015: Three Amigos (3) to Two Amigos (2) | behavioural | **split** |
| Ronnie | 2024: Harry joined, **silent partner** | nominal | **pool** |

Effective Phase 4 unit count: **19, not 20**.

Three champions invisible at franchise level: **Vincent Gatta** won 2014, now drafts for Nolan & Vinny. **Mike Long** shares the 2017 title, his solo franchise shows 0. **Gregory DellaPia** left Antdell & Ernie in 2015 and won 2021 with Rob & GregBo.

### Verified data
2,339 picks 2013-2025, 12 franchises every season, no survivorship gaps. 37,106 weekly roster rows with `started`/`points`. 3,938 transactions 2014-2025; 2013 has none. **52 assertions pass, 0 fail.** 2025 archive draft reconciles to Sleeper **168 of 168**. Identity map **12 of 12** verified by overall-pick join, zero name similarity used. 2018 overall pick 38 is a **forfeit** under rule 3.2's 2-minute clock, not a gap.

### Phase 2 result
**League-wide DRAFTED share of starter points: 68.9%.** Range 60.2 to 76.2. Basis: 2014-2025, the twelve seasons with transaction data (G-003 excludes 2013 from the acquisition split).
**It does not predict winning.** Cambrias 64.9% with 3 titles. Antdell & Ernie 64.5% with **0**. Rob & GregBo 82.4%, highest in league, 1 title.

### Two champions, two mechanisms
| | Actual W% | All-play W% | Gap | Drafted share | Titles |
|---|---|---|---|---|---|
| Cambrias | .606 | .606 | **0.000** | 64.9 | 3 |
| Phil Baldino | .596 | .563 | **+.033** | 72.3 | 3 |
| Antdell & Ernie | .484 | .489 | -.005 | 64.5 | **0** |

Cambria wins on raw strength. Baldino outperforms his all-play. **Anthony has not been unlucky.** Baldino also has the better rate: 3 in 9 seasons vs 3 in 13.

---

## PART 2 - DEAD ENDS. Cost real time. Do not repeat.

1. **Yahoo Fantasy API is CLOSED.** Fantasy Sports scope no longer exists in Yahoo's developer console. A valid OAuth token returns `oauth_problem="additional_authorization_required"`. Verified on two apps, screenshot-confirmed. No Python wrapper routes around it. Yahoo now requires written application and review.
2. **The 5% bonus gap is ACCEPTED.** Six 40-yard long-play bonuses, Yahoo 2013-2024 only, 6.14 pts/team-week, present in team totals, absent from per-player rows. Flips 47 of 1,128 games (4.17%). The Phase 2 ratio is unaffected - both sides bonus-exclusive. Owner confirmed these were a **deliberate rule change to raise difficulty**. Keep as a product idea for a rules-evolution feature; not an analysis blocker.
3. **Rule 3.3 (draft order = reverse prior finish) is NOT FOLLOWED.** 17 of 141 slot assignments match, 12.1% vs 8.3% random. Slot is unpredictable until it posts.
4. **Browser scraping Yahoo works but rate-limits** at ~50 fetches with HTTP 999.
5. **Quarantined fields**, no traceable derivation: `value`, `adp_consensus_score`, `adp_differential_pct`, `risk_tolerance`, and LeagueLegacy's `scoring_format` (says half-ppr for all 14 seasons; Sleeper says `rec=1.0` full PPR).
6. **`adp_effective_pick` is NULL on all 2,339 rows.** ADP is recoverable only as `overall_pick - adp_differential`, valid on 2,039 of 2,339.

---

## PART 3 - REMAINING WORK

**A. Significance-test the FAAB finding.** 46.8 vs 34.7 is the only live signal. Permutation test it. If it holds, it is the answer to "what do champions do."

**B. In-season, not draft-day.** Every draft-day door is closed. Look at: waiver timing (early-week vs late), start-sit accuracy versus `is_optimal`, points-left-on-bench, and streaming behaviour at QB/TE/DEF.

**C. Cambria vs Baldino.** They win differently. Cambria 35.0 tx/season, Anthony 36.2 - **near-identical volume, opposite outcomes**. Volume is not it. Test bid size, timing, and target quality.

**D. Anthony's actual leak.** Not draft position, not drafted share, not luck. Candidates: start-sit, FAAB sizing, roster construction late.

**E. Phase 5 simulator.** Slot 4 is primary after the confirmed draw; the other 11
slots remain references. Survival probability, run probability, opportunity cost,
per-slot decision cards.

---

## PART 4 - FILES

| Path | Contents |
|---|---|
| `out/picks.csv` | 2,339 picks, all seasons |
| `out/pick_value.csv` | picks joined to realized starter production, VOR, vs-expected, hit/bust |
| `out/drafted_vs_acquired.csv` | 156 franchise-seasons, the central number |
| `out/champions.csv` | 13 seasons |
| `out/franchises.csv` | 15 franchises, spans, titles, active |
| `out/franchise_eras.csv` | 20 eras, people, titles, confidence |
| `out/franchise_lineage.md` | person-vs-franchise reasoning, era rules |
| `out/identity_map.csv` | 12 of 12 verified mappings |
| `out/assertions.csv` | 52 checks, 0 failures |
| `out/gap_register.md` | G1-G7, open and closed |
| `out/gap_report_2026-08-11.md` | 18 confirmed gaps, scrape list |
| `src/ingest.py` | Phase 1, re-runnable |
| `src/phase2_value.py` | Phase 2, re-runnable |

Sources: `made-resources/YeahThatFantasyLeague_LeagueLegacy_Archive_2013-2026/` (71 files) and `LeagueLegacy-io/leaguelegacy_YeahThatFantasyLeague_full_export/` (33 files). Archive A wins for picks and weekly rosters; export B wins for transaction items.

---

## CONSTRAINTS

Never backfill a pick, roster, transaction, or result. Never merge manager identities on name similarity. Every derived table carries source, source_ref, fetched_at, confidence. Every 2013-2024 figure carries the bonus-exclusive basis note. Hyphens only, no em dashes, no emojis. Tables over bullets. Lead with the answer. Report confidence and sample size beside every claim.

**With 13 champions, most comparisons will not reach significance. That has already proven true for every draft-day hypothesis. Do not manufacture a clean recipe to satisfy the framing of a question.**


## Draft Room v2 - shipped 2026-08-12

Live app: https://anthonydellapia1117.github.io/yeahthatfantasyleague/out/draft_room.html
(local `out/draft_room.html` is the offline fallback; same embedded model).
Six gated phases per docs/DRAFT_ROOM_BUILD_ORDER.md: broadcast-grade design
system, live pick-clock mode (duration from draft settings), sixteen features (roster-need-aware
recommendation first), the quarantined league-mate simulator, GitHub Pages
deployment via the gh-pages workflow, and this review. Draft-morning production
uses the mapped, gated `.github/workflows/draft-refresh.yml` chain in
`docs/DRAFT_MORNING.md`; an engine-only commit is invalid.
The survival math is frozen: 41 Python guards + 350 browser guards, including 42
JS parity anchors, plus the calibration benchmark gate every merge.

## Draft-day features + conviction overlay - shipped 2026-08-13

Four draft-day surfaces on top of v2, math untouched (the five survival
functions are byte-identical to the pre-feature main; the diff proof runs at
every merge):

- Pick grade: 0-100 gear beside the live answer. Presentation, not decision -
  named weights in code (GRADE_W), three bands carry the message (red 0-39
  not at this price, amber 40-69 defensible, green 70-100 take him). Guard 9
  proves the grade reads no banned field and no verdict reads the grade;
  six pinned anchors including the monotone Dak curve gate every merge.
  Evidence chips (play-caller REPORTED + date, team PROE, FFC band) sit
  beside the gear and never enter the number.
- Recommendations panel: on WAIT or COIN FLIP, 2 alternatives by default
  (toggle 3/4/5, search appends one, max 6), each with its own gear.
- Draft grid: 12 team columns x 14 rounds, position-coded, live feed.
- Value board: overall top 50/100 + positional top 5/10/20 with FLEX and
  DST, drafted auto-remove/grey-out toggle, K/DST floor labels.

Conviction overlay (Expansion Phase B): `data/my_board.csv` - schema and the
pre-registered scoring rule live in the file header. The engine applies it
AFTER build_model as a pure transform (apply_overlay): YOUR CALL chips beside
model VOR on every surface, survival of each bull to every slot's picks plus the
Sleeper-confirmed slot-4 primary when the board is populated, within-tier resort
on positional panels (display),
and its ONE decision role - the coin-flip tie-break toward bulls. The model
primary is always the wait-or-reach subject; guard 10 (10 checks) proves the
overlay reaches no other arithmetic and that an empty board is byte-identical
to no overlay. The shipped board is empty - populate it with your calls and
regenerate.

## Expansion Phases C-E - shipped 2026-08-13

Three shard-fed pages beside the draft room, all on the same design system,
all with tap-any-number provenance (tap a number, see its shard, field,
source, and fetch time):

- out/players.html - hash-routed player pages: value vs market with the FFC
  band and attribution, literal 2025 nflverse usage columns, draft capital,
  YOUR CALL block, K/DST floor labels. Absent blocks (combine, snap share,
  EPA, xFP, routes) are declared absent, never estimated.
- out/teams.html - all 32 teams: curated play-caller card (19 confirmed
  rows; uncurated teams say so), PROE with its measurement basis, vacated
  opportunity (departed vs arrivals with the computation note), depth chart
  ranked by value with the official slot as metadata.
- out/home.html - the action board: draft countdown from the payload, data
  staleness board, overlay completeness, attributed trending adds, the one
  history fact (consensus #1, 0-for-13, p=0.323 - colour, not strategy),
  links to every surface.

Guards: test_pages_data.py sections 10-12 resolve every on-page number
reference against the committed shard fields and assert every honesty label.
Smoke scenarios 10-12 run the pages on a hermetic local server. N1 stands:
the engine reads nothing from this layer.

## App shell - shipped 2026-08-13

out/nav.js is the single chrome source: the fixed bar (gold hairline, YTFL
HUB wordmark, countdown/LIVE pill reusing the draft room's own state, mobile
drawer), the kicker header style, and the phase 3 polish (opt-in reveals and
border-lift hovers, reduced-motion aware). All five pages share the #0b1120
dark family, an 1100px container, and the same header treatment; semantic
verdict colors are guard-asserted unmoved. The draft room include sits
outside the ENGINE-DATA sentinels (regeneration verified byte-identical), the
bar collapses to 36px in live mode, and a smoke guard keeps the answer, gear,
and verdict above the fold at 390px. Guards: test_pages_data sections 13-15;
smoke scenario 13.

## Big Board - shipped 2026-08-13

out/big_board.html - the pre-draft master list. The rank is VOR and nothing
else (the guard asserts the sort expression in code); tiers render as cliff
breaks under the position filters. Every factor Anthony asked for sits on the
row as a LABELLED evidence chip with tap-provenance - market band and bye
(FFC), 2025 workload (nflverse), depth slot (ESPN), play-caller with its
source tag, PROE - and the factor ledger at the top states where each factor
lives: decision input (VOR, survival timing), displayed evidence (coaching,
team context - N1, rejected as probability input p=0.99), or not wired on
purpose (schedule/competition - no stamped source, SOS approximations on the
reject list). No hidden composite, ever. Guards: pages-data section 11b; smoke
scenario 15 (on-screen order proven equal to payload VOR order).
