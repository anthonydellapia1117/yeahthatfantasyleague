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
every rung's hit probability from that curve, and searches three payout bands:

| ticket | band | legs tried | legs per game |
|---|---|---|---|
| A, high | +1000 to +2600 | 8 to 11 | 3 |
| B, medium | +500 to +999 | 5 to 8 | 2 |
| C, low | +250 to +499 | 3 to 6 | 2 |

Standing gates, all enforced in code: one leg per player across the whole
card; cushion (mean minus line, over mean) at least 25 percent; hit probability
between 62 and 95 percent; posted price no worse than -700 (-800 for A); line
floors of 9.5 receiving yards, 2.5 receptions, 149.5 passing yards; ladders
with fewer than five rungs (four for receptions) are not trusted; a rung is
credited at most two points above its own de-vigged price so a poor fit can
never be harvested as edge; running backs only on rushing-yard ladders, no
quarterback rushing, no running-back receiving; receivers must exist in the
season engine. Tickets share no players. On a small slate only the per-game
cap relaxes, one step at a time, the probability and cushion gates never do,
and the card says so.
Writes `fdcard.json`, `fdsummary.json`.

## 5. Render

    python3 fdrender.py

Writes `email_fd2.html` (Gmail-safe: `bgcolor` buttons, no style block),
`email_fd2.txt`, `part1.html` + `part2.html` (the same HTML in two halves for
a tool with a small read window), and `subject.txt`.

## 6. Send

One email, both recipients, HTML body plus the plain-text alternative:

- to: anthonydellapia@gmail.com, alexaragozzino@yahoo.com
- subject: contents of `subject.txt`
- htmlBody: `email_fd2.html` in full (read `part1.html` then `part2.html` and concatenate if the file cannot be read whole)
- body: `email_fd2.txt`

Never send a placeholder body. Send once. Before sending, search Gmail sent
mail for today's subject prefix; if a card already went out today, stop.

## Standing rules

- Never invent a line, a price, a matchup or a designation. A clear "not found" beats a guess.
- Report expected value honestly. Every long parlay at a real book is negative; the card says so.
- The card is model output, not advice, and the email says so.
- Run outputs (`ev_*.json`, `fdcard.json`, `email_fd2.*`, and the rest) are gitignored. Commit nothing from a routine run unless a script needed a fix; then commit only the fix, on the working branch, with `[skip ci]` in the title.
- Credits: 500 per month on the free plan. A full Sunday costs about 104 with rushing markets, 78 without. `pull_meta.json` carries the remaining count and the email prints it; under 120, upgrade the plan before the next Sunday.
