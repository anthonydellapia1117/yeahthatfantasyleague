# YTFL 2026 Draft Board - ffopportunity Data Analysis

Generated: August 28, 2026
Data source: ffopportunity v0.1.2 (ffverse) + nflreadr, R 4.6.1
Seasons analyzed: 2020-2025 (6 years), 2026 preseason ADP
Repo: https://github.com/anthonydellapia1117/yeahthatfantasyleague/tree/main/docs/ffopportunity

## Methodology

4 rounds of R-based extraction from the ffopportunity package. Every signal was tested for year-over-year repeatability AND next-season predictiveness (control test). Two of three new signal candidates FAILED their control tests and are flagged as display-only. The gap signal (total_fantasy_points_diff) is a fade filter, not a discovery signal. exp_per_game outpredicts gap 2.4-4x as a predictor of next-season points.

Key correlations (YoY stability):
- Team opportunity supply: r=.48-.52 (most stable signal found)
- Backfield command: r=.472
- RB inside-5 share: r=.338 (corrected from .079)
- YAC over expected: r=.558-.720 BUT NOT predictive (failed control)
- Gap signal: r=.175-.284 (fade only)
- neutral_script_role: r=.091-.177 (near-random, do not use)

## TARGETS (high expected points, no fade flag, 2025 season)

| Player | Pos | Team | Exp/Game | Gap/Game | ADP Range |
|---|---|---|---|---|---|
| Christian McCaffrey | RB | SF | 25.5 | -1.14 | 1st-5th round |
| Trevor Lawrence | QB | JAC | 21.2 | -1.17 | 8th-15th |
| Dak Prescott | QB | DAL | 20.9 | -2.41 | 9th-15th |
| Brock Purdy | QB | SF | 20.5 | -0.47 | 10th-22nd |

CMC is the clear #1 overall pick - highest expected points per game AND no fade (underperformed slightly). The QBs are value picks - Lawrence and Prescott go middle rounds but put up elite expected numbers.

## AVOIDS (fade flag - overperformed, likely to regress)

| Player | Pos | Team | Exp/Game | Gap/Game | Actual Pts | Fade Severity |
|---|---|---|---|---|---|---|
| Tucker Kraft | TE | GB | 8.89 | +5.76 | 117 | Severe - scored ~98 pts above expectation |
| Puka Nacua | WR | LAR | 19.0 | +4.40 | 375 | Moderate - elite talent but drafted at ceiling |
| Jaxon Smith-Njigba | WR | SEA | 17.5 | +3.69 | 360 | Moderate - breakout may regress |

Kraft is the clearest avoid - being drafted as a TE1 but overperformed by nearly 100 points. Nacua and JSN are still elite talents but the data says they are being valued at their ceiling, not their floor.

## RB: Best Run-Blocking Teams (2025, YOE per carry)

| Rank | Team | Carries | YOE/Carry | Stuff Rate | Verdict |
|---|---|---|---|---|---|
| 1 | BAL | 392 | +0.90 | 15.3% | Elite - Derrick Henry's home |
| 2 | BUF | 458 | +0.72 | 12.9% | Elite - target any BUF RB |
| 3 | LA | 483 | +0.67 | 12.2% | Elite - Kyren Williams boost |
| 4 | DET | 407 | +0.58 | 17.4% | Strong - Jahmyr Gibbs boost |
| 5 | IND | 374 | +0.56 | 15.5% | Strong - Jonathan Taylor boost |
| 6 | MIA | 380 | +0.51 | 21.3% | Good but high stuff rate |
| 7 | DAL | 383 | +0.41 | 13.1% | Good - low stuff rate |
| 8 | CHI | 455 | +0.39 | 13.6% | Good - high volume |

## QB: Designed Rush Leaders (2025, min 6 games)

| Rank | QB | Team | Designed/Game | Designed Share | Rush TDs | Verdict |
|---|---|---|---|---|---|---|
| 1 | Justin Fields | NYJ | 5.0 | 61.6% | 3 | High value if starting |
| 2 | Josh Allen | BUF | 4.4 | 59.3% | 13 | Gold standard - rush + TD equity |
| 3 | Jalen Hurts | PHI | 4.1 | 62.7% | 6 | Gold standard - tush push TDs |
| 4 | Jaxson Dart | NYG | 3.4 | 55.8% | 7 | Rookie - monitor role |
| 5 | Bo Nix | DEN | 3.1 | 58.9% | 2 | Solid designed role |
| 6 | Jayden Daniels | WAS | 3.0 | 35.6% | 2 | Scramble-heavy - less sticky |
| 7 | Lamar Jackson | BAL | 2.85 | 55.2% | 1 | Lower TD equity than expected |

