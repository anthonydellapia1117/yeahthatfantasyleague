# YTFL ffopportunity - Complete R Code Audit
# All R code used across 4 rounds + preseason + draft board analysis
# R 4.6.1, ffopportunity v0.1.2, nflreadr, dplyr, readr, tidyr
# Generated: August 28, 2026

# =============================================================================
# YTFL ffopportunity R Pipeline - Complete Code Audit
# All R code used across 4 rounds + preseason + draft board
# R 4.6.1, ffopportunity v0.1.2, nflreadr, dplyr, readr, tidyr
# =============================================================================

# =============================================================================
# ROUND 1 - BULLISH POSITION EXTRACTS (2020-2025 weekly)
# Output: bullish_rb/wr/qb/te/gap_signal CSVs
# =============================================================================

library(ffopportunity)
wk <- ep_load(season = 2020:2025, type = "weekly")
out <- path.expand("~/Desktop/ff-hub/ffopportunity_data")

# --- 1. RB ---
rb <- wk[wk$position == "RB", c(
  "season", "week", "player_id", "full_name", "position", "posteam",
  "receptions", "receptions_exp",
  "rush_attempt", "rec_attempt",
  "rush_yards_gained", "rush_yards_gained_exp",
  "rush_touchdown", "rush_touchdown_exp",
  "rec_touchdown", "rec_touchdown_exp",
  "rec_yards_gained", "rec_yards_gained_exp",
  "total_fantasy_points", "total_fantasy_points_exp", "total_fantasy_points_diff",
  "total_touchdown_diff"
)]

rb$expected_td_equity <- rowSums(cbind(rb$rec_touchdown_exp, rb$rush_touchdown_exp), na.rm = TRUE)
rb$team_rush_att <- ave(rb$rush_attempt, rb$posteam, rb$season, rb$week, FUN = function(x) sum(x, na.rm = TRUE))
rb$backfield_command <- ifelse(rb$team_rush_att > 0, rb$rush_attempt / rb$team_rush_att, NA)
rb$target_volume <- rowSums(cbind(rb$receptions, rb$receptions_exp), na.rm = TRUE) / 2
write.csv(rb, file.path(out, "bullish_rb_2020_2025.csv"), row.names = FALSE, na = "")

# --- 2. WR ---
wr <- wk[wk$position == "WR", c(
  "season", "week", "player_id", "full_name", "position", "posteam",
  "receptions", "receptions_exp",
  "rec_attempt", "rec_air_yards",
  "rec_yards_gained", "rec_yards_gained_exp",
  "rec_touchdown", "rec_touchdown_exp",
  "total_fantasy_points", "total_fantasy_points_exp", "total_fantasy_points_diff",
  "total_touchdown_diff"
)]

wr$tprr_proxy <- ifelse(wr$receptions_exp > 0, wr$rec_attempt / wr$receptions_exp, NA)
wr$yprr_proxy <- ifelse(wr$receptions_exp > 0, wr$rec_yards_gained_exp / wr$receptions_exp, NA)
wr$team_targets <- ave(wr$rec_attempt, wr$posteam, wr$season, wr$week, FUN = function(x) sum(x, na.rm = TRUE))
wr$first_read_share <- ifelse(wr$team_targets > 0, wr$rec_attempt / wr$team_targets, NA)
wr$team_rec_exp <- ave(wr$receptions_exp, wr$posteam, wr$season, wr$week, FUN = function(x) sum(x, na.rm = TRUE))
wr$vacated_targets <- wr$team_rec_exp - wr$receptions_exp
write.csv(wr, file.path(out, "bullish_wr_2020_2025.csv"), row.names = FALSE, na = "")

# --- 3. QB ---
qb <- wk[wk$position == "QB", c(
  "season", "week", "player_id", "full_name", "position", "posteam",
  "rush_attempt", "pass_attempt",
  "rush_yards_gained", "rush_yards_gained_exp",
  "rush_touchdown", "rush_touchdown_exp",
  "pass_completions", "pass_completions_exp",
  "pass_yards_gained", "pass_yards_gained_exp",
  "pass_touchdown", "pass_touchdown_exp",
  "pass_interception", "pass_interception_exp",
  "total_fantasy_points", "total_fantasy_points_exp", "total_fantasy_points_diff",
  "total_touchdown_diff"
)]

