# Agent handoff spec

**For the next agent working this repository. Written 2026-08-26, twelve days
before the draft, by the Claude session that built most of it, at Anthony's
direction, because everything load-bearing that lives only in a context window
dies when that window closes.**

Read sections 1 and 2 before touching anything. The module map is section 6 and
it is the least important part of this document.

---

## 1. THE THREE FAILURE MODES YOU ARE INHERITING

These are not general advice. They are the mechanisms behind the defects that
actually reached this project's live site, derived in `docs/SELF_AUDIT_2026-08-26.md`
from all 39 known defects. An outside reviewer found fourteen of them, including
four of the five that shipped and stayed. This section is why.

### 1.1 "I verify against my own intent rather than the source of truth"

The pick clock shipped hardcoded to 120 seconds against a draft whose
`settings.pick_timer` is 60. Tests were written. They passed. They tested that a
two-minute countdown counted down correctly from two minutes. What was never done
was `GET /v1/draft/{id}` and read the field.

The same mechanism produced the freshness defect (verified the fetch *resolved*,
not that the payload was *fresh* - a shared cache served 118-second-old picks) and
the cron defect (verified the workflow *existed*, not that it had *succeeded* -
8 of 14 scheduled runs had failed, the last four consecutively, while the live
site served four-day-old data).

**The rule this generates:** when a value is knowable from a server, a file, or a
computation, a test that asserts your code handles that value correctly is not
evidence the value is right. Go read it from the source. `src/preflight_draft.py`
exists because the audit predicted this shape would recur and then found it -
nothing read `draft.type` or `settings.reversal_round`, and the snake math was
correct only because today's settings happen to match the assumption.

### 1.2 "I do not read my own output as evidence"

The VONA artifact shipped with 57 of 204 branch nodes carrying **negative VONA** -
a mathematical impossibility, printed in the file, in a field named `vona`. That
file was generated here, guards were written for its provenance block and its
thresholds, and `min(n["vona"] for n in nodes)` was never once run.

**The rule this generates:** after generating any artifact, interrogate its
*values*, not just its *schema*. Ask what is impossible in this data and check for
it. Guards that assert a key exists are the weakest kind - `test_mock.py` asserted
`engine_generated` existed and never that it matched, for weeks.

### 1.3 "I accept a specification as a substitute for verification"

"Two minutes" came from the build order. `TEAMS = 12` came from knowing the
league. The step-function sd bands came from an earlier session. In each case a
number entered the system as an assertion by an author, and no step ever asked
reality whether it was still true. The outside reviewer's structural advantage was
having no memory of the specification, so the only available reference was the
world.

**The rule this generates:** treat every number that arrived from a document -
including this one - as a claim with an owner and a date, not as a fact. If you
cannot name the computation or the API field behind a number, it is unverified.

### 1.4 The corollary that ties them together

Sixteen of the 39 defects were **silent** - the system looked healthy and was
wrong - and the silent set contains **every defect that reached the live site and
stayed**. Loud failures were always caught within hours and none ever reached
Anthony. This project does not have a bug-finding problem; it has a silence
problem.

**So: for every feature you add, ask "how would this look if it were broken?" If
the answer is "the same", that is a defect in the feature, not a monitoring gap.**
Fix it before you ship the feature.

---

## 2. WHAT THIS IS

A single-owner, single-league fantasy football draft assistant for a 12-team,
14-round, full-PPR, **6-point passing TD** Sleeper league, drafting **2026-09-08**.
Owner and only user: Anthony DellaPia (Sleeper user `345197760305307648`, roster
7, franchise "Antdell & Ernie", league `1389378429505241088`, draft
`1389378429505241089`).

It is a static site - HTML with embedded JSON payloads, deployed to GitHub Pages,
no server, no database, no build step. Python scripts compute artifacts into
`out/`; the pages read them. **The live site IS the build**: every ship ends with
a byte-comparison of the deployed files against the repo.

Seven surfaces, all in `out/`: `home.html` (hub), `big_board.html`,
`players.html`, `teams.html`, `draft_room.html` (the draft-night surface),
`paths.html` (the VONA decision tree), `ff-hub.html` (the retrospective dashboard
for the 2013-2025 history analysis).

### What it deliberately does NOT do

- **It does not pick for you.** It grades, ranks, and shows expected values. The
  final call is Anthony's, always.
