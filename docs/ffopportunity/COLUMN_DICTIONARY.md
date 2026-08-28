# ffopportunity Data Dictionary

Source: [ffverse/ffopportunity](https://github.com/ffverse/ffopportunity) v0.1.2
License: Models and data CC BY-SA 4.0; R code GPL-3
Exported: R 4.6.1 via Homebrew, 2026-08-28
Seasons: 2020-2025

## File Inventory

| File | Description | Granularity |
|---|---|---|
| ep_weekly_2020_2025.csv | All weekly EP data combined | Player x Week |
| ep_weekly_{year}.csv | Per-season weekly splits | Player x Week |
| ep_season_2020_2025.csv | Season-level aggregates | Player x Season |
| ep_pbp_pass_{year}.csv | Play-by-play pass detail | Play-level |
| ep_pbp_rush_{year}.csv | Play-by-play rush detail | Play-level |
| bullish_rb_2020_2025.csv | RB BULLISH criteria extract | Player x Week |
| bullish_wr_2020_2025.csv | WR BULLISH criteria extract | Player x Week |
| bullish_qb_2020_2025.csv | QB BULLISH criteria extract | Player x Week |
| bullish_te_2020_2025.csv | TE BULLISH criteria extract | Player x Week |
| bullish_gap_signal_2020_2025.csv | ADP-orthogonal discovery signal | Player x Week |

## Column Naming Convention

Every stat comes in three forms:
- **actual**: what happened (e.g. receptions)
- **_exp**: expected value from xgboost model using play context (down, distance, field position, air yards, personnel)
- **_diff**: actual minus expected (the gap - positive = overperformed, negative = underperformed)

Team-level variants use _team suffix (e.g. receptions_exp_team = team total expected receptions).

## Core Columns (weekly)

| Column | Type | Description |
|---|---|---|
| season | int | NFL season year |
| week | int | Week of season |
| game_id | chr | Unique game identifier |
| player_id | chr | NFLverse/GSIS player ID |
| full_name | chr | Player full name |
| position | chr | QB, RB, WR, TE |
| posteam | chr | Possession team abbreviation |

## Pass Stats

| Column | Description |
|---|---|
| pass_attempt | Pass attempts (actual) |
| pass_air_yards | Total air yards on passes |
| pass_completions / _exp / _diff | Completions |
| pass_yards_gained / _exp / _diff | Passing yards |
| pass_touchdown / _exp / _diff | Passing TDs |
| pass_first_down / _exp / _diff | Passing first downs |
| pass_interception / _exp / _diff | Interceptions thrown |
| pass_two_point_conv / _exp / _diff | Passing 2pt conversions |
| pass_fantasy_points / _exp / _diff | Fantasy points from passing |

## Rush Stats

| Column | Description |
|---|---|
| rush_attempt | Rush attempts (actual) |
| rush_yards_gained / _exp / _diff | Rushing yards |
| rush_touchdown / _exp / _diff | Rushing TDs |
| rush_first_down / _exp / _diff | Rushing first downs |
| rush_fumble_lost | Fumbles lost on rushes |
| rush_two_point_conv / _exp / _diff | Rushing 2pt conversions |
| rush_fantasy_points / _exp / _diff | Fantasy points from rushing |

## Receiving Stats

| Column | Description |
|---|---|
| rec_attempt | Routes run / targets (receiving attempts) |
| rec_air_yards | Air yards on receptions |
| receptions / _exp / _diff | Receptions |
| rec_yards_gained / _exp / _diff | Receiving yards |
| rec_touchdown / _exp / _diff | Receiving TDs |
| rec_first_down / _exp / _diff | Receiving first downs |
| rec_fumble_lost | Fumbles lost on receptions |
| rec_two_point_conv / _exp / _diff | Receiving 2pt conversions |
| rec_fantasy_points / _exp / _diff | Fantasy points from receiving |

## Total / Composite

| Column | Description |
|---|---|
| total_yards_gained / _exp / _diff | All-purpose yards |
| total_touchdown / _exp / _diff | Total TDs (pass + rush + rec) |
| total_first_down / _exp / _diff | Total first downs |
| total_fantasy_points / _exp / _diff | Total fantasy points (scored at 4-pt pass TDs) |
| total_touchdown_diff | TD actual minus expected |

## BULLISH Derived Columns

### bullish_rb_2020_2025.csv
| Column | BULLISH Criterion | Description |
|---|---|---|
| expected_td_equity | Expected-TD equity | rec_touchdown_exp + rush_touchdown_exp (replaces Vegas implied_total) |
| backfield_command | Backfield command | rush_attempt / team_rush_attempt (share of backfield workload) |
| target_volume | Target volume | (receptions + receptions_exp) / 2 |

### bullish_wr_2020_2025.csv
| Column | BULLISH Criterion | Description |
|---|---|---|
| tprr_proxy | TPRR proxy | rec_attempt / receptions_exp (targets per expected route) |
| yprr_proxy | Adjusted YPRR proxy | rec_yards_gained_exp / receptions_exp (expected yards per route) |
| first_read_share | First-read share | rec_attempt / team_rec_attempt (target share within team/week) |
| vacated_targets | Vacated targets | team_receptions_exp - player_receptions_exp (opportunity to teammates) |

### bullish_qb_2020_2025.csv
| Column | BULLISH Criterion | Description |
|---|---|---|
| qb_fantasy_points_exp_6pt | Prior EPA (rescored) | Expected points rebuilt at 6-pt pass TDs (league scoring) |
| prior_epa_proxy | Prior EPA | total_fantasy_points_exp (opportunity-adjusted production) |
| team_implied_total | Team implied total | Sum of team total_fantasy_points_exp for the week |

### bullish_te_2020_2025.csv
| Column | BULLISH Criterion | Description |
|---|---|---|
| route_participation_proxy | Route participation | receptions_exp (best available proxy - no raw route counts in ffopportunity) |
| receiving_market_share | Receiving market share | rec_yards_gained_exp / team_rec_yards_gained_exp |

### bullish_gap_signal_2020_2025.csv
| Column | Description |
|---|---|
| total_fantasy_points_diff | The gap: actual - expected fantasy points. ADP-orthogonal (r = -0.155 vs ADP). Positive = overperformed, negative = underperformed. |

## Scoring Note

total_fantasy_points_exp is scored at 4-point passing TDs. If your league uses 6-point pass TDs, rebuild from component _exp columns (pass_touchdown_exp * 6, rush_touchdown_exp * 6, pass_yards_gained_exp / 25, rush_yards_gained_exp / 10, pass_interception_exp * -2). See bullish_qb_2020_2025.csv for the rescored version.