qb$pass_td_exp_6pt <- qb$pass_touchdown_exp * 6
qb$rush_td_exp_6pt <- qb$rush_touchdown_exp * 6
qb$pass_yds_exp_pts <- qb$pass_yards_gained_exp / 25
qb$rush_yds_exp_pts <- qb$rush_yards_gained_exp / 10
qb$int_exp_pts <- qb$pass_interception_exp * -2
qb$qb_fantasy_points_exp_6pt <- rowSums(cbind(qb$pass_td_exp_6pt, qb$rush_td_exp_6pt, qb$pass_yds_exp_pts, qb$rush_yds_exp_pts, qb$int_exp_pts), na.rm = TRUE)
qb$prior_epa_proxy <- qb$total_fantasy_points_exp
qb$team_implied_total <- ave(qb$total_fantasy_points_exp, qb$posteam, qb$season, qb$week, FUN = function(x) sum(x, na.rm = TRUE))
write.csv(qb, file.path(out, "bullish_qb_2020_2025.csv"), row.names = FALSE, na = "")

# --- 4. TE ---
te <- wk[wk$position == "TE", c(
  "season", "week", "player_id", "full_name", "position", "posteam",
  "receptions", "receptions_exp",
  "rec_attempt", "rec_air_yards",
  "rec_yards_gained", "rec_yards_gained_exp",
  "rec_touchdown", "rec_touchdown_exp",
  "total_fantasy_points", "total_fantasy_points_exp", "total_fantasy_points_diff",
  "total_touchdown_diff"
)]

te$route_participation_proxy <- te$receptions_exp
te$team_rec_yds_exp <- ave(te$rec_yards_gained_exp, te$posteam, te$season, te$week, FUN = function(x) sum(x, na.rm = TRUE))
te$receiving_market_share <- ifelse(te$team_rec_yds_exp > 0, te$rec_yards_gained_exp / te$team_rec_yds_exp, NA)
write.csv(te, file.path(out, "bullish_te_2020_2025.csv"), row.names = FALSE, na = "")

# --- 5. Gap signal ---
gap <- wk[, c(
  "season", "week", "player_id", "full_name", "position", "posteam",
  "total_fantasy_points", "total_fantasy_points_exp", "total_fantasy_points_diff",
  "total_touchdown_diff",
  "receptions_exp", "rec_yards_gained_exp", "rec_touchdown_exp",
  "rush_touchdown_exp", "rush_yards_gained_exp",
  "pass_touchdown_exp", "pass_yards_gained_exp", "pass_completions_exp"
)]
write.csv(gap, file.path(out, "bullish_gap_signal_2020_2025.csv"), row.names = FALSE, na = "")

# =============================================================================
# ROUND 2 - ADVANCED EXTRACTS (Copilot round 1 analysis)
# Output: proe_weekly, vegas_weekly, line_quality, qb_rush_split, adot_redzone, regression_flags
# NOTE: proe_weekly, vegas_weekly, regression_flags were DEPRECATED in round 4
# =============================================================================

library(ffopportunity); library(dplyr); library(readr); library(tidyr)

OUT <- path.expand("~/Desktop/ff-hub/ffopportunity_data")
dir.create(OUT, recursive = TRUE, showWarnings = FALSE)

wk <- ep_load(season = 2020:2025, type = "weekly")
pp <- ep_load(season = 2020:2025, type = "pbp_pass")
pr <- ep_load(season = 2020:2025, type = "pbp_rush")

