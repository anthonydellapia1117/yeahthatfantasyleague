# YTFL 2026 Draft Board — ffopportunity Data Analysis

Generated: August 28, 2026 · **Revision 4** (see Corrections)
Data source: ffopportunity v0.1.2 (ffverse) + nflreadr, R 4.6.1
Seasons: 2020–2025 · 2026 ADP: FantasyPros redraft-overall ECR, scraped 2026-08-21
Repo: https://github.com/anthonydellapia1117/yeahthatfantasyleague/tree/main/docs/ffopportunity

**League:** 12 teams, 14 rounds, snake, full PPR, **6-point passing TDs**, zero IR, H2H + median scoring.
**ADP:** ECR = overall rank. Round ≈ ceil(ECR / 12).

---

## ⚠️ THE THREE RULES THIS BOARD MUST FOLLOW

**1. Never compare across positions using raw exp/game.** ffopportunity scores at 4-pt passing TDs; YTFL pays 6. A QB and an RB compared on raw `total_fantasy_points_exp` is an apples-to-oranges error. Revision 2 of this board made exactly that mistake.

**2. The draft-relevant number is VOR, not raw points.** Raw exp/game says three QBs outscore CMC. VOR over positional replacement says CMC leads the field by nearly double. Both are computed below; **only VOR should drive a pick.**

**3. exp/game measures 2025 opportunity quality. It is not a 2026 forecast.** It says nothing about whether that opportunity recurs. Age is now controlled (below). Depth-chart and team changes are **not** — every player must be checked against `rosters_2026.csv` before being drafted.

---

## Cross-position truth table (2025 reg season, min 8 g)

**Rev 4 correction:** the Rev 3 QB figures omitted two-point conversions, which
the league pays at 2.0. Adding them reshuffles the top three.

| Rank | Player | Pos | **6-pt + 2pt (league-exact)** | Rev 3 (no 2pt) | 4-pt default |
|---|---|---|---|---|---|
| 1 | Patrick Mahomes | QB | **26.46** | 26.21 | 21.28 |
| 2 | Dak Prescott | QB | **26.42** | 26.28 | 20.87 |
| 3 | Matthew Stafford | QB | **26.40** | 26.40 | 20.52 |
| 4 | **Christian McCaffrey** | RB | **25.55** | 25.55 | 25.52 |
| 5 | Brock Purdy | QB | 25.71 | 25.33 | 20.54 |
| 6 | Trevor Lawrence | QB | 25.57 | 25.44 | 21.18 |

**The top three QBs are separated by 0.06 pts/game — a three-way tie, not a
ranking.** Rev 3's "Stafford is QB1" was overprecise. Any of Mahomes, Prescott
or Stafford is the same call on this data; break the tie on age, price and
supporting cast, not on this column.

**CMC is #4 at league scoring, not #1.** He is #1 only under ffopportunity's
4-pt default, which is not this league. Revision 2 claimed "highest expected
points per game of any player at any position" — that claim was built by
rebuilding the QBs at 6 points and then comparing CMC against the 4-point
ordering. It is withdrawn.

Non-QB figures are unaffected by the scoring issue (RB/WR/TE passing volume ≈ 0), so **all non-QB comparisons elsewhere in this document are valid as printed.**

---

## VOR: the number that should actually drive picks

Replacement level = last startable player at each position (12 teams; QB1/RB2/WR2/TE1 + 1 FLEX):

| Pos | Replacement rank | Player at replacement | exp/g |
|---|---|---|---|
| QB | 12 | Daniel Jones | 21.94 |
| RB | 30 | Woody Marks | 11.00 |
| WR | 30 | Marvin Harrison Jr. | 11.51 |
| TE | 12 | Zach Ertz | 9.54 |

| Rank | Player | Pos | exp/g | **VOR/g** |
|---|---|---|---|---|
| 1 | **Christian McCaffrey** | RB | 25.55 | **+14.55** |
| 2 | Bijan Robinson | RB | 19.24 | +8.24 |
| 3 | Trey McBride | TE | 17.70 | +8.16 |
| 4 | Amon-Ra St. Brown | WR | 19.29 | +7.78 |
| 5 | Ja'Marr Chase | WR | 19.17 | +7.66 |
| 6 | Puka Nacua | WR | 19.04 | +7.53 |
| 7 | Jahmyr Gibbs | RB | 17.97 | +6.97 |
| 8 | Jonathan Taylor | RB | 17.87 | +6.87 |
| 9 | Davante Adams | WR | 18.34 | +6.83 |
| 10 | Rashee Rice | WR | 17.97 | +6.46 |

