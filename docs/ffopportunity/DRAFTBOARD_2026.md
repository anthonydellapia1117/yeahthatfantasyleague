# YTFL 2026 Draft Board — ffopportunity Data Analysis

Generated: August 28, 2026 (revised — see Corrections section)
Data source: ffopportunity v0.1.2 (ffverse) + nflreadr, R 4.6.1
Seasons analyzed: 2020–2025 (6 years), 2026 preseason ADP (FantasyPros redraft-overall ECR, scraped 2026-08-21)
Repo: https://github.com/anthonydellapia1117/yeahthatfantasyleague/tree/main/docs/ffopportunity

**League:** 12 teams, 14 rounds, snake, full PPR, **6-point passing TDs**, zero IR, H2H + median scoring.
**ADP note:** ECR values below are overall ranks. In a 12-team draft, round ≈ ceil(ECR / 12).

---

## Methodology

4 rounds of R-based extraction from ffopportunity. Every signal was tested for year-over-year repeatability **and** next-season predictiveness (control test within production tier). Two of three new signal candidates FAILED their control tests and are display-only. The gap signal (`total_fantasy_points_diff`) is a **fade filter, not a discovery signal**. `exp_per_game` outpredicts gap 2.4–4x.

Key correlations (YoY stability):
- Team opportunity supply: r=.48–.52 (most stable signal found)
- Backfield command: r=.472
- RB inside-5 share: r=.338 (corrected from .079)
- YAC over expected: r=.558–.720 **BUT NOT predictive** (failed control — signs flip across tiers)
- Gap signal: r=.175–.284 (fade only)
- neutral_script_role: r=.091–.177 (near-random, do not use)

### ⚠️ Two signals, two different questions

This board mixes a **team** signal (line quality, opportunity supply, Vegas) with a **player** signal (the fade flag). They measure different things and frequently point in opposite directions.

**The correct synthesis:** good line + no fade = target. Good line + fade = **the line quality is already priced into the overperformance**, and the player is expensive. Never recommend a player on team traits alone when his individual gap says fade.

---

## ⚠️ SCORING CORRECTION — READ BEFORE USING QB NUMBERS

`total_fantasy_points_exp` in ffopportunity is scored at **4-point passing TDs**. YTFL pays **6**. Every QB expected-points figure from `regression_flags_clean` is therefore **understated by roughly 3–6 points per game**.

Rebuilt at league scoring (`pass_touchdown_exp*6 + rush_touchdown_exp*6 + pass_yards_gained_exp*0.04 + rush_yards_gained_exp*0.1 + receptions_exp*1.0 + pass_interception_exp*-1.0`), 2025 regular season, min 8 games:

| Rank | QB | Team | 6-pt exp/g | 4-pt exp/g | Diff | ECR | Fade |
|---|---|---|---|---|---|---|---|
| 1 | **Matthew Stafford** | LA | **26.40** | 20.52 | +5.88 | 104.3 | no |
| 2 | **Dak Prescott** | DAL | **26.28** | 20.87 | +5.41 | 79.5 | no |
| 3 | **Patrick Mahomes** | KC | **26.21** | 21.28 | +4.93 | 100.4 | no |
| 4 | Trevor Lawrence | JAC | 25.44 | 21.18 | +4.26 | 77.3 | no |
| 5 | Brock Purdy | SF | 25.33 | 20.54 | +4.79 | 96.5 | no (9 g) |
| 6 | Drake Maye | NE | 23.60 | 19.41 | +4.19 | 38.3 | **FADE** |
| 7 | Josh Allen | BUF | 23.15 | 20.35 | +2.80 | 25.9 | **FADE** |
| 8 | Caleb Williams | CHI | 23.15 | 19.34 | +3.81 | — | no |
| 9 | Justin Herbert | LAC | 22.94 | 18.77 | +4.17 | — | no |
| 10 | Bo Nix | DEN | 22.76 | 18.89 | +3.87 | — | no |
| 14 | Jalen Hurts | PHI | 21.37 | 18.49 | +2.88 | — | no |

