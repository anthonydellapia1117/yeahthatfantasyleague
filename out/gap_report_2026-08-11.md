# YTFL Data Gap Report - Phases 2 through 5

**Prepared 2026-08-11.** Every count below was reproduced by reading the named file in this session. Corpus shorthand used throughout:

| Key | Absolute path |
|---|---|
| **A** | `/Users/anthony/Claude/Projects/ff-hub/made-resources/YeahThatFantasyLeague_LeagueLegacy_Archive_2013-2026/` |
| **B** | `/Users/anthony/Claude/Projects/ff-hub/LeagueLegacy-io/leaguelegacy_YeahThatFantasyLeague_full_export/` |
| **raw** | `/Users/anthony/Claude/Projects/ff-hub/raw/` (Sleeper 2025 and 2026 pulls) |
| **out** | `/Users/anthony/Claude/Projects/ff-hub/out/` (derived, not a source) |

---

## 1. The answer

**Phases 2, 3 and 4 can run today on a stated basis. Phase 5 cannot select a live branch and will not be able to until the 2026 draft order posts on Sleeper. No scrape changes that.**

The single most important missing item is **per-player long-play bonus points for the 2,256 Yahoo-era team-weeks, seasons 2013 through 2024**. The cause is now identified exactly, not merely suspected:

`A/00_league/seasons.csv` column `stat_modifiers` carries six long-play bonus categories in every season 2013 through 2024 and in neither Sleeper season:

| stat_id | Name (from `stat_categories`) | Value | Present 2013-2024 | Present 2025-2026 |
|---|---|---|---|---|
| 59 | 40 Yd Comp | 1 | Yes, 12 of 12 seasons | No |
| 60 | 40 Yd Pass TD | 2 | Yes | No |
| 61 | 40 Yd Rush | 1 | Yes | No |
| 62 | 40 Yd Rush TD | 2 | Yes | No |
| 63 | 40 Yd Rec | 1 | Yes | No |
| 64 | 40 Yd Rec TD | 2 | Yes | No |

Those bonuses are inside the official team score in `B/matchups_all.csv` column `points` but are absent from every per-player row in `B/rosters_weekly_all.csv` and `A/02_gamecenter/matchup_rosters.csv`. Summing `points` over `started == 'true'` and comparing to `matchups_all.csv` `points`, with `points` coalesced to `points_ppr` where zero (n = 2,452 team-weeks, 0 unmatched):

| Season | Team-weeks | Exact match on `points` | Mean residual | Median residual |
|---|---|---|---|---|
| 2013 | 184 | 5 | 6.77 | 7.00 |
| 2014 | 184 | 9 | 6.95 | 7.00 |
| 2015 | 184 | 9 | 6.58 | 6.00 |
| 2016 | 184 | 10 | 6.32 | 6.00 |
| 2017 | 184 | 7 | 6.00 | 5.00 |
| 2018 | 184 | 8 | 6.70 | 6.50 |
| 2019 | 184 | 18 | 6.01 | 6.00 |
| 2020 | 184 | 10 | 5.98 | 5.00 |
| 2021 | 196 | 17 | 5.68 | 5.00 |
| 2022 | 196 | 13 | 5.50 | 5.00 |
| 2023 | 196 | 11 | 5.52 | 5.00 |
| 2024 | 196 | 15 | 5.85 | 5.00 |
| **2025** | **196** | **196** | **0.00** | **0.00** |

Across the 2,256 Yahoo-era team-weeks the residual is a whole integer in 2,227, non-negative in 2,233, exactly zero in 138, max 26.00, min -7.00. That is bonus points, not lost data, and it is why 2025 reconciles 196 of 196.

**Consequence, stated plainly.** The Phase 2 central number (DRAFTED vs ACQUIRED share of starter points) is a ratio on a bonus-exclusive numerator and a bonus-exclusive denominator, so it is internally consistent and computes today. What does not survive is any claim that per-pick realized points equal official in-league scoring for 2013-2024, and any absolute starter-point total that ties out to the official season total. Per-pick VOR and hit/bust inherit a real distortion, because the six bonuses concentrate on deep-threat WRs, explosive RBs and vertical QBs, which is exactly the archetype signal Phase 2 is built to measure.

The central number as it computes today, on `points` coalesced to `points_ppr` where zero, n = 22,063 started rows, 287,369.4 total starter points:

| Season | DRAFTED share of starter points |
|---|---|
| 2013 | 70.8% |
| 2014 | 76.5% |
| 2015 | 73.2% |
| 2016 | 61.5% |
| 2017 | 63.1% |
| 2018 | 73.2% |
| 2019 | 70.0% |
| 2020 | 74.8% |
| 2021 | 74.4% |
| 2022 | 72.2% |
| 2023 | 59.9% |
| 2024 | 62.8% |
| 2025 | 65.2% |

---

## 2. What is present and canonical