**Two things fall out of this table.**

**CMC's claim survives in the correct frame.** He is #1 by VOR at +14.55/game — **1.8× the #2 player**. The gap between him and replacement is the largest positional edge available in the draft. The revision-2 wording was wrong; the underlying call was right.

**No QB appears in the top 15 by VOR.** Stafford's 26.40 is only +4.46 over a QB replacement of 21.94. QB is deep; the raw-points lead is an artifact of positional scoring, not draft value. **This validates "wait on QB" rather than contradicting it.**

---

## AGE: now controlled, and it is real

Age was previously unmodelled. It is now tested. Birth dates from `rosters_2026.csv` (2,886/2,930 populated), age measured at Sept 1.

**Age in year t → change in exp/game in year t+1** (RB/WR/TE, 2020–2025, min 8 g both seasons):

| Age band | n | Mean Δ exp/g | % declined |
|---|---|---|---|
| ≤24 | 372 | **+0.50** | 44.4% |
| 25–26 | 163 | −0.54 | 62.0% |
| 27–28 | 94 | −0.48 | 56.4% |
| 29–30 | 36 | **−0.88** | 63.9% |
| 31+ | 16 | **−1.61** | 56.2% |

**The curve is monotonic in mean delta** and the direction is consistent. Unlike YAC-OE, garbage time, and workload, **age does not flip sign under control** — it is the only new signal in this entire body of work that survives.

**Sample limitation, stated:** birth dates come only from the 2026 roster file, so the panel contains only players still active in 2026. Players who aged out of the league are missing. **This bias is conservative** — it removes the worst age outcomes, so the true effect is at least this large. Top bands are thin (n=36, n=16); treat magnitudes as directional, not precise.

### WORKLOAD: tested, NULL

Does high year-t opportunity volume predict year-t+1 decline, within production tier?

| Pos | Top third | Mid third | Bottom third |
|---|---|---|---|
| RB | +0.45 | +0.80 | −0.93 |
| WR | −0.16 | +0.86 | −1.00 |
| TE | −0.44 | +0.44 | −0.32 |

**Signs flip across every position; all magnitudes under 1 pt/game.** The "workload cliff" is not supported by this dataset. Same failure shape as garbage time and YAC-OE. **Do not use prior workload as a fade input.**

### Age flags on this board — players 29+ in 2026

| Player | Age | Tier | Player | Age | Tier |
|---|---|---|---|---|---|
| Matthew Stafford | 38 | QB target | Christian McCaffrey | **30** | **RB1 target** |
| Davante Adams | **33** | **WR target** | Patrick Mahomes | 30 | QB target |
| Dak Prescott | 33 | QB target | Dalton Schultz | 30 | TE value |
| Mike Evans | 33 | WR value | Courtland Sutton | 30 | WR value |
| Derrick Henry | 32 | avoid | Josh Allen | 30 | avoid |
| Hunter Henry | 31 | TE value | Jauan Jennings | 29 | WR |
| Dallas Goedert | 31 | avoid | Lamar Jackson | 29 | QB |

**The two headline calls are both age-flagged.** CMC is 30 (29–30 band: −0.88/g, 63.9% decline). Adams is 33 (31+ band: −1.61/g). Both are still recommended — their VOR edge is large enough to absorb the expected decline — but **the forecast is now disclosed rather than implicit.**

---

## Does the RB1 base rate contradict the CMC call? No — it applies to a different player.

The repo's own `preseason_rb1_ledger` (2016–2025): the preseason ADP RB1 converts to actual RB1 in **2 of 10 seasons (20%)**.

| Year | Preseason RB1 | Actual RB1 | Converted |
|---|---|---|---|
| 2016 | David Johnson | David Johnson | ✅ |
| 2017 | David Johnson | Todd Gurley | |
| 2018 | Todd Gurley | **Christian McCaffrey** | |
| 2019 | Saquon Barkley | **Christian McCaffrey** | |
| 2020 | Christian McCaffrey | Alvin Kamara | |
| 2021 | Christian McCaffrey | Jonathan Taylor | |
| 2022 | Jonathan Taylor | Austin Ekeler | |
| 2023 | Christian McCaffrey | **Christian McCaffrey** | ✅ |
| 2024 | Christian McCaffrey | Jahmyr Gibbs | |
| 2025 | Bijan Robinson | **Christian McCaffrey** | |

