# Phase 0 - Plan and File Inventory

**2026-08-11. Gate: awaiting approval. No pipeline code written.**

---

## Lead: the data situation is far better than the brief assumed

The LeagueLegacy archive is **already extracted** inside `made-resources`. It is complete, covers **2013-2025**, and carries starter-level weekly scoring plus full transaction history. Three consequences:

| Brief assumed | Actual | Effect |
|---|---|---|
| Survivorship defect blocks run detection on 2016-2021 | `04_draft/draft_results.csv` has **12 managers in every season, 2013-2025**, including departed ones (GaTTa, Nolan & Vinny, LFTLR, Team JoeBa) | **The blocker is gone.** No Yahoo recovery needed |
| Phase 2 needs nflverse for season stats | `02_gamecenter/matchup_rosters.csv` has 37,106 rows with `started`, `is_optimal`, `points`, `points_ppr`, per player per week per season | **No external stats source required.** In-league scoring, already computed |
| 2024, 2015, 2014 champions unknown | `03_playoffs/championship_games.csv` covers all 13 seasons | **All resolved** |

`player_id` is nflverse GSIS format (`00-0029668`), so an external join stays available if ever needed. It is not needed for the stated mission.

---

## Correction to the championship ledger - please confirm before Phase 1

Resolving 2024 changes the title counts the brief states as ground truth. I am flagging rather than silently proceeding.

| Season | Archive winner | Runner-up | Brief said |
|---|---|---|---|
| 2013 | **Ronnie** (Ron Malandro) | LFTLR | not listed |
| 2014 | **GaTTa** (Vincent Gatta) | Cambrias | unknown |
| 2015 | **Chris & Dom** (Chris Juliano) | Cambrias | unknown |
| 2016 | Chris & Dom | Team JoeBa | Chris Juliano - matches |
| 2017 | Richie (Rich Nolfi) | Chris & Dom | matches |
| 2018 | Phil Baldino | Frank & Julian | matches |
| 2019 | Cambrias (Dante Cambria) | Richie | matches |
| 2020 | Ronnie | Pung & Tralie | matches |
| 2021 | Rob & GregBo (Rob Flacco) | Ronnie | matches |
| 2022 | Cambrias | Richie | matches |
| 2023 | Phil Baldino | Ronnie | matches |
| **2024** | **Phil Baldino** | Cambrias | **UNKNOWN - now resolved** |
| 2025 | Cambrias | **Antdell & Ernie** | matches |

**Revised title counts:**

| Manager | Titles | Seasons |
|---|---|---|
| Dante Cambria | 3 | 2019, 2022, 2025 |
| **Phil Baldino** | **3** | 2018, 2023, **2024** |
| Chris Juliano | 2 | 2015, 2016 |
| Ron Malandro | 2 | 2013, 2020 |
| Rich Nolfi | 1 | 2017 |
| Rob Flacco | 1 | 2021 |
| Vincent Gatta | 1 | 2014 (departed, merged into Nolan Lawrence 2017) |
| Anthony DellaPia | **0** | **2025 runner-up, lost 164.92 to 152.48** |

Two changes to the brief's framing:
1. **Phil Baldino is tied at 3, not behind at 2.** Phase 3f targets Cambria as "the strongest single signal." With Baldino also at 3 and titles in back-to-back years 2023-2024, the dedicated-analysis target should be **both**, and the more interesting question is what separates them from each other.
2. **Anthony lost the 2025 final by 12.44 points.** "0 titles" understates the position. The gap to close is one game, not a rebuild.

---

## File inventory

### Primary source: LeagueLegacy archive, 2013-2026
`made-resources/YeahThatFantasyLeague_LeagueLegacy_Archive_2013-2026/` - 71 files, 19 MB, 16 sections.