- **It does not simulate championship odds.** The pick engine's objective is a
  *stated proxy* - points over replacement tilted toward the weeks 15-17 schedule -
  and the card says so on its face.
- **It does not let display features touch decisions.** The BULLISH tag, the
  signal encoding, opponent tendencies, and team names are all display-only, and
  guards prove they never enter a score, grade, or verdict path.
- **It does not silently recompute for a mock's format.** In DRAFT MODE it labels
  the mismatch instead.
- **It does not use Yahoo data.** That work was cancelled - the LeagueLegacy
  archive supplied the Yahoo era.

---

## 3. GOVERNANCE RULES, WITH THEIR RATIONALE

Each of these was bought with a defect. Do not relax one without reading why it
exists.

**R1. Derive, never hardcode.** Any value the server, the data, or a computation
can supply must come from there. *Why:* the 120s clock, and `TEAMS`/`ROUNDS` still
being module constants (now cross-checked by `src/preflight_draft.py`).

**R2. The frozen math law.** Ten function bodies - `fit_sd_curve`, `sd_for`,
`_raw_survival`, `survival`, `cond_survival` in Python and `sdFor`, `erfc`,
`rawSurvival`, `survival`, `condSurvival` in JS - must stay byte-identical to
`origin/main`. `tests/mathdiff.py` prints `MATH DIFF PROOF: EMPTY` or the build
stops. *Why:* the survival model took three bug-fix rounds and an audit to
stabilise; it is not to be casually edited.

**R3. Cross-surface parity.** Python and JS implementations of the same maths must
agree, proven by reference anchors embedded in the payload. *Why:* the JS computed
`1 - erf(z)`, which saturates to a hard zero past z≈6 while Python's `erfc` keeps
mass - the room showed "0%" for players demonstrably on the board. Two surfaces
disagreeing has happened twice.

**R4. One conditioning frame.** Never mix conditional and unconditional survival
in a single expression. *Why:* twice - the wait-or-reach comparison, then VONA's
28% negative nodes.

**R5. The shared forward-pick policy.** Any projection solving more than one pick
MUST route through `src/forward_policy.py`: it consumes its own prior selections
and respects both positional caps and the exact single shared-FLEX starter
composition. *Why:* four occurrences of the same defect class, each fixed at a
call site until the shared layer finally existed. Coarse caps alone still allowed
RB3 and WR3 to consume two FLEX slots; `starter_path_feasible()` is the contract.

**R6. The gate law.** Every suite runs as `sh tests/run_gate.sh <cmd>`. It requires
exit 0 AND the sentinel AND no `^[0-9]+ FAILURES` AND no `SKIP` (override with
`GATE_ALLOW_SKIP=1`, and say what coverage you lose). It reports `RAN n GUARDS`.
*Why:* a pipe returns the pipe's exit code - a false green was committed. Then, one
level up, a suite printed five SKIPs and `ALL PASS` and the gate called it green.

**R7. The pipe law.** NEVER pipe a suite through `tail`/`head`/`grep`, even
interactively. Write gate output to a file and read the file. *Why:* R6, twice.

**R8. Display-only means guarded.** A feature declared display-only gets a guard
proving it never reaches a score or verdict.

**R9. A wrong number is worse than no number.** When data is missing or stale, show
the absence. The clock renders `-:--` with "clock unavailable - use Sleeper"
rather than a plausible countdown.

**R10. Alert on the deliverable, not the machine.** Monitor the published artifact
on the live site, not whether a job ran. *Why:* three silent-cron incidents;
`src/check_publication.py` is the fix.

**R11. Provenance on every artifact.** Every `out/data/*.json` carries a
`provenance` block with generation date, sources, method, and stated limitations.
Anything engine-derived carries `engine_generated`, and a guard asserts it matches.

**R12. Never quote a pooled rate when the strata are unbalanced.** *Why:* 93.5% of
BULLISH tags land in one ADP band, so the pooled comparison measures the market.

**R13. Commit convention.** Author `Anthony DellaPia <anthonydellapia@gmail.com>`.
Hyphens, not em dashes. No emojis. No model identifiers in anything pushed. Use
`git -c core.hooksPath=/dev/null commit`.

---

## 4. BUILD AND TEST, EXACT COMMANDS IN ORDER