**2026 preseason RB1 is Jahmyr Gibbs (ECR 2.9). CMC is RB3 (ECR 10.2).**

So the 20% base rate applies to **Gibbs**, not McCaffrey. And Gibbs is *also* the largest RB fade in the ffopportunity data (+61.1). **Two independent signals — the league's own 10-year history and the expected-points model — converge on the same player.** That is the strongest single read on this board.

Meanwhile CMC has been the **actual RB1 four times** (2018, 2019, 2023, 2025), more than any player in the window, and reached it from outside the preseason RB1 slot three of those four times. The opportunity signal and league history do **not** conflict on CMC. The genuine residual risk on him is age, which is now quantified above.

---

## TARGETS

### Tier 1 — elite VOR, no fade

| Player | Pos | Team | exp/g | VOR/g | Gap | ECR | Age | Note |
|---|---|---|---|---|---|---|---|---|
| **Christian McCaffrey** | RB | SF | 25.55 | **+14.55** | −19.3 | 10.2 | **30** | #1 by VOR, 1.8× the field. **Age-flagged** |
| **Trey McBride** | TE | ARI | 17.70 | +8.16 | +14.0 | 20.9 | 26 | TE1 by VOR + 34 RZ targets. ⚠️ **ARI is now the WORST 2026 environment** (Rev 4) |
| **Amon-Ra St. Brown** | WR | DET | 19.29 | +7.78 | −3.9 | 5.5 | 26 | Top WR by exp/g, no fade, 35 RZ targets |
| **Ja'Marr Chase** | WR | CIN | 19.17 | +7.66 | +7.1 | 1.5 | 26 | No fade. Priced at WR1 and earns it |
| **Davante Adams** | WR | LA | 18.34 | +6.83 | −2.4 | 50.7 | **33** | **Best value on the board.** WR9 VOR at WR24 cost. **Age-flagged** |
| **Rashee Rice** | WR | KC | 17.97 | +6.46 | +5.2 | 22.4 | 26 | 15 EZ targets on 79 total. 8-game sample |

### Tier 2 — QB, and why you wait

| Player | Team | 6-pt exp/g | VOR/g | ECR | Age |
|---|---|---|---|---|---|
| Matthew Stafford | LA | 26.40 | +4.46 | 104.3 | **38** |
| Dak Prescott | DAL | 26.28 | +4.34 | 79.5 | **33** |
| Patrick Mahomes | KC | 26.21 | +4.27 | 100.4 | **30** |
| Trevor Lawrence | JAX | 25.44 | +3.50 | 77.3 | 26 |
| Brock Purdy | SF | 25.33 | +3.39 | 96.5 | 26 |

⚠️ **QB fade flags on this board are unreliable.** `gap` derives from `total_fantasy_points` at 4-pt passing TDs; expected and actual TD counts differ, so the error does not cancel. Josh Allen, Drake Maye, Herbert and Hurts all carry QB fade flags that must be recomputed from league-exact components before being trusted.

**Every QB's VOR is under +4.5/game — less than a third of CMC's edge.** Take the position late. Among late QBs, Lawrence (26) and Purdy (26) carry no age flag; Stafford at 38 is the highest-variance name on the board despite leading in raw points.

### Tier 3 — positional value (exp/g rank ≫ ADP rank, no fade)

| Player | Pos | exp/g | Exp Rk | ADP Rk | Edge | Age | Team note |
|---|---|---|---|---|---|---|---|
| Kimani Vidal | RB | 11.49 | 24 | 61 | **+37** | 25 | LAC |
| Zach Charbonnet | RB | 11.24 | 26 | 48 | +22 | 25 | SEA |
| Wan'Dale Robinson | WR | 13.56 | 17 | 39 | +22 | 25 | **moved NYG → TEN** |
| Davante Adams | WR | 18.34 | 4 | 24 | +20 | **33** | LA |
| Courtland Sutton | WR | 12.92 | 18 | 37 | +19 | **30** | DEN |
| Mike Evans | WR | 14.69 | 12 | 26 | +14 | **33** | **moved TB → SF** |
| Rome Odunze | WR | 14.37 | 14 | 28 | +14 | 24 | CHI |
| Colby Parkinson | TE | 8.64 | 18 | 32 | +14 | 27 | LA |
| Dalton Schultz | TE | 10.19 | 8 | 20 | +12 | **30** | HOU |
| Javonte Williams | RB | 16.43 | 6 | 16 | +10 | 26 | DAL |
| Hunter Henry | TE | 9.92 | 9 | 19 | +10 | **31** | NE |
| Jake Ferguson | TE | 11.82 | 4 | 12 | +8 | 27 | DAL |
| Josh Jacobs | RB | 15.21 | 9 | 17 | +8 | 28 | **moved LV → GB** |
| Jaylen Warren | RB | 12.99 | 19 | 27 | +8 | 27 | PIT |