**The re-rank changes the board.** Stafford and Mahomes are QB1 and QB3 under league scoring and were **absent from the previous version entirely**. Both go ~round 9 (ECR 100–104), two-plus rounds later than Lawrence and Prescott, for equal or better expected production.

---

## TARGETS

### Tier 1 — elite expected production, no fade

| Player | Pos | Team | Exp/Game | Gap (total) | ECR | Note |
|---|---|---|---|---|---|---|
| **Christian McCaffrey** | RB | SF | **25.52** | −19.3 | 10.2 | Highest exp/g of any player. Underperformed by 19 pts — **fade risk is inverted** |
| **Amon-Ra St. Brown** | WR | DET | **19.29** | −3.9 | 5.5 | Highest non-QB WR exp/g, no fade, 35 RZ targets |
| **Bijan Robinson** | RB | ATL | 19.27 | +43.2 | 3.7 | ⚠️ elite exp/g **but fade-flagged** — see AVOIDS |
| **Ja'Marr Chase** | WR | CIN | 19.16 | +7.1 | 1.5 | No fade. Priced at WR1 and earns it |
| **Puka Nacua** | WR | LAR | 19.04 | +70.4 | 3.5 | ⚠️ **largest fade in the dataset** — see AVOIDS |
| **Davante Adams** | WR | LA | 18.34 | −2.4 | 50.7 | **Best value on the board** — WR4 by exp/g at WR24 cost |
| **Rashee Rice** | WR | KC | 18.11 | +5.2 | 22.4 | 8 games. 15 EZ targets on 79 total = elite TD equity |
| **Trey McBride** | TE | ARI | 17.76 | +14.0 | 20.9 | TE1 by a wide margin, best 2026 environment |

CMC is the clearest single call on the board: the highest expected points per game of any player at any position, drafted 10th, and he **underperformed** his expectation — the opposite of fade risk.

### Tier 2 — QB value (use the 6-pt numbers above)

| Player | Pos | Team | 6-pt Exp/G | ECR | Note |
|---|---|---|---|---|---|
| Matthew Stafford | QB | LA | 26.40 | 104.3 | **QB1 by league scoring, drafted ~round 9** |
| Dak Prescott | QB | DAL | 26.28 | 79.5 | Best supporting environment (36.7 tgt/g, 41.7 rec TD exp) |
| Patrick Mahomes | QB | KC | 26.21 | 100.4 | QB3 at round-9 cost |
| Trevor Lawrence | QB | JAC | 25.44 | 77.3 | No fade, solid |
| Brock Purdy | QB | SF | 25.33 | 96.5 | 9 games — smaller sample, discount accordingly |

**Do not draft a QB before round 7.** The 4th-through-10th ranked QBs by expected points all cost round 7 or later, and the two highest are the cheapest of the group.

### Tier 3 — positional value (exp/game rank far ahead of ADP rank, no fade)

| Player | Pos | Exp/G | Exp Rank | Pos ADP Rank | Edge |
|---|---|---|---|---|---|
| Zach Ertz | TE | 9.63 | 12 | 71 | **+59** |
| Kimani Vidal | RB | 11.49 | 24 | 61 | **+37** |
| Zach Charbonnet | RB | 11.24 | 26 | 48 | +22 |
| Wan'Dale Robinson | WR | 13.56 | 17 | 39 | +22 |
| Davante Adams | WR | 18.34 | 4 | 24 | +20 |
| Courtland Sutton | WR | 12.92 | 18 | 37 | +19 |
| Tyrone Tracy Jr. | RB | 11.10 | 28 | 46 | +18 |
| Mike Evans | WR | 14.69 | 12 | 26 | +14 |
| Rome Odunze | WR | 14.37 | 14 | 28 | +14 |
| Colby Parkinson | TE | 8.64 | 18 | 32 | +14 |
| Dalton Schultz | TE | 10.19 | 8 | 20 | +12 |
| Javonte Williams | RB | 16.43 | 6 | 16 | +10 |
| Hunter Henry | TE | 9.92 | 9 | 19 | +10 |
| Jake Ferguson | TE | 11.82 | 4 | 12 | +8 |
| Josh Jacobs | RB | 15.21 | 9 | 17 | +8 |
| Jaylen Warren | RB | 12.99 | 19 | 27 | +8 |

