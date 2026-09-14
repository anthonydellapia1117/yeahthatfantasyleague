# Weekly runbook (FanDuel card)

Runs at noon Eastern on every NFL Sunday, on Thanksgiving, and on Christmas.
Every step is a script in this directory; a fresh session can run it cold.
The projection engine is only used for player positions and teams. Every
probability on the card is read from FanDuel's own alternate ladders.

## 0. Preconditions

- Gmail tool available (send, search, get_message). Without it, stop and report.
- Repository checked out with `parlay/` present. If `parlay/fdpull.py` is not on
  the checked-out branch, fetch and check out `claude/fantasy-draft-advisor-9ufbgd`.
- The Odds API key: Gmail search `from:team@the-odds-api.com subject:"Welcome to The Odds API"`,
  open the message, copy the key. It is used once, inline, in step 1. Never print
  it, never write it to a file, never commit it.

## 0b. Refresh usage logs and grade the last card

    python3 gamelogs.py 2026-09-01 <yesterday YYYY-MM-DD> data/gamelogs_2026.json
    python3 fdgrade.py cards/<date of the last card>.json

`gamelogs.py` pulls box scores from ESPN's public site API (no key) and
merges new games into the season log; it is what the usage check in step
4 reads. `fdgrade.py` grades the previous card against the actual box
scores, writes `results/<date>.json`, and prints the running calibration.
Skip the grade if `results/` already has that date. Both files, plus
`data/gamelogs_2026.json`, are committed in step 7.

## 1. Pull the slate

    cd parlay
    ODDS_API_KEY=<key> python3 fdpull.py

Lists NFL events, keeps games kicking off today (Eastern) at least 20 minutes
out, pulls eight FanDuel markets per game (receptions, receiving yards,
passing yards, rushing yards, main and alternate) with bet-slip links. Eight
credits per game. If the month's remaining credits would not cover the slate
plus a 20-credit reserve it drops the two rushing markets on its own and says
so; `--lite` forces that. It also wipes every per-run file from the previous
build, `exclude.txt` included, so nothing stale survives. Writes
`events.json`, `ev_<id>.json`, `pull_meta.json`.

If it prints `NO GAMES TODAY`, stop. Send nothing. Report one line.

`--dry-run` lists the games without pulling odds and spends no credits.

## 2. Calibrate the book's margins

    python3 fdcal.py

Measures the two-way hold on main lines and the one-sided margin on alternate
rungs from today's actual prices. Writes `fdcal.json`.

## 3. Injury exclusions

Web-search the day's inactives and injury report for the teams in
`events.json`. Write `exclude.txt`, one player per line, for anyone listed
questionable, doubtful or out, plus any player whose starting quarterback is
out. Leave the file absent if nobody qualifies. Never guess a designation.

## 4. Build the card

    python3 fdfinal.py

Fits a two-parameter distribution to each player's alternate ladder, reads
every rung's hit probability from that curve, applies the usage check, and
searches three payout bands for the ticket with the highest joint
probability, which means the fewest legs that reach the band:

| ticket | band | legs tried | legs per game |
|---|---|---|---|
| A, high | +1000 to +2600 | 4 to 6 | 2 |
| B, medium | +500 to +999 | 3 to 5 | 2 |
| C, low | +250 to +499 | 2 to 4 | 2 |

Why fewest legs: FanDuel's margin is about 7 percent on every rung and flat
across the ladder (measured 2026-09-13), so each extra leg costs 7 percent
of the ticket's true hit rate at the same payout. At +1000 a 4-leg ticket
keeps 76 cents of true value per dollar and an 8-leg ticket keeps 58.

Usage check (`usage.py`): for every receiving or rushing rung, expected
targets or carries from the player's recent role (current season first,
last season only if still on the same team) give a second probability. The
leg uses the lower of the market's number and the usage number, and a leg
whose expected targets cannot cover the line is dropped as fragile. Week
one's ticket-killing misses were all usage failures (2, 4, 6, 6 targets).

Standing gates, all enforced in code: one leg per player across the whole
card; hit probability between 45 and 95 percent on the lower of the two
numbers (a 4-leg +1000 needs rungs near -115, which sit at 50 percent
before the margin cap, so a 50 floor would quietly forbid the shortest
tickets); cushion at least 10 percent; posted price no worse than -800;
line floors of 9.5 receiving yards, 2.5 receptions, 149.5 passing yards,
19.5 rushing yards; ladders with fewer than five distinct lines (four for
receptions) are not trusted; a rung is credited at most two points above
its own de-vigged price so a poor fit can never be harvested as edge;
running backs only on rushing-yard ladders, no quarterback rushing, no
running-back receiving; receivers must exist in the season engine. Tickets
share no players. On a small slate only the per-game cap relaxes, one step
at a time, the probability gate never does, and the card says so.
Writes `fdcard.json`, `fdsummary.json`, and `cards/<today>.json` (the
persisted card that next week's grade reads).

## 5. Render

    python3 fdrender.py

Writes `email_fd2.html` (Gmail-safe: `bgcolor` buttons, no style block),
`email_fd2.txt`, `part1.html` + `part2.html` (the same HTML in two halves for
a tool with a small read window), and `subject.txt`.

## 6. Send

One email, both recipients, HTML body plus the plain-text alternative:

- to: the two recipients named in the routine's prompt (addresses are never committed here)
- subject: contents of `subject.txt`
- htmlBody: `email_fd2.html` in full (read `part1.html` then `part2.html` and concatenate if the file cannot be read whole)
- body: `email_fd2.txt`

Never send a placeholder body. Send once. Before sending, search Gmail sent
mail for today's subject prefix; if a card already went out today, stop.

## 7. Commit the record

    git add cards results data/gamelogs_2026.json
    git commit -m "parlay: card and results for <date> [skip ci]"
    git push

Only those paths. Every other run output stays gitignored.

## Standing rules

- Never invent a line, a price, a matchup or a designation. A clear "not found" beats a guess.
- Report expected value honestly. Every long parlay at a real book is negative; the card says so.
- The card is model output, not advice, and the email says so.
- Run outputs (`ev_*.json`, `fdcard.json`, `email_fd2.*`, and the rest) are gitignored. A routine run commits only the record in step 7, plus a script fix if one was needed, on the working branch, with `[skip ci]` in the title.
- Credits: 500 per month on the free plan. A full Sunday costs about 104 with rushing markets, 78 without. `pull_meta.json` carries the remaining count and the email prints it; under 120, upgrade the plan before the next Sunday.