Full detail and rehearsed timings: `docs/DRAFT_MORNING.md`. The short form:

```sh
# 0. environment
export PAGES=https://anthonydellapia1117.github.io/yeahthatfantasyleague
mkdir -p /tmp/pw && (cd /tmp/pw && npm install --no-save playwright-core)   # once

# 1. is the world still what the app assumes?
python3 src/preflight_draft.py

# 2. rebuild (pure stdlib, no network beyond Sleeper/FFC/nflverse)
python3 src/engine_2026.py
python3 src/build_cvs_inputs.py
python3 src/build_cvs.py
python3 src/build_vona_tree.py          # derives from the engine - rebuild together

# 3. gates - every one through run_gate
python3 tests/test_run_gate.py
sh tests/run_gate.sh python3 tests/test_survival.py
GATE_SENTINEL="MATH DIFF PROOF: EMPTY" sh tests/run_gate.sh python3 tests/mathdiff.py
for t in cvs vor baserates archetypes ceiling bullish ws2 mock \
         bullish_vs_adp vona draft_vs_acquired pages_data; do
  sh tests/run_gate.sh python3 tests/test_$t.py
done
GATE_ALLOW_SKIP=1 sh tests/run_gate.sh python3 tests/test_analysis.py

# 4. browser suite (26 hermetic scenarios)
NODE_PATH=/tmp/pw/node_modules sh tests/run_gate.sh \
  node tests/smoke_draft_room.js out/draft_room.html
# OR, if macOS Chrome is not auto-detected, run this instead:
PW_CHROMIUM="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  NODE_PATH=/tmp/pw/node_modules sh tests/run_gate.sh \
  node tests/smoke_draft_room.js out/draft_room.html

# 5. ship, then PROVE it shipped
git push -u origin <branch>            # PR, ready-for-review, squash-merge
files="out/engine_2026.json out/cvs.json out/draft_room.html out/big_board.html out/paths.html out/ff-hub.html out/data/vona_tree_2026.json out/data/bullish_vs_adp.json out/data/sos_2026.json out/data/td_rates_2025.json out/data/volatility_2025.json"
attempt=0; all_match=0
while [ "$attempt" -lt 30 ]; do
  all_match=1
  for f in $files; do
    curl -fsS "$PAGES/$f?bust=$(date +%s)" | cmp -s - "$f" || all_match=0
  done
  [ "$all_match" -eq 1 ] && break
  attempt=$((attempt + 1))
  [ "$attempt" -lt 30 ] && sleep 10
done
[ "$all_match" -eq 1 ] || { echo "DEPLOY PROOF FAILED after 30 attempts" >&2; exit 1; }
for f in $files; do
  curl -fsS "$PAGES/$f?bust=$(date +%s)" | cmp -s - "$f" || {
    echo "DIFFERS $f" >&2; exit 1;
  }
  echo "BYTE-IDENTICAL $f"
done
```

**Guard counts as of this writing** (a fixed-count suite that suddenly runs fewer
is a regression): survival 39, cvs 18, vor 50, baserates 70, archetypes 17, ceiling 14,
bullish 29, ws2 63, mock 45, bullish_vs_adp 43, vona 17702, draft_vs_acquired 23,
pages_data 289, run_gate 16, analysis 38 (33 without the history cache), smoke 347.
VONA's current count is data-dependent because it independently checks every
rendered node, feasible action, and dominance witness. A legitimate live ADP
refresh can change its tree shape and count; a lower VONA count alone is not a
regression when the reconciliation guards still pass.

**Rebuilding the analysis layer** needs the historical cache, which is NOT in the
repo: `python3 src/fetch_history.py` (~156MB, nine families, `HISTORY` env var to
relocate). Do this before touching `build_archetypes`, `build_ceiling`,
`build_base_rates`, `build_bullish*`, `bullish_vs_adp`, `build_ws2_audit`, or
anything in `analyze_*`.

---

## 5. THE REJECTED-APPROACHES LIST

**Do not re-litigate these.** Each was tested and lost. Re-proposing one without
new evidence wastes a cycle.

