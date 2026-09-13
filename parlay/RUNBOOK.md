# Weekly runbook

The automation fires Sunday morning and runs this sequence. Each step names
the module that does the work, so a fresh session can pick it up cold.

## 1. Slate

Research the current week's Sunday schedule: kickoff times in Eastern, point
spread and game total per game, and the Sunday-morning injury report for the
games that have not yet kicked off. Discard any game whose kickoff has passed.

Split each total into two team totals with `project.implied_totals(spread_home, total)`.

## 2. Projections

`project.load_engine('../out/engine_2026.json')` reads the YTFL season
projections. `receiver_game`, `back_game` and `qb_game` invert season fantasy
points into per-game stat means and scale them by the team implied total.

Drop any player carrying a questionable or worse designation. Drop the whole
team if its starting quarterback is in doubt.

## 3. Validate before trusting

Pull whatever real prop lines can be found for the slate and compare them to
the model means. The market line is the market's estimate of the mean, so the
gap is the model error. If mean absolute error on receiving and passing props
exceeds 12 percent, stop and report rather than betting: the decomposition
constants need refitting.

**Quarterback rushing props are permanently excluded.** Validation puts model
error there at 35 to 63 percent because the rush/pass split of a quarterback's
fantasy points is not recoverable from a single fantasy total.

## 4. Leg library

Build candidate legs at several standard lines per player, keep those with hit
probability between 0.62 and 0.93, then apply the practical price filter: no
leg whose fair price is worse than -600, because books do not post those and
the capital efficiency is poor.

## 5. Search

`fastjoint.joint_one_factor` scores candidate tickets quickly; the full
`propmath.joint_probability` copula verifies the finalists. **One leg per
player** is enforced, which both avoids the correlation books price most
aggressively and keeps the one-factor approximation accurate to about 4 percent.

Search three payout bands: 250 to 499, 500 to 999, and 1000 plus. Rank by
expected value at a 7 percent effective hold, which is realistic for deep
alternate lines.

## 6. Robustness gate

Every ticket must clear expected value above 1.0 at the 7 percent hold, and the
report must state its expected value after a 5 and 10 percent haircut on the
projected means. A ticket that only works at zero haircut is model error, not
edge, and should be labelled as such.

## 7. Card assembly

Pick one high, two medium, two low, with at most 40 percent leg overlap between
tickets. Simulate the whole card **with shared legs moving together** so the
reported all-miss probability is honest rather than the naive independent one.

Stakes are quarter Kelly on the correlated hit probability.

## 8. Send

`email_build.render` produces the HTML. Email both a plain-text and an HTML
body to the owner. Always include: minimum acceptable price per leg, the
concentration warning naming any leg that appears in three or more tickets,
and the expected value under haircut.

## Standing rules

- Never invent a line, a price, or a matchup. A clear "not found" beats a guess.
- Never include a player with an unresolved injury designation.
- Report expected value honestly even when it is thin or negative.
- The card is model output, not advice, and the email must say so.