| Data type | Canonical file | Rows | Which corpus wins, and why |
|---|---|---|---|
| Draft picks | `A/04_draft/draft_results.csv` | 2,339 | **A wins.** Same 2,339 rows as `B/draft_picks_all.csv`, but A adds `service_player_id` (2,339 of 2,339 populated), which resolves 9 picks that fail the `player_id` join. `B/draft_index_all.json` holds only 2,012 and must never be the pick spine |
| Pick-to-production key | `service_player_id` in `A/04_draft/draft_results.csv` and `A/02_gamecenter/matchup_rosters.csv` | - | Same-season pick-to-roster join: 2,317 of 2,339 on `service_player_id` versus 2,308 of 2,339 on `player_id`. Use `player_id` only as fallback |
| Weekly rosters | `A/02_gamecenter/matchup_rosters.csv` | 37,106 | **A wins.** Value-identical to `B/rosters_weekly_all.csv` on shared columns, but carries `matchup_id`, `team_id`, `member_name`, `service_player_id`. B carries `player` and `nfl_team` names A lacks; keep both open |
| Official team score | `B/matchups_all.csv` column `points` | 2,452 | Agrees with column `result` in 2,452 of 2,452 team-rows. This is the score of record, not the roster sum |
| Lineup slots | `lineup_slot` in `B/rosters_weekly_all.csv` / `lineup_position` in `A/02_gamecenter/matchup_rosters.csv` | 37,106 | Nine values: BN 14,531, RB 4,903, WR 4,901, QB 2,452, TE 2,452, W/R/T 2,452, DEF 2,452, K 2,451, IR 512 |
| Transactions header | `B/transactions_all.csv` | 3,938 | 2014-2025 only. `type`: add/drop 2,819, add 447, drop 423, trade 248, commissioner 1 |
| Transaction items | `B/transaction_items_all.csv` | 7,404 | **B wins for the join.** Carries `player_id` (7,404 of 7,404), `week`, `date`, `direction`. A's `05_transactions/transaction_items.csv` has no name column but carries the nested cross-platform player JSON |
| Cross-platform player crosswalk | `A/05_transactions/transaction_items.csv` column `player` plus `B/draft_index_all.json` `draftResults[].player` | 943 and 663 distinct players | Union covers 691 of the 700 drafted players. Fields: `yahoo_id`, `espn_id`, `sleeper_id`, `fleaflicker_id`, `mfl_id`, `nfl_id`, `cbs_id`, `sportradar_id`, `fantasypros_id`, `gsis_id` |
| Scoring rules | `A/00_league/seasons.csv` columns `stat_categories`, `stat_modifiers` | 14 | The only authoritative statement of scoring. `stat_id` 11 (`Rec`) = 1 in all 14 seasons, i.e. full PPR |
| Platform provenance | `A/00_league/seasons.csv` and `B/seasons_settings.csv` column `service_type` | 14 | yahoo 2013-2024, sleeper 2025-2026. Every basis discontinuity lands on that boundary |
| 2025 draft, live | `raw/sleeper_2025_picks.json` (168) and `GET /v1/draft/1245905122333040640` | 168 | `slot_to_roster_id` is populated and non-identity; it reproduces `draft_slot` for all 168 picks. `picked_by` non-null 168 of 168, `cpu_autopick` = 0 |
| 2026 player pool and market ADP | Sleeper projections endpoint, live | 3,301 | Fetched 2026-08-11, all six positions HTTP 200: QB 355, RB 744, WR 1,364, TE 649, K 157, DEF 32. `stats.adp_ppr` populated on 3,301 of 3,301 |
| Identity, franchises, champions | `out/identity_map.csv`, `out/franchises.csv`, `out/franchise_lineage.md`, `out/champions.csv` | - | Derived, already verified 12 of 12 and 13 of 13. Not sources |

---

## 3. Confirmed gaps, blocking first