# 1. PROE - coaching scheme, weekly
bind_rows(
  pp %>% transmute(season, week, posteam, xpass, is_pass = 1),
  pr %>% filter(qb_scramble == 1) %>% transmute(season, week, posteam, xpass, is_pass = 1),
  pr %>% filter(qb_scramble != 1) %>% transmute(season, week, posteam, xpass, is_pass = 0)
) %>%
  filter(!is.na(xpass), !is.na(posteam), posteam != "") %>%
  group_by(season, week, posteam) %>%
  summarise(plays = n(), pass_rate = mean(is_pass), xpass_rate = mean(xpass),
            proe = (mean(is_pass) - mean(xpass)) * 100, .groups = "drop") %>%
  filter(plays >= 10) %>%
  write_csv(file.path(OUT, "proe_weekly_2020_2025.csv"))

# 2. Vegas per week - total_line only in pp, bind_rows fills NA for pr
bind_rows(
  pp %>% select(season, week, posteam, implied_total, total_line, vegas_wp),
  pr %>% select(season, week, posteam, implied_total, vegas_wp)
) %>%
  filter(!is.na(implied_total), !is.na(posteam), posteam != "") %>%
  group_by(season, week, posteam) %>%
  summarise(implied_total = mean(implied_total), total_line = mean(total_line, na.rm = TRUE),
            vegas_wp = mean(vegas_wp), .groups = "drop") %>%
  write_csv(file.path(OUT, "vegas_weekly_2020_2025.csv"))

# 3a. Line quality by gap
pr %>%
  filter(position == "RB", qb_dropback != 1, qb_scramble != 1,
         !is.na(rush_yards_exp), !is.na(posteam), posteam != "") %>%
  mutate(yoe = rushing_yards - rush_yards_exp) %>%
  group_by(season, posteam, run_location, run_gap) %>%
  summarise(carries = n(), yoe_per_carry = mean(yoe),
            stuff_rate = mean(rushing_yards <= 0), .groups = "drop") %>%
  filter(carries >= 15) %>%
  write_csv(file.path(OUT, "line_quality_by_gap_2020_2025.csv"))

# 3b. Line quality team
pr %>%
  filter(position == "RB", qb_dropback != 1, qb_scramble != 1, !is.na(rush_yards_exp)) %>%
  group_by(season, posteam) %>%
  summarise(carries = n(), yoe_per_carry = mean(rushing_yards - rush_yards_exp),
            stuff_rate = mean(rushing_yards <= 0), .groups = "drop") %>%
  filter(carries >= 100) %>%
  write_csv(file.path(OUT, "line_quality_team_2020_2025.csv"))

# 4. QB rushing split - fix: convert rush_touchdown to numeric
pr %>%
  filter(position == "QB") %>%
  mutate(rush_touchdown = as.numeric(as.character(rush_touchdown))) %>%
  group_by(season, rusher_player_id, full_name, posteam) %>%
  summarise(designed = sum(qb_scramble != 1), scrambles = sum(qb_scramble == 1),
            designed_yards = sum(rushing_yards[qb_scramble != 1], na.rm = TRUE),
            scramble_yards = sum(rushing_yards[qb_scramble == 1], na.rm = TRUE),
            designed_td = sum(rush_touchdown[qb_scramble != 1], na.rm = TRUE),
            games = n_distinct(week), .groups = "drop") %>%
  filter(games >= 6) %>%
  mutate(designed_per_game = designed / games, designed_share = designed / (designed + scrambles)) %>%
  write_csv(file.path(OUT, "qb_rush_split_2020_2025.csv"))

# 5. TRUE aDOT and red-zone target share
pp %>%
  filter(!is.na(receiver_player_id), receiver_player_id != "") %>%
  group_by(season, receiver_player_id, receiver_full_name, receiver_position, posteam) %>%
  summarise(targets = n(), adot = mean(air_yards, na.rm = TRUE),
            deep_share = mean(air_yards >= 20, na.rm = TRUE),
            rz_targets = sum(yardline_100 <= 20, na.rm = TRUE),
            ez_targets = sum(yardline_100 <= 10, na.rm = TRUE),
            catchable = mean(pass_completion_exp, na.rm = TRUE), .groups = "drop") %>%
  filter(targets >= 20) %>%
  write_csv(file.path(OUT, "adot_redzone_2020_2025.csv"))

