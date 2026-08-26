# YeahThatFantasyLeague - What I'm Building and Why

**A 13-season investigation into one question, and the tool it produced.**
Draft day: September 8, 2026. Twelve teams, snake, full PPR.

---

## The question I actually asked

I have played in this league for thirteen seasons. I have never won it.

Two men have three titles each. I have zero. So I asked what seemed like the obvious question:

> **What do champions in this league do on draft day that I don't?**

I did not want folklore. I wanted it measured - against every pick, every roster, every transaction, and every result the league has ever produced. 2,339 draft picks. 37,106 weekly roster rows. 3,938 transactions. Thirteen champions.

---

## The answer, and it is not the one anyone wants

**There is no draft-day roadmap. Eight separate hypotheses were tested. All eight are null.**

| What people believe | What the data says |
|---|---|
| Champions wait on quarterbacks | 6.46 rounds vs 5.92 - p = 0.252. Folklore. |
| Champions avoid early QBs | 62% vs 48% - p = 0.266. Folklore. |
| Champions load up on running backs | 2.15 vs 2.01 in rounds 1-5. Noise. |
| Champions load up on receivers | 2.00 vs 2.03. Noise. |
| Draft slot matters | Champions spread across seats 2 through 12. No pattern. |
| Roster construction predicts finish | Correlations of -0.01, -0.05, +0.11. All zero. |
| Keeping your drafted players wins | Correlation +0.04. Dead. |
| Spending aggressively on waivers wins | p = 0.197. Dead. |

**No two champions drafted the same way.** Here are all thirteen, rounds one through five:

```
2013 Ronnie        QB WR RB RB WR      2020 Ronnie        RB RB QB WR WR
2014 GaTTa         TE WR TE WR RB      2021 Rob & GregBo  WR RB QB WR RB
2015 Chris & Dom   WR TE RB QB RB      2022 Cambrias      RB RB WR RB RB
2016 Chris & Dom   WR WR WR RB TE      2023 Phil Baldino  WR RB RB RB WR
2017 Richie        WR RB RB WR WR      2024 Phil Baldino  WR RB WR QB TE
2018 Phil Baldino  RB WR RB WR RB      2025 Cambrias      RB RB TE RB WR
2019 Cambrias      RB WR RB WR WR
```

And the most striking number in the whole project: **the consensus #1 player on the board has been drafted by the eventual champion exactly 0 times in 13 seasons.** Chasing the best available name has never once won this league.

### The uncomfortable part

I am not unlucky. I am not passive. I am not bad at this.

| | Me | Cambrias (3 titles) |
|---|---|---|
| Share of points from drafted players | 65.4% | 65.2% |
| Transactions per season | 36.2 | 35.0 |
| Luck (all-play gap) | -0.005 | 0.000 |

**On every input anyone can measure, I am the statistical twin of a three-time champion.** I lost the 2025 final by 12.44 points.

### The one thing that survived

**Lineup efficiency** - the share of your optimal points you actually started. Champions 89.75% against a field of 88.44%, p = 0.078. Above the significance line, so it is a lead, not a finding. But it's the only one standing.

I sit at 88.55%, seventh of fifteen. That's **15.14 points left on my bench every week, 212 a season.** The gap to Phil Baldino is 21 points a season, against a title lost by 12.44.

Then I tested *that*, and it got humbler still: only **14%** of my lost running-back points were knowable at lineup lock. 65% were hindsight spikes nobody could have predicted. And Baldino isn't reading matchups better than me - **he just makes fewer moves. 69 career swaps to my 107.** Pure discipline is worth about 10 points a season.

**So the honest bottom line: there is no secret. There is a small, real edge in not fiddling, and there is the draft itself - where the only thing that has ever mattered is knowing what the board will actually do.**

---

## Which is why the tool is about the board, not about champions

Since champion-mimicry is provably worthless here, the engine models the only things that are real:

1. **What a player is worth** - projected points under *this league's* exact scoring, converted to value over replacement. Not generic rankings. My league pays 6 points for passing touchdowns; using a standard board would have under-valued every quarterback by 40 to 66 points a season.
2. **Whether he'll still be there** - a probability fitted to *this league's own* 2,039 historical picks. Not a national average. How *these twelve people* actually deviate from consensus.
3. **Who picks before I do** - every seat between my turns, and what each of them historically reaches for.

That third one is the piece I most wanted, and its story is worth telling because it shows how the whole project works.

**Opponent tendencies are real and they persist.** Correlation of +0.813 between how a franchise drafted 2013-2019 and 2020-2025, with a p-value under 0.00002. Ronnie takes running backs in the first three rounds at nearly twice Chris & Dom's rate, and has for a decade. That is the single strongest signal in this entire investigation.

**And I still refused to put it into the math.** When I folded it into the survival probabilities and tested it, the forecasts got *worse*. The reason is beautiful: with ten or twelve seats between my picks, Ronnie's running-back appetite cancels Chris & Dom's aversion, and the group averages out to exactly league-normal. The effect only survives at the turn, where only two or three seats pick in between.

So it ships as **something I look at**, not something the model believes. Which is the rule this whole project runs on: *a number that cannot survive being tested does not get to influence a decision.*

---

## The App: what it looks like and how to read it

One file. Opens in a browser by double-clicking. No server, no login, no internet dependency beyond the live league feed. It has **two modes and it switches between them by itself.**

---

### MODE 1 - Pre-Draft *(what it shows today, and until the order is drawn)*

