# Draft morning runbook - 2026-09-08

Rehearsed end-to-end on 2026-08-19; timings below are from that
rehearsal on the remote container. The compute is under two minutes;
with the ship steps and the deploy wait, budget about ten minutes
wall-clock plus reading time. Every step is a hard gate: a failure
stops the line, and the draft room keeps serving the last committed
build until the whole sequence is green.

## The night before

- [ ] `data/my_board.csv` - every BULL/BEAR call in, each with a reason
      and a source. Unsourced conviction does not get graded.
- [ ] If Walter shipped a guide revision: drop the new file in `data/`,
      run `python3 "src/parse_walter.py"` (path quoting matters - the
      guide filename contains a space), review
      `data/walter/extraction_report.json` and the unresolved queue,
      and re-run `python3 src/build_cvs.py`. The board footer's source
      sha must match the new file.
- [ ] Decide the walter layer state for the draft: config
      `walter_enabled` in `data/cvs_weights.json` (rebuild-level) and
      the live WALTER LAYER toggle on the big board (mid-draft,
      localStorage `ytfl_walter_live`). Default: both ON.

## The morning sequence

Run from the repo root, in this order, no parallelism. Timings are the
rehearsal's `real` times.

| # | Command | Rehearsed | What it does |
|---|---|---|---|
| 1 | `git fetch origin main && git checkout -B claude/chat-migration-desktop-ruannr origin/main` | 5 s | clean start from main |
| 1b | `python3 src/preflight_draft.py` | 1 s | geometry preflight: asserts the LIVE draft is still snake, no third-round reversal, and the teams/rounds the payload ships. Stop here on a mismatch - every computed pick number depends on it |
| 2 | `python3 src/engine_2026.py` | 3.7 s | live ADP + projections; rewrites the sentinel payload, engine_2026.json, decision cards |
| 3 | `python3 src/build_cvs_inputs.py` | 2.0 s | nflverse volatility, TD rates, 2026 SOS |
| 4 | `python3 src/build_cvs.py` | 0.3 s | the CVS board payload |
| 4a | `python3 src/build_vona_tree.py` | 1.0 s | the PATHS tree - derives from the engine payload, so it MUST be rebuilt with it; the page guards fail if it falls behind |
| 4b | `python3 tests/test_run_gate.py` | 0.3 s | gate-runner self-test: proves the masking shapes (pipe, compound wrapper, exit-0 liar) are caught |
| 5 | `sh tests/run_gate.sh python3 tests/test_survival.py` | 0.6 s | 39 frozen-behavior guards |
| 6 | `GATE_SENTINEL="MATH DIFF PROOF: EMPTY" sh tests/run_gate.sh python3 tests/mathdiff.py` | 0.1 s | ten function bodies byte-identical to origin/main |
| 7 | `sh tests/run_gate.sh python3 tests/test_cvs.py` | 0.1 s | anchor law, cap, signals, determinism |
| 7b | `sh tests/run_gate.sh python3 tests/test_vor.py` | 0.1 s | exact scoring, derived flex allocation, derived tiers |
| 7c | `sh tests/run_gate.sh python3 tests/test_baserates.py` | 0.1 s | base-rate artifact integrity + board wiring |
| 7d | `sh tests/run_gate.sh python3 tests/test_archetypes.py` | 0.1 s | archetype tags: computed thresholds, zero-IR flags, page wiring |
| 7e | `sh tests/run_gate.sh python3 tests/test_ceiling.py` | 0.1 s | ceiling lens: boom rates, zero-IR availability, enabled view |
| 7f | `sh tests/run_gate.sh python3 tests/test_bullish.py` | 0.2 s | BULLISH engine: probabilistic gates, state machine, ADP-edge accounting |
| 7g | `sh tests/run_gate.sh python3 tests/test_ws2.py` | 0.1 s | WS2 claims audit: verdict ledger coherent, cited-value canary, curse tag cross-check |
| 7h | `sh tests/run_gate.sh python3 tests/test_mock.py` | 0.1 s | mock-draft validation: roster legality, caps, board-beats-chalk deltas |
| 7i | `sh tests/run_gate.sh python3 tests/test_bullish_vs_adp.py` | 0.1 s | BULLISH-vs-ADP test: reviewed INCONCLUSIVE verdict verbatim, cited figures cross-check the cells, ADP-confound disclosure, tag stays display-only |
| 7j | `sh tests/run_gate.sh python3 tests/test_vona.py` | 0.6 s | VONA path tree: real round-8 value lookahead, one-frame expectations, full replacement-state distribution, full-precision local Pareto decisions, exact shared FLEX including observed TE use, auditable candidate ledgers, representative modal continuation disclosed, no BULLISH on nodes |
| 7k | `sh tests/run_gate.sh python3 tests/test_draft_vs_acquired.py` | 0.2 s | drafted-vs-acquired: champions-vs-field intervals, era flags, the two results kept distinct |
| 8 | `sh tests/run_gate.sh python3 tests/test_pages_data.py` | 0.5 s | 289 page/data guards including N.1 artifact loading/failure, contrast, and teaser |
| 9 | `GATE_ALLOW_SKIP=1 sh tests/run_gate.sh python3 tests/test_analysis.py` | 0.3 s | analysis guards. The five determinism reruns are cache-gated; without the HISTORY cache they skip, and run_gate now FAILS on a skip unless you say it is expected - hence the explicit `GATE_ALLOW_SKIP=1`. Coverage lost when you use it: 5 of 38 checks in this suite, and they are the ones proving the artifacts reproduce. With the cache they run and take ~25 min - merge-gate territory, not morning territory |
| 10 | full smoke (see the playwright note below) | 120 s + install | 347 guards across 26 hermetic browser scenarios including DRAFT MODE, the forward-pick law, N.1 success/failure, the path ledger, and 390px PATHS coverage |
| 11 | commit (convention below), push, draft PR, ready, squash-merge on green, reset branch | ~3 min | ship |
| 12 | deploy byte-compare (loop below) | ~2 min | the live site IS the build |