## WR: Red Zone Target Leaders (2025, min 20 targets)

| Rank | WR | Team | Targets | aDOT | RZ Targets | EZ Targets | Catchable % |
|---|---|---|---|---|---|---|---|
| 1 | Amon-Ra St. Brown | DET | 172 | 8.1 | 35 | 21 | 69.2% |
| 2 | Davante Adams | LA | 139 | 13.2 | 34 | 24 | 57.5% |
| 3 | Jauan Jennings | SF | 101 | 10.0 | 23 | 12 | 62.2% |
| 4 | George Pickens | DAL | 137 | 11.3 | 23 | 10 | 62.6% |
| 5 | Jaxon Smith-Njigba | SEA | 189 | 11.1 | 23 | 8 | 62.9% |
| 6 | Ja'Marr Chase | CIN | 185 | 8.5 | 22 | 8 | 67.1% |
| 7 | Courtland Sutton | DEN | 139 | 12.2 | 21 | 9 | 58.8% |
| 8 | Puka Nacua | LAR | 208 | 10.1 | 21 | 10 | 66.1% |
| 9 | Troy Franklin | DEN | 107 | 12.4 | 21 | 11 | 61.1% |
| 10 | Khalil Shakir | BUF | 118 | 3.4 | 20 | 7 | 75.8% |
| 11 | Rashee Rice | KC | 79 | 4.3 | 19 | 15 | 71.6% |

Adams is the standout - 34 RZ targets + 13.2 aDOT = deep balls AND red zone work. Rice has only 79 targets but 15 inside the 10 = elite TD equity if healthy. Shakir is a PPR machine (75.8% catchable, 3.4 aDOT = slot volume).

## TE: Red Zone Target Leaders (2025)

| Rank | TE | Team | Targets | aDOT | RZ Targets | EZ Targets |
|---|---|---|---|---|---|---|
| 1 | Trey McBride | ARI | 170 | 6.6 | 34 | 12 |
| 2 | Jake Ferguson | DAL | 103 | 4.6 | 25 | 14 |
| 3 | Hunter Henry | NE | 103 | 8.2 | 24 | 11 |
| 4 | Colby Parkinson | LA | 70 | 5.1 | 24 | 10 |
| 5 | Tyler Warren | IND | 114 | 5.3 | 23 | 13 |
| 6 | Colston Loveland | CHI | 109 | 9.8 | 19 | 8 |
| 7 | Brock Bowers | LV | 87 | 6.5 | 18 | 10 |
| 8 | Dallas Goedert | PHI | 89 | 7.5 | 17 | 10 |

McBride is TE1 by a wide margin - 34 RZ targets on 170 total. Ferguson and Warren are value picks with elite red zone usage. Note: Tucker Kraft is NOT on this list despite being a popular TE target - he is on the AVOID list (fade flag).

## 2026 Team Environments (Vegas implied totals)

| Tier | Teams | Implied Total | Games Priced |
|---|---|---|---|
| Elite | ARI (28.3), WAS (25.8), MIA (25.3) | 25+ | 6-8 |
| Strong | DAL (24.9), ATL (24.9), IND (24.9), LV (24.2), CIN (23.8) | 24-25 | 6-8 |
| Good | TEN, NO, BUF, NYJ, CAR, TB, NYG (23-24) | 23-24 | 6-9 |
| Neutral | CHI, GB, CLE, DEN, DET, MIN, NE (22-23) | 22-23 | 6-9 |
| Low | SF, LAC, HOU, PIT, BAL, LA, PHI, SEA, KC (21-22) | 21-22 | 6-8 |

ARI is the #1 environment - highest Vegas implied total (28.3) AND most pass-heavy team (38.2 targets/game). Best landing spot for skill players in 2026.

Note: Fantasy playoff weeks 15-17 have only 4 of 48 games priced. Re-pull schedule_2026.csv nearer to the draft for playoff-window Vegas data.

