# YeahThatFantasyLeague! — Complete League Legacy Data Archive

**League:** YeahThatFantasyLeague! (League Legacy ID 3854, slug `totallyheterosexualmensffl-id-42081`)
**Sport / Format:** NFL · redraft
**Seasons covered:** 2013–2026 (14 seasons)
**Source:** https://leaguelegacy.io/leagues/totallyheterosexualmensffl-id-42081-id-3854
**Extracted:** 2026-08-11T10:52:29.668Z

---

## What this archive is

This is a full structured export of every dataset that the League Legacy site renders for this league. Rather than scraping rendered HTML tables, the data was pulled directly from the application's own JSON endpoints, so the values here are the exact underlying records the site uses — including many fields that are computed but never displayed on screen (luck, schedule strength, coach score, points share, optimal-lineup points, ADP differentials, transaction value, and so on).

Every folder in this archive maps to one tab in the site's left-hand navigation. Files are CSV unless the underlying data is a chart series with an irregular shape, in which case it is preserved as JSON so nothing is lost.

---

## Folder map (one folder per site tab)

| Folder | Site tab | What it holds |
|---|---|---|
| `00_league/` | League Home | League settings, the member roster, the season registry, roster slot configuration |
| `01_history/` | History | All-time standings, per-season finishes, Elo-style league rating over time |
| `02_gamecenter/` | Gamecenter | Every head-to-head matchup ever played, plus the player-by-player lineup behind each one |
| `03_playoffs/` | Playoffs | Championship games, playoff-only matchups, title-run paths, playoff extremes |
| `04_draft/` | The Draft | Every draft pick in league history with value and ADP context |
| `05_transactions/` | Transactions | Every waiver claim and trade, the players moved, and transaction-value charts |
| `06_players/` | Players | All-time player performance ledger, positional summaries, all-pro selections |
| `07_versus/` | Versus | Head-to-head records between every pair of managers, as a matrix and as long-form rows |
| `08_finances/` | Finances | Dues and payment ledger (see caveats — this league has never used the feature) |
| `09_schedule/` | Schedule | League calendar events, scheduled and completed |
| `10_newsletters/` | Newsletters | Published newsletter issues with links back to the site |
| `11_achievements/` | Achievements | Badge counts per manager (see caveats) |
| `12_record_book/` | Record Book | The full catalogue of 476 tracked records (see caveats) |
| `13_season_teams/` | (cross-tab) | The complete unabridged season-team table, every computed column retained |
| `14_members/` | Member pages | Per-manager career history and transaction profiles |
| `15_rules_notes/` | Rules / Notes | The written league constitution and season annotations |
| `16_franchise/` | Franchise | Franchise dashboard stats |
| `_manifest.csv` | — | Row count, column count and byte size of every file in this archive |

---

## How the tables link together

Five identifier columns tie the entire archive into one relational model.

**`member_id`** is the permanent identity of a manager and never changes across seasons. It is the spine of the archive: it appears in `00_league/members.csv`, `01_history/all_time_standings.csv`, `02_gamecenter/matchups.csv` (as both `member_id` and `opponent_member_id`), `07_versus/head_to_head_pairs.csv`, `14_members/member_profiles.csv` and the record book tables. Join on this whenever you want a manager's full career. A human-readable `member_name` column has been denormalised onto essentially every table so the CSVs are readable on their own without joining.

**`team_id`** (`season_team_id` in the source data) identifies one manager in one specific season. It is the bridge between season-level and event-level data: `13_season_teams/season_teams_full.csv` is the parent table, and `02_gamecenter/matchups.csv`, `04_draft/draft_results.csv` and `05_transactions/transactions.csv` all reference it. Use `team_id` rather than `member_id` when you need to attribute an event to the right season, because managers change team names and co-managers over time.

**`season`** is the four-digit year and is present as a plain text column on every event-level table. It is the simplest way to slice the archive chronologically. `00_league/seasons.csv` is the reference table and carries that year's scoring format, roster configuration, playoff structure and week counts, which matters because the league's rules changed over time — matchup counts move from 184 to 196 per season starting in 2021, for example.

**`matchup_id`** links a single team's weekly result in `02_gamecenter/matchups.csv` to the individual player lines in `02_gamecenter/matchup_rosters.csv`. Note that `matchup_guid` is shared by both sides of a game, so every real head-to-head contest appears as two rows — one from each manager's perspective. Group by `matchup_guid` to collapse to one row per game; that duplication is why the matchup file has 2452 rows rather than half that.

**`player_id`** (an NFL GSIS identifier such as `00-0025394`) connects `06_players/players_all_time.csv`, `04_draft/draft_results.csv` and `02_gamecenter/matchup_rosters.csv`, letting you trace a player from the draft board, through every week he was rostered, to his career totals in this league.

A worked example: to answer "how many points did Cambrias get from players he drafted himself," start at `04_draft/draft_results.csv` filtered to that manager, join to `02_gamecenter/matchup_rosters.csv` on `player_id` plus `season`, and restrict to rows where `started` is true and the `team_id` matches the drafting team.