| # | Gap | Status | Severity | What it blocks | Closeable by scrape |
|---|---|---|---|---|---|
| G1 | Per-player long-play bonus points absent, 2013-2024. Residual mean 5.50 to 6.95 per team-week, 2,256 team-weeks, integer in 2,227 | unreliable | **blocking** | Absolute in-league starter points, cross-position VOR, per-pick realized-vs-expected, hit/bust. Phase 3 archetype scoring and luck controls inherit it | **Yes.** Scrape item 1 |
| G2 | 2026 draft slot assignment does not exist. `GET /v1/draft/1389378429505241089` returns `draft_order: null`, `status: "pre_draft"`, `slot_to_roster_id` identity 1-to-1 through 12-to-12, `/picks` returns 0. `B/seasons_meta_full.json` 2026 has `draft_at: null`, `status: "pre-draft"` | missing | **blocking** | Phase 5 branch selection. Survival probability, opportunity cost and every decision card are slot-conditional. Simulator can only run 12 times, once per slot | **No.** LeagueLegacy is a downstream Sleeper mirror for 2026. Poll Sleeper |
| G3 | `points` is literally 0 on all 886 rows of 2024 weeks 1-5, in both corpora. 540 started rows, 60 team-weeks summing to 0.00 | unreliable | **blocking uncorrected** | 2024 loses 28% of starter points and its DRAFTED share reads as an artifact | **Mostly no.** Coalescing to `points_ppr` restores 534 of 540 starters. 2 starter rows have blank `points_ppr` and are unrecoverable locally. Scrape item 4 |
| G4 | `A/06_players/players_all_time.csv` shows `total_pts` = 0, `avg_started_pts` = 0, `started_weeks` = 35 for Mike Williams `00-0033536`. All 78 roster rows carry `points` = 0, of which 42 are started | unreliable | blocking for that player | 42 started player-weeks across 2018-2023 contribute zero to the split. He is the player behind 7 draft picks and 9 transaction items | **Yes.** Scrape item 3 |
| G5 | Raw ADP: `adp` and `adp_pick` 0 of 2,339 in `B/draft_picks_all.csv`; `adp_effective_pick` and `adp_effective_adp` 0 of 2,339 in `A/04_draft/draft_results.csv`; both null on all 2,012 objects in `B/draft_index_all.json` | missing | degrading | Absolute ADP curves, ADP tiers, market-relative run detection for 12 of 13 seasons | **Probe only.** The site's own JSON returns null. ADP is derivable as `overall_pick - adp_differential` for 2,039 picks. Scrape item 5 |
| G6 | `adp_differential` missing on 300 of 2,339 picks. Worst seasons 2022 (61 of 180) and 2025 (52 of 168). By position: WR 71, RB 63, DEF 53, TE 49, K 41, QB 14, blank 7, DB 2 | partial | degrading | Phase 4 reach-vs-ADP. Rounds 1-5 lose only 21 of 779 (2.7%), but 2025 rounds 1-5 lose 6 of 60 (10.0%) and that is the highest-weight season | **Partly.** Scrape item 5 |
| G7 | `B/draft_index_all.json` `draftResults` holds 2,012, not 2,339. The 327-pick shortfall is fully deterministic: GaTTa 62, LFTLR 121, Team JoeBa 137 (the three `status=departed` franchises, absent in every season) = 320, plus the 7 `00-0021142` picks | unreliable | degrading | Nothing, if the CSVs stay canonical. Becomes serious if the JSON is ever substituted: it drops 3 of 15 franchises, 21 of 156 franchise-seasons, and one title-holder | **Yes, but not by pagination.** Scrape item 2 |
| G8 | 7 draft picks and 9 transaction items carry `player_id` `00-0021142` with blank name and blank position. That id appears 0 times in any roster file and 0 times in `B/players_alltime.csv` | missing | degrading, **resolvable locally** | Phase 3 rounds 1-5 positional sequence for 2022 (overall pick 35 is round 3) | **No scrape needed.** All 7 carry `service_player_id` 30120, which maps 78 of 78 to gsis `00-0033536` in `A/02_gamecenter/matchup_rosters.csv` |
| G9 | No per-pick timestamps, pick durations, or autopick flags in either corpus or in Sleeper. 28 JSON keys, 24 CSV columns, 10 Sleeper pick keys, none temporal. All 12 Yahoo PDFs return 1 to 2 characters under `pdftotext` | missing | moderate, not blocking | Nothing Phase 4 or Phase 5 names. Run participation and response-to-runs are ordinal over `overall_pick`. Clock length is known: `league_rules.md` rule 3.2 says 2 minutes, Sleeper `settings.pick_timer` = 60 for both 2025 and 2026 | **No.** LeagueLegacy is an importer with no time column. Do not spend budget here |
| G10 | `B/matchups_all.csv` `projected_points` and `opponent_projected_points` are 0 of 196 for 2025, populated 184 or 196 of 184 or 196 for every season 2013-2024 | missing | degrading | Phase 2 realized-vs-expected if expectation is taken from stored projections. Phase 3 projection-error luck controls lose 2025 | **No.** Platform boundary, LeagueLegacy holds nothing. Use an empirical slot-based baseline instead |
| G11 | 2024 weeks 1-5: `is_optimal` disagrees with `started` on 0 of 886 rows. Every other 2024 week disagrees on 26 to 56 rows; season-wide disagreement is 593 to 824 for every other season | unreliable | degrading | Any Phase 3 coaching-efficiency or lineup-luck control silently reports perfect lineup setting for 60 franchise-weeks | **Yes.** Scrape item 4, same request as G3 |
| G12 | Acquisition mechanism: `faab_bid` populated on 779 of 3,938 transactions (19.8%), absent entirely for 2014 and 2015; `waiver_priority` 0 of 3,938; `budget_amount` 0 of 7,404 in both `B/transaction_items_all.csv` and `A/05_transactions/transaction_items.csv` | partial | degrading | The waiver-versus-free-agent sub-split of ACQUIRED. Trade is separable (248 trades, `trade_partner` populated 248 of 248); waiver versus plain add is not | **Yes.** Scrape item 6 |
| G13 | 2013 has zero transactions in both corpora. `B/transaction_items_all.csv` spans 2014-2025 only. 12 of 156 franchise-seasons have no transaction log | missing | minor, documented caveat | Not the split itself. 516 of 1,656 2013 started rows resolve to ACQUIRED by the residual rule, and 2013 week 1 has 0 non-drafted starters with a monotone ramp to week 16, which is the signature of in-season acquisition. What is lost is mechanism, week, and trade partner | **No.** `A/00_league/seasons.csv` shows 2013 `transactions_imported_at` = 2024-09-10 23:19:56 and `status` = completed. The import ran and returned nothing. Upstream absence at Yahoo |
| G14 | Injury games lost exists only as IR slot usage, and only for 2020-2024: 512 player-weeks (2024 141, 2020 112, 2021 109, 2022 80, 2023 70), zero in 2013-2019 and 2025 | partial | degrading | Phase 3 injury-games-lost luck control for 8 of 13 seasons | **No.** `B/seasons_settings.csv` `roster_positions` shows an IR count of 2 only in 2020-2024. The league had no IR slot elsewhere, so there is nothing to scrape |
| G15 | 473 started rows are both drafted by and re-acquired by the same franchise in the same season, worth 4,375.5 raw starter points (1.56%). Week ordering resolves 418; 53 have a same-week gain and 3 have a trailing `loss` while still starting | partial | cosmetic | Nothing if you order by week. A naive set-membership rule misclassifies up to 1.56% of the central number | **No.** Grepping every CSV header in both corpora for `acquis\|acquire\|obtained\|added_via\|source\|origin\|how_` returns zero hits. No per-roster-row timestamp exists |
| G16 | `is_keeper` = 0 on all 2,339 picks in both draft files; `A/04_draft/keeper_results.csv` is 0 rows; `draft_index_all.json` `keeperResults` is an empty list. Meanwhile `A/00_league/seasons.csv` `use_keepers` = 1 for 2025 and 2026 | missing | degrading for Phase 5 | Every pick is modelled as a live selection. A 2026 simulator on a keeper league with no keeper data will mis-price the top of the board | **Yes.** Scrape item 7 |