| Rejected | Why, with the number |
|---|---|
| **Opponent tendencies inside the probability model** | Real and persistent, but folding them into the arithmetic was rejected. The backtest that settled it: p=0.99 - no predictive gain. They ship as display only, and the guard enforcing that is the most important test in `test_survival.py`. |
| **Power-law sd curve** | Adopted, then LOST ITS OWN BACKTEST. Leave-one-season-out over 2,039 picks: it did not beat the step function it replaced (10 of 13 seasons to the step, two-sided p=0.092 - a wash). Its capped tail misfits the real decline past ADP 115. |
| **Step-function sd (4-band)** | The original. Adjacent-ADP survival differed **8,284x** at pick 48. Cliff drove verdicts at exactly the boundaries where wait-or-reach flips. |
| **INTERP sd - ADOPTED, do not replace casually** | 12-bin piecewise linear. Beats the step 12 of 13 seasons, two-sided p=0.0034 - the only significant comparison in the backtest. A calibration benchmark guard now blocks any sd change that predicts worse out of sample. |
| **Reverting to raw VOR sums for multi-pick objectives** | Disproved by the M1 mock validation: raw VOR prices a duplicate at starter value, so it drafts three elite TEs. Use lineup value from `forward_policy`. |
| **Automating the BULLISH-vs-ADP verdict** | A three-state rule (BEATS/UNDERPOWERED/NULL) computed from six cells plus a post-hoc minimum-detectable-effect search. Unsound three ways: post-hoc MDE is not an equivalence test, six cells with no multiplicity control, and the BEATS branch was sign-blind. The verdict is now REPORTED text, fixed by review, with the builder cross-checking every cited figure against the computed cells. |
| **Calling the BULLISH-vs-ADP result NULL** | It is INCONCLUSIVE. +13.4pp with a 95% CI of [-2.1, +28.9] permits slight harm and useful lift alike. |
| **Quoting the pooled BULLISH tagged-vs-untagged rate** | 63.0% vs 26.8% looks decisive and measures ADP: 93.5% of tags land in the pos1-12 band. |
| **Durability fade as a draft signal** | Dropped under a pre-registered rule after investigation. |
| **Recency-bias coefficient** | No effect found, therefore not used. |
| **Injury-market inefficiency** | None established; one candidate flagged, nothing shipped. |
| **Optimizing for drafted-share of starter points** | Champions draw 71.0% from drafted players, the field 68.7%: +2.3pp, CI [-5.2, +9.7], overlapping zero in both eras. What separates champions is total production (+203.3, CI [163.4, 243.0]). Targeting drafted share targets the one quantity that does not distinguish winners. |
| **Yahoo history via yfpy OAuth** | CANCELLED - the LeagueLegacy archive supplied the Yahoo era. `src/fetch_yahoo.py` and `src/oauth_exchange.py` remain but are not wired. |
| **Gating VONA branching on slot number** | Rejected before building. Branching is computed from the action set at each node, never prescribed by seat. |
| **The VONA p25 epsilon branch rule** | Rejected after cold review. Its cutoff was estimated from the same model gaps it classified, so model compression or dispersion changed what counted as a decision. It could also hide a genuine lineup-value tradeoff. The tree now keeps the computed Pareto frontier on VONA and expected lineup gain. |
| **A VONA survival floor** | Rejected after cold review. Truncating low-probability player states changed the expectation and could invent a named recommendation. The full positive-VOR top-survivor distribution now includes replacement as an explicit zero-value state and publishes an honest fallback when replacement is modal. |
| **Making the repo private to fix the PII exposure** | Rejected: GitHub Pages on a private repo requires Pro, so it would take the app dark twelve days before the draft. Fixed by pruning instead. |

---

## 6. MODULE MAP

**Draft-night path** (touch with maximum care):
- `draft_board.py` (repo root) - fetches the league from Sleeper: `roster_positions`,
  `scoring_settings`, `total_rosters`. Scores projections under league-exact rules.
  The lineup shape and scoring ARE derived here; `TEAMS`/`ROUNDS` in
  `engine_2026.py` are not, which is what the preflight covers.
- `src/engine_2026.py` -> `out/engine_2026.json` - the payload every page reads.
  Survival model, per-slot decision cards, opponent priors. Contains the frozen
  math (R2). Embedded directly into `draft_room.html` between sentinel markers.
- `src/forward_policy.py` - the shared multi-pick layer (R5). `starter_caps()`
  supplies coarse bounds; `starter_targets()` and `starter_path_feasible()`
  enforce the exact seven-skill-starter composition with one shared FLEX;
  `roster_caps()` covers full rosters (+1 spare), with `pick_marginal()` and
  `phantom_lineup_pts()` for lineup value.