---

## Folder-by-folder detail

### 00_league
`league_info.csv` is a key/value dump of every league-level setting, including which site features are switched on. `members.csv` carries 24 manager records with their permanent ID, slug, commissioner flags, franchise branding and current league rating. `seasons.csv` holds 14 rows, one per season, with the full ruleset in force that year.

### 01_history
`all_time_standings.csv` reproduces the site's All-Time Standings table: career record, all-play record (how a manager would have fared against the entire league every week), league rating, and a JSON trophy count. `season_results.csv` is the most useful single file for narrative work — 168 rows, one per manager per season, with final rank, playoff seed, record, points for and against, luck, schedule strength, coach rank, draft rank and manager rank side by side. `member_rating_by_season.csv` tracks how each manager's rating moved year to year.

### 02_gamecenter
`matchups.csv` is the largest analytical asset: 2452 rows covering every scored week from 2013 onward, with actual points, projected points, optimal-lineup points, weekly scoring rank, points share, coach score and a luck figure for both the manager and his opponent, plus flags for playoff, championship, consolation, game-of-the-week and rivalry games. `matchup_rosters.csv` explodes each of those into 37106 individual player-week lines showing lineup slot, whether the player was started, whether he would have been in the optimal lineup, and points scored. That optimal flag is what makes "points left on the bench" analysis possible.

### 03_playoffs
`championship_games.csv` lists all 13 title games with winner, loser, both scores and margin. `road_to_championship_games.csv` walks each champion's postseason path game by game. `playoff_matchups.csv` is a pre-filtered slice of the main matchup table containing only postseason and consolation games.

### 04_draft
`draft_results.csv` contains 2339 picks. Beyond the obvious round, pick and player columns it carries the site's computed `value` for the pick and, where available, ADP context — the consensus pick the player normally went at, and how far this league reached or waited relative to that.

### 05_transactions
`transactions.csv` holds 3938 waiver moves and trades with the FAAB bid or waiver priority used, the player added and dropped, and a `value` score representing how much the move ultimately helped or hurt. `transaction_items.csv` breaks multi-player trades into their 7404 constituent player movements, which is what you need for trades involving more than one player per side.

### 06_players
`players_all_time.csv` is a 1008-row career ledger: total points in this league, average when started, best single week, weeks rostered versus weeks started, times drafted, times added and dropped, and championship contributions. `all_pro_teams.csv` and `all_pro_leaders.csv` hold the site's positional honour rolls.

### 07_versus
`head_to_head_matrix.csv` is the human-readable grid — one row per manager, one column per opponent, cells showing the all-time series record. `head_to_head_pairs.csv` is the same information in long form with far more depth: 198 directed pairings carrying points for and against, average margin, current streak, last meeting, and a separate playoff-only sub-record. Use the long form for analysis and the matrix for reading.

### 13_season_teams
`season_teams_full.csv` deliberately retains every column the API returns, unfiltered, including nested stat blocks preserved as JSON strings. If a column you need was dropped for readability elsewhere, it is here. `season_team_position_stats.csv` breaks each team-season into 1092 rows of positional production with league rank.

### 15_rules_notes
`league_rules.md` and `league_rules.csv` contain the league constitution as written by the commissioner, split into its 17 numbered subsections across six sections. `season_annotations.csv` holds 198 in-season notes attached to specific weeks and matchups.

---

## Caveats and known gaps

Three things in this archive are thinner than they should be, and all three have the same cause: at the moment of extraction the League Legacy site was running a background recalculation job over this league, and it had cleared the affected tables while it rebuilt them. The site itself was displaying "Your Record Book is currently running updates" during the capture.

**Record Book.** `12_record_book/record_index.csv` is complete — all 476 tracked record definitions with their names, labels, categories and direct URLs. What is missing is the per-record holder, ranking and history data, which returned empty for every record key while the job ran. Re-running the extraction once the site finishes rebuilding will populate roughly 15,000 additional rows across current holders, top rankings, member rankings, historical succession and per-season holders.

**Achievements.** `member_achievement_summary.csv` has the 21 managers but their badge counts read zero, and the recent-achievements feed came back empty, for the same reason. An earlier probe during this session saw roughly 820 achievement events, so the data does exist and will return.

**Finances.** `08_finances/` is genuinely empty rather than blocked. The finance feature is enabled on the league but no dues or payments have ever been entered, so every manager's debits, credits and net are zero. This is an accurate reflection of the source.

Two smaller notes. The 2013 season has no transaction history — it predates transaction importing for this league, so `transactions.csv` starts at 2014 even though matchups and drafts go back to 2013. And newsletters only exist for 2025; earlier seasons have none.

## A note on personal data

Manager email addresses, linked user account identifiers, Discord IDs and platform service keys were deliberately excluded from every CSV. Names, slugs, team names and all competitive statistics are retained in full. If you need those identity fields they remain available in your own commissioner view on the site.