---

## 4. Scrape list for leaguelegacy.io

Ordered by value per request. Items 1 through 4 are the ones that change results.

### 1. Gamecenter per-matchup box score, all Yahoo-era team-weeks (highest value)

- **Scope**: 2,256 team-weeks. Seasons 2013 through 2024, all weeks, all 12 franchises. 2025 needs nothing.
- **What to capture per player row**: the per-player score exactly as the site renders it, plus `player_id` or `service_player_id`, `lineup_position`, and `started`. If a stat line is exposed, capture the raw counts for `40 Yd Comp`, `40 Yd Pass TD`, `40 Yd Rush`, `40 Yd Rush TD`, `40 Yd Rec`, `40 Yd Rec TD`, `Ret TD`, `Pick Six`, and `Rec`. Raw stats are strictly better than a rendered score, because points can then be recomputed from `A/00_league/seasons.csv` `stat_modifiers` independently.
- **Pilot before committing**: scrape one matchup first. Season 2013, week 1, franchise Cambrias. The 9 started rows sum to 146.52 in both corpora; `A/02_gamecenter/matchups.csv` `points` for that team-week is 150.52. If the scraped player rows sum to 150.52, the endpoint carries the bonus and the full pull is justified. If they sum to 146.52, stop, and the gap is permanent and must be disclosed rather than closed.
- **Acceptance test**: sum over `started` rows equals `B/matchups_all.csv` `points` within 0.02 for at least 2,250 of 2,256 team-weeks, matching the 196 of 196 that 2025 already achieves.
- **Note for the scraper author**: `B/matchups_all.csv` `points` is bonus-inclusive and agrees with `result` in 2,452 of 2,452 team-rows, so LeagueLegacy does hold the bonus in its own database. It simply does not emit it in the bulk roster export.

### 2. Per-season draft pages for the three departed franchises

- **Scope**: 327 picks. GaTTa 62 (2013-2016), LFTLR 121 (2013-2020), Team JoeBa 137 (2013-2021).
- **Why not the JSON endpoint**: `B/draft_index_all.json` excludes these three franchises entirely in every season they existed. The exclusion is server-side and tied to franchise-member linkage, so pagination will not recover them. The per-season draft pages do render them, which the CSVs prove.
- **What to capture**: the nested `player` object for each pick, specifically `yahoo_id`, `espn_id`, `sleeper_id`, `fleaflicker_id`, `mfl_id`, `nfl_id`, `cbs_id`, `sportradar_id`, `fantasypros_id`, `gsis_id`, `normalized_name`. That crosswalk is the actual reason to do this pull. It is currently missing for the 37 players who were only ever drafted by departed franchises.
- **Season ids observed in the export**: 16824=2013, 16823=2014, 16822=2015, 16821=2016, 16820=2017, 16819=2018, 16818=2019, 16817=2020, 16816=2021, 16793=2022, 16792=2023, 29820=2024, 29821=2025.
- **Also capture while there**: the 2018 forfeit. `B/draft_picks_all.csv` is missing exactly one overall pick in 2018, number 38, and LFTLR is the only 2018 franchise with 14 picks rather than 15. Capture the site's rendering of that cell so the forfeit becomes a row rather than an absence.

