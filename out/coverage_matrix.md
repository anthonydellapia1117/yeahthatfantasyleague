# Coverage Matrix - Phase 1

Generated 2026-08-11. Source A = LeagueLegacy archive. Source B = Sleeper public API.

| Season | Draft picks | Weekly rosters | Transactions | Champion | Sleeper | Status |
|---|---|---|---|---|---|---|
| 2013 | 192 (12x16) | 2909 | - | yes | n/a | **verified** |
| 2014 | 192 (12x16) | 2941 | 248 | yes | n/a | **verified** |
| 2015 | 180 (12x15) | 2752 | 251 | yes | n/a | **verified** |
| 2016 | 180 (12x15) | 2755 | 280 | yes | n/a | **verified** |
| 2017 | 180 (12x15) | 2758 | 350 | yes | n/a | **verified** |
| 2018 | 179 (12x15) | 2753 | 318 | yes | n/a | **PARTIAL** (179/180) |
| 2019 | 180 (12x15) | 2757 | 319 | yes | n/a | **verified** |
| 2020 | 180 (12x15) | 2838 | 336 | yes | n/a | **verified** |
| 2021 | 180 (12x15) | 3032 | 368 | yes | n/a | **verified** |
| 2022 | 180 (12x15) | 3011 | 380 | yes | n/a | **verified** |
| 2023 | 180 (12x15) | 2990 | 379 | yes | n/a | **verified** |
| 2024 | 168 (12x14) | 2874 | 405 | yes | n/a | **verified** |
| 2025 | 168 (12x14) | 2736 | 304 | yes | verified 168/168 | **verified** |

## Totals

- Draft picks: **2339** across 13 seasons, 2013-2025
- Weekly roster rows: **37,106**  |  Transactions: **3,938**
- Identity map: **12/12 verified**, each at 14/14 picks, joined on overall pick number
- 2025 cross-source reconciliation: **168/168 agree** (name-normalized)

## Excluded by decision

| Item | Reason |
|---|---|
| Sleeper league `1092592577628426240` (labelled 2024) | Empty trial shell: 0 picks, 0 transactions, all records 0-0-0 |
| `made-resources/py/*.ipynb` | Hardcoded Yahoo OAuth tokens in source cells |
| `team_tendencies_from_history.xlsx` | `risk_tolerance` column has no traceable derivation |
