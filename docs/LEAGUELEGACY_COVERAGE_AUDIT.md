# LeagueLegacy coverage audit

Commissioned belief: *"the pipeline reads only 04_draft/draft_results.csv
and only from 2016 forward."* **Both halves are incorrect.** What follows
is read from the ingestion code, not inferred.

## Correction 1 - the pipeline reads seven archive files, not one

| Archive file | Read by | Size |
|---|---|---|
| `02_gamecenter/matchup_rosters.csv` | phase2_value, phase3_lineup, phase3e_startsit, build_app_data, verify_yahoo | 2.9M |
| `04_draft/draft_results.csv` | ingest, phase2_value | 268K |
| `01_history/season_results.csv` | phase2_value, phase3_remainder | 36K |
| `05_transactions/transactions.csv` | phase3_remainder | 468K |
| `03_playoffs/championship_games.csv` | ingest | 4K |
| `06_players/players_all_time.csv` | phase3e_startsit | 80K |
| `matchups_all.csv` (export) | verify_yahoo | 384K |

`matchup_rosters.csv` - named in the brief as unread - is the single most
read file in the archive.

## Correction 2 - the drafted-vs-acquired analysis was already built and run

`src/phase2_value.py` has computed it since 2026-08-11, writing
`out/drafted_vs_acquired.csv` for **all thirteen completed seasons,
2013-2025**. Its docstring states the goal in the brief's own words:
"splits each franchise-season's starter points into DRAFTED versus
ACQUIRED. That split decides whether this league is won on draft day or
after it." It was never blocked on unread files.

What was genuinely missing - and is now added in
`src/draft_vs_acquired.py` - is the champions-versus-field comparison
with intervals, and the era flags.

## Correction 3 - the archive is committed TWICE

Two full copies, both tracked in git:
- `made-resources/YeahThatFantasyLeague_LeagueLegacy_Archive_2013-2026/`
  read by ingest.py, phase2_value.py, build_app_data.py
- `LeagueLegacy-io/YeahThatFantasyLeague_LeagueLegacy_Archive_2013-2026/`
  read by phase3_lineup.py, phase3e_startsit.py, phase3_remainder.py,
  verify_yahoo.py

`verify_yahoo.py` reads from BOTH. This is a real hazard: a correction
applied to one copy is invisible to half the pipeline. Recommend
consolidating on `LeagueLegacy-io/` and leaving a pointer, but that
touches seven scripts and is not draft-night critical, so it is logged
rather than done.

## Where "2016 forward" WAS true, and is now fixed

The C2 league base-rate table capped its own window at 2016 - not because
of the archive, but because its league loop was nested inside the market
loop, and the market side starts at 2016 where the FFC ADP cache starts.
`src/build_base_rates.py` now runs two independent loops:
league 2013-2025, market 2016-2025, each window stated separately.
**League joins rose from 1,448 to 1,867, a 29% increase in sample.**

## Still unread, and what each would buy

| File | Size | What it holds | Worth reading? |
|---|---|---|---|
| `05_transactions/transaction_items.csv` | 4.1M | item-level adds/drops with FAAB bids | YES - the FAAB-discipline question needs bid amounts, and only the summary file is read today |
| `leaguelegacy_.../rosters_weekly_all.csv` | 2.6M | weekly rosters incl. bench | overlaps matchup_rosters; useful only for bench-vs-started questions |
| `03_playoffs/playoff_matchups.csv` | 88K | playoff bracket detail | modest - championship_games already read |
| `01_history/all_time_standings.csv` | 4K | all-time standings | derivable from what is read |
| `08_finances/*`, `10_newsletters/*`, `11_achievements/*` | small | league color | no analytical value |
| `12_record_book/record_index.csv` | 100K | record book | no analytical value |

## Ground truth verified against the files

Every item in the correction brief checks out exactly:

- **2013 exists.** `seasons.csv` covers 2013-2026; thirteen completed
  seasons 2013-2025.
- **Champions**, from `champions_by_season.csv`: 2013 Ronnie, 2014 GaTTa,
  2015 & 2016 Chris & Dom, 2017 Richie, 2018 Phil Baldino, 2019 Cambrias,
  2020 Ronnie, 2021 Rob & GregBo, 2022 Cambrias, 2023 & 2024 Phil
  Baldino, 2025 Cambrias. **Baldino is tied with Cambria at 3 titles and
  is the more recent dynasty** (back-to-back 2023-24 at 12-2 and 11-3).
  The research director report's "Cambria is the benchmark" framing is
  incomplete and is corrected on the findings page.
- **Median scoring is new.** `use_median_scoring` = 0 for 2013-2024,
  1 for 2025-2026. **Every historical season was pure H2H, so the C4
  ceiling weighting cannot be validated against league history** - the
  format did not exist. Recorded next to the C4 entry.
- **Season length changed.** 13 weeks with playoffs from week 14 through
  2020; 14 weeks with playoffs from week 15 from 2021. Both base rates
  and the champions analysis now flag the boundary.
- **Keepers: OPEN QUESTION, not resolved.** `use_keepers` = 1 for
  2025-2026 and 0 before, but the 2025 Sleeper draft had zero keeper
  picks and `keeper_results.csv` is 2 bytes. Flagged for the
  commissioner, deliberately not resolved here.

## Provenance rule applied

LeagueLegacy is a derivative import of Yahoo. Where it could disagree
with another repo source on a draft pick, `src/ingest.py` already
cross-validates the 2025 archive draft against Sleeper pick-for-pick and
reports conflicts rather than preferring either silently.