Deep-round names (Vidal, Charbonnet, Tracy, Ertz, Parkinson) are **volume-dependent** — the edge assumes a role they may not hold. Treat as late-round dart throws, not core targets.

---

## AVOIDS — expensive fades

**9 of the top 24 ADP picks are fade-flagged.** This is the single most actionable finding on the board.

| ECR | Player | Pos | Team | Gap (total) | Gap/G | Exp/G | Cost of the mistake |
|---|---|---|---|---|---|---|---|
| **2.9** | **Jahmyr Gibbs** | RB | DET | **+61.1** | +3.60 | 17.97 | **Round 1. Largest RB fade in the dataset** |
| **3.5** | **Puka Nacua** | WR | LAR | **+70.4** | +4.40 | 19.04 | **Round 1. Largest fade of any player** |
| **3.7** | **Bijan Robinson** | RB | ATL | +43.2 | +2.54 | 19.27 | Round 1 |
| **4.8** | **Jaxon Smith-Njigba** | WR | SEA | **+62.8** | +3.69 | 17.48 | Round 1 |
| **12.7** | **Jonathan Taylor** | RB | IND | **+56.5** | +3.32 | 17.99 | Round 2 |
| **17.7** | **James Cook** | RB | BUF | **+52.2** | +3.07 | 14.71 | Round 2 |
| 17.9 | Brock Bowers | TE | LV | +26.7 | +2.22 | 12.46 | Round 2 |
| 20.1 | George Pickens | WR | DAL | +29.1 | +1.71 | 15.34 | Round 2 |
| **22.2** | **De'Von Achane** | RB | MIA | **+56.1** | +3.50 | 16.63 | Round 2 |
| 25.9 | Josh Allen | QB | BUF | +38.4 | +2.40 | 20.35 | Round 3 |
| 29.9 | Zay Flowers | WR | BAL | +38.2 | +2.25 | 12.06 | Round 3 |
| 36.4 | Tee Higgins | WR | CIN | +34.9 | +2.32 | 11.78 | Round 4 |
| 38.3 | Derrick Henry | RB | BAL | +26.6 | +1.56 | 14.88 | Round 4 |
| 38.3 | Drake Maye | QB | NE | +26.0 | +1.53 | 19.41 | Round 4 |
| 77.1 | Tucker Kraft | TE | GB | +46.1 | +5.76 | 8.89 | Round 7 |

**Reading this table correctly.** A fade flag is **not** "do not draft." Nacua, Gibbs, Bijan, and JSN are genuinely elite players. The flag says their 2025 production ran ~30–70 points ahead of what their opportunity justified, and the controlled historical pattern is a ~30-point regression. At a first-round price with no discount, that risk is unpriced. **The flag is a price signal, not a talent signal.**

The RB cluster is the sharpest read: **Gibbs, Taylor, Achane, and Cook are four of the five largest RB fades in the dataset and all go inside the top 25 picks.**

---

## RB: Best Run-Blocking Teams (2025, YOE per carry)

| Rank | Team | Carries | YOE/Carry | Stuff Rate | Lead back status |
|---|---|---|---|---|---|
| 1 | BAL | 392 | +0.90 | 15.3% | Derrick Henry — **FADE (+26.6)** |
| 2 | BUF | 458 | +0.72 | 12.9% | James Cook — **FADE (+52.2)** |
| 3 | LA | 483 | +0.66 | 12.2% | Kyren Williams — clean (+15.5, no flag) |
| 4 | DET | 407 | +0.58 | 17.4% | Jahmyr Gibbs — **FADE (+61.1)** |
| 5 | IND | 374 | +0.56 | 15.5% | Jonathan Taylor — **FADE (+56.5)** |
| 6 | MIA | 380 | +0.51 | 21.3% | De'Von Achane — **FADE (+56.1)** |
| 7 | DAL | 383 | +0.41 | 13.1% | Javonte Williams — clean (−20.2) |
| 8 | CHI | 455 | +0.39 | 13.6% | committee |