# 6. Regression flags - the fade signal
wk %>%
  group_by(season, player_id, full_name, position) %>%
  summarise(games = n(),
            pts = sum(total_fantasy_points, na.rm = TRUE),
            exp_pts = sum(total_fantasy_points_exp, na.rm = TRUE),
            gap = sum(total_fantasy_points_diff, na.rm = TRUE),
            td = sum(total_touchdown, na.rm = TRUE),
            td_exp = sum(total_touchdown_exp, na.rm = TRUE), .groups = "drop") %>%
  filter(games >= 8) %>%
  mutate(gap_per_game = gap / games, td_gap = td - td_exp,
         fade_flag = gap > 20, exp_per_game = exp_pts / games) %>%
  write_csv(file.path(OUT, "regression_flags_2020_2025.csv"))

# =============================================================================
# 2026 PRESEASON DATA (nflreadr)
# Output: ff_rankings_adp_2026, depth_charts_2026, rosters_2026, schedule_2026
# =============================================================================

library(nflreadr)

# 2026 schedule
sched <- load_schedules()

# Current rosters (90-man camp rosters)
ros <- load_rosters()

# Depth charts
dc <- load_depth_charts()

# Fantasy rankings (ADP)
ff <- load_ff_rankings()

# Export
OUT <- path.expand("~/Desktop/ff-hub/ffopportunity_data")

write.csv(ff, file.path(OUT, "ff_rankings_adp_2026.csv"), row.names = FALSE, na = "")
write.csv(dc, file.path(OUT, "depth_charts_2026.csv"), row.names = FALSE, na = "")
write.csv(ros, file.path(OUT, "rosters_2026.csv"), row.names = FALSE, na = "")
s2026 <- sched[sched$season == 2026, ]
write.csv(s2026, file.path(OUT, "schedule_2026.csv"), row.names = FALSE, na = "")

# =============================================================================
# ROUND 3 - Copilot round 2 analysis (YAC, neutral script, EPA, weather, rebuilt)
# Output: yac_over_expected, neutral_script_role, epa_per_opportunity (DEPRECATED),
#         playoff_weather, proe_weekly_reg, vegas_weekly_reg, regression_flags_clean
# =============================================================================

library(ffopportunity); library(dplyr); library(readr); library(tidyr)

OUT <- path.expand("~/Desktop/ff-hub/ffopportunity_data")
dir.create(OUT, recursive = TRUE, showWarnings = FALSE)

pp <- ep_load(season = 2020:2025, type = "pbp_pass")
pr <- ep_load(season = 2020:2025, type = "pbp_rush")
wk <- ep_load(season = 2020:2025, type = "weekly")

# factor-safe numeric coercion (rush_touchdown ships as factor)
num <- function(x) if (is.factor(x)) as.numeric(as.character(x)) else as.numeric(x)
# regular season only - drops 156 playoff rows
reg <- function(d) d %>% filter(week <= ifelse(season == 2020, 17, 18))

# 1. YAC OVER EXPECTED - strongest repeatable signal (r=.558-.720)
pp %>%
  reg() %>%
  filter(num(complete_pass) == 1, !is.na(receiver_player_id), receiver_player_id != "",
         !is.na(receiver_position), receiver_position %in% c("WR","RB","TE"),
         !is.na(yards_after_catch), !is.na(yards_after_catch_exp)) %>%
  group_by(season, receiver_player_id, receiver_full_name, receiver_position, posteam) %>%
  summarise(receptions = n(),
            yac = sum(num(yards_after_catch)), yac_exp = sum(num(yards_after_catch_exp)),
            yac_oe_total = sum(num(yards_after_catch) - num(yards_after_catch_exp)),
            yac_oe_per_rec = mean(num(yards_after_catch) - num(yards_after_catch_exp)),
            .groups = "drop") %>%
  filter(receptions >= 25) %>%
  write_csv(file.path(OUT, "yac_over_expected_2020_2025.csv"))