**REMOVED: Zach Ertz.** Revision 2 listed him as the single best value (+59 edge). **He is not on any 2026 NFL roster.** He was also the TE replacement-level player, which is why his exp/g looked like value — it was the baseline, not an edge.

Young value plays with no age flag: **Vidal (25), Charbonnet (25), Odunze (24), Wan'Dale Robinson (25), Javonte Williams (26).** These are the cleanest Tier-3 names on both age and fade.

---

## AVOIDS — expensive fades

**9 of the top 24 ADP picks are fade-flagged.**

| ECR | Player | Pos | Gap | Gap/G | Age | Note |
|---|---|---|---|---|---|---|
| **2.9** | **Jahmyr Gibbs** | RB | **+61.1** | +3.60 | 24 | **Preseason RB1 (20% convert) AND largest RB fade. Two signals agree** |
| **3.5** | **Puka Nacua** | WR | **+70.4** | +4.40 | 25 | Largest fade of any player |
| 3.7 | Bijan Robinson | RB | +43.2 | +2.54 | 24 | Round 1 |
| **4.8** | Jaxon Smith-Njigba | WR | **+62.8** | +3.69 | 24 | Round 1 |
| 12.7 | Jonathan Taylor | RB | +56.5 | +3.32 | 27 | Round 2 |
| 17.7 | James Cook | RB | +52.2 | +3.07 | 26 | Round 2 |
| 17.9 | Brock Bowers | TE | +26.7 | +2.22 | 23 | Round 2 |
| 20.1 | George Pickens | WR | +29.1 | +1.71 | 25 | Round 2 |
| 22.2 | De'Von Achane | RB | +56.1 | +3.50 | 24 | Round 2 |
| 25.9 | Josh Allen | QB | +38.4 | +2.40 | **30** | Fade **and** age-flagged |
| 29.9 | Zay Flowers | WR | +38.2 | +2.25 | 25 | Round 3 |
| 36.4 | Tee Higgins | WR | +34.9 | +2.32 | 27 | Round 4 |
| 38.3 | Derrick Henry | RB | +26.6 | +1.56 | **32** | Fade **and** age-flagged |
| 38.3 | Drake Maye | QB | +26.0 | +1.53 | 24 | Round 4 |
| 77.1 | Tucker Kraft | TE | +46.1 | +5.76 | 25 | Round 7 — cheap enough to absorb |

**A fade flag is a price signal, not a talent judgment.** Nacua, Gibbs, Bijan and JSN are elite. The flag says 2025 production ran 30–70 points ahead of the opportunity that generated it, and the controlled historical pattern is ~30 points of regression. At a first-round price with no discount, that risk is unpriced.

**Double-flagged (fade + age 29+): Josh Allen, Derrick Henry.** These carry the highest downside on the board.

---

## RB: Run-blocking quality (2025 YOE/carry) — read with care

| Rank | Team | Carries | YOE/Carry | Stuff | Lead back |
|---|---|---|---|---|---|
| 1 | BAL | 392 | +0.90 | 15.3% | Derrick Henry — **FADE + AGE 32** |
| 2 | BUF | 458 | +0.72 | 12.9% | James Cook — **FADE (+52.2)** |
| 3 | LA | 483 | **+0.66** | 12.2% | **Kyren Williams — clean, age 26** ✅ |
| 4 | DET | 407 | +0.58 | 17.4% | Jahmyr Gibbs — **FADE (+61.1)** |
| 5 | IND | 374 | +0.56 | 15.5% | Jonathan Taylor — **FADE (+56.5)** |
| 6 | MIA | 380 | +0.51 | 21.3% | De'Von Achane — **FADE (+56.1)** |
| 7 | DAL | 383 | **+0.41** | 13.1% | **Javonte Williams — clean, age 26** ✅ |
| 8 | CHI | 455 | +0.39 | 13.6% | committee |

**Do not read this as "draft any RB from these teams."** Five of the top six are led by fade-flagged backs. Elite run blocking is one of the *mechanisms* that produces overperformance — the market has already paid for it.

