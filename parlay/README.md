# Sunday Prop Parlay Engine

A standalone side project. It borrows the YeahThatFantasyLeague projection
engine as an input and shares none of its purpose, its league rules, or its
deployment. Nothing here reads or writes YTFL state.

## What it answers

Given a Sunday slate, which combinations of player props maximise expected
value inside a chosen payout band.

## The governing identity

A parlay's legs have true probabilities `p_i` and book-implied
probabilities `q_i`. The payout is the product of the decimal prices,
which is the product of `1/q_i`. So

```
EV per dollar = (joint probability) x (payout)
             = product(p_i) x product(1/q_i)      [if legs are independent]
             = product(p_i / q_i)
```

Expected value is the **product of the per-leg edge ratios**. Leg count
does not appear. Payout length does not appear. Only edge per leg, and how
many times you multiply it.

Three consequences follow, and they drive every decision in this repo.

### 1. Long stacks of likely legs beat short stacks of longshots

Two tickets with the same 6 percent edge per leg:

| structure | payout | hit rate | EV per $1 |
|---|---|---|---|
| 8 legs at -250 | +1376 | 10.65% | **1.572** |
| 3 legs at +260 | +4566 | 2.62% | 1.223 |

Same edge per leg, very different outcome, because `1.06^8 = 1.59` and
`1.06^3 = 1.19`. The longer stack multiplies the edge more times.

### 2. Edge is easier to hold on likely legs

Edge is a ratio, so a fixed error in the probability estimate does
proportionally more damage where the probability is small.

| model p | implied q | edge | edge if p is over-estimated by 0.05 |
|---|---|---|---|
| 0.80 | 0.741 | 1.080 | 1.012 (keeps 94% of edge) |
| 0.50 | 0.476 | 1.050 | 0.945 (edge gone) |
| 0.18 | 0.160 | 1.125 | 0.812 (deeply negative) |

A five-point miss costs six percent of the edge at p = 0.80 and destroys
it at p = 0.18. That asymmetry, not the payout, is the reason to build
long stacks of likely legs.

### 3. The same mechanism compounds the vig, so edge must be real

If every leg is fairly priced and the book holds 4.5 percent, the edge
ratio per leg is `1/1.045 = 0.957` and it compounds downward.

| legs | payout | kept per $1 with no edge |
|---|---|---|
| 3 | +174 | 0.876 |
| 6 | +653 | 0.768 |
| 10 | +2793 | 0.644 |

**Without a genuine per-leg edge, more legs is strictly worse.** The
structure only pays when something real offsets the hold.

## Where the edge actually comes from

Not from out-projecting the book. Validation below shows the model lands
within 6 to 10 percent of market lines on its good categories, which is
respectable and is nowhere near enough to beat the price on a single leg.

The edge is **correlation**. A parlay priced as if its legs were
independent, whose legs are in fact positively correlated, pays more than
the joint probability deserves. Measured lift, Gaussian copula:

| structure | independent | correlated | lift |
|---|---|---|---|
| QB pass yards + his WR1 receiving yards, r = .50 | 56.2% | 62.0% | +10.2% |
| QB completions + WR1 recs + TE recs, r = .40 | 43.9% | 52.9% | +20.5% |
| 4-leg single-game stack, r = .35 | 33.4% | 44.5% | +33.5% |
| 4 legs in four different games | 33.4% | 33.4% | +0.2% |

Scattering legs across games earns nothing. Concentrating them inside one
offence earns a third more joint probability at the same price. The whole
optimiser exists to find the densest correlation that still clears the
payout band.

**Caveat that must not be lost:** many books now price a same-game parlay
with a correlation adjustment, which claws back most of this lift. The
edge is largest where the legs can be combined without that adjustment.

## Model validation

Season fantasy points are inverted into per-game stat means, then scaled
by the Vegas implied team total. Checked against real market lines:

| prop category | mean absolute error vs market |
|---|---|
| Receiving yards, receptions | 6% |
| Passing yards, completions | 6% |
| Rushing yards | 10% |
| **Quarterback rushing yards and carries** | **35 to 63%** |

Quarterback rushing is **excluded from every ticket**. The rush/pass split
of a quarterback's fantasy points is a free parameter that a single
fantasy total cannot pin down, so the model has no information there and
says so rather than guessing.

Anytime-touchdown props are also excluded: touchdown rate is the highest
variance term in the projection and is already embedded in the fantasy
total rather than independently estimated.

## Distributions

- **Counts** (receptions, completions): negative binomial, variance-to-mean
  1.45. Target share itself varies week to week on top of the catch
  process, so counts are overdispersed relative to Poisson.
- **Yardage**: gamma, shape fixed by the empirical coefficient of
  variation (0.55 receiving, 0.50 rushing, 0.28 passing). Gamma rather
  than normal because yardage cannot go negative and is right-skewed; a
  normal model puts real mass below zero for low-volume players and
  systematically overprices the under.
- **Joint probability**: Gaussian copula. Each leg's marginal maps to a
  latent normal threshold, latents are correlated through a Cholesky
  factor, and the orthant probability is estimated by Monte Carlo. With
  the identity matrix this collapses to the independent product, which is
  the correct default for legs in different games.

## Files