# 2. NEUTRAL-SCRIPT ROLE - replaces garbage time (failed control)
bind_rows(
  pp %>% reg() %>% filter(!is.na(receiver_player_id), receiver_player_id != "") %>%
    transmute(season, posteam, player_id = receiver_player_id,
              full_name = receiver_full_name, position = receiver_position,
              kind = "target", qtr = num(qtr), sd = num(score_differential),
              wp = num(vegas_wp), down = num(down)),
  pr %>% reg() %>% filter(position == "RB", num(qb_dropback) != 1, num(qb_scramble) != 1) %>%
    transmute(season, posteam, player_id = rusher_player_id,
              full_name, position, kind = "carry", qtr = num(qtr),
              sd = num(score_differential), wp = num(vegas_wp), down = num(down))
) %>%
  filter(!is.na(sd), !is.na(wp)) %>%
  mutate(neutral = abs(sd) <= 8 & qtr <= 3, early = down %in% c(1, 2)) %>%
  group_by(season, player_id, full_name, position, posteam, kind) %>%
  summarise(opportunities = n(),
            neutral_opps = sum(neutral), neutral_share = mean(neutral),
            early_down_share = mean(early, na.rm = TRUE),
            mean_wp = mean(wp), .groups = "drop") %>%
  filter(opportunities >= 40) %>%
  write_csv(file.path(OUT, "neutral_script_role_2020_2025.csv"))

# 3. EPA PER OPPORTUNITY - efficiency independent of volume (DEPRECATED - QB contamination)
bind_rows(
  pp %>% reg() %>% filter(!is.na(receiver_player_id), receiver_player_id != "", !is.na(ep)) %>%
    transmute(season, player_id = receiver_player_id, full_name = receiver_full_name,
              position = receiver_position, ep = num(ep), kind = "rec"),
  pr %>% reg() %>% filter(!is.na(rusher_player_id), rusher_player_id != "", !is.na(ep)) %>%
    transmute(season, player_id = rusher_player_id, full_name, position, ep = num(ep), kind = "rush")
) %>%
  group_by(season, player_id, full_name, position, kind) %>%
  summarise(opps = n(), ep_total = sum(ep), ep_per_opp = mean(ep), .groups = "drop") %>%
  filter(opps >= 40) %>%
  pivot_wider(names_from = kind, values_from = c(opps, ep_total, ep_per_opp)) %>%
  write_csv(file.path(OUT, "epa_per_opportunity_2020_2025.csv"))

# 4. FANTASY-PLAYOFF WEATHER (wk 15-17)
bind_rows(
  pp %>% transmute(season, week, posteam, roof, surface, wind = num(wind), temp = num(temp)),
  pr %>% transmute(season, week, posteam, roof, surface, wind = num(wind), temp = num(temp))
) %>%
  filter(week >= 15, week <= 17, !is.na(posteam), posteam != "") %>%
  group_by(season, posteam) %>%
  summarise(games = n_distinct(week),
            outdoor_share = mean(roof %in% c("outdoors", "open"), na.rm = TRUE),
            mean_wind = mean(wind, na.rm = TRUE), mean_temp = mean(temp, na.rm = TRUE),
            harsh_share = mean(wind >= 15 | temp <= 32, na.rm = TRUE), .groups = "drop") %>%
  write_csv(file.path(OUT, "playoff_weather_2020_2025.csv"))

# 5. REBUILT PROE + VEGAS - regular season only
bind_rows(
  pp %>% reg() %>% transmute(season, week, posteam, xpass = num(xpass), is_pass = 1),
  pr %>% reg() %>% filter(num(qb_scramble) == 1) %>% transmute(season, week, posteam, xpass = num(xpass), is_pass = 1),
  pr %>% reg() %>% filter(num(qb_scramble) != 1) %>% transmute(season, week, posteam, xpass = num(xpass), is_pass = 0)
) %>%
  filter(!is.na(xpass), !is.na(posteam), posteam != "") %>%
  group_by(season, week, posteam) %>%
  summarise(plays = n(), proe = (mean(is_pass) - mean(xpass)) * 100, .groups = "drop") %>%
  filter(plays >= 25) %>%
  write_csv(file.path(OUT, "proe_weekly_reg_2020_2025.csv"))