Playwright note for step 10: the repo has no package.json, so a fresh
container has no playwright-core. Install the driver once per session and
run the smoke against the browser this image already ships - in the
container, do NOT run `playwright install`, the binary is already at
/opt/pw-browsers/chromium:

    mkdir -p /tmp/pw && (cd /tmp/pw && npm install --no-save playwright-core)
    NODE_PATH=/tmp/pw/node_modules sh tests/run_gate.sh node tests/smoke_draft_room.js out/draft_room.html

The smoke takes the browser path from `PW_CHROMIUM` when it is set and
otherwise checks that container path and the standard macOS Chrome and Chromium
locations. An explicit macOS invocation is:

    PW_CHROMIUM="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
      NODE_PATH=/tmp/pw/node_modules sh tests/run_gate.sh \
      node tests/smoke_draft_room.js out/draft_room.html

CI supplies its downloaded executable through `PW_CHROMIUM`.

If the teaser leak guard in step 8 fails after a regen, today's ADP
moved a top name in or out of the allowed subset - rerun
`python3 src/build_teaser.py`, then repeat step 8.

Data-dependent test note: assertions that name a specific player from a
live payload (the big board conflicts view is the one that bit us) must
stay payload-driven - read out/cvs.json and assert on what is actually
in it, including the empty states. A refresh day that legitimately has
no conflicts must not fail the suite.

Gate law, second clause: run_gate now reports `RAN n GUARDS` on every run
and FAILS on any `SKIP` line unless `GATE_ALLOW_SKIP=1` is set. A skipped
guard is not a passing guard - the suite that printed five SKIPs and then
`ALL PASS` is why. If you set the override, say in the same place what
coverage you are giving up.

Pipe law: NEVER pipe a suite through tail/head/grep, even when exploring
interactively - a pipe returns the pipe tail's exit code and hides the
suite's, the exact masking shape run_gate.sh exists to close, and it bit
twice (the C5 background smoke, then again reading a truncated tail
during DRAFT MODE debugging). Run `sh tests/run_gate.sh <suite>` with
output to a file and read the file.

