# ff-hub

Thirteen seasons of **YeahThatFantasyLeague** turned into evidence: 2,339 draft picks, 37,106 roster-weeks, 156 franchise-seasons, 13 verified champions.

## The finding

**There is no draft-day roadmap in this league.** Eight draft-day hypotheses were tested and all eight are null. The single surviving lead is **lineup efficiency**, and it is a start-sit problem, not a draft problem.

| Hypothesis | Measured | p | Verdict |
|---|---|---|---|
| Champions wait on QB | 6.46 vs 5.92 rounds | 0.252 | folklore |
| Champions avoid QB in rounds 1-5 | 62% vs 48% | 0.266 | folklore |
| Champions load RB early | 2.15 vs 2.01 | - | noise |
| Champions load WR early | 2.00 vs 2.03 | - | noise |
| Draft slot matters | mean 7.5 vs 6.5 expected | - | no pattern |
| Drafted share predicts winning | corr +0.043 | - | dead |
| FAAB aggression | 46.8 vs 35.7 | 0.197 | dead |
| Champions draft the #1 board player | 0 of 13 | 0.323 | striking, not significant |
| **Lineup efficiency** | **89.75% vs 88.44%** | **0.078** | **strongest lead** |

## Start here

| File | What it is |
|---|---|
| `out/HANDOFF.md` | Distilled state. Read this first |
| `out/ff-hub.html` | Static dashboard. Serve the repo over HTTP so its N.1 artifact can load |
| `docs/CHAT_HISTORY_*.md` | Full redacted build transcript |
| `plugin/skills/ff-hub/` | Claude Code skill carrying the verified history |

## The draft room

Live app: https://anthonydellapia1117.github.io/yeahthatfantasyleague/out/draft_room.html
(add it to the phone home screen - it installs like an app). The local file
`out/draft_room.html` is the offline fallback; both carry the same embedded model.

Draft-morning flow is the gated sequence in `docs/DRAFT_MORNING.md`. The engine,
CVS inputs, CVS board, and VONA tree are one provenance-linked build and must be
regenerated together; every listed gate must pass before a branch is pushed for
review. Never use an engine-only rebuild or manually push directly to main. The
fully gated scheduled `draft-refresh` workflow is the documented automation
exception.

GitHub Pages redeploys in about a minute. Projections, ADP, and injury
statuses move daily - regenerate the morning of 2026-09-08.

## Rebuild

```bash
python3 src/ingest.py          # Phase 1: ingest and reconcile, 52 assertions
python3 src/phase2_value.py    # Phase 2: pick value and drafted-vs-acquired
python3 src/phase3_lineup.py   # Phase 3A: lineup efficiency + positional gap
python3 src/build_app_data.py  # dashboard data (app_data.json)
python3 -m http.server 8000    # from the repo root
# open http://127.0.0.1:8000/out/ff-hub.html
```

## Basis, stated once

Yahoo seasons 2013-2024 are **bonus-exclusive**: six 40-yard long-play bonuses worth 6.14 points per team-week sit in official team totals but not in per-player rows. Ratios are unaffected; absolute point totals are understated by about 5 percent. Yahoo's Fantasy API is closed to new apps, so this is accepted and disclosed rather than fixed. See `out/gap_register.md` G1.

## Rules of the road

Never backfill a missing value. Never merge two manager identities on name similarity. Every derived table carries source, source_ref, fetched_at, confidence. With 13 champions, most comparisons will not reach significance - that is the expected outcome, not a failure.