### 3. Mike Williams, gsis `00-0033536`, all weekly scores

- **Scope**: 78 roster rows across 2018 through 2023, of which 42 are started. All 78 carry `points` = 0 and blank `points_ppr` in both corpora, and `B/players_alltime.csv` reports `total_pts` 0 against `started_weeks` 35.
- **Why it matters**: this one player accounts for 42 of the 49 started player-weeks in the corpus that are zero on every row they appear in. Across 22,063 started rows only 20 `player_id` values are all-zero, and only 6 of those have any started weeks.
- **Get it from the same box scores as item 1** if that pull happens; otherwise request the player game log directly.

### 4. 2024 weeks 1 through 5, gamecenter box score

- **Scope**: 60 team-week cells. Season 2024, weeks 1 to 5.
- **Two things to recover**: (a) per-player `points` for the 2 started rows with blank `points_ppr` that the local coalesce cannot fix (lineup slots RB and TE, 1 each); (b) the true `is_optimal` flag, which is a verbatim copy of `started` on all 886 rows in that window and is therefore fabricated.
- **Do not extend this to any other season.** Sweeping all 13 seasons, 2024 weeks 1 to 5 are the only season-weeks where team points are greater than 0 and player-level started points sum to 0. All other 2,392 team-weeks are clean on this test.
- **Cheap local fix first**: coalescing `points` to `points_ppr` where `points` is 0 restores 534 of 540 starter rows and drops 2024's mean residual from 41.32 to 5.85, in line with every other Yahoo season. Do that regardless of whether this scrape runs.

### 5. Per-pick ADP as the draft view renders it

- **Scope**: all 2,339 picks, 13 requests, one per season. Prioritise 2025 then 2022; within season prioritise rounds 1-5, then TE, then K and DEF.
- **What to ask for**: the absolute consensus pick and consensus ADP behind each pick, plus whatever provider name and as-of date the site states. The vintage matters: reach-vs-ADP is meaningless if a 2013 pick is being scored against a present-day board.
- **Set expectations low.** `adp_effective_pick` and `adp_effective_adp` are present in the site's own JSON payload schema with value `null` on all 2,012 objects. The upstream API returns null, so a re-pull of the same endpoint returns the same nulls. Only the rendered draft page is worth trying, and any ADP it displays may be computed client-side from the differential, which is already available offline.
- **If the scrape returns nothing, say so in the log**, because then the reconstruction below is the ceiling and the 300 gaps are permanent.
- **Reconstruction already available, no scrape required**: `ADP = overall_pick - adp_differential`, valid on 2,039 of 2,339 picks. Under that sign 0 of 2,039 values are non-positive; under the opposite sign 30 are, which is impossible. One legitimate out-of-range case: 2021 overall pick 174 Carlos Hyde, differential -7.2, reconstructs to 181.2 in a 180-pick draft. Do not clamp it silently. `adp_differential_pct` is `adp_differential` divided by that season's recorded pick count times 100 and carries zero additional information; drop it. `adp_consensus_score` is literally 0 on roughly half of its populated rows in every season with no trend; do not weight anything with it.

### 6. Waiver mechanism and FAAB

- **Scope**: 3,159 non-trade transactions that carry no bid, seasons 2014-2025. FAAB by season currently: 2016 72, 2017 108, 2018 86, 2019 65, 2020 73, 2021 69, 2022 78, 2023 57, 2024 66, 2025 105; zero for 2014 and 2015.
- **What to capture**: the transaction detail view's waiver-versus-free-agent tag, the bid amount, and the waiver priority. `waiver_priority` is 0 of 3,938 and `budget_amount` is 0 of 7,404 in both corpora, so both fields exist in the schema and are being dropped or were never imported.
- **Expect 2014 and 2015 to come back empty.** `A/00_league/seasons.csv` gives `waivers_type` = `rolling` for those seasons, and FAAB does not appear in the data until 2016.

### 7. Keeper flags and per-season draft settings

- **Scope**: 14 seasons.
- **What to capture**: the keeper designation per pick, and the per-season draft settings page including any pick-timer value. `is_keeper` is 0 on all 2,339 picks, `A/04_draft/keeper_results.csv` is 0 rows, and `draftResults[].keeperResults` is an empty list, yet `use_keepers` = 1 for 2025 and 2026. Either the league genuinely ran no keepers through 2024 and turned them on for the Sleeper era, or the flag is being dropped. Confirm which.
- **The pick timer is a cheap bonus.** Sleeper gives 60 seconds for 2025 and 2026; `league_rules.md` rule 3.2 says 2 minutes and is stale in the same way rule 3.3 was found stale. A per-season settings page would give the clock for the 12 seasons Sleeper does not cover.