**Top bar.** Title on the left, a status chip on the right reading `MODE 1 - PRE-DRAFT - all 12 scenarios`. The chip is the app telling me what it thinks the world is doing.

**Panel 1: The table, as mapped today.** A twelve-row grid - one row per seat.

| Seat | Handle | Franchise era | 1st QB | 1st TE | n_eff |
|---|---|---|---|---|---|
| 5 | dcambs | Cambrias | 8.26 | 5.17 | 5.62 |
| 7 | antdell | Antdell & Ernie | 7.57 | 6.03 | 5.35 |
| 9 | pbaldino | Phil Baldino | 5.23 | 5.84 | 4.96 |

This is *who is in the room*, translated from Sleeper handles into thirteen years of history. "1st QB 8.26" means the Cambrias typically take their first quarterback around round eight - the latest in the league. `n_eff` is how much history that number rests on; anything thin is labelled so I never quote a number that's really just one season wearing a costume.

**Panel 2: Twelve tabs, one per seat.** Because the draft order isn't drawn yet, the app plans for *every* seat I could get. When Sleeper posts the order it collapses to mine automatically and says so.

**Panel 3: The card itself.** This is the heart of it. One row per round:

| Rd | Pick | **Best available and why** | **Wait or reach** | **Watch** |
|---|---|---|---|---|

- **Best available and why** - the name in bold, then the reasoning in plain sight: value over replacement, tier, ADP, the odds he's even there, and an injury flag in red if he's questionable. A fallback name sits underneath in small type.

- **Wait or reach** - the column I built this app for. A single verdict, **WAIT in green** or **TAKE NOW in red**, and then the actual sentence:

  > *Take **Breece Hall** now - 66% he is gone by pick 42.*
  > *Or wait: **Cam Skattebo** projects within 5 points and is 76% to last to your next pick.*

  That is the entire draft in two lines. Not "who is best" - every ranking site answers that. **"What does waiting actually cost me?"**

- **The seat strip**, directly under the verdict - the piece I wanted most:

  > **10 seats pick before your next turn** - collectively 1.00x league average at RB
  > `Frank & Julian 0.94x` `Phil Baldino 1.08x` `Ronnie 1.22x` `Chris & Dom 0.83x` …

  Red chips are the threats, green are the safe ones. When it says 1.00x collectively, that is the app being honest that this particular gap washes out - and when it doesn't, I'll see it immediately.

- **Watch** - tier cliffs ("RB tier empties before your next turn"), coin flips between players too close to separate, and which specific franchises are due to take a quarterback or tight end before I pick again.

---

### MODE 2 - Live *(it arms itself the moment the draft starts)*

The league gives me **a pick clock - 60 seconds in the live 2026 draft - and if I blow it I forfeit the pick.** So this screen is built to be read in under five seconds from across a room. The room reads the duration from the draft's own settings; the two-minute figure in earlier drafts of this document was the old Yahoo-era rule and was never the Sleeper timer.

**The clock, huge, counting down**, turning red under thirty seconds. Above it: which seat is on the clock, by franchise name, and whether it's me.

**The answer, in 64-point type.** One name. Position, team, value, tier underneath. Injury flag if relevant. That's it - that's the decision.

**Two runners-up** in normal size, each labelled with why it's not the pick, or flagged as a coin flip if it's genuinely too close.

**The wait-or-reach line**, now recalculated against *the players actually gone*, not the pre-draft model.

**Survival table** - the top fourteen players still on the board, each with the odds he survives to my next pick, with "going, going" flagged on anyone under 40%. This is the panel that tells me whether to grab now or trust the board.

It polls the league every ten seconds while drafting, backs off to sixty when idle, and if the connection drops it says so honestly and keeps showing the last good model with its age stamped on it.

---

## What the perfect draft day looks like

**The morning of September 8th,** I run one command. Projections, ADP, and injury statuses all move daily, so the board rebuilds from that morning's truth.

**I open one file.** It already knows my seat, who's sitting on either side of me, and what each of them has done for thirteen years.

**When my pick comes,** I don't scroll rankings and I don't panic. I read one name, and one sentence telling me what waiting costs. If the answer is *wait*, I wait - with a number behind it, not a feeling.

**When someone reaches,** the board updates in ten seconds and every probability recalculates against who is actually gone.

**And I stop reaching.** Because the single largest thing this project found is that the old version of this engine systematically told me players were more likely to vanish than they were - on 133 of 144 cards, by an average of 21 percentage points. That is precisely the pressure that makes you take a guy a round early. It's fixed. Several **TAKE NOW** calls are now correctly **WAIT**.

---

## What's still to come

**An in-season start-sit tool.** The evidence says my measurable leak isn't the draft at all - it's lineup decisions, and specifically running backs in the last four seasons. But it also says most of that leak isn't knowable from season averages; it needs live weekly projections at the moment lineups lock. That's a September build, on the same verified foundation.

---

## The rule this whole thing runs on

Every number in this app traces to a file I can open. Nothing is asserted without a sample size and a confidence attached. When something failed its test, it got recorded as a failure and kept out of the math - including the feature I most wanted.

**Four bugs were found in the survival model in a single day, three of them by an independent audit checking my own work.** One of them meant the consensus #1 player was listed as 50% likely to be available at pick 1 - before anyone had drafted anything.

That is the point. **A fantasy tool that tells you what you want to hear is worth nothing.** This one is built to be provably right, or to say plainly that it doesn't know.