| File | Rows | Phase | Why it matters |
|---|---|---|---|
| `04_draft/draft_results.csv` | 2,339 | 1, 3, 4 | Every pick 2013-2025. Carries `adp_effective_pick`, `adp_differential`, `is_keeper`, `from_trade`, `value`. **Reach-vs-ADP is pre-computed** |
| `02_gamecenter/matchup_rosters.csv` | 37,106 | **2** | `started`, `is_optimal`, `points`, `points_ppr` by player-week-season. The drafted-vs-acquired split lives here |
| `05_transactions/transactions.csv` | 3,938 | **2** | `type`, `faab_bid`, `player_added`, `transaction_week`. The acquired side |
| `05_transactions/transaction_items.csv` | 7,404 | 2 | Item-level detail |
| `03_playoffs/championship_games.csv` | 13 | 1, 3 | Champion ledger, resolved |
| `01_history/season_results.csv` | 168 | 3e | 14 seasons x 12. Finish, PF, PA - luck controls |
| `02_gamecenter/matchups.csv` | 2,452 | 3e | Close-game record |
| `13_season_teams/season_teams_full.csv` | 168 | 3 | Franchise-season spine |
| `13_season_teams/season_team_position_stats.csv` | 1,092 | 3 | Positional production by franchise-season |
| `00_league/members.csv` | 24 | 1 | Identity spine. 24 member records vs 12 rosters - co-ownership |
| `00_league/seasons.csv` | 14 | 1 | Roster size and scoring changes over the decade - Phase 3g weighting |
| `15_rules_notes/season_annotations.csv` | 695 | 1 | Rule changes by season |
| `03_playoffs/playoff_matchups.csv` | 364 | 3 | Playoff paths |
| `07_versus/head_to_head_pairs.csv` | 198 | 4 | Manager-vs-manager |
| `04_draft/keeper_results.csv` | **0** | - | Empty. No keeper league |
| `08_finances/member_finance_entries.csv` | 0 | - | Empty |
| `11_achievements/achievements_recent.csv` | 0 | - | Empty |

### Secondary sources in made-resources
| File | Status |
|---|---|
| `2022 - 2024_historical_draft_data.xlsx` | Superseded by the archive. Use only as a cross-check |
| `Yahoo League Historical Data_24.xlsx`, `Yahoo League Past Drafts.xlsx`, `Yahoo Draft Data.xlsx` | Cross-validation candidates. Not yet opened |
| `team_tendencies_from_history.xlsx` | Contains a `risk_tolerance` column with no traceable derivation. **Quarantine, do not use** |
| `league_positional_frequencies_by_round.xlsx` | Derived, not source. Recompute rather than trust |
| `draft_order_2025 (1).xlsx` | 2025 order. Useful for slot-effect validation |

### Live API
Sleeper 2025 `1245905122328846336` and 2026 `1389378429505241088`, public read-only.

### Not available
| Item | Status |
|---|---|
| Reference repo `anthonydellapia1117/yeahthatfantasyleague` | **Exists but is empty**, 0 KB, pushed today. Nothing to read |
| LeagueLegacy zip on Desktop | Not present. The extracted archive in `made-resources` supersedes it |
| Colab Yahoo downloader | Only `.ipynb` found is `Desktop/2 \| Ayvede/sports-ml-engine/notebooks/data_ingestion.ipynb`, an unrelated Ayvede project. **Please point me at the right notebook if it matters** |

---

## Repo root decision

The brief says "this directory." My working directory is `/Users/anthony/CardinalHealth`, which is a **protected client directory** under standing rules and must not receive `out/` or `raw/`.

**Setting repo root to `/Users/anthony/Claude/Projects/ff-hub/`.** All paths below are relative to it. Say the word if you want it elsewhere.

---

## Plan by phase

### Phase 1 - Ingest and reconcile
Build `raw/` as immutable snapshots: copy the archive verbatim, pull Sleeper 2025 and 2026 JSON. Normalize to `out/` tables: `picks`, `franchise_seasons`, `weekly_rosters`, `transactions`, `champions`, `members`.

Identity resolution is the main work. Archive uses franchise names (`Cambrias`, `Rob & GregBo`, `Chris & Dom`); Sleeper uses handles (`dcambs`, `RobFlacc`, `chrisanddom`). Join on `team_id` and `member_id` where present, and require an evidence field per mapping. Never fuzzy-match names - the `RobFlacc` / `domflacco` near-miss already proved that trap is live.