### Explicitly not on this list

| Not scraping | Why |
|---|---|
| Per-pick timestamps for any season | LeagueLegacy is an importer of finished Yahoo and Sleeper drafts. Its pick object has no time column in any of its 28 JSON keys or 24 CSV columns. Yahoo's public draft results view, which is exactly what the 12 image PDFs show, does not display one either |
| 2013 transactions | `A/00_league/seasons.csv` 2013 `transactions_imported_at` = 2024-09-10 23:19:56, `status` = completed. The import ran and returned zero rows. The absence is upstream at Yahoo, not in the export |
| 2026 draft order or 2026 standings | `B/seasons_meta_full.json` 2026 carries `service_type` sleeper. LeagueLegacy is a downstream mirror and cannot post the order before Sleeper does. Poll `GET https://api.sleeper.app/v1/draft/1389378429505241089` for `draft_order` going non-null or `slot_to_roster_id` going non-identity, then `/picks` |
| 2025 projections | Platform boundary. Every projection field is empty or 0 for both Sleeper seasons across matchups, standings, season_teams and league_meta |
| IR or injury data for 2013-2019, 2025, 2026 | `B/seasons_settings.csv` `roster_positions` shows no IR slot in those seasons. The league had none. There is nothing to fetch |
| `B/draft_index_all.json` with pagination | The 327-pick shortfall is franchise-scoped, not paginated. See scrape item 2 |
| 2026 player pool and ADP | Already available live and free from Sleeper: 3,301 rows across six positions, 3,301 with `adp_ppr`, verified HTTP 200 on 2026-08-11. Re-pull near draft day since ADP moves |

---

## 5. Fields to quarantine

| Field and file | Evidence | Verdict |
|---|---|---|
| `scoring_format` in `A/00_league/seasons.csv` and `B/seasons_settings.csv` | Reads `half-ppr` on all 14 rows. `stat_modifiers` `stat_id` 11 (`Rec`) = 1 in every one of those same 14 rows, and Sleeper 2025/2026 `rec` = 1.0 | **Unreliable metadata. Never read.** The league is full PPR in every season |
| `points` in `B/rosters_weekly_all.csv` and `A/02_gamecenter/matchup_rosters.csv`, seasons 2013-2024 | Exact-match to `matchups_all.csv` `points` in 5 to 18 of 184-196 team-weeks per season versus 196 of 196 in 2025 | **Usable but bonus-exclusive.** Label the basis on every figure derived from it. Never claim a tie-out to the official score |
| `points` for 2024 weeks 1-5, both corpora | Literal 0 on all 886 rows including 540 started; all 60 team-weeks sum to 0.00 | **Quarantine, then repair.** Coalesce to `points_ppr`; 534 of 540 starter rows recover, 2 do not |
| `optimal_points` in `B/matchups_all.csv` | Reconciles to the sum of roster `points` over `is_optimal == 'true'` at 0.00 delta in all 2,256 team-weeks for 2013-2024, i.e. built from the same bonus-exclusive column | **Contaminated the same way.** Cannot serve as a true-basis ceiling |
| `is_optimal` for 2024 weeks 1-5 | Disagrees with `started` on 0 of 886 rows; every other 2024 week disagrees on 26 to 56 | **Fabricated. Exclude those 60 franchise-weeks** from any coaching-efficiency measure |
| `points` versus `points_ppr` convention in `B/matchups_all.csv` | 2013-2024 the roster sum matches `points_ppr` in 85 to 155 team-weeks per season and `points` in 5 to 18. In 2025 the convention inverts: the roster sum matches `points` 196 of 196 and `points_ppr` 2 of 196 | **Any code reading `points_ppr` as the team score is wrong for 2025.** Read `points` as the official score in all seasons |
| `adp_effective_pick`, `adp_effective_adp`, `adp`, `adp_pick` | 0 of 2,339 in all four columns across both corpora, null on all 2,012 JSON objects | **Empty. Delete the columns or stop copying them through.** `out/picks.csv` carries `adp_effective_pick` populated 0 of 2,339 |
| `adp_differential_pct` | Equals `adp_differential` divided by that season's recorded pick count times 100, matching on 2,039 of 2,039 rows under half-away-from-zero rounding | **Redundant.** Drop it. Note the denominator is recorded picks, so 2018 divides by 179 not 180 |
| `adp_consensus_score` | Populated on the same 2,039 rows, roughly half of them literally 0, with no trend by season | **Do not weight anything with it** |
| `B/draft_index_all.json` `draftResults` | 2,012 records, missing 320 picks belonging to three departed franchises and 7 picks with player id `00-0021142` | **Never the pick spine.** Use it only for the cross-platform crosswalk, and know that the crosswalk it provides has a franchise-shaped hole |
| `player_id` `00-0021142` | 7 draft picks and 9 transaction items, blank name and position. Zero occurrences in any roster file or `players_alltime.csv` | **Bad gsis.** Map through `service_player_id` 30120 to gsis `00-0033536`, Mike Williams WR |
| `player_id` `00-0036501`, position DB | 2 picks named Michael Carter, 2021 overall 108 and 2022 overall 119. `A/00_league/roster_positions.csv` lists only qb, rb, wr, te, k, def, so no DB is startable | **Wrong person.** `service_player_id` 33495 maps to gsis `00-0036924`, Michael Carter RB |
| `player_id` as a cross-season person key | Spencer Shrader is `00-0039576` in 2024 (2 roster rows) and `espn-4571557` in 2025 (3 rows). Separately, 219 of the 1,003 distinct gsis ids in `A/02_gamecenter/matchup_rosters.csv` map to more than one `service_player_id` | **`service_player_id` is right within a season, gsis is right across seasons.** Collapse the Shrader pair by hand |
| `B/final_standings_by_season.csv` and `B/standings_by_season.csv`, 2026 rows | 12 rows, `rank` 1-12, `record` "0-0", wins/losses/ties/points_for/points_against/avg_points/moves all literal 0, `inseason_rank` = `rank` = `team_key` = Sleeper `roster_id` on 12 of 12. The 2026 rows also label teams by Sleeper `team_name` while 2013-2025 use LeagueLegacy member names | **Not a finish and not a slot.** Do not seed Phase 5 from it. It is not information-free about seating (`roster_id` equalled the 2025 draft slot for 6 of 12, which is P = 5.9e-4 under a uniform permutation) but n = 1 season, so label any prior built from it as such |
| `A/13_season_teams/season_teams_full.csv` columns `stats`, `stat_rosters` | 0 of 168 rows populated. `positions` is populated 156 of 168 but is itself bonus-exclusive (2013 Ronnie: positions total 1,582.5 versus `total_points` 1,713.5, gap exactly 131.0) | **No recovery path here.** Ruled out as a source for the bonus |
| `B/players_alltime.csv` `total_pts` | Lower than the roster sum for 921 of 1,008 players, mean -128.85, and covers fewer weeks (Kelce 175 versus 187) | **Not a scoring source** |
| `out/gap_register.md` G-005 | States "`adp_effective_pick` and `adp_differential` validated against 2025 Sleeper and are usable". `adp_effective_pick` is 0 of 2,339. `out/PHASE0_PLAN.md` line 67 makes the same error | **Correct the register before it is cited as clearance** |