- `src/build_cvs.py` + `build_cvs_inputs.py` -> `out/cvs.json` - the board the room
  and big board render. Reads the engine payload; the engine never reads CVS.
- `out/draft_room.html` - ~2,400 lines. Live polling, clock, pick engine, DRAFT
  MODE, simulator. The single most defect-dense file in the repo.

**Coupling that is not obvious:**
- `engine_2026.json` is **embedded** in `draft_room.html`, not fetched. Rebuilding
  the engine rewrites that HTML between its sentinel markers.
- `cvs.json` and the engine must share a `generated` date; the room warns on
  mismatch (`draft_room.html:~1627`). Only cvs has this warning.
- `vona_tree_2026.json` and `mock_drafts_2026.json` record `engine_generated`; a
  page guard now asserts it matches. No other artifact records its engine.
- `pages.yml` deploys an **explicit HTML file list** plus `out/data/*.json` by
  wildcard. A new page must be added to that list or it 404s live - this bit once
  (`paths.html`). Guard 8c checks nav-linked pages; a non-nav-linked page would
  still slip.
- `nav.js` is the single source for navigation and the kicker style. Seven items.
- The engine must NOT import from the pages-data layer; guard N1 enforces it.

**Analysis layer** (needs the `HISTORY` cache; not on the draft-night path):
`ingest.py`, `phase2_value.py`, `phase3_lineup.py`, `phase3_remainder.py`,
`phase3e_startsit.py`, `build_app_data.py`, `draft_vs_acquired.py`,
`build_base_rates.py`, `build_archetypes.py`, `build_ceiling.py`,
`build_bullish*.py`, `bullish_vs_adp.py`, `build_ws2_audit.py`, `analyze_*.py`.

**Sequencing constraints:**
1. `engine_2026.py` before `build_cvs.py` (CVS reads the payload).
2. `build_cvs_inputs.py` before `build_cvs.py`.
3. `build_vona_tree.py` AFTER `engine_2026.py`, always in the same pass.
4. `ingest.py` before `phase2_value.py` before `phase3_lineup.py`.
5. `fetch_history.py` before any analysis builder, on a fresh machine.

**Do-not-modify:**
- The ten frozen math functions (R2).
- `docs/CHAT_HISTORY_2026-08-11.md` - an archived record; leave its historical text
  alone even when purging language elsewhere.

`out/ff-hub.html` is no longer on this list. The reviewed N.1 BULLISH-vs-ADP
finding is a dedicated tab that loads `out/data/bullish_vs_adp.json` at runtime,
renders the artifact's fixed INCONCLUSIVE verdict verbatim, and exposes loading,
schema-failure, and HTTP-failure states. Keep the eight original league-history
null hypotheses distinct from this later test.

---

## 7. SHARP EDGES

- **`data/Walter Ai-2026_Advanced_Fantasy_Guide.md` has a space in the filename.**
  Quote the path.
- **Tests must be payload-driven, never data-pinned.** Two tests hardcoded one
  day's data and failed on correct behavior after a refresh. If you assert a player
  name, read it from the payload, and handle the empty state.
- **`.activef {display:flex}` beats the `hidden` attribute.** There is an explicit
  `[hidden]{display:none}` rule on two pages because of it.
- **The smoke server must answer `/favicon.ico`** (204) or the zero-console-error
  assertion trips.
- **`run_gate` matches `^[0-9]+ FAILURES` anchored** because a PASS label
  containing the word "FAILURES" produced a false positive.
- **Sleeper's `slot_to_roster_id` returns the identity map before the draw.** A
  genuine draw landing on identity is 1 in 12!, so identity means "not drawn".
- **`roster_id == 7` and Anthony's expected `slot == 7` are the same integer by
  coincidence.** They are different things. `draft_room.html:461` maps them
  correctly; do not let an edit conflate them.
- **`out/data/heartbeat.txt`** exists to guarantee a diff so the daily cron commit
  keeps the scheduled workflow alive past GitHub's 60-day inactivity disable.
- **Three artifacts differ by 0.01 across Python builds** (`points_left_per_week`),
  a documented round-half jitter. Not a bug; do not chase it.