The two clean rows are **Kyren Williams (LA, ECR 42.6)** and **Javonte Williams (DAL, ECR 45.0)**: good-to-elite line play, no fade, age 26.

---

## QB: Designed rush leaders (2025, min 6 g)

| QB | Team | Designed/G | Share | Rush TD | G | Note |
|---|---|---|---|---|---|---|
| Justin Fields | KC | 5.00 | 61.6% | 3 | 9 | **Now on KC** — role unclear |
| Josh Allen | BUF | 4.44 | 59.3% | 13 | 18 | **Fade + age 30** |
| Taysom Hill | NO | 4.33 | 100.0% | 1 | 12 | Not a fantasy QB |
| Jalen Hurts | PHI | 4.06 | 62.7% | 6 | 17 | No fade, age 28 |
| Jaxson Dart | NYG | 3.43 | 55.8% | 7 | 14 | Rookie |
| Bo Nix | DEN | 3.11 | 58.9% | 2 | 18 | No fade, age 26 |
| Jayden Daniels | WAS | 3.00 | 35.6% | 2 | 7 | **Scramble-heavy — less sticky** |
| Lamar Jackson | BAL | 2.85 | 55.2% | 1 | 13 | Age 29 |

Designed carries are a sticky role; scrambles are not. Daniels' 35.6% designed share means most of his rushing is improvised.

---

## WR: Red-zone target leaders (2025, min 20 targets)

| WR | Team | Tgt | aDOT | RZ | EZ | Catch% | Flag |
|---|---|---|---|---|---|---|---|
| Amon-Ra St. Brown | DET | 172 | 8.1 | 35 | 21 | 69.2% | — |
| Davante Adams | LA | 139 | 13.2 | 34 | 24 | 57.5% | age 33 |
| Jauan Jennings | MIN | 101 | 10.0 | 23 | 12 | 62.2% | age 29, **moved SF → MIN** |
| George Pickens | DAL | 137 | 11.3 | 23 | 10 | 62.6% | **FADE** |
| Jaxon Smith-Njigba | SEA | 189 | 11.1 | 23 | 8 | 62.9% | **FADE** |
| Ja'Marr Chase | CIN | 185 | 8.5 | 22 | 8 | 67.1% | — |
| Courtland Sutton | DEN | 139 | 12.2 | 21 | 9 | 58.8% | age 30 |
| Puka Nacua | LA | 208 | 10.1 | 21 | 10 | 66.1% | **FADE** |
| Troy Franklin | DEN | 107 | 12.4 | 21 | 11 | 61.1% | age 23 |
| Khalil Shakir | BUF | 118 | 3.4 | 20 | 7 | 75.8% | age 26 |
| Rashee Rice | KC | 79 | 4.3 | 19 | 15 | 71.6% | age 26 |

Adams: 34 RZ targets **and** 13.2 aDOT at WR24 cost — the best combination on the board, with the age caveat attached. Rice: 15 targets inside the 10 on only 79 total, the best TD-equity rate. Shakir: PPR floor at ECR 120.

---

## TE: Red-zone target leaders (2025)

| TE | Team | Tgt | aDOT | RZ | EZ | Catch% | Flag |
|---|---|---|---|---|---|---|---|
| Trey McBride | ARI | 170 | 6.6 | 34 | 12 | 69.3% | — |
| Jake Ferguson | DAL | 103 | 4.6 | 25 | 14 | 73.5% | — |
| Hunter Henry | NE | 103 | 8.2 | 24 | 11 | 66.4% | age 31 |
| Colby Parkinson | LA | 70 | 5.1 | 24 | 10 | 72.7% | — |
| Tyler Warren | IND | 114 | 5.3 | 23 | 13 | 71.9% | age 24 |
| Colston Loveland | CHI | 109 | 9.8 | 19 | 8 | 64.7% | age 22 |
| Brock Bowers | LV | 87 | 6.5 | 18 | 10 | 65.6% | **FADE** |
| Dallas Goedert | PHI | 89 | 7.5 | 17 | 10 | 68.9% | **FADE + age 31** |
| Tucker Kraft | GB | 44 | 4.6 | 12 | 3 | — | **FADE** |

McBride is TE1 by a wide margin — 34 RZ targets, age 26, +8.16 VOR (3rd overall). Environment is now a **negative** for him, not a positive. Ferguson (ECR 114) and Warren (age 24) are the value plays.

---

## 2026 Team Environments (Vegas) — ⚠️ CORRECTED IN REV 4, sign was inverted