**This table must not be read as "draft any RB from these teams."** Five of the top six run-blocking teams are led by fade-flagged backs. That is not a coincidence — **elite run blocking is one of the mechanisms that produces overperformance**, and the market has already paid for it.

The two actionable rows are **LA (Kyren Williams, +0.66 YOE, no fade, ECR 42.6)** and **DAL (Javonte Williams, +0.41 YOE, −20.2 gap, ECR 45.0, RB6 by exp/game)**. Both offer elite-to-good line play without the regression risk.

---

## QB: Designed Rush Leaders (2025, min 6 games)

| QB | Team | Designed/G | Designed Share | Rush TDs | Games | Note |
|---|---|---|---|---|---|---|
| Justin Fields | NYJ | 5.00 | 61.6% | 3 | 9 | High value if starting — 9-game sample |
| Josh Allen | BUF | 4.44 | 59.3% | 13 | 18 | Elite rushing, but **fade-flagged** |
| Taysom Hill | NO | 4.33 | 100.0% | 1 | 12 | Hybrid role, not a fantasy QB |
| Jalen Hurts | PHI | 4.06 | 62.7% | 6 | 17 | Tush-push TD equity, no fade |
| Jaxson Dart | NYG | 3.43 | 55.8% | 7 | 14 | Rookie — monitor role |
| Marcus Mariota | WAS | 3.20 | 64.0% | 0 | 10 | Backup |
| Bo Nix | DEN | 3.11 | 58.9% | 2 | 18 | Solid designed role, no fade |
| Jayden Daniels | WAS | 3.00 | 35.6% | 2 | 7 | **Scramble-heavy — less sticky**, 7-game sample |
| Lamar Jackson | BAL | 2.85 | 55.2% | 1 | 13 | Lower designed volume than reputation |

Designed carries are a **sticky role**; scrambles are volatile. Daniels' 35.6% designed share means most of his rushing is improvised and less repeatable.

---

## WR: Red Zone Target Leaders (2025, min 20 targets)

| Rank | WR | Team | Targets | aDOT | RZ | EZ | Catchable | Fade |
|---|---|---|---|---|---|---|---|---|
| 1 | Amon-Ra St. Brown | DET | 172 | 8.1 | 35 | 21 | 69.2% | no |
| 2 | Davante Adams | LA | 139 | 13.2 | 34 | 24 | 57.5% | no |
| 3 | Jauan Jennings | SF | 101 | 10.0 | 23 | 12 | 62.2% | no |
| 4 | George Pickens | DAL | 137 | 11.3 | 23 | 10 | 62.6% | **FADE** |
| 5 | Jaxon Smith-Njigba | SEA | 189 | 11.1 | 23 | 8 | 62.9% | **FADE** |
| 6 | Ja'Marr Chase | CIN | 185 | 8.5 | 22 | 8 | 67.1% | no |
| 7 | Courtland Sutton | DEN | 139 | 12.2 | 21 | 9 | 58.8% | no |
| 8 | Puka Nacua | LA | 208 | 10.1 | 21 | 10 | 66.1% | **FADE** |
| 9 | Troy Franklin | DEN | 107 | 12.4 | 21 | 11 | 61.1% | no |
| 10 | Khalil Shakir | BUF | 118 | 3.4 | 20 | 7 | 75.8% | no |
| 11 | Rashee Rice | KC | 79 | 4.3 | 19 | 15 | 71.6% | no |

Adams is the standout: 34 RZ targets **and** a 13.2 aDOT — deep work plus red-zone volume, at WR24 cost. Rice has 15 targets inside the 10 on only 79 total, the best TD-equity rate on the board. Shakir is a PPR floor play (75.8% catchable, 3.4 aDOT = slot volume) at ECR 120.

---

## TE: Red Zone Target Leaders (2025)