---

## 8. WATCH FOR THESE DEFECT CLASSES

The five that recurred, from `docs/SELF_AUDIT_2026-08-26.md` §1.3. In every case
the first fix was applied at a call site instead of as a shared rule, which is why
there was a second and a third.

1. **Multi-pick independence (4 occurrences).** Any new consumer that picks more
   than once must route through `forward_policy`. Nothing mechanically prevents a
   new one from re-implementing selection inline.
2. **Name normalization (3).** Suffixes, then father/son collisions, then
   diacritics. **There are still two independent normalizers** -
   `ingest._norm_player` and `build_pages_data.norm_name` - and the diacritic fold
   is only in the second. The tests assert a match *rate* against today's data, not
   the normalizer's *contract*, so each repair patches a symptom.
3. **Silent cron / stale publication (3).** Alert on the published artifact.
4. **Fail-open guards (3).** A guard that builds evidence and never asserts; a
   wrapper that swallows an exit code; a suite that skips and says ALL PASS. Ask of
   every new guard: *what change would make this fail?* If you cannot answer, it is
   decoration.
5. **Conditioning frame (2).** R4.

---

## 9. OPEN ITEMS

| Item | State | Next action |
|---|---|---|
| **Archive PII in git HISTORY** | Removed from HEAD by the 2026-08-26 prune; still reachable in history at/before `bd8aff7`. Repo is public. | **Anthony's call, deferred to after the draft.** (a) accept, (b) `git filter-repo` + force-push (invalidates clones), (c) private repo - rejected for now, Pages would go dark. |
| **Live browser-to-Sleeper path** | **NEVER EXERCISED.** All 347 smoke guards across 26 scenarios are hermetic - they stub the Sleeper API. No test has ever driven a real browser against the real API. | Anthony tests it himself on the deployed page. This is the single largest untested surface and it is the draft-night one. |
| **Keeper status** | `use_keepers` is on for 2025-2026 but the 2025 draft had zero keeper picks and `keeper_results.csv` is 2 bytes. | OPEN QUESTION for the commissioner. **Do not resolve by inference.** |
| **Draft order** | UNDRAWN as of 2026-08-26 22:12Z. | A Routine runs `src/check_draft_order.py` every 2h and self-retires on the draw. The room collapses to the real seat automatically. |
| **`transaction_items.csv` / FAAB bids** | Deleted in the prune; the FAAB-discipline question still lacks bid-level data. | Restore from history if the work is wanted. |
| **Second normalizer** | `ingest._norm_player` lacks the diacritic fold. | One shared normalizer with a contract test. |
| **Typed grade weights** | `GRADE_W` and `PE` are judgment constants, never backtested. Honest on the card, but the largest exception to R1. | Backtest or keep labelled. |
| **Optional-shard silent degradation** | `base_rates`/`ceiling`/archetypes/bullish fetch failures vanish columns with no notice. | Add a visible "unavailable" state + a smoke scenario. |
| **12-team geometry inside DRAFT MODE** | `sleeperListHtml` bands and `simBand` labels are hardcoded 12x14; wrong in a 10-team mock. | Derive from `GEO`. |
| **VONA UI budget coupling** | `MAX_NODES = 120` is a deliberate UI safety budget, not a statistical threshold. The current largest slot is 102 nodes and passes the 390px no-overflow smoke, leaving 18 nodes of headroom. A valid future board can exceed it and block the linked refresh. | Keep the failure loud. Inspect the complete tree on mobile before deliberately raising the budget; never truncate actions to fit. |

---

## 10. BEFORE ANY COMMIT

1. `python3 src/preflight_draft.py` if you touched anything draft-geometry-shaped.
2. Full gate battery (§4). Every suite through `run_gate`, output to a file.
3. `mathdiff` prints `MATH DIFF PROOF: EMPTY`.
4. Smoke suite, 347 guards PASS.
5. **Interrogate the values of any artifact you regenerated**, not just its schema
   (§1.2). What would be impossible in this data? Check for it.
6. Ask of any new guard: what change would make this fail? (§8.4)
7. Ask of any new feature: how would this look if it were broken? (§1.4)
8. Rebuilt the engine? Rebuild `build_vona_tree.py` in the same pass.
9. After merge, byte-compare the deployed files. The live site IS the build.
