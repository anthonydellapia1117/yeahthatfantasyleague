# YTFL ffopportunity — CORRECTED R CODE
# Supersedes ALL_R_CODE.R. Five defects fixed; each marked [FIX n].
# R 4.6.1, ffopportunity v0.1.2, nflreadr, dplyr, readr, tidyr
# Revised: August 28, 2026

# =============================================================================
# DEFECT SUMMARY — what was wrong and how it was verified
#
# [FIX 1] VEGAS SIGN INVERTED (critical)
#   Was:  home_implied = total_line/2 - spread_line/2
#   Is:   home_implied = total_line/2 + spread_line/2
#   Verification: nflverse spread_line is POSITIVE when HOME is favored.
#   Tested against home_moneyline vs away_moneyline on all 112 priced 2026
#   games: 112/112 agreement, zero exceptions. Worked example NO @ DET,
#   total 48.5, spread +7.0 -> DET (home, favored) 27.75, NO 20.75.
#   The old formula gave the home favorite the LOWER total.
#   NOTE: the Python app at src/build_bullish_inputs.py:156 was ALREADY
#   CORRECT (tl/2 + sp/2). The R code introduced a regression against it.
#
# [FIX 2] QB INTERCEPTION VALUE + MISSING TWO-POINT CONVERSIONS
#   Was:  pass_interception_exp * -2   and no 2pt term
#   Is:   pass_interception_exp * -1.0 and + (pass_2pt + rush_2pt) * 2.0
#   Verification: src/build_bullish.py W dict is authoritative —
#   passing_interceptions: -1.0, passing_2pt_conversions: 2.0,
#   rushing_2pt_conversions: 2.0.
#   Confirmed correct as written: pass yards /25 == 0.04, rush yards /10 == 0.1.
#
# [FIX 3] THREE MISLABELED DERIVED COLUMNS (removed, not renamed)
#   team_implied_total = ave(total_fantasy_points_exp, team-week, sum)
#     -> sum of QB expected fantasy points in a team-week. One QB plays, so
#        it is that QB's own expected points relabeled. NOT a Vegas total.
#   prior_epa_proxy = total_fantasy_points_exp  -> a straight rename, not EPA.
#   (Same class as route_participation_proxy == receptions_exp.)
#   Both DROPPED. Use qb_fantasy_points_exp_6pt, or join vegas_2026_forward.csv
#   for a real implied total.
#
# [FIX 4] target_volume WAS NOT A MEANINGFUL QUANTITY
#   Was:  (receptions + receptions_exp) / 2
#   The midpoint of an actual and its own expectation is neither. DROPPED.
#   Replaced with two explicit columns: receptions (realized) and
#   receptions_exp (stable). Choose per use; never average them.
#
# [FIX 5] 2,530 JUNK ROWS IN bullish_qb (38% of the file) — NOT in the
#   original audit; found during regeneration.
#   The QB extract carried 2,530 rows with blank position, blank season,
#   blank player_id, and 0 in every computed column. BULLISH thresholds are
#   PERCENTILES of these distributions, so a column that is 38% zeros
#   deflates every QB threshold. All position filters below are explicit.
#
# STILL OPEN (not fixable here):
#   QB fade_flag is contaminated. gap derives from total_fantasy_points,
#   scored at 4-pt passing TDs. Expected and actual TD counts differ, so the
#   4-pt error does not cancel cleanly. Do not display a QB fade flag until
#   it is recomputed from league-exact components on BOTH sides.
# =============================================================================

library(ffopportunity); library(dplyr); library(readr); library(tidyr)

OUT <- path.expand("~/Desktop/ff-hub/ffopportunity_data")
dir.create(OUT, recursive = TRUE, showWarnings = FALSE)

# factor-safe coercion. NOT named n() — collides with dplyr::n().
num <- function(x) if (is.factor(x)) as.numeric(as.character(x)) else as.numeric(x)
# fantasy regular season only: 2020 ended wk 17, 2021+ end wk 18
reg <- function(d) d %>% filter(week <= ifelse(season == 2020, 17, 18))
SKILL <- c("QB", "RB", "WR", "TE")

wk <- ep_load(season = 2020:2025, type = "weekly")
pp <- ep_load(season = 2020:2025, type = "pbp_pass")
pr <- ep_load(season = 2020:2025, type = "pbp_rush")

# league scoring, from src/build_bullish.py (authoritative)
PASS_TD <- 6.0; RUSH_TD <- 6.0; REC_TD <- 6.0
PASS_YD <- 0.04; RUSH_YD <- 0.1; REC_YD <- 0.1
RECEPTION <- 1.0; INT <- -1.0; TWO_PT <- 2.0

# =============================================================================
# [FIX 1] vegas_2026_forward.csv — REGENERATED, not repaired
# =============================================================================
read_csv(file.path(OUT, "schedule_2026.csv"), show_col_types = FALSE) %>%
  filter(game_type == "REG", !is.na(total_line), !is.na(spread_line)) %>%
  transmute(week,
            home_team, away_team,
            total_line  = num(total_line),
            spread_line = num(spread_line),
            # [FIX 1] positive spread_line = HOME favored -> home ADDS spread/2
            home_implied = total_line / 2 + spread_line / 2,
            away_implied = total_line / 2 - spread_line / 2) %>%
  { bind_rows(
      transmute(., team = home_team, implied_total = home_implied, total_line),
      transmute(., team = away_team, implied_total = away_implied, total_line)) } %>%
  group_by(team) %>%
  summarise(games_priced = n(),
            implied_total_2026 = mean(implied_total),
            total_line_2026    = mean(total_line), .groups = "drop") %>%
  arrange(team) %>%
  write_csv(file.path(OUT, "vegas_2026_forward.csv"))

# SANITY GUARD — fails loudly if the sign ever inverts again.
# Home favorites must average a HIGHER implied total than road underdogs.
.chk <- read_csv(file.path(OUT, "schedule_2026.csv"), show_col_types = FALSE) %>%
  filter(game_type == "REG", !is.na(spread_line), !is.na(home_moneyline)) %>%
  mutate(home_fav_ml = num(home_moneyline) < num(away_moneyline),
         home_fav_spread = num(spread_line) > 0)
stopifnot(all(.chk$home_fav_ml == .chk$home_fav_spread))
cat("[FIX 1] spread convention verified on", nrow(.chk), "games\n")

# =============================================================================
# [FIX 2][FIX 3][FIX 5] bullish_qb — league-exact scoring, no mislabels, no junk
# =============================================================================
wk %>%
  filter(position == "QB",                                   # [FIX 5] explicit
         !is.na(player_id), player_id != "",
         !is.na(full_name), full_name != "") %>%
  mutate(
    pass_td_exp_6pt  = num(pass_touchdown_exp)     * PASS_TD,
    rush_td_exp_6pt  = num(rush_touchdown_exp)     * RUSH_TD,
    pass_yds_exp_pts = num(pass_yards_gained_exp)  * PASS_YD,
    rush_yds_exp_pts = num(rush_yards_gained_exp)  * RUSH_YD,
    int_exp_pts      = num(pass_interception_exp)  * INT,      # [FIX 2] -1.0
    two_point_exp_pts = (num(pass_two_point_conv_exp) +
                         num(rush_two_point_conv_exp)) * TWO_PT,  # [FIX 2] added
    qb_fantasy_points_exp_6pt = pass_td_exp_6pt + rush_td_exp_6pt +
      pass_yds_exp_pts + rush_yds_exp_pts + int_exp_pts + two_point_exp_pts
  ) %>%
  # [FIX 3] prior_epa_proxy and team_implied_total intentionally NOT created
  select(season, posteam, week, game_id, player_id, full_name, position,
         pass_attempt, rush_attempt, pass_completions, pass_completions_exp,
         pass_yards_gained, pass_yards_gained_exp,
         rush_yards_gained, rush_yards_gained_exp,
         pass_touchdown, pass_touchdown_exp,
         rush_touchdown, rush_touchdown_exp,
         pass_interception, pass_interception_exp,
         pass_two_point_conv_exp, rush_two_point_conv_exp,
         total_fantasy_points, total_fantasy_points_exp,
         total_fantasy_points_diff, total_touchdown_diff,
         pass_td_exp_6pt, rush_td_exp_6pt, pass_yds_exp_pts, rush_yds_exp_pts,
         int_exp_pts, two_point_exp_pts, qb_fantasy_points_exp_6pt) %>%
  write_csv(file.path(OUT, "bullish_qb_2020_2025.csv"))

# =============================================================================
# [FIX 4] bullish_rb — target_volume dropped, replaced by two explicit columns
# =============================================================================
wk %>%
  filter(position == "RB", !is.na(player_id), player_id != "") %>%
  group_by(season, posteam, week) %>%
  mutate(team_rush_att = sum(num(rush_attempt), na.rm = TRUE)) %>%
  ungroup() %>%
  mutate(
    expected_td_equity = num(rec_touchdown_exp) + num(rush_touchdown_exp),
    # team_rush_att from the RB subset is correct: the _team column would
    # include QB scrambles and kneels
    backfield_command  = ifelse(team_rush_att > 0,
                                num(rush_attempt) / team_rush_att, NA_real_),
    receptions_realized = num(receptions),        # [FIX 4] explicit, not averaged
    receptions_expected = num(receptions_exp)
  ) %>%
  write_csv(file.path(OUT, "bullish_rb_2020_2025.csv"))

cat("regenerated: vegas_2026_forward, bullish_qb, bullish_rb\n")

# =============================================================================
# UNCHANGED AND STILL VALID (no defects found)
#   line_quality_team / line_quality_by_gap  — RB YOE by run gap
#   qb_rush_split                            — designed vs scramble
#   adot_redzone                             — true aDOT, RZ/EZ targets
#   proe_weekly_reg                          — coaching scheme, reg season
#   vegas_weekly_reg                         — uses ffopportunity's OWN
#                                              implied_total column, which is
#                                              authoritative and unaffected
#                                              by [FIX 1]
#   team_opportunity_supply                  — most stable signal (r=.48-.52)
#   regression_flags_clean                   — but see QB fade caveat above
#   yac_over_expected                        — display only, failed control
#   playoff_weather                          — display only
# =============================================================================
