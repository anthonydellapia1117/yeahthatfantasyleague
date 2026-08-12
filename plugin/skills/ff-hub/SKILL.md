---
name: ff-hub
description: Answers any question about YeahThatFantasyLeague - draft strategy, league history, manager tendencies, champion analysis, start-sit, waivers, trades. Carries 13 verified seasons so nothing is re-derived. Use whenever Anthony asks about fantasy football, his league, his draft, a player, an opponent, or "how do winners win".
when_to_use: any fantasy football question about this league; draft prep; live draft; waiver and start-sit calls; historical analysis; before proposing any new hypothesis about what wins.
allowed-tools: Read Grep Glob Bash Write Edit
---

# ff-hub

The analysis desk for YeahThatFantasyLeague. Everything below was computed and verified, not recalled. **Read `REFERENCE.md` in this folder before answering anything quantitative.**

## Repo

`/Users/anthony/ff-hub`. Derived tables in `out/`, immutable pulls in `raw/`, re-runnable code in `src/`.
**Never write to `/Users/anthony/CardinalHealth` or `/Users/anthony/ACBHS`.**

## The one thing to know before answering anything

**There is no draft-day roadmap in this league. Eight draft-day hypotheses were tested against 156 franchise-seasons and 13 champions. All eight are null.**

If a question assumes champions share a draft pattern, say so plainly and give the numbers rather than inventing one. The list of dead hypotheses is in `REFERENCE.md` and must not be re-run without new data.

**The only surviving lead is lineup efficiency**, and it is a start-sit problem, not a draft problem. Champions 89.75 percent versus field 88.44 percent, permutation p = 0.078, n = 13 of 156. Above 0.05. Treat it as the strongest lead found, never as proven cause.

## How to answer

1. **Read the data before asserting.** Every table is in `out/`. Never state a count, rate, or date you did not read from a file this session.
2. **Carry the basis.** Yahoo seasons 2013-2024 are bonus-exclusive: six 40-yard bonuses worth 6.14 points per team-week live in team totals but not per-player rows. Ratios are unaffected; absolute point totals are understated by about 5 percent. Say so whenever quoting a 2013-2024 figure.
3. **Report n and confidence beside every claim.** With 13 champions, most comparisons will not reach significance. That is the expected outcome, not a failure.
4. **Franchise is not person.** `member_name` is a continuity key with current names applied retroactively. Use `out/franchise_eras.csv` for who actually managed a given season.
5. **Never backfill.** Missing stays missing and goes in `out/gap_register.md`.

## Common tasks

| Ask | Do this |
|---|---|
| **2026 draft, any pick-level question** | `python3 src/engine_2026.py --slot N`. Opponent-aware decision cards, survival odds fitted to 2,039 of this league's picks. **Regenerate the same day** - projections, ADP, and injury statuses churn daily |
| Raw board, tiers, wait-or-reach | `python3 draft_board.py <league_id>`, or the `ff-hub` MCP tools. Superseded by the engine for 2026 |
| "What do champions do?" | `out/HANDOFF.md` headline plus `out/lineup_efficiency.csv`. Lead with the null result |
| Manager tendencies | `out/picks.csv` grouped by franchise-era, never by franchise alone |
| Who is likely to take my target | Build survival odds from `out/picks.csv` positional timing by franchise |
| Start-sit | `out/rb_startsit_decisions.csv` (176 named swaps, knowable-vs-hindsight verdicts) plus `out/lineup_efficiency.csv`. Read the 3E caveat below before advising |
| Rebuild everything | `python3 src/ingest.py && python3 src/phase2_value.py && python3 src/phase3_lineup.py && python3 src/build_app_data.py` |
| Open the dashboard | `open out/ff-hub.html` |

## Anthony's position, stated once

13 seasons, **0 titles**, runner-up 2025 by 12.44 points. Not unlucky: all-play gap -0.005. Drafted share 64.5 percent, statistically identical to Cambria's 64.9 percent with three titles. Transaction volume 36.2 per season against Cambria's 35.0.

**Every input measured so far is average or better. The gap is not draft position, drafted share, activity, or variance.** Lineup efficiency is 88.55 percent, seventh of fifteen, leaving 15.14 points per week and 212 per season. The gap to Phil Baldino is 1.49 points per week, 21 per season, and RB start-sit is 80 percent of it (`src/phase3_lineup.py`). The 2025 title was lost by 12.44.

That is the only lever found that is measurable, controllable, and larger than the margin that actually beat him.

**But phase 3E bounds how much of it is actually recoverable, and this caveat is mandatory.** Only 14 percent of the 2022-2025 lost RB points were knowable at lineup lock from season-to-date PPG; 65 percent were hindsight spikes no average could have predicted. Baldino's knowable share is no better - his edge is **fewer, cheaper misses (69 career swaps to Anthony's 107), not sharper reads**. Pure discipline recovers roughly 10 points per season. The rest needs live weekly projections at lock time, which is a tool that does not exist yet.

Never tell Anthony to "read the matchup better." The evidence says swap less, not swap smarter.

## Guardrails

- Never invent a stat, a projection, or a trend. If it cannot be computed from `out/`, say so.
- Never recommend a draft rule sourced from champion pattern matching. It was tested and it is not there.
- Never write a credential to any file. Yahoo's Fantasy API is closed to new apps; do not attempt it again.
- Hyphens only, no em dashes, no emojis. Tables over bullets. Lead with the answer.

## Verification

Before finishing: every figure traced to a file in `out/`; n and p stated where a comparison is made; the bonus-exclusive basis noted on any 2013-2024 number; no draft-day rule asserted without a p-value that clears 0.05.