| Rank | TE | Team | Targets | aDOT | RZ | EZ | Catchable | Fade |
|---|---|---|---|---|---|---|---|---|
| 1 | Trey McBride | ARI | 170 | 6.6 | 34 | 12 | 69.3% | no |
| 2 | Jake Ferguson | DAL | 103 | 4.6 | 25 | 14 | 73.5% | no |
| 3 | Hunter Henry | NE | 103 | 8.2 | 24 | 11 | 66.4% | no |
| 4 | Colby Parkinson | LA | 70 | 5.1 | 24 | 10 | 72.7% | no |
| 5 | Tyler Warren | IND | 114 | 5.3 | 23 | 13 | 71.9% | no |
| 6 | Colston Loveland | CHI | 109 | 9.8 | 19 | 8 | 64.7% | no |
| 7 | Brock Bowers | LV | 87 | 6.5 | 18 | 10 | 65.6% | **FADE** |
| 8 | Dallas Goedert | PHI | 89 | 7.5 | 17 | 10 | 68.9% | **FADE** |
| — | Tucker Kraft | GB | 44 | 4.6 | 12 | 3 | — | **FADE** |

McBride is TE1 by a wide margin — 34 RZ targets on 170 total, in the best 2026 environment. Ferguson (ECR 114) and Henry are the value plays. Kraft **is** in the dataset (44 targets, 12 RZ) — he simply does not rank top-8, and he is fade-flagged.

---

## 2026 Team Environments (Vegas implied totals) — ⚠️ LOW CONFIDENCE

| Tier | Teams | Implied Total |
|---|---|---|
| Elite | ARI (28.3), WAS (25.8), MIA (25.3) | 25+ |
| Strong | DAL (24.9), ATL (24.9), IND (24.9), LV (24.2), CIN (23.8) | 24–25 |
| Good | TEN, NO, BUF, NYJ, CAR, TB, NYG | 23–24 |
| Neutral | CHI, GB, CLE, DEN, DET, MIN, NE | 22–23 |
| Low | SF, LAC, HOU, PIT, BAL, LA, PHI, SEA, KC | 21–22 |

**Treat this table as provisional.** Only **6–9 of 17 games** are priced per team, the resulting range is compressed (21.04–28.33), and the priced games are not a random sample — they are the ones books posted earliest. The "Low" tier containing KC, BAL, PHI, and LA — four of the strongest rosters in the league — is a strong signal that this reflects **early-schedule difficulty, not season-long environment**.

Use ARI's top ranking (corroborated independently by 2025 opportunity supply) with moderate confidence. Do not use the bottom tier to downgrade anyone.

Fantasy playoff weeks 15–17 have only **4 of 48 games priced**. Re-pull `schedule_2026.csv` nearer the draft.

---

## 2025 Team Opportunity Supply (most pass-heavy)

| Rank | Team | Targets/G | Carries/G | Rec TD Exp | Rec Yds Exp |
|---|---|---|---|---|---|
| 1 | ARI | 38.2 | 21.5 | 32.8 | 4585 |
| 2 | CIN | 37.6 | 22.4 | 30.3 | 4529 |
| 3 | DAL | 36.7 | 27.4 | **41.7** | 4734 |
| 4 | DEN | 36.1 | 26.8 | 29.3 | 4283 |
| 5 | LA | 35.1 | 27.4 | **43.9** | 4705 |
| 6 | NO | 34.8 | 25.6 | 19.7 | 4061 |
| 7 | KC | 34.4 | 25.3 | 32.1 | 4033 |
| 8 | DET | 34.2 | 26.0 | 30.6 | 4417 |
| 9 | HOU | 34.2 | 27.9 | 28.0 | 4177 |
| 10 | CHI | 33.8 | 29.7 | 28.6 | 4466 |

This is the **most stable signal in the entire dataset** (r=.48–.52 YoY) and deserves more weight than the 2026 Vegas table above.

ARI leads both supply and Vegas — genuinely the best skill-position environment. **LA (43.9) and DAL (41.7) lead in expected receiving TDs**, which supports Adams, Nacua, Prescott, Pickens, and Ferguson as environment-boosted — and partly explains why LA and DAL pass-catchers overperformed.