---

## 6. Checked and found fine, do not re-audit

| Checked | Result |
|---|---|
| Pick-to-production join key | `player_id` vocabulary is shared: draft prefixes gsis 2,142, DEF 174, espn 22, yahoo 1; roster prefixes 33,537 / 3,255 / 292 / 22. Zero blanks on either side. Same-season join 2,308 of 2,339 on `player_id`, 2,317 of 2,339 on `service_player_id`. The residual 22 are genuine draft-and-cut, only two earlier than round 8 (2021 overall 40 Gus Edwards, 2016 overall 89 Devin Funchess). Model them as realized starter points of zero |
| Team-name vocabulary | Identical across `draft_picks_all.team`, `rosters_weekly_all.team` and `transactions_all.team`. Zero unmatched values in all three directions, all 13 seasons, 12 teams each |
| Acquired-side join | `B/transaction_items_all.csv` carries `player_id` on 7,404 of 7,404 and joins 7,230 of 7,404 (97.6%) to same-season roster rows. `B/transactions_all.csv` has no `player_id` column at all; route through the items file |
| Residual attribution rule | A started row whose (season, team, player_id) is not in that team's draft set is ACQUIRED. Validated against 2014-2025 where the log exists: 7,240 of 7,300 non-drafted starter-weeks independently confirmed as `direction == 'gain'`, 99.18% agreement. Residual is a strict superset of the transaction-confirmed acquired set, so it never produces a false DRAFTED |
| 2013 drafted-versus-acquired | Computable without transactions. 1,656 started rows, 1,140 DRAFTED, 516 ACQUIRED. Week 1 has 0 non-drafted starters and the count ramps monotonically to week 16, the exact signature of in-season acquisition. The 2013 draft set is complete: 192 picks, 12 teams, 16 rounds, 0 blank `player_id` |
| Injury data | Not absent. `lineup_slot` / `lineup_position` carries IR on 512 player-weeks, identical in both corpora, all with `started` = false and `points` = 0. 130 distinct players, 50 of the 60 franchise-seasons in 2020-2024 have at least one. `A/00_league/seasons.csv` `roster_positions` shows the IR slot existed only 2020-2024, so the other seasons are structurally, not accidentally, empty |
| Cross-platform crosswalk location | Not JSON-only. `A/05_transactions/transaction_items.csv` column `player` holds the full nested player object for 7,395 of 7,404 rows, 943 distinct players. Union with the JSON covers 691 of the 700 drafted players. The 9 with no crosswalk anywhere: `00-0000108` David Akers, `00-0021142`, `00-0022787` Matt Schaub, `00-0025824` Garrett Hartley, `00-0026163` Rashard Mendenhall, `00-0027094` Andre Brown, `00-0029209` Ryan Broyles, `00-0029260` LaMichael James, `00-0029547` Vick Ballard |
| Official score integrity | `B/matchups_all.csv` `points` agrees with column `result` in 2,452 of 2,452 team-rows. The roster sum disagrees with `result` in 102, so 51 games would flip on the roster basis. Never use the roster sum to decide a game |
| Duplicate archive copies | `made-resources/.../02_gamecenter/matchup_rosters.csv` and `LeagueLegacy-io/YeahThatFantasyLeague_LeagueLegacy_Archive_2013-2026/02_gamecenter/matchup_rosters.csv` are byte-identical, md5 `8af0df7f29ed0d413b72a47e9187396b`. `diff -rq` across the two archive trees shows only `.DS_Store` differing. `B/rosters_weekly_all.csv` is md5 `c8ce70f84275758c9638a50a02a36096` and is a different file with a different schema, not a byte-identical twin |
| Starter counts | 9 started rows in 2,447 of 2,452 team-weeks. Five exceptions have 8: 2015 wk6 LFTLR, 2015 wk12 Richie, 2018 wk13 Cambrias, 2023 wk16 Richie, 2025 wk6 Pung & Tralie. Missing slots are 1 K, 1 RB, 3 WR |
| `started` column encoding | Lowercase `true` / `false`, 22,063 true and 15,043 false file-wide. A case-sensitive filter on `True` returns zero rows |
| 2018 forfeit | `B/draft_picks_all.csv` 2018 holds 179 picks; overall pick 38 is the only one missing. LFTLR is the only 2018 franchise with 14 picks rather than 15, so the forfeit is LFTLR's. Genuine event under rule 3.2, not missing data |
| Yahoo draft PDFs | All 12 files in `/Users/anthony/Claude/Projects/ff-hub/made-resources/Yahoo Draft Results - 2014 to 2024/` return 1 to 2 characters under `pdftotext`. Image-only, confirmed on all 12. Note the folder name understates coverage: the files span 2013 through 2024, not 2014 through 2024 |
| Other repo spreadsheets | Eight `.xlsx` files under `made-resources/`. `Yahoo Draft Data.xlsx` (sheet `All`, columns Year, Team, Owner, Standings, Round, Pick, Player, First, Last, Full Name, Position), `2022 - 2024_historical_draft_data.xlsx` (year, manager_name, round, overall_pick, player_name, player_position), `draft_order_2025 (1).xlsx` (round, overall_pick, pick_in_round, team_id, manager_name, draft_slot, snake_round, has_keeper, keeper_player, keeper_cost_round). **None carries a timestamp, and none carries ADP.** They add nothing the CSVs lack |
| The one real ADP board in the repo | `made-resources/Yahoo League Historical Data_24.xlsx` and `..._2025 Prep.xlsx` both carry a sheet `Sleeper ADP` (291 rows: ADP, Round & Pick, Player, Team Abbr., Position) and a sheet `2024 Players` with `current adp`. Dated to 2024 preseason by its top rows. It prices 165 of the 168 2024 picks including all 12 that lack a differential, and it cannot touch any other season. Different basis from LeagueLegacy's consensus, so keep it in its own flagged column, 2024 only |
| Sleeper 2025 autopick | `raw/sleeper_2025_drafts.json` and `raw/sleeper_2026_drafts.json` both carry `settings.cpu_autopick` = 0 and `autopause_enabled` = 0, and all 168 picks in `raw/sleeper_2025_picks.json` have a non-null `picked_by`. No 2025 pick was an auto-pick |
| Sleeper 2025 draft pace | `start_time` 1756943669161 and `last_picked` 1756948710360: 5,041.2 seconds for 168 picks, 30.2 seconds mean interval against a 60-second timer. One season of pace data, enough to sanity-check a simulator clock assumption |
| Sleeper slot storage | `slot_to_roster_id` on the single-draft endpoint is where the seat assignment lives, not `draft_order` alone. For 2025 it is populated and non-identity and reproduces `draft_slot` on all 168 picks. The cached list-endpoint files in `raw/` omit the key entirely for both seasons, which is why an earlier read concluded it was null |
| 2026 market inputs | Sleeper projections, all six positions, HTTP 200 on 2026-08-11, 3,301 rows with 3,301 `adp_ppr`. `draft_board.py` line 61 still carries a defensive try/except on the premise that K and DEF may 404. For 2026 they do not. Note this is global market ADP, not this league's behaviour, so calibrate against `draft_picks_all.csv` before using it for survival curves |