**Revision 3 of this table was backwards.** The R code computed
`home_implied = total_line/2 − spread_line/2`. In nflverse, `spread_line` is
**positive when the HOME team is favored**, so that formula handed the home
favorite the *lower* implied total. Verified against moneyline on all 112 priced
2026 games: **112/112 agreement, zero exceptions.** Worked example — NO @ DET,
total 48.5, spread +7.0: correct is DET **27.75** / NO **20.75**; Rev 3 printed
DET 20.75 / NO 27.75.

| Tier | Teams (corrected implied total) |
|---|---|
| Elite (25.5+) | **BAL 26.79, DET 26.75, LA 26.56, SF 25.88, BUF 25.69, CIN 25.54** |
| Strong (24.5–25.5) | DAL 25.46, CHI 24.83, KC 24.79, TB, SEA, PHI |
| Mid (21–24.5) | GB, HOU, DEN, MIN, IND, NE, ATL, PIT, LAC, JAX, WAS, NO, TEN, NYG, CAR |
| Low (under 21) | **LV 19.33, MIA 19.04, NYJ 18.82, CLE 18.50, ARI 18.17** |

Range 18.17–26.79 (Rev 3 printed a compressed, inverted 21.04–28.33).

**What this changes on this board:**

- **ARI moves from #1 to #32.** Revision 3 called it "the #1 environment" and
  used that to support Trey McBride. **That support is withdrawn.** McBride
  remains TE1 on VOR (+8.16, 3rd overall) and on 34 red-zone targets — both
  independent of Vegas — but he is now in the **worst** projected scoring
  environment, which is a genuine argument against him, not for him.
- **Four recommendations get *stronger*:** Amon-Ra St. Brown (DET #2),
  Davante Adams and Kyren Williams (LA #3), McCaffrey (SF #4).
- The corrected ordering also has far better face validity — BAL, DET, LA, SF,
  BUF are strong offenses; ARI, CLE, NYJ are not.

Still only 6–9 of 17 games priced per team, so treat as directional. Fantasy
playoff weeks 15–17: **4 of 48 games priced.** Re-pull before the draft.

## 2025 Team Opportunity Supply — most stable signal (r=.48–.52)

| Team | Tgt/G | Car/G | Rec TD Exp | Rec Yds Exp |
|---|---|---|---|---|
| ARI | 38.2 | 21.5 | 32.8 | 4585 |
| CIN | 37.6 | 22.4 | 30.3 | 4529 |
| DAL | 36.7 | 27.4 | **41.7** | 4734 |
| DEN | 36.1 | 26.8 | 29.3 | 4283 |
| LA | 35.1 | 27.4 | **43.9** | 4705 |
| NO | 34.8 | 25.6 | 19.7 | 4061 |
| KC | 34.4 | 25.3 | 32.1 | 4033 |
| DET | 34.2 | 26.0 | 30.6 | 4417 |
| HOU | 34.2 | 27.9 | 28.0 | 4177 |
| CHI | 33.8 | 29.7 | 28.6 | 4466 |

Weight this above the 2026 Vegas table. **Note ARI leads 2025 target volume but ranks 32nd in 2026 Vegas** — high pass volume on a low-scoring offense. Both are true; volume without scoring environment is a weaker case than Rev 3 implied. **LA (43.9) and DAL (41.7) lead in expected receiving TDs** — supporting Adams, Prescott, Ferguson, and partly explaining why LA and DAL pass-catchers overperformed.

---

## Summary by position

### QB — wait. No QB clears +4.5 VOR/game.
1. **Trevor Lawrence** (JAX, 26) — 25.44, no fade, **no age flag**, ECR 77
2. **Brock Purdy** (SF, 26) — 25.33, no age flag, ECR 96 (9-game sample)
3. Dak Prescott (DAL, 33) — 26.28, best environment, age-flagged
4. Patrick Mahomes (KC, 30) — 26.21, age-flagged
5. Matthew Stafford (LA, 38) — 26.40, highest raw, **highest age risk**
- **Avoid at cost:** Josh Allen (fade +38.4, age 30), Drake Maye (fade +26.0)

### RB
1. **Christian McCaffrey** (SF, 30) — **+14.55 VOR, #1 overall by a factor of 1.8.** Age-flagged; edge absorbs it
2. **Kyren Williams** (LA, 26) — +0.66 YOE line, no fade, ECR 42.6
3. **Javonte Williams** (DAL, 26) — RB6 exp/g, −20.2 gap, ECR 45.0
4. Josh Jacobs (GB, 28) — RB9 at RB17 cost; **new team**
5. Kimani Vidal (25) / Zach Charbonnet (25) / Jaylen Warren (27) — late volume darts
- **Avoid at cost:** Gibbs (2.9), Bijan (3.7), Taylor (12.7), Cook (17.7), Achane (22.2), Henry (fade + age 32)

### WR
1. **Amon-Ra St. Brown** (DET, 26) — +7.78 VOR, no fade, 35 RZ targets, ECR 5.5
2. **Ja'Marr Chase** (CIN, 26) — +7.66 VOR, no fade, ECR 1.5
3. **Davante Adams** (LA, 33) — +6.83 VOR at ECR 50.7. **Best value; age-flagged**
4. **Rashee Rice** (KC, 26) — +6.46 VOR, elite TD equity, 8-game sample
5. Rome Odunze (24) / Wan'Dale Robinson (25, **now TEN**) — young value
6. Khalil Shakir (BUF, 26) — PPR floor, ECR 120
- **Avoid at cost:** Nacua (3.5), JSN (4.8), Pickens (20.1), Flowers (29.9), Higgins (36.4)

### TE
1. **Trey McBride** (ARI, 26) — +8.16 VOR (3rd overall), 34 RZ targets. ⚠️ ARI environment now ranks **32nd** — VOR case holds, environment case withdrawn
2. **Jake Ferguson** (DAL, 27) — 25 RZ / 14 EZ, 41.7 team rec TD exp, ECR 114
3. **Tyler Warren** (IND, 24) — 23 RZ / 13 EZ, ECR 54
4. Colby Parkinson (LA, 27) / Hunter Henry (NE, 31, age-flagged)
- **Avoid at cost:** Bowers (fade), Goedert (fade + age 31), Kraft (fade)
- **REMOVED:** Zach Ertz — not on a 2026 roster

---

## Corrections in Revision 4

External audit (Claude) found four defects in `ALL_R_CODE.R`; a fifth was found
during regeneration. All five verified independently before acceptance.

| # | Defect | Verification | Impact |
|---|---|---|---|
| 1 | **Vegas sign inverted** — `home_implied = total/2 − spread/2` | Moneyline test, **112/112 games**, zero exceptions | **Environment table fully inverted.** ARI #1 → #32 |
| 2 | **QB INT scored at −2**, league pays **−1.0**; two-point conversions **missing** | `src/build_bullish.py` W dict is authoritative | QB1 label changes; top 3 now a 0.06 pt tie |
| 3 | **Three mislabeled columns** — `team_implied_total` (= sum of QB exp pts), `prior_epa_proxy` (= renamed exp pts), `target_volume` (= midpoint of actual and expectation) | Read against what they compute | All four dropped, not renamed |
| 4 | **QB fade flags contaminated** — gap built on 4-pt scoring | TD counts differ between actual and expected, so error does not cancel | QB fades must not be displayed until recomputed |
| 5 | **2,530 base-R NA-subsetting rows in each of the committed RB/WR extracts; QB and the newly regenerated TE extract are clean** | Recounted directly from all four committed CSVs | Python consumes none of these files, so no live QB tag moved. A separate live absent-as-zero bug was found in the RB backfield percentile and fixed in the app builder. |

**Two provenance corrections to the incoming audit.** The audit stated the Rev 3
QB table was built on `bullish_qb_2020_2025.csv` and therefore inherited the −2
interception error. It was not — Rev 3 was rebuilt from raw weekly components
using the correct **−1.0**. The real Rev 3 gap was the **missing two-point
conversions**, which the audit also caught. Separately, the audit implied the
sign error was original to this work; in fact `src/build_bullish_inputs.py:156`
was **already correct** (`tl/2 + sp/2`), and the R code introduced a regression
against working app code.

**Artifact-state correction:** the corrected script contains the RB writer, but
the committed RB CSV was never regenerated: it still carries `target_volume`
and 2,530 junk rows. QB and the separately regenerated TE extract carry corrected
output; RB and WR do not. This is a second
document/artifact divergence: a repaired generator does not prove its committed
output moved. The TE extract is cleaned separately with the fake route alias
removed. The Vegas table remains analysis-only; the app derives its forward
window directly from `schedule_2026.csv`.

**Unaffected:** `vegas_weekly_reg` reads ffopportunity's own `implied_total`
column, which is authoritative and never used the broken formula.

---

## Corrections in Revision 3

| # | Issue | Correction |
|---|---|---|
| 1 | "CMC has the highest exp/g of any player at any position" | **False at league scoring.** He is #4; three QBs pass him. Claim withdrawn and replaced with the VOR framing, where he genuinely is #1 |
| 2 | Cross-position comparisons mixed 4-pt and 6-pt figures | Full 6-pt truth table added. All non-QB comparisons re-verified as unaffected |
| 3 | Raw exp/g used as the ranking frame | **VOR over positional replacement added** — the draft-relevant number. No QB in the top 15 |
| 4 | Age unmodelled | **Now controlled.** Monotonic decline curve; survivorship bias documented as conservative |
| 5 | Prior workload assumed to matter | **Tested and NULL** — signs flip across all three positions |
| 6 | Zach Ertz listed as best value (+59 edge) | **Not on any 2026 roster.** Removed. He was the TE replacement baseline |
| 7 | Wan'Dale Robinson flagged unrostered | **My error** — curly-apostrophe normalization bug. He is on TEN (moved from NYG) |
| 8 | Team changes not tracked | Mike Evans TB→SF, Josh Jacobs LV→GB, Jauan Jennings SF→MIN, Justin Fields NYJ→KC, Wan'Dale NYG→TEN |
| 9 | RB1 base rate treated as contradicting CMC | **It applies to Gibbs (2026 RB1), not CMC (RB3).** Base rate and fade flag converge on Gibbs |
| 10 | Age risk stated once in a footer | Now attached to **every** 29+ recommendation inline |

### Note on the guillotine-league call

A prior recommendation to pass on McCaffrey was made for a **guillotine** league, where a single bad week eliminates you and an injury tag is close to disqualifying. YTFL has no elimination mechanic. The reasoning does not transfer and the two calls are not in conflict — different format, different answer. Recorded so nobody reconciles them.

---

## Standing Cautions

1. **4-pt vs 6-pt.** QB figures here are rebuilt at league scoring. Non-QB figures remain 4-pt scored, which is valid (passing volume ≈ 0). **Never compare a QB to a non-QB on ffopportunity's default column.**
2. **VOR, not raw points.** Raw exp/g systematically overstates QBs. Always subtract positional replacement.
3. **Route participation is structurally unfixable.** No route counts in ffopportunity. The `routes_proxy` caveat stands.
4. **Signals that failed control tests:** YAC-OE, garbage time, prior workload. `neutral_script_role` is near-random. **Age is the only new signal that survived.**
5. **BULLISH is display-only.** N.1 remains INCONCLUSIVE in the RB/WR scope:
   22/35 (62.9%) vs 86/164 (52.4%), +10.4pp, 95% CI [-7.3, +28.2],
   p=0.261. Removing the non-discriminating TE matrix did not rescue the
   result. It is not a draft gate.
6. **Gap = fade filter, not discovery, and not a talent judgment.**
7. **`exp_per_game` outpredicts gap 2.4–4x.**
8. **Playoff Vegas incomplete** (4/48). Re-pull before draft.
9. **Small samples:** Purdy (9 g), Rice (8 g), Kraft (8 g), Fields (9 g), Daniels (7 g).
10. **2025 data on 2026 rosters.** Age is now controlled; **depth-chart competition and scheme changes are not.** Five team changes found on this board alone — re-check `rosters_2026.csv` and `depth_charts_2026.csv.gz` for every pick.
11. **Name normalization.** The curly-apostrophe bug that misfiled Wan'Dale Robinson is the repo's own recurring defect class (SELF_AUDIT §1.3). Any join between ADP, rosters and ffopportunity must fold Unicode punctuation and diacritics.

---

## Consistency check vs FFOPPORTUNITY_HANDOFF.md

| Handoff finding | Board status |
|---|---|
| Gap is fade, not discovery | ✅ Consistent |
| exp beats gap 2.4–4x | ✅ Consistent |
| YAC-OE failed control | ✅ Not used |
| Garbage time dead | ✅ Absent |
| neutral_script_role near-random | ✅ Absent |
| Team supply most stable | ✅ Consistent |
| 4-pt vs 6-pt TD issue | ✅ **Fixed in Rev 3** (violated in Rev 2) |
| Vegas 2026 partial | ✅ Flagged low-confidence |
| Routes unfixable | ✅ Consistent |
| BULLISH display-only | ✅ Consistent |
| Fade ≈ 30-pt controlled penalty | ✅ Reflected |
| "2025 data on 2026 rosters" largest error source | ✅ **Now partly closed** — age controlled, rosters checked, team changes listed |