---

## Summary: Top 2026 Targets by Position

### QB — wait, then take value
1. **Matthew Stafford** (LA) — QB1 at 26.40 6-pt exp/g, ECR 104 (~round 9)
2. **Dak Prescott** (DAL) — 26.28, best supporting environment, ECR 79
3. **Patrick Mahomes** (KC) — 26.21, ECR 100
4. **Trevor Lawrence** (JAC) — 25.44, no fade, ECR 77
5. Jalen Hurts (PHI) — 21.37, no fade, tush-push TD equity
- **AVOID at cost:** Josh Allen (ECR 25.9, fade +38.4), Drake Maye (ECR 38.3, fade +26.0)

### RB
1. **Christian McCaffrey** (SF) — 25.52 exp/g, no fade, ECR 10.2. **The best value in round 1**
2. **Kyren Williams** (LA) — +0.66 YOE line, no fade, ECR 42.6
3. **Javonte Williams** (DAL) — RB6 by exp/g, −20.2 gap, ECR 45.0
4. Josh Jacobs — RB9 by exp/g at RB17 cost
5. Jaylen Warren / Zach Charbonnet / Kimani Vidal — late-round volume dart throws
- **AVOID at cost:** Gibbs (2.9), Bijan (3.7), Taylor (12.7), Cook (17.7), Achane (22.2)

### WR
1. **Amon-Ra St. Brown** (DET) — 19.29 exp/g, no fade, 35 RZ targets, ECR 5.5
2. **Ja'Marr Chase** (CIN) — 19.16 exp/g, no fade, ECR 1.5
3. **Davante Adams** (LA) — 18.34 exp/g (WR4) at ECR 50.7 (WR24). **Best value on the board**
4. **Rashee Rice** (KC) — 15 EZ targets on 79 total, ECR 22.4
5. Mike Evans / Rome Odunze / Courtland Sutton — +14 to +19 rank edge
6. Khalil Shakir (BUF) — PPR floor, 75.8% catchable, ECR 120
- **AVOID at cost:** Nacua (3.5), JSN (4.8), Pickens (20.1), Flowers (29.9), Higgins (36.4)

### TE
1. **Trey McBride** (ARI) — 34 RZ targets, best environment, ECR 20.9
2. **Jake Ferguson** (DAL) — 25 RZ / 14 EZ, 41.7 team rec TD exp, ECR 114
3. **Tyler Warren** (IND) — 23 RZ / 13 EZ, ECR 54
4. Hunter Henry (NE) — TE9 by exp/g at TE19 cost
5. Dalton Schultz / Colby Parkinson / Zach Ertz — deep value
- **AVOID at cost:** Brock Bowers (17.9, fade +26.7), Dallas Goedert (fade +36.4), Tucker Kraft (77.1, fade +46.1)

---

## Corrections applied in this revision

| # | Issue | Correction |
|---|---|---|
| 1 | Kraft "scored ~98 pts above expectation" | **Actually +46.1.** 8 games × 5.76 gap/g = 46.1. `exp_pts` = 71.1, actual 117.2 |
| 2 | QB exp/game used 4-pt scoring in a 6-pt league | Rebuilt all QBs at league scoring; +2.8 to +5.9 pts/g |
| 3 | Stafford and Mahomes absent | Added — QB1 and QB3 under league scoring |
| 4 | "Any DET / IND / BUF / BAL RB" | All four lead backs are fade-flagged. Reframed |
| 5 | Josh Allen listed as QB target #1 | Fade-flagged (+38.4). Moved to avoid-at-cost |
| 6 | Brock Bowers listed as TE target #4 | Fade-flagged (+26.7). Moved to avoid-at-cost |
| 7 | Only 3 avoids named | **9 of the top 24 ADP picks are fade-flagged.** All listed |
| 8 | TARGETS had 4 players, 3 of them QBs | Expanded to tiers with ARSB, Chase, Adams, McBride, Rice |
| 9 | Kraft called "a popular TE target / TE1" | ECR 77.1 (~round 7), not a TE1 price |
| 10 | Kraft "the clearest avoid" | Disagree — see below |
| 11 | Kraft "NOT on this list" (TE RZ table) | He **is** in the data (44 tgt, 12 RZ); just not top-8 |
| 12 | LA YOE/carry listed +0.67 | Source value is **+0.66** |
| 13 | QB rush ranks skipped Hill and Mariota | Restored for completeness |
| 14 | 2026 Vegas presented as settled | Flagged low-confidence: 6–9 of 17 games priced |
| 15 | No ADP cross-reference | Added value board and expensive-fade table |