Commit convention: author `Anthony DellaPia <anthonydellapia@gmail.com>`,
hyphens not em dashes, no emojis. Deploy compare loop. It waits for the complete
artifact set, cache-busts every request, times out after about five minutes, and
exits nonzero on any mismatch:

    export PAGES=https://anthonydellapia1117.github.io/yeahthatfantasyleague
    files="out/engine_2026.json out/cvs.json out/draft_room.html out/big_board.html out/paths.html out/ff-hub.html out/data/vona_tree_2026.json out/data/bullish_vs_adp.json out/data/sos_2026.json out/data/td_rates_2025.json out/data/volatility_2025.json"
    attempt=0
    all_match=0
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
        echo "DIFFERS  $f" >&2
        exit 1
      }
      echo "BYTE-IDENTICAL  $f"
    done

## Before the clock starts

- [ ] Big board footer: cvs generated date and engine generated date are
      BOTH today; walter sha matches the current guide; config echo says
      cap 10%, walter_enabled true.
- [ ] Draft room on the phone (430pt): live pill goes LIVE when the
      party opens; seat matches Sleeper's real draw and the Layer 3
      notification; the pick engine card renders below the verdict card.
- [ ] `E.league.draft_id` in the sentinel payload matches the Sleeper
      draft lobby id.
- [ ] Big board WALTER LAYER toggle set to the decided state.
- [ ] Screen-lock off / wake lock allowed in the browser (the room
      requests one, but check the OS will not fight it).

## Automation

Four layers. The build and its independent verifier are aimed at 6:00 AM
Eastern (10:00 UTC) on 2026-08-28 (the pre-draft dry run) and 2026-09-08
(draft morning); the order and publication watches run on their own cadences.

LAYER 1 - `.github/workflows/draft-refresh.yml`. The machine that does
the work. Cron-fired on those two dates, it runs steps 2 through 10 of
the sequence above on a GitHub runner and commits to main only if every
gate passes; the push fires `pages.yml`, which is what deploys. A red
gate means no commit, so the last verified build keeps serving. It needs
no container, no session, and no API keys. `workflow_dispatch` runs it on
demand with a `dry_run` input that defaults to true - every gate runs,
nothing is committed.

LAYER 2 - a scheduled Claude Routine per date, firing after the workflow.
It confirms the live site actually byte-matches main, and if the workflow
went red it diagnoses the failure, pushes a fix to
`claude/chat-migration-desktop-ruannr`, and reports. It does not push to
main; a 6:00 AM failure leaves the whole day to land the fix, and the
deployed build is never in a broken state while that happens.

LAYER 3 - the draft-order draw watch. A Claude Routine runs
`python3 src/check_draft_order.py` every two hours until the draw (or
2026-09-08, whichever first). The script mirrors the room's own
detection semantics - the identity slot map counts as NOT drawn - and
the Routine stays silent until the order is real, then push-notifies
Anthony with his slot and retires itself. The room needs nothing from
it: it already collapses to the detected seat live (the order-hypothesis
card retires, renderPre follows the real slot); the watch exists so
Anthony hears about the draw without opening the app.

LAYER 4 - the publication watch. The pages-data cron failed 8 of its
first 14 scheduled runs (the last four consecutively) and nothing
noticed - the third silent-cron incident. The lesson, applied: alert on
missing successful PUBLICATION, not on workflow execution. A daily
Claude Routine runs `python3 src/check_publication.py`, which reads the
LIVE site's deployed provenance.json - the thing a green run actually
produces - and stays silent while it is under 48 hours old.
STALE or UNREADABLE push-notifies Anthony and triggers a diagnosis of
the failed run. The Routine retires itself after draft day.

Anthony still owns the night-before checklist - the board calls, any
Walter revision, the walter layer decision. No automation layer edits `data/`.

If the draft date or time moves, update the workflow cron AND the
Routines rather than adding new ones, so there is only ever one scheduled
run per morning. The workflow refuses to run outside 2026 on purpose.

## If something breaks

Three failed fixes on any step: stop, run the draft on the last
committed build (it is deployed and byte-verified), and note the gap.
Within `draft_room.html`, the engine replaces only the sentinel payload, but it
also rewrites the engine JSON and decision cards. A failed run never deploys
because the gates prevent a commit. Nothing on this page is irreversible; the
last green build is always one `git checkout
origin/main -- out/` away.