Assertions: picks == teams x rounds per season; contiguous pick numbers; one roster per round; no duplicate player within a draft; archive 2025 draft reconciles to Sleeper 2025 draft pick-for-pick. **That last one is a genuine cross-source validation and I expect it to pass at 168 of 168.**

Deliverables: `out/coverage_matrix.md`, `out/gap_register.md`.

### Phase 2 - Value layer
For each franchise-season, sum starter points from `matchup_rosters` where `started = true`. Tag each player-week as **drafted** (appears in that franchise's `draft_results` that season) or **acquired** (appears in `transactions` as an add, or in neither, which becomes its own bucket). Report the split before any draft-day conclusion, per the brief.

Compute per pick: realized starter points, VOR against positional replacement derived from the actual league that season, realized-vs-expected for the draft slot, hit and bust rates.

**Caveat I will test first:** `matchup_rosters` gives points as scored in-league, but roster size and scoring changed across the decade (`seasons.csv`, 57 columns). VOR must be computed within-season, never pooled across eras.

### Phase 3 - Champion question
Archetypes from rounds 1-5 positional sequence, clustered across **all 156 franchise-seasons** (13 x 12), not just the 13 champions. Per archetype: n, champion rate, playoff rate, mean finish, mean PF, Wilson interval. Permutation test against random assignment. Any archetype with n < 5 is labeled insufficient and excluded from recommendations.

Luck controls from `season_results` and `matchups`: points against, close-game record, and the Phase 2 drafted-vs-acquired split.

Dedicated analysis on **Cambria and Baldino, 3 titles each**, testing whether either is distinguishable from the field on draft-day dimensions or whether the edge is post-draft.

Recency weighting: exponential decay on season, half-life proposed at **4 seasons**, stated explicitly and sensitivity-tested at 3 and 6. Empirical-Bayes shrinkage toward league baselines for small per-manager n.

**Honest expectation, stated now:** with 13 champions and 156 franchise-seasons, most archetype comparisons will not reach significance. I expect the defensible output is a small number of conditional rules with wide bands, plus a substantial folklore section. I will not manufacture a clean recipe.

### Phase 4 - Manager tendency models
Per manager, recency-weighted and shrunk: position by round, opening construction, QB and TE timing, K and DEF timing, reach vs ADP using the archive's own `adp_differential`, run participation, response to runs, behavior by slot region. Per-manager n reported on every line; anything under 5 observations labeled low confidence.

### Phase 5 - 2026 execution engine
Monte Carlo simulator parameterized on Anthony's slot, run for all 12. Per slot: survival probability per target, positional run probability by round, expected value at next pick by position, opportunity cost of passing, recommended sequence, championship probability. Output per-slot per-round decision cards.

**This supersedes nothing in the existing doctrine except its slot-7 assumption**, which was explicitly provisional.

---

## Risks I want acknowledged before Phase 1

| Risk | Handling |
|---|---|
| Archive is a vendor export, not primary. Its `value` and `adp_consensus_score` columns have no published derivation | Use `adp_effective_pick` and `adp_differential` only after validating them against the 2025 Sleeper draft. Quarantine `value` unless it validates |
| Co-ownership changes franchise identity over 13 years | Model the **franchise**, carry `co_owned` and the member set per season. Never merge franchises across a name change without a `team_id` link |
| 2013-2015 had 15-16 rounds vs 14 now | Round-indexed comparisons must normalize by draft length or restrict to rounds 1-5 |
| Small-n everywhere | Shrinkage and explicit intervals on every claim. Folklore section is mandatory, not optional |

---

## Ask

1. **Approve the corrected championship ledger**, in particular Phil Baldino at 3 titles including 2024.
2. **Confirm repo root** `/Users/anthony/Claude/Projects/ff-hub/`.
3. **Point me at the Colab notebook** if it holds anything the archive does not, or confirm it is unnecessary.
4. Approve proceeding to Phase 1.

Nothing has been written except this file. No code, no `raw/`, no `out/` tables.