### Recommendations I disagree with

**"Kraft is the clearest avoid."** He is the *smallest* fade among the named avoids by total gap (46.1 vs Nacua's 70.4 and Gibbs' 61.1), it came over only 8 games, and at ECR 77 he costs a 7th-round pick. **Gibbs at ECR 2.9 with a 61.1 gap is a far more expensive mistake.** Rank fades by cost × magnitude, not magnitude alone.

**"Nacua and JSN are being valued at their ceiling."** Correct, but understated — they are the #1 and #3 largest fades in the dataset, going 3rd and 5th overall. That deserves stronger framing than "moderate."

**The "Any [team] RB" construction.** Unsound as written. It applies a team signal to players whose individual data contradicts it. Five of the top six run-blocking teams have fade-flagged lead backs.

---

## Standing Cautions

1. **4-pt vs 6-pt pass TD.** `total_fantasy_points_exp` is scored at 4-pt passing TDs; YTFL pays 6. The QB table above is rebuilt from components. **All other `exp` figures on this board remain 4-pt scored** — acceptable for non-QBs (whose passing volume is ~0) but must be rebuilt before any QB comparison.
2. **Route participation is structurally unfixable.** ffopportunity has no route counts. The `routes_proxy` caveat must remain on every surface.
3. **Two of three new signals failed control tests** (YAC-OE, garbage time). `neutral_script_role` is near-random. Hold every new signal at display until it passes a null test against 13 seasons of YTFL data.
4. **BULLISH tag is display-only** (p=0.104, underpowered). Do not use as a draft gate.
5. **The gap signal is a fade filter, not a discovery signal.** Use it to price overperformers, not to find sleepers. It is also **not a talent judgment** — Nacua and Gibbs remain elite players.
6. **`exp_per_game` outpredicts gap 2.4–4x.** Prefer it as the ranking input.
7. **Playoff weeks 15–17 Vegas data is incomplete** (4 of 48 games priced). Re-pull before the draft.
8. **Small-sample players carry hidden risk:** Purdy (9 g), Rice (8 g), Kraft (8 g), Fields (9 g), Daniels (7 g), Burrow (8 g). Per-game rates are noisier than the tables suggest.
9. **2025 data, 2026 rosters.** Every production figure is from 2025. Team changes, depth-chart moves, and rookie arrivals are **not** reflected in exp/game. Cross-check `rosters_2026.csv` and `depth_charts_2026.csv.gz` before finalizing — this is the largest unmodelled source of error on the board.

---

## Consistency check against FFOPPORTUNITY_HANDOFF.md

| Handoff finding | Board status |
|---|---|
| Gap is fade, not discovery | ✅ Consistent |
| exp beats gap 2.4–4x | ✅ Consistent |
| YAC-OE failed control | ✅ Consistent — not used for any recommendation |
| Garbage time dead | ✅ Consistent — absent |
| neutral_script_role near-random | ✅ Consistent — absent |
| Team supply most stable (r=.48–.52) | ✅ Consistent |
| 4-pt vs 6-pt TD issue | ✅ **Fixed in this revision** (was violated) |
| Vegas 2026 partial coverage | ✅ **Fixed in this revision** (was presented as settled) |
| Routes unfixable | ✅ Consistent |
| BULLISH display-only | ✅ Consistent |
| Fade ≈ 30-pt controlled penalty | ✅ Now reflected in avoid framing |
