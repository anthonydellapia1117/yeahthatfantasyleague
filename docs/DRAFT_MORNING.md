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
| 2 | `python3 src/engine_2026.py` | 3.7 s | live ADP + projections; rewrites the sentinel payload, engine_2026.json, decision cards |
| 3 | `python3 src/build_cvs_inputs.py` | 2.0 s | nflverse volatility, TD rates, 2026 SOS |
| 4 | `python3 src/build_cvs.py` | 0.3 s | the CVS board payload |
| 5 | `python3 tests/test_survival.py` | 0.6 s | 37 frozen-behavior guards |
| 6 | `python3 tests/mathdiff.py` | 0.1 s | ten function bodies byte-identical to origin/main |
| 7 | `python3 tests/test_cvs.py` | 0.1 s | anchor law, cap, signals, determinism |
| 8 | `python3 tests/test_pages_data.py` | 0.5 s | ~200 page/data guards incl. contrast + teaser |
| 9 | `python3 tests/test_analysis.py` | 0.3 s | analysis guards (the heavy reruns skip loudly without the history cache - fine on draft morning; with the cache they take ~25 min and are merge-gate territory, not morning territory) |
| 10 | full smoke: `NODE_PATH=<playwright-core install> node tests/smoke_draft_room.js out/draft_room.html` | 94 s | 17 hermetic browser scenarios |
| 11 | commit (convention below), push, draft PR, ready, squash-merge on green, reset branch | ~3 min | ship |
| 12 | deploy byte-compare (loop below) | ~2 min | the live site IS the build |

If the teaser leak guard in step 8 fails after a regen, today's ADP
moved a top name in or out of the allowed subset - rerun
`python3 src/build_teaser.py`, then repeat step 8.

Commit convention: author `Anthony DellaPia <anthonydellapia@gmail.com>`,
hyphens not em dashes, no emojis. Deploy compare loop:

    until curl -sS "$PAGES/out/cvs.json" | cmp -s - out/cvs.json; do sleep 10; done
    for f in out/engine_2026.json out/cvs.json out/draft_room.html out/big_board.html; do
      curl -sS "$PAGES/$f" | cmp -s - "$f" && echo "BYTE-IDENTICAL  $f" || echo "DIFFERS  $f"
    done

with `PAGES=https://anthonydellapia1117.github.io/yeahthatfantasyleague`.

## Before the clock starts

- [ ] Big board footer: cvs generated date and engine generated date are
      BOTH today; walter sha matches the current guide; config echo says
      cap 10%, walter_enabled true.
- [ ] Draft room on the phone (430pt): live pill goes LIVE when the
      party opens; seat auto-detects to 7; the pick engine card renders
      below the verdict card.
- [ ] `E.league.draft_id` in the sentinel payload matches the Sleeper
      draft lobby id.
- [ ] Big board WALTER LAYER toggle set to the decided state.
- [ ] Screen-lock off / wake lock allowed in the browser (the room
      requests one, but check the OS will not fight it).

## If something breaks

Three failed fixes on any step: stop, run the draft on the last
committed build (it is deployed and byte-verified), and note the gap.
The engine regen only ever touches its sentinel payload - a regen
failure cannot corrupt the app shell. Nothing on this page is
irreversible; the last green build is always one `git checkout
origin/main -- out/` away.