## 2025 Team Opportunity Supply (most pass-heavy)

| Rank | Team | Targets/Game | Carries/Game | Rec TD Exp | Rec Yds Exp |
|---|---|---|---|---|---|
| 1 | ARI | 38.2 | 21.5 | 32.8 | 4585 |
| 2 | CIN | 37.6 | 22.4 | 30.3 | 4529 |
| 3 | DAL | 36.7 | 27.4 | 41.7 | 4734 |
| 4 | DEN | 36.1 | 26.8 | 29.3 | 4283 |
| 5 | LA | 35.1 | 27.4 | 43.9 | 4705 |
| 6 | NO | 34.8 | 25.6 | 19.7 | 4061 |
| 7 | KC | 34.4 | 25.3 | 32.1 | 4033 |
| 8 | DET | 34.2 | 26.0 | 30.6 | 4417 |
| 9 | HOU | 34.2 | 27.9 | 28.0 | 4177 |
| 10 | CHI | 33.8 | 29.7 | 28.6 | 4466 |

ARI leads in both Vegas implied total AND pass-heavy opportunity supply. DAL has the highest expected receiving TDs (41.7) - target Cowboys pass catchers. LA has 43.9 expected rec TDs - Adams and Nacua are in a high-scoring environment.

## Summary: Top 2026 Draft Targets by Position

### QB
1. Josh Allen (BUF) - 4.4 designed runs/game, 13 rush TDs, elite environment
2. Jalen Hurts (PHI) - 4.1 designed runs/game, 62.7% designed share, tush push TDs
3. Trevor Lawrence (JAC) - 21.2 exp/game, no fade, value in middle rounds
4. Dak Prescott (DAL) - 20.9 exp/game, no fade, best team environment (24.9 implied)

### RB
1. Christian McCaffrey (SF) - 25.5 exp/game, no fade, #1 overall
2. Any BUF RB - +0.72 YOE/carry, 12.9% stuff rate (elite line)
3. Any BAL RB - +0.90 YOE/carry (best line in NFL)
4. Any DET RB - +0.58 YOE/carry, Gibbs/Montgomery boost
5. Any IND RB - +0.56 YOE/carry, Taylor boost

### WR
1. Amon-Ra St. Brown (DET) - 35 RZ targets, 69.2% catchable, 172 total targets
2. Davante Adams (LA) - 34 RZ targets, 13.2 aDOT, 24 EZ targets, high-scoring team
3. Ja'Marr Chase (CIN) - 22 RZ targets, 185 total targets, 67.1% catchable
4. Rashee Rice (KC) - 15 EZ targets on only 79 total = elite TD equity if healthy
5. Khalil Shakir (BUF) - 75.8% catchable, 20 RZ targets, elite slot volume

### TE
1. Trey McBride (ARI) - 34 RZ targets, 170 total, best environment (28.3 implied total)
2. Jake Ferguson (DAL) - 25 RZ targets, 14 EZ targets, elite team environment
3. Tyler Warren (IND) - 23 RZ targets, 13 EZ targets, strong line (+0.56 YOE/carry)
4. Brock Bowers (LV) - 18 RZ targets, 10 EZ targets, decent environment (24.2 implied)
5. AVOID: Tucker Kraft (GB) - fade flag, +5.76 gap/game, 117 pts was ~98 above expectation

## Standing Cautions

1. 4-pt vs 6-pt pass TD: total_fantasy_points_exp is scored at 4-pt pass TDs. If your league uses 6-pt (YTFL does), rebuild from components. The bullish_qb file has the rescored version.
2. Route participation is structurally unfixable from this dataset. ffopportunity has no route counts. The routes_proxy caveat must remain.
3. Two of three new signal candidates failed their control tests (YAC-OE, garbage time). Hold every new signal at display until it passes a null test against 13 seasons of YTFL data.
4. BULLISH tag is display-only (p=0.104, underpowered). Do not use it as a draft gate.
5. The gap signal is a fade filter, not a discovery signal. Use it to AVOID overperformers, not to find sleepers.
6. exp_per_game outpredicts gap 2.4-4x. Prefer exp_per_game as the ranking input.
7. Playoff weeks 15-17 Vegas data is incomplete (4 of 48 games priced). Re-pull before draft.