bind_rows(
  pp %>% transmute(season, week, posteam, implied_total = num(implied_total),
                   total_line = num(total_line), vegas_wp = num(vegas_wp)),
  pr %>% transmute(season, week, posteam, implied_total = num(implied_total),
                   total_line = NA_real_, vegas_wp = num(vegas_wp))
) %>%
  reg() %>%
  filter(!is.na(implied_total), !is.na(posteam), posteam != "") %>%
  group_by(season, week, posteam) %>%
  summarise(implied_total = mean(implied_total, na.rm = TRUE),
            total_line = mean(total_line, na.rm = TRUE),
            vegas_wp = mean(vegas_wp, na.rm = TRUE), .groups = "drop") %>%
  write_csv(file.path(OUT, "vegas_weekly_reg_2020_2025.csv"))

# 6. REBUILT REGRESSION FLAGS - drops 9 junk rows
wk %>%
  filter(!is.na(player_id), player_id != "", !is.na(position),
         position %in% c("QB","RB","WR","TE"), !is.na(full_name), full_name != "") %>%
  reg() %>%
  group_by(season, player_id, full_name, position) %>%
  summarise(games = n_distinct(week),
            pts = sum(num(total_fantasy_points), na.rm = TRUE),
            exp_pts = sum(num(total_fantasy_points_exp), na.rm = TRUE),
            gap = sum(num(total_fantasy_points_diff), na.rm = TRUE),
            td = sum(num(total_touchdown), na.rm = TRUE),
            td_exp = sum(num(total_touchdown_exp), na.rm = TRUE), .groups = "drop") %>%
  filter(games >= 8, games <= 18) %>%
  mutate(gap_per_game = gap / games, exp_per_game = exp_pts / games,
         td_gap = td - td_exp, fade_flag = gap > 20) %>%
  write_csv(file.path(OUT, "regression_flags_clean_2020_2025.csv"))

# =============================================================================
# ROUND 4 - Final extracts (Copilot round 3 analysis)
# Output: vegas_2026_forward, team_opportunity_supply, epa_per_target_clean
# =============================================================================

library(ffopportunity); library(dplyr); library(readr); library(tidyr)
OUT <- path.expand("~/Desktop/ff-hub/ffopportunity_data")
num <- function(x) if (is.factor(x)) as.numeric(as.character(x)) else as.numeric(x)
SKILL <- c("WR","RB","TE")

# 1. 2026 VEGAS - real forward lines, wk1-6. Replaces Week-1 hardcode.
read_csv(file.path(OUT, "schedule_2026.csv"), show_col_types = FALSE) %>%
  filter(game_type == "REG", !is.na(total_line), !is.na(spread_line)) %>%
  transmute(week, home_team, away_team, total_line = num(total_line), spread_line = num(spread_line),
            home_implied = total_line/2 - spread_line/2,
            away_implied = total_line/2 + spread_line/2) %>%
  pivot_longer(c(home_team, away_team), names_to = "side", values_to = "team") %>%
  mutate(implied_total = ifelse(side == "home_team", home_implied, away_implied)) %>%
  group_by(team) %>%
  summarise(games_priced = n(), implied_total_2026 = mean(implied_total),
            total_line_2026 = mean(total_line), .groups = "drop") %>%
  write_csv(file.path(OUT, "vegas_2026_forward.csv"))

# 2. TEAM OPPORTUNITY SUPPLY - r=.48-.52, most stable signal available.
wk <- ep_load(season = 2020:2025, type = "weekly")
wk %>%
  filter(!is.na(posteam), posteam != "", posteam != "NA",
         week <= ifelse(season == 2020, 17, 18)) %>%
  distinct(season, posteam, week, .keep_all = TRUE) %>%
  group_by(season, posteam) %>%
  summarise(games = n_distinct(week),
            team_targets = sum(num(rec_attempt_team), na.rm = TRUE),
            team_carries = sum(num(rush_attempt_team), na.rm = TRUE),
            team_rec_yds_exp = sum(num(rec_yards_gained_exp_team), na.rm = TRUE),
            team_rec_td_exp = sum(num(rec_touchdown_exp_team), na.rm = TRUE),
            team_rush_td_exp = sum(num(rush_touchdown_exp_team), na.rm = TRUE),
            .groups = "drop") %>%
  mutate(targets_pg = team_targets/games, carries_pg = team_carries/games) %>%
  write_csv(file.path(OUT, "team_opportunity_supply_2020_2025.csv"))