| file | role |
|---|---|
| `propmath.py` | odds conversion, de-vigging, distributions, copula, Kelly |
| `project.py` | season fantasy points to per-game prop means |
| `build.py` | correlation matrix and ticket scoring |
| `optimize.py` | searches leg combinations for best EV inside a payout band |
| `run_sunday.py` | orchestrator: slate in, five tickets out, email sent |

## Honest limits

- The engine prices probability. It does not have a live odds feed, so it
  reports the fair price and the minimum acceptable price per leg, and the
  bettor confirms the real number at the book.
- Projections are preseason and do not yet incorporate in-season form.
- Correlation coefficients are literature and judgement values, not fitted
  from a labelled sample of this season's games.
- Nothing here is a guarantee. A positive expected value is a statement
  about a long run of identical decisions, not about one Sunday.

---

## Calibration against real book prices (2026-09-13)

Two real Fanatics tickets were transcribed and priced against the model.
They are the first live prices the engine has seen and they corrected two
things.

**The hold is a total on the ticket, not a per-leg multiplier.** The
nine-leg ticket priced at +1237 against a model-correlated fair of +1330,
which is a 7 to 8 percent total hold. Applying that same 8 percent per leg
would have implied an 85 percent total, and an earlier version of the
search did exactly that, which is why it returned no viable ticket above
+1000. `book_decimal = (1 / joint_correlated) / (1 + total_hold)`.

**Fanatics already prices the correlation inside a same-game parlay.**
The offered price sits near the model's *correlated* fair and far from its
*independent* fair:

| ticket | independent fair | correlated fair | offered |
|---|---|---|---|
| 7-leg | +1693 | +936 | +667 |
| 9-leg | +2864 | +1330 | +1237 |

So the correlation lift documented above is **not** free money on that
book's same-game product; it is already in the price. No ticket structure
beats their pricing. Expected value under this model is the same for every
ticket and equals `1 / (1 + hold)`. What structure still controls is
robustness, not edge.

**Cushion is the metric that survives.** Cushion is the distance between
the projection and the line, as a fraction of the projection. Of the seven
legs on the losing ticket, six had 20 to 35 percent cushion and one had 4
percent; that one leg was a coin flip and accounts for most of the gap
between the two tickets' prices. The optimiser now maximises the *minimum*
cushion across a ticket subject to the payout band, which is the right
objective when per-leg book prices are not visible.

**One projection was materially wrong.** Solving for the Skattebo mean
that reconciles both tickets to a common hold gives 86 rush-and-receiving
yards against the model's 74, a 17 percent gap. The engine runs preseason
projections and had not repriced the Giants for Nabers being questionable.
In-week injury repricing is now a named limitation.

## Deep links into a bet slip

Researched 2026-09-13.

| book | possible | mechanism |
|---|---|---|
| DraftKings | yes | `dksb://sb/addbet/{outcomeId}` custom scheme |
| FanDuel | yes | `.../addToBetslip?marketId=..&selectionId=..` |
| Fanatics | **no** | no scheme, no documented betslip link, none known |

Neither working format is published by the book. Both need that book's
internal market and selection ids, which come from a paid or free-tier odds
feed rather than from the book itself. The Odds API returns them with
`includeLinks=true` and `includeSids=true` on a free 500-credit tier, which
is the cheapest route to tappable legs for DraftKings and FanDuel. Fanatics
has no route at all.

---

## Real per-leg prices and bet-slip links (2026-09-13, afternoon)

The Odds API (an existing key in the owner's inbox from April) returns
FanDuel player props with `includeLinks=true` and `includeSids=true`. Every
outcome, including every alternate rung, carries a FanDuel
`addToBetslip?marketId=..&selectionId=..` link. Five late games returned
1,234 priced outcomes. `fdlines.py` flattens them, `fdcal.py` measures the
book's margins, `fdfinal.py` prices and builds, `email_fd.py` renders with
a tappable button per leg.

Three findings, in order of how much they change the picture.

**FanDuel's implied outcome spreads are wider than the model's.** Fitting a
two-parameter distribution to each alternate ladder recovers the book's own
view: receiving-yard coefficient of variation median 0.70 against the
model's 0.55; passing 0.35 against 0.28; receptions dispersion 1.25 against
1.45. On yards the model was too tight, so it overstated the chance of
clearing any deep alternate line. Every apparent per-leg edge in the first
FanDuel build came from that error, and the optimiser found it because
that is what optimisers do. Probabilities are now read from the book's own
fitted curve, with no credit taken for the model.

**The alternate-ladder margin is 7.1 percent, measured, not assumed.** Where
an alternate rung sits on the same line as the two-way main line, the
alternate's implied probability exceeds the de-vigged main by a median 3.7
points. Two-way main-line hold is 6.1 percent.

**The morning's "8 percent hold" on the owner's 9-leg Fanatics slip was
wrong.** Re-priced with FanDuel's fitted spreads, that slip has a 4.4
percent correlated hit rate and a fair price near +2200 against +1237 paid.
Long alternate-line parlays are steeply negative on both books. The
defensible play is fewer legs, wider cushion, smaller stakes, and the
platform question is settled by building identical legs in both apps and
comparing slip totals, not by anything on this page.

`fdfinal.py` builds tickets with no correlation credit, because FanDuel
groups same-game legs into an SGP and reprices them; the emailed price is
the straight product of posted prices and the slip total is the real one.
