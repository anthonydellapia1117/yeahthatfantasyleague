# Yahoo Harvest - Status 2026-08-11

## Proven

**The missing bonus points are recoverable from Yahoo.** Verified at player level on
2013 week 1, Three Amigos (Anthony):

| Player | Yahoo | LeagueLegacy | Missing |
|---|---|---|---|
| Aaron Rodgers QB | 30.62 | 24.62 | +6.00 |
| A.J. Green WR | 41.20 | 37.20 | +4.00 |
| Steven Jackson RB | 18.20 | 17.20 | +1.00 |
| 6 other starters | identical | identical | 0 |
| TOTAL | 150.62 | 139.62 | +11.00 |

All deltas are whole integers on big-play players. Yahoo per-player values are
bonus-inclusive; LeagueLegacy dropped the six 40-yard bonuses on import.

Also recovered: **authentic per-season team names**. 2013 shows Three Amigos, The Dro's
(Ronald), nolan's Team, Prestige WorldWide (Mike Pungitore), Team JoeBa, Daddy's Team,
Funky Monkeys, SlobMyCobb, Chris's Team, Robert's Team, and two separate Vincent teams.
This independently corroborates the franchise lineage taken from owner testimony.

## Blocked, two independent limits

**1. Yahoo rate limit.** HTTP 999 after roughly 50 rapid fetches. Cooldown exceeds
several minutes; exact duration not measured. 2013 weeks 1-7 completed clean (2,464
rows, 0 errors) before the wall. Full job needs about 1,000 fetches.

**2. No bulk data channel out of the browser.**

| Channel | Result |
|---|---|
| Programmatic download | Blocked, no user gesture |
| POST to local sink | **Blocked by mixed content.** Page is HTTPS, sink is http://127.0.0.1. No CSP header, so mixed content is the cause |
| javascript_tool return | Caps near 1 KB, about 20 rows per call |
| get_page_text | Works, roughly 900 rows per call, but consumes very large context |

Local sink at `src/sink.py` is written and self-tested, including CSV quoting. It works;
the browser simply cannot reach it from an HTTPS origin.

## Known defect in the harvested rows

The right-side numeric team id is wrong, always resolving to 8. `team_name` is correct
on every row, so keying on name is sound. Fix before any re-run: drop the id, or read
it from the team link href rather than a body-wide regex.

## The path that actually works

`src/fetch_yahoo.py` with yfpy. All 14 league ids are wired, game keys are queried per
season rather than hardcoded, and Sleeper is already proven working with no credentials.
It needs one thing: a Yahoo developer app.

1. https://developer.yahoo.com/apps/ - Web Application, redirect `https://localhost:8080`,
   permission Fantasy Sports Read
2. `cp .env.example .env` and paste the two values
3. `.venv-yahoo/bin/python src/fetch_yahoo.py --season 2024`
4. Approve in the browser, paste the code. Then `--all`

That path has no rate-limit problem of this kind and no extraction bottleneck.

## What it is worth

| Measure | Value |
|---|---|
| Bonus as share of scoring | 4.99% |
| Head-to-head results that flip | 47 of 1,128, 4.17% |
| Phase 2 drafted-vs-acquired ratio | unaffected, both sides bonus-exclusive |
| Phase 5 2026 simulator | does not use Yahoo data at all |