# 3. REBUILT EPA - drops the 122 QB rows (defect).
ep_load(season = 2020:2025, type = "pbp_pass") %>%
  filter(week <= ifelse(season == 2020, 17, 18),
         !is.na(receiver_player_id), receiver_player_id != "",
         receiver_position %in% SKILL, !is.na(ep)) %>%
  group_by(season, receiver_player_id, receiver_full_name, receiver_position) %>%
  summarise(targets = n(), ep_per_target = mean(num(ep)), .groups = "drop") %>%
  filter(targets >= 40) %>%
  write_csv(file.path(OUT, "epa_per_target_clean_2020_2025.csv"))

# =============================================================================
# DRAFT BOARD ANALYSIS (not exported to repo, terminal output only)
# =============================================================================

library(dplyr); library(readr)
OUT <- path.expand("~/Desktop/ff-hub/ffopportunity_data")

# Load 2026 ADP
adp <- read_csv(file.path(OUT, "ff_rankings_adp_2026.csv"), show_col_types = FALSE) %>%
  filter(pos %in% c("QB","RB","WR","TE")) %>%
  select(player, pos, team, ecr, bye) %>%
  rename(full_name = player, posteam = team)

# Load key signals
reg <- read_csv(file.path(OUT, "regression_flags_clean_2020_2025.csv"), show_col_types = FALSE)
vegas26 <- read_csv(file.path(OUT, "vegas_2026_forward.csv"), show_col_types = FALSE)
team_opp <- read_csv(file.path(OUT, "team_opportunity_supply_2020_2025.csv"), show_col_types = FALSE)
line_q <- read_csv(file.path(OUT, "line_quality_team_2020_2025.csv"), show_col_types = FALSE)
qb_split <- read_csv(file.path(OUT, "qb_rush_split_2020_2025.csv"), show_col_types = FALSE)
adot_rz <- read_csv(file.path(OUT, "adot_redzone_2020_2025.csv"), show_col_types = FALSE)

# TARGETS: high exp_per_game, no fade flag, 2025 season
targets <- reg %>%
  filter(season == 2025, !fade_flag, exp_per_game >= 8) %>%
  left_join(adp, by = c("full_name" = "full_name", "position" = "pos")) %>%
  filter(!is.na(ecr)) %>%
  arrange(desc(exp_per_game)) %>%
  select(full_name, position, posteam, exp_per_game, gap_per_game, ecr, bye)

# AVOIDS: fade flag = TRUE (overperformers who regress)
avoids <- reg %>%
  filter(season == 2025, fade_flag) %>%
  left_join(adp, by = c("full_name" = "full_name", "position" = "pos")) %>%
  filter(!is.na(ecr)) %>%
  arrange(desc(gap_per_game)) %>%
  select(full_name, position, posteam, exp_per_game, gap_per_game, pts, ecr)

# RB: best line quality teams (2025)
line_q %>% filter(season == 2025) %>% arrange(desc(yoe_per_carry))

# QB: designed rush share (sticky role)
qb_split %>% filter(season == 2025) %>% arrange(desc(designed_per_game))

# WR: aDOT + red zone (2025)
adot_rz %>% filter(season == 2025, receiver_position == "WR") %>% arrange(desc(rz_targets))

# TE: red zone targets (2025)
adot_rz %>% filter(season == 2025, receiver_position == "TE") %>% arrange(desc(rz_targets))

# 2026 Team Environments (Vegas implied total)
vegas26 %>% arrange(desc(implied_total_2026))

# Team Opportunity Supply (2025, targets per game)
team_opp %>% filter(season == 2025) %>% arrange(desc(targets_pg))