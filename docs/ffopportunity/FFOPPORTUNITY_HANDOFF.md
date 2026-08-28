# ffopportunity → YTFL Integration: Handoff Brief

**Prepared:** 2026-08-28
**Repo:** https://github.com/anthonydellapia1117/yeahthatfantasyleague
**Data path:** `docs/ffopportunity/` (42 data files + 2 documentation files)
**Purpose:** Wire ffopportunity-derived signals into the Python draft engine before the 2026-09-08 live draft.

---

## 1. Project overview

### What YTFL is

YeahThatFantasyLeague is a live fantasy-football draft-decision engine built on 13 seasons of league history (2,339 archive picks). It runs a static HTML draft room (`out/draft_room.html`) polling the Sleeper API live, backed by a Python engine (`src/engine_2026.py`) that produces every number the room displays: VOR, tiers, replacement ranks, survival probabilities, and per-slot decision cards.

**League format (non-standard — this matters for every scoring calculation):**
- 12 teams, 14 rounds, snake draft, drawn order
- Full PPR
- **6-point passing TDs** (not the standard 4)
- Zero IR slots
- Head-to-head **plus** league-median scoring (every week is scored twice)
- 60-second pick clock
- Draft date: 2026-09-08

**Architecture constraints:**
- Python standard library only, zero dependencies
- Fetches nflverse parquet directly from GitHub releases
- Data lives in JSON artifacts under `out/data/`
- Repo is public — no PII, no real names, no financial balances

### What BULLISH is

The BULLISH tag encodes the owner's stated intent:

> "These are the guys I will stand on, because I love their situation, their history, their matchup schedule, their supporting cast, their coaching scheme."

It is implemented in `src/build_bullish.py` (tag engine) and `src/build_bullish_inputs.py` (threshold/percentile computation) as a **probabilistic k-of-n gate**. Each criterion yields P(met); the position gate is P(at least k of n) computed exactly via Poisson-binomial. Thresholds are percentiles of the repo's own computed distributions, never imported constants.

**Conventions:** BULLISH at P ≥ 0.60, WATCH at P ≥ 0.35. TTL 72 hours, after which BULLISH degrades to WATCH.

**Current criteria matrices:**

| Position | Gate | Criteria |
|---|---|---|
| RB | 4 of 5 | receiving_volume, expected_td_equity, line_quality, availability, backfield_command |
| WR | 4 of 5 | target_earning (TPRR), yprr, first_read, opportunity, on_field_dropback_presence (includes pass blocks; not routes) |
| QB | 2 of 3 | rushing, environment, efficiency |
| TE | **SUSPENDED** (former 2 of 2) | No live criteria. The former on-field-dropback input includes pass blocks, while market_share was constant at 0.9 for all 19 veterans. |

**Critical status:** The BULLISH tag is **display-only**. INCONCLUSIVE — incremental value over ADP remains unresolved in the RB/WR scope after suspending the non-discriminating TE matrix. Among positional ADP ranks 1–12, tagged players finished top-12 in 22/35 cases (62.9%) vs 86/164 (52.4%), +10.4pp, 95% CI [-7.3, +28.2], p=0.261. Restricting the earlier mixed RB/WR/TE scope to RB/WR reduced the top-band sample from 300 to 199 players (43 to 35 tagged) and widened the interval from 31.0pp to 35.5pp. That is the expected direction when a non-discriminating group is removed: fewer observations mean more uncertainty. Because the verdict held while uncertainty increased, the unresolved limitation is the ADP-gated design, not one individual criterion. The current interval permits harm and useful lift alike. Only three tags occur at ranks 13–24 and none at 25–48, so those regions are not identifiable. Coarse bands do not adjust for exact ADP, position, season, or repeated players. Tags stay display-only pending continuous-ADP, season-held-out testing.

### What we set out to do

Import the ffverse `ffopportunity` dataset (expected-points modelling, 2020–2025) to answer one question: **can any of it give the tag genuine edge over ADP, rather than restating the market?**

Four rounds of extraction and testing followed. The headline result is that **most candidates failed**, and that is the most valuable output of the work — three signals that looked strong were killed by control tests before they could reach a verdict surface.

---

## 2. Complete file inventory

**Source:** ffopportunity v0.1.2 (ffverse). License: models and data CC BY-SA 4.0; R code GPL-3.
**Export:** R 4.6.1 (2026-06-24) via Homebrew, exported 2026-08-28T07:38:04Z.
**Coverage:** 2020–2025, 36,063 weekly rows, 3,789 season rows.

### Round 1 — BULLISH position extracts (5 files)

| File | Rows | Derived columns |
|---|---|---|
| `bullish_rb_2020_2025.csv` | 11,491 | `expected_td_equity` (rec_touchdown_exp + rush_touchdown_exp), `backfield_command` (rush_attempt / team_rush_attempt), `target_volume` ((receptions + receptions_exp)/2) |
| `bullish_wr_2020_2025.csv` | 16,013 | `tprr_proxy` ⚠️ **MISLABELED**, `yprr_proxy` (rec_yards_gained_exp / receptions_exp), `first_read_share` (rec_attempt / team_rec_attempt), `vacated_targets` (team_receptions_exp − player_receptions_exp) |
| `bullish_qb_2020_2025.csv` | 6,650 | `qb_fantasy_points_exp_6pt` (rescored to 6-pt pass TDs), `prior_epa_proxy` (total_fantasy_points_exp), `team_implied_total` |
| `bullish_te_2020_2025.csv` | 6,730 valid rows | `receiving_market_share` (rec_yards_gained_exp / team_rec_yards_gained_exp); route participation is unavailable and the false alias was removed |
| `bullish_gap_signal_2020_2025.csv` | 36,063 | `total_fantasy_points_diff` — ADP-orthogonal (r = −0.155 vs ADP) |

### Round 1 — Raw data (20 files)

| File(s) | Rows | Notes |
|---|---|---|
| `ep_weekly_2020_2025.csv` | 36,063 | 159 columns, player × week |
| `ep_weekly_2020.csv` … `ep_weekly_2025.csv` | ~6,000 ea | Per-season splits |
| `ep_season_2020_2025.csv` | 3,789 | 158 columns; identical schema to weekly minus `game_id`/`week`, plus `games` |
| `ep_pbp_pass_2020.csv` … `2025.csv` | 18,463 (2025) | 57 columns, play-level |
| `ep_pbp_rush_2020.csv` … `2025.csv` | 15,345 (2025) | 50 columns, play-level |

### Round 2 — Advanced extracts (4 surviving)

| File | Rows | Description |
|---|---|---|
| `line_quality_by_gap_2020_2025.csv` | 1,336 | RB yards-over-expected by `run_location` × `run_gap`, season × team, min 15 carries |
| `line_quality_team_2020_2025.csv` | 192 | RB YOE per carry, team level (32 × 6 seasons exactly), min 100 carries |
| `qb_rush_split_2020_2025.csv` | 238 | Designed carries vs scrambles, `designed_per_game`, `designed_share`, min 6 games |
| `adot_redzone_2020_2025.csv` | 1,568 | True aDOT, `deep_share` (20+ air yards), `rz_targets` (inside 20), `ez_targets` (inside 10), `catchable`, min 20 targets. ⚠️ 4 NA-position rows, 1 QB row |

### Round 2 — 2026 preseason (4 files)

| File | Rows | Description |
|---|---|---|
| `ff_rankings_adp_2026.csv` | 6,011 | 9 ECR sources, scraped 2026-08-21 |
| `depth_charts_2026.csv.gz` | 475,639 | Through 2026-08-27, gzipped 9.9 MB |
| `rosters_2026.csv` | 2,930 | Current 90-man camp rosters |
| `schedule_2026.csv` | 272 | Full 2026 season, 46 columns. **112 games carry `total_line`/`spread_line`** |

### Round 3 — Corrected and new extracts (6 files)

| File | Rows | Description |
|---|---|---|
| `yac_over_expected_2020_2025.csv` | 1,066 | YAC over expected per reception, min 25 receptions. **Clean — zero defects** |
| `neutral_script_role_2020_2025.csv` | 1,459 | One-score games (abs(score_differential) ≤ 8), first 3 quarters. `neutral_share`, `early_down_share`, `mean_wp`, min 40 opportunities. ⚠️ 2 junk rows |
| `playoff_weather_2020_2025.csv` | 192 | Weeks 15–17: `outdoor_share`, `mean_wind`, `mean_temp`, `harsh_share` (wind ≥15 or temp ≤32). **Clean — 32×6, zero NAs** |
| `proe_weekly_reg_2020_2025.csv` | 3,230 | Rebuilt PROE, regular season only, min 25 plays |
| `vegas_weekly_reg_2020_2025.csv` | 3,230 | Rebuilt Vegas, regular season only |
| `regression_flags_clean_2020_2025.csv` | 2,015 | Season-level `fade_flag`, `exp_per_game`, `gap_per_game`, `td_gap`. Games bounded 8–18, QB/RB/WR/TE only |

### Round 4 — Final extracts (3 files)

| File | Rows | Description |
|---|---|---|
| `vegas_2026_forward.csv` | 32 | **DO NOT CONSUME.** The R export inverted home/away in 224/224 team-games. The app derives its own verified table from `schedule_2026.csv`. |
| `team_opportunity_supply_2020_2025.csv` | 192 | Team pass-attempt/carry supply — the denominator every share metric divides by. `pass_attempts_pg`, `carries_pg`, `team_rec_td_exp`, `team_rush_td_exp`. **Renamed from `team_targets`/`targets_pg`: the source column `rec_attempt_team` carries pass attempts, not targets. Values unchanged.** |
| `epa_per_target_clean_2020_2025.csv` | 997 | EPA per target, WR/TE/RB only (QB contamination removed), min 40 targets |

### Documentation (2 files)

| File | Status |
|---|---|
| `COLUMN_DICTIONARY.md` | ⚠️ Covers rounds 1–2 only. **Needs updating for rounds 3–4** |
| `PROVENANCE.txt` | Export metadata, R version, package version, license |

### Deprecated — removed from repo (4 files)

| File | Reason |
|---|---|
| `proe_weekly_2020_2025.csv` | 156 playoff rows (4.6%). Superseded by `proe_weekly_reg` |
| `vegas_weekly_2020_2025.csv` | 156 playoff rows. Superseded by `vegas_weekly_reg` |
| `regression_flags_2020_2025.csv` | 9 junk NA rows with impossible `games` values (379–438; max possible is 17). Superseded by `regression_flags_clean` |
| `epa_per_opportunity_2020_2025.csv` | 122 QB rows + 2 NA — position filter never applied; QB EPA is not comparable to receiver EPA and silently polluted any percentile. Superseded by `epa_per_target_clean` |

---

## 3. All findings across 4 rounds

### 3.1 Mislabeled columns (silent wrong answers)

**`rec_attempt` is TARGETS, not routes.** Verified two ways: WR 2025 totals give `receptions / rec_attempt` = 0.621, which is the NFL target catch rate (~0.65), not a route-based rate. And zero rows exist where `rec_attempt < receptions`, which would be impossible if it were routes.

**Consequence 1 — `tprr_proxy` is actually aDOT.** It computes `rec_attempt / receptions_exp` ≈ 1/expected-catch-rate, which is a **depth-of-target** metric.

| Correlation (n=234 WR seasons, 50+ targets) | r |
|---|---|
| `tprr_proxy` vs aDOT | **+0.917** |
| `tprr_proxy` vs target volume | **−0.059** |
| `tprr_proxy` vs yards/target | +0.162 |

Gating WRs on this tags deep boom/bust threats and **fades high-volume slot receivers**. In full PPR that is backwards.

**Consequence 2 — `route_participation_proxy` is `receptions_exp` renamed.** No transformation applied. It is not route participation.

**Structural limit:** ffopportunity contains **no route counts at all**. Both route-participation criteria (WR and TE) are unfixable from this dataset. The pre-existing `routes_proxy` flaw in the app — counting pass-block snaps as routes — **is not patched by any of this work.** That caveat must stand.

### 3.2 The gap signal — a fade filter, not discovery

`total_fantasy_points_diff` (actual minus expected) is ADP-orthogonal at r = −0.155. Tested 2020–2025, ≥8 games, next-season outcome:

| Year-t gap | n | Δ next-year points | % improved |
|---|---|---|---|
| Unlucky (< −20) | 105 | −11.0 | 37% |
| Neutral (−20 to +20) | 787 | −0.2 | 48% |
| **Lucky (> +20)** | **161** | **−47.7** | **22%** |

**It works in one direction only.** Overperformers collapse; underperformers do *not* bounce back. Controlling for year-t production tier, the penalty holds:

| Tier | Lucky Δ | Rest Δ | Penalty |
|---|---|---|---|
| Top 25% scorers | −58.6 | −28.4 | **−30.2** |
| Mid 50% | −33.4 | −4.7 | **−28.6** |

A consistent ~30-point penalty across tiers ≈ 2 points/game ≈ a WR2→WR3 move. **This is real and survives its control.**

**But `exp` outpredicts `gap` by 2.4–4x:**

| Position | r(gap_t, gap_t+1) | r(gap_t, pts_t+1) | **r(exp_t, pts_t+1)** |
|---|---|---|---|
| QB | 0.210 | 0.192 | **0.447** |
| RB | 0.201 | 0.239 | **0.629** |
| WR | 0.175 | 0.283 | **0.673** |
| TE | 0.284 | 0.169 | **0.683** |

**Implication:** use `exp_per_game` as the ranking input and `gap` only as a fade filter.

### 3.3 Signals that FAILED their control test

Three candidates looked strong on raw correlation and died under control for production tier. Reporting these is the point — each would have produced a confident wrong answer.

**YAC over expected — repeatable but NOT predictive.**

Year-over-year stability is the highest of anything tested:

| Position | YoY r (round 3 confirm) |
|---|---|
| RB | **+0.691** |
| TE | **+0.599** |
| WR | **+0.572** |

Face validity holds — 2025 leaders are Tucker Kraft (+5.51), DK Metcalf (+2.89), Bijan Robinson (+2.60). But controlling for production tier, next-year fantasy points:

| Tier | High YAC-OE | Low YAC-OE | Edge |
|---|---|---|---|
| Top 33% | 215.7 | 230.0 | **−14.3** |
| Mid 33% | 155.2 | 136.8 | **+18.4** |
| Bot 33% | 96.5 | 94.6 | +1.8 |

**Signs flip.** YAC-OE measures a real, stable, repeatable *skill* that does not translate into next-year fantasy points. **Repeatability is not predictiveness.** This was initially recommended as the best new candidate in round 3 and was withdrawn in round 4 after this test. Display only.

**Garbage time — dead.**

Defined as target share at posteam win probability < 0.20. (`vegas_wp` confirmed as posteam WP: 27.0% of pass plays vs 16.4% of rush plays occur at WP < 0.20, i.e. trailing teams throw.)

Uncontrolled it looked strong: high-garbage players declined −16.6 vs low-garbage −32.3, a +15.7 spread. Controlled for production tier:

| Tier | Spread (high − low garbage) |
|---|---|
| Top 33% | −0.3 |
| Mid 33% | +28.8 |
| Bot 33% | −10.5 |

Signs flip, magnitudes inconsistent. **Noise. Do not extract as a gate.**

**`neutral_script_role` — near-random.**

Built in round 3 specifically to replace the mislabeled `tprr_proxy`. Year-over-year stability of `neutral_share`:

| Position | r |
|---|---|
| WR | +0.122 |
| RB | +0.091 |
| TE | +0.177 |

**Cannot replace `tprr_proxy`.** Only `early_down_share` is marginally usable (RB +0.413, TE +0.346, WR +0.260).

### 3.4 Signals that PASSED

**Team opportunity supply — the most stable signal found.**

| Column | YoY r |
|---|---|
| `rec_yards_gained_exp_team` | **+0.523** |
| `rec_touchdown_exp_team` | **+0.520** |
| `rec_attempt_team` | **+0.479** |
| `rush_attempt_team` | +0.369 |

More stable than any player-level round-3 signal, and it is the denominator every share metric already divides by. Exported as `team_opportunity_supply_2020_2025.csv`.

**Terminology correction.** These columns were exported as `team_targets`/`targets_pg` but are built from `rec_attempt_team`, which carries **pass attempts**, not receiver targets. Verified on the committed data: `pass_attempt_team == rec_attempt_team` in 36,063/36,063 rows, constant within all 3,386 team-games, and reproducing the file from `pass_attempt_team` yields all 192 rows exactly. Renamed to `team_pass_attempts`/`pass_attempts_pg`; **no value changed**. Note the stability figures above are unaffected — they were computed on the same numbers under the old name.

Do not confuse this with `bullish_wr_2020_2025.csv`'s `team_targets`, which is a genuinely different field (sum of WR `rec_attempt`) and remains correctly named.

**PROE — the coaching-scheme signal.** Computed as actual pass rate minus expected (`xpass`), with dropbacks = pass plays + QB scrambles. 2025 range: NYJ −12.5 (most run-heavy) to ARI +1.8 (most pass-happy). This is the **only** direct measure of coaching scheme in the entire dataset, and coaching scheme is named explicitly in the BULLISH intent.

Extreme values verified as legitimate, not bugs: 2021 wk13 NE at −57.1 PROE is the Bills wind game (3 pass attempts). Filter is min 25 plays.

**Line quality — present after all.** Believed absent from ffopportunity; it exists at play level. RB rush yards over expected per carry, 2025: BAL +0.90, BUF +0.72, LA +0.66 (best) to CLE −0.77, LV −0.64 (worst). Provides an **independent second source** against the app's existing `team_line_ybc`.

**QB rushing split.** 1,149 scrambles vs 1,260 designed QB runs in 2025. Designed carries are a sticky role; scrambles are volatile. The app's current `rush_ypg` merges them.

**Per-week Vegas.** `implied_total` populates on 100% of plays with 17 distinct weekly values per team, range 15.2–29.5. The app preserves Week 1 only for RB expected-TD equity; QB environment and WR opportunity use the separately derived forward horizon below.

### 3.5 Corrected finding — RB inside-5 share

Initially computed at r = 0.079 using share-of-own-plays as the denominator. **That was wrong.** Recomputed with the correct denominator (share of *team* inside-5 carries): **r = 0.338**.

A positive control caught the error — `backfield_command` (carry share) returned r = +0.472 in the same run, which is the expected magnitude for a known-stable role metric, validating the method.

**The corrected finding is still consequential:** goal-line role (0.338) is **less stable** than workload role (0.472). RB `expected_td_equity` rests on the weaker of the two. This warrants a confidence weight, not a rewrite.

### 3.6 Defects found and fixed

**Round 2 defects (found in round 2, fixed in round 3):**

| # | File | Defect | Fix verified |
|---|---|---|---|
| 1 | `regression_flags` | 9 junk rows, `player_id=NA`, `games` 379–438 (max possible 17). One had `pts=73.5` | 2052 → 2015 rows, 0 junk, games bounded 8–18 ✅ |
| 2 | `proe_weekly`, `vegas_weekly` | 156 postseason rows (4.6%) — weeks 19–22. Playoff sample is 14 good teams only; fantasy season ends wk 17 | 3386 → 3230, exactly 156 removed ✅ |
| 3 | `adot_redzone` | 4 NA-position rows (22–62 targets), 1 QB row | Not yet fixed — low impact |
| 4 | `regression_flags` | Bo Melton tagged `DB` (position from defensive snaps) | Fixed by position filter ✅ |

**Round 3 defects (found in round 3, fixed in round 4):**

| # | File | Defect | Fix verified |
|---|---|---|---|
| 5 | `epa_per_opportunity` | **122 QB rows + 2 NA** — position filter never applied | Rebuilt as `epa_per_target_clean`, 997 rows, WR/TE/RB only ✅ |
| 6 | `neutral_script_role` | 1 NA-position row, 1 Taysom Hill (QB) | Cosmetic, unfixed — file not recommended for wiring anyway |

**Clean on first build:** `yac_over_expected`, `playoff_weather` (192 = 32×6 exactly, zero NAs), `line_quality_team` (192 exactly), `vegas_weekly` (3386/3386 populated, no NAs), `qb_rush_split` (factor conversion correct).

### 3.7 Standing data issue — 4-pt vs 6-pt passing TDs

`total_fantasy_points_exp` and **every** `total_fantasy_points*` column in ffopportunity is scored at **4-point passing TDs**. The league pays **6**.

This affects: `bullish_gap_signal`, `regression_flags_clean`, and all `_diff`/`_exp` composite columns. Only `bullish_qb_2020_2025.csv` carries a rescored column (`qb_fantasy_points_exp_6pt`).

**Rebuild formula from components:**
```
pass_touchdown_exp * 6
+ rush_touchdown_exp * 6
+ rec_touchdown_exp * 6
+ pass_yards_gained_exp / 25
+ rush_yards_gained_exp / 10
+ rec_yards_gained_exp / 10
+ receptions_exp * 1.0        (full PPR)
+ pass_interception_exp * -1.0
```
Note the league's own weights from `src/build_bullish.py`: `passing_yards: 0.04`, `passing_tds: 6.0`, `passing_interceptions: -1.0`, `rushing_yards: 0.1`, `rushing_tds: 6.0`, `receptions: 1.0`, `receiving_yards: 0.1`, `receiving_tds: 6.0`, fumbles lost `-2.0`.

---

## 4. Coverage matrix

| Criterion | Status | Feeding file | Stability |
|---|---|---|---|
| **RB** backfield_command | ✅ Full | `bullish_rb_2020_2025.csv` | r=0.472 |
| **RB** line_quality | ✅ Full | `line_quality_team_2020_2025.csv` | independent 2nd source |
| **RB** availability | ✅ Full | existing `gp_rate_2yr` (app) | — |
| **RB** target_volume | ✅ Full | `bullish_rb_2020_2025.csv` | — |
| **RB** expected_td_equity | ⚠️ Partial | inside-5 share | r=0.338 — weaker than assumed |
| **WR** first_read | ✅ Full | FTN charting (existing app input) | — |
| **WR** target_earning (TPRR) | ❌ **Broken** | `tprr_proxy` = aDOT (r=+0.917) | replacement failed |
| **WR** route_participation | ❌ **Impossible** | no route counts exist in ffopportunity | — |
| **WR** opportunity | ⚠️ Partial | vacated targets | rookie bug unpatched |
| **WR** yprr | ⚠️ Partial | `yprr_proxy` | inherits routes flaw |
| **QB** rushing | ✅ Full | `qb_rush_split_2020_2025.csv` | designed/scramble split |
| **QB** efficiency | ✅ Full | existing `epa_per_att` + `epa_per_target_clean` | cross-check |
| **QB** environment | ✅ Forward scope | Raw `schedule_2026.csv`, current contiguous fully priced horizon Weeks 1-6 | Activated for QB only; exact scope ships in provenance |
| **TE** market_share | ✅ Full | `bullish_te_2020_2025.csv` | — |
| **TE** route_participation | ❌ **Broken** | = `receptions_exp` renamed | unfixable |
| **Coaching scheme** | ✅ **New** | `proe_weekly_reg_2020_2025.csv` | only direct measure available |
| **Matchup schedule** | ⚠️ Partial | `playoff_weather_2020_2025.csv` | display-only |
| **Supporting cast** | ❌ Missing | — | no input |

**Summary:** 8 full, 5 partial, 4 broken/missing. **The two route-participation criteria are structurally unfixable from this dataset** — that is a hard limit, not a to-do item.

---

## 5. Wiring plan

### Priority 1 — highest-value single change

**Raw `schedule_2026.csv` → separately derived `forward_implied_total`**

The prior code read Week 1 only:
```python
implied = {}
with open(games_path) as fh:
    for r in csv.DictReader(fh):
        if r["season"] == "2026" and r["week"] == "1" and r.get("total_line"):
            tl, sp = float(r["total_line"]), float(r["spread_line"] or 0)
            # spread_line is home-relative in nflverse
            implied[r["home_team"]] = round(tl / 2 + sp / 2, 2)
            implied[r["away_team"]] = round(tl / 2 - sp / 2, 2)
```

This extrapolates an entire 17-game season, coaching environment, and matchup schedule from **one Sunday's betting line**. It was identified as the weakest proxy in the app.

**Implemented replacement:** the app does not read the derived R CSV. It validates
the raw 272-game schedule snapshot (32 canonical teams, 17 games each), derives the maximal
contiguous fully priced prefix, and computes home = total/2 + spread/2 under the
independently verified nflverse sign. Current horizon is Weeks 1-6, 93 games and
186 team-games. Week 7 is 7/14 priced. The values feed QB environment and WR
opportunity only; Week-1 RB expected-TD equity is isolated.

The snapshot is not static. Daily `pages-data` refreshes nflverse `games.csv`,
synchronizes its 2026 regular-season rows into the committed snapshot, validates
before any consumer runs, and stages snapshot plus metadata in the same commit.
The metadata records pull time, upstream/snapshot/decision-input digests, horizon,
and priced game/team-game counts. The artifact reports `HORIZON_EXTENDED`,
`CONTRACTED`, `REPRICED`, or `UNCHANGED`, persists the last material event, and
shows its schedule-only same-build tag delta on Home and Draft Room. `CONTRACTED`
fails before replacing the last verified broader snapshot; temporary unpricing and
intentional narrowing cannot be safely distinguished automatically. The 06:00
draft-refresh remains intentionally HISTORY-free and consumes the last validated
committed snapshot. Before publishing attribution, the consumer independently
rederives the stored transition, validates finite totals for all 32 teams, and
rejects ambiguous mixed schedule/model movement. A model-only change therefore
cannot masquerade as a schedule-only tag delta.

**Feeds:** QB `environment` criterion, WR `opportunity` criterion.
**Verdict:** **GATE.**

⚠️ **Caution:** the current forward judgment ends after Week 6. The artifact states
every priced/scheduled count so the scope cannot masquerade as a full-season view.
As more complete weeks price, the derived horizon and tags may move visibly.

### Full wiring table

| File | Feeds criterion | Python target | Gate/Display |
|---|---|---|---|
| `schedule_2026.csv` | QB environment, WR opportunity through a verified derived horizon | `build_bullish_inputs.py` | **ACTIVATED; exact source digest + coverage gate** |
| `team_opportunity_supply_2020_2025.csv` | share denominators (all positions) — note the supply column is **pass attempts** | `build_bullish_inputs.py` | **GATE** |
| `line_quality_team_2020_2025.csv` | RB line_quality | `build_bullish.py` RB block | **GATE** |
| `qb_rush_split_2020_2025.csv` | QB rushing | `build_bullish.py` QB block | **GATE** |
| `proe_weekly_reg_2020_2025.csv` | coaching scheme (new criterion) | `build_bullish_inputs.py` + new criterion | Display → gate after null test |
| `regression_flags_clean_2020_2025.csv` | fade filter; `exp_per_game` as rank input | `build_bullish.py` | Display → gate after null test |
| `adot_redzone_2020_2025.csv` | replaces mislabeled `tprr_proxy`; `rz_targets` feeds RB expected_td_equity | `build_bullish.py` WR/RB blocks | Display |
| `epa_per_target_clean_2020_2025.csv` | QB efficiency cross-check | `build_bullish.py` | Display (conflict flag on disagreement) |
| `line_quality_by_gap_2020_2025.csv` | RB line_quality detail | — | Display |
| `playoff_weather_2020_2025.csv` | matchup schedule context | context chip | **Display only** |
| `yac_over_expected_2020_2025.csv` | — **failed control test** | — | **Display only — do not gate** |
| `neutral_script_role_2020_2025.csv` | — **near-random (r=.09–.18)** | — | **Do not wire** |
| `bullish_gap_signal_2020_2025.csv` | fade filter | superseded by `regression_flags_clean` | Display |
| `vegas_weekly_reg_2020_2025.csv` | historical Vegas context | — | Display |
| `ff_rankings_adp_2026.csv` | ADP cross-source | existing ADP pipeline | Reference |
| `rosters_2026.csv`, `depth_charts_2026.csv.gz` | roster/depth resolution | existing crosswalk | Reference |
| `schedule_2026.csv` | source for `vegas_2026_forward` | — | Source |

### Integration notes for the Python side

- Existing threshold convention in `build_bullish.py`: `p_soft(value, thr, band)` where `band = (p75 - p50) / 2` of the criterion's own distribution. New criteria must follow this — **percentiles of our own distribution, never imported constants.**
- Proportion criteria use `p_prop(k, n, thr)` (normal approximation on sample proportion).
- Position gate uses `p_at_least(ps, k)` — exact Poisson-binomial.
- A criterion with no input **must not** silently count as met. Current code sets `p_gate = 0.0` when `len(ps) < need`, and appends a reason string. Preserve this.
- All artifacts are digest-linked: `build_bullish.py` raises if `inputs_content_sha256` or any `input_content_sha256` entry mismatches the engine payload. New inputs must be added to that manifest or the build fails closed.

---

## 6. Standing cautions

1. **4-pt vs 6-pt passing TDs.** Every `total_fantasy_points*` column in ffopportunity is scored at 4-point passing TDs; the league pays 6. `regression_flags_clean` inherits this. **Rebuild from component `_exp` columns before any of it touches a verdict.** See §3.7 for the formula.

2. **The routes_proxy flaw is NOT patched.** ffopportunity contains no route counts. The app's existing weakness — counting pass-block snaps as routes — survives this entire body of work. **Keep that caveat on every surface that displays a route-derived number.** It is especially damaging for TEs, who frequently pass-block on dropbacks, systematically suppressing their TPRR/YPRR/route-participation percentiles.

3. **Hold every new signal at display until null-tested against 13 seasons.** Of the candidates tested across four rounds, **three of the most promising failed their control tests** (YAC-OE, garbage time, neutral_script_role). Raw correlation and year-over-year stability are *not* sufficient evidence. The controlled test — does the signal predict next-year outcomes *within* a production tier — is the one that matters.

4. **BULLISH remains display-only.** INCONCLUSIVE — incremental value over ADP remains unresolved in the RB/WR scope after suspending the non-discriminating TE matrix. Among positional ADP ranks 1–12, tagged players finished top-12 in 22/35 cases (62.9%) vs 86/164 (52.4%), +10.4pp, 95% CI [-7.3, +28.2], p=0.261. Restricting the earlier mixed RB/WR/TE scope to RB/WR reduced the top-band sample from 300 to 199 players (43 to 35 tagged) and widened the interval from 31.0pp to 35.5pp. That is the expected direction when a non-discriminating group is removed: fewer observations mean more uncertainty. Because the verdict held while uncertainty increased, the unresolved limitation is the ADP-gated design, not one individual criterion. The current interval permits harm and useful lift alike. Only three tags occur at ranks 13–24 and none at 25–48, so those regions are not identifiable. Coarse bands do not adjust for exact ADP, position, season, or repeated players. Tags stay display-only pending continuous-ADP, season-held-out testing.

5. **`COLUMN_DICTIONARY.md` retains historical cautions.** The TE false route
   alias is removed. The WR `tprr_proxy` warning remains because ffopportunity
   has no route counts and the field is still not TPRR.

6. **2026 Vegas coverage is partial and explicit.** The activated horizon is Weeks
   1-6, 93 games / 186 team-games; Week 7 is 7/14 priced. The artifact exposes the
   boundary and recomputes it every build from the daily-synchronized snapshot.
   A synthetic Week-7 completion proves the event moves to 107 games / 214
   team-games; a synthetic contraction fails closed without replacing either
   snapshot file.

7. **Repeatability ≠ predictiveness.** This is the single most important methodological lesson of the four rounds. YAC-OE is the most repeatable signal in the dataset (r up to 0.691) and predicts nothing about next-year fantasy points once production tier is controlled.

---

## 7. Data locations and environment

### Paths

| Location | Path |
|---|---|
| Local working folder | `~/Desktop/ff-hub/ffopportunity_data/` |
| Local repo | `~/Claude/Projects/yeahthatfantasyleague/` |
| GitHub repo | https://github.com/anthonydellapia1117/yeahthatfantasyleague |
| Data in repo | `docs/ffopportunity/` |
| App data artifacts | `out/data/` |
| Engine | `src/engine_2026.py`, `draft_board.py` (repo root) |
| BULLISH | `src/build_bullish.py`, `src/build_bullish_inputs.py` |

### R environment

```r
# R 4.6.1 (2026-06-24) via Homebrew
library(ffopportunity)   # v0.1.2
library(dplyr); library(readr); library(tidyr)

pp <- ep_load(season = 2020:2025, type = "pbp_pass")
pr <- ep_load(season = 2020:2025, type = "pbp_rush")
wk <- ep_load(season = 2020:2025, type = "weekly")
```

### R gotchas (hard-won)

```r
# 1. rush_touchdown in PR ships as a FACTOR. Coerce before any math.
#    Do NOT name the helper n() — it collides with dplyr::n().
num <- function(x) if (is.factor(x)) as.numeric(as.character(x)) else as.numeric(x)

# 2. total_line exists in PP but NOT in PR. Use bind_rows with an explicit NA column.
pr %>% transmute(season, week, posteam, total_line = NA_real_, ...)

# 3. Fantasy regular season only — 2020 ended wk 17, 2021+ end wk 18.
reg <- function(d) d %>% filter(week <= ifelse(season == 2020, 17, 18))

# 4. Always filter position explicitly. The epa_per_opportunity defect was
#    122 QB rows leaking into a receiver distribution.
filter(receiver_position %in% c("WR","RB","TE"))

# 5. Filter junk IDs: player_id != "" and !is.na(player_id) and
#    full_name != "NA" — NA-keyed aggregation rows appear otherwise.
```

### Key column reference

**PP (pbp_pass), 57 columns.** Used: `receiver_player_id`, `receiver_full_name`, `receiver_position`, `posteam`, `season`, `week`, `complete_pass`, `air_yards`, `yards_after_catch`, `yards_after_catch_exp`, `yardline_100`, `xpass`, `vegas_wp`, `implied_total`, `total_line`, `ep`, `pass_completion_exp`, `score_differential`, `qtr`, `down`, `goal_to_go`, `roof`, `surface`, `wind`, `temp`.
Unused: `desc`, `play_id`, `passer_*`, `relative_to_sticks`, `relative_to_endzone`, `era`, `qb_hit`, `posteam_type`, `pass_location`, `shotgun`, `no_huddle`, `fixed_drive`, `half_seconds_remaining`, `game_seconds_remaining`, `ydstogo`, `two_point_*`, `interception`, `first_down_pass`, `yardline_exp`, `pass_touchdown_exp`, `pass_first_down_exp`, `pass_interception_exp`.

**PR (pbp_rush), 50 columns.** Used: `rusher_player_id`, `full_name`, `position`, `posteam`, `season`, `week`, `rushing_yards`, `rush_yards_exp`, `rush_touchdown`, `run_location`, `run_gap`, `qb_dropback`, `qb_scramble`, `yardline_100`, `xpass`, `vegas_wp`, `implied_total`, `ep`, `goal_to_go`, `score_differential`, `qtr`, `down`.
Unused: `run_gap_dir`, `era`, `posteam_type`, `shotgun`, `no_huddle`, `fixed_drive`, `half_seconds_remaining`, `game_seconds_remaining`, `ydstogo`, `two_point_*`, `first_down_rush`, `rushing_yards_exp`, `rushing_td_exp`, `rushing_fd_exp`.

**WK (weekly), 159 columns.** Naming convention: every stat exists as `actual`, `_exp` (xgboost expected from play context — down, distance, field position, air yards, personnel), and `_diff` (actual − expected). Team-level variants carry `_team`.
80+ `_team` columns exist; only 5 are used (`rec_attempt_team`, `rush_attempt_team`, `rec_yards_gained_exp_team`, `rec_touchdown_exp_team`, `rush_touchdown_exp_team`). Team `_diff` columns were tested and are mostly luck (r = 0.11–0.30 YoY) — not recommended.

### Assessment of remaining unused columns

Tested or evaluated and **not** recommended for extraction:
- **Team `_diff` columns** — r = 0.112–0.297 YoY. Mostly luck.
- **`relative_to_sticks`, `relative_to_endzone`** — derivable from `ydstogo`/`yardline_100`, already extracted.
- **`qb_hit`, `pass_location`, `shotgun`, `no_huddle`, `fixed_drive`** — measure things that failed the same control test as garbage time, or are scheme descriptors already captured better by PROE.
- **`era`, `posteam_type`, `surface`** — no fantasy signal; `roof`/`wind`/`temp` already captured in `playoff_weather`.
- **Garbage time / win-probability splits** — explicitly tested and **dead**.

**Conclusion: the dataset is exhausted for incremental edge.** Further extraction adds files, not signal.

---

## 8. Recommended execution order

1. **Forward Vegas is complete for its approved scope.** Raw schedule input,
   verified sign, 32-team/full-schedule reconciliation, daily snapshot sync,
   dynamic horizon event, immutable activation delta, QB/WR consumers only. Do not
   substitute the broken R CSV.
2. **Wire `team_opportunity_supply`** as share denominators. Gate.
3. **Wire `line_quality_team` and `qb_rush_split`** into their RB/QB criteria. Gate.
4. **Rebuild `regression_flags_clean` at 6-pt passing TDs** from component `_exp` columns. Then wire `exp_per_game` as a display-ranked input.
5. **Add PROE as a new coaching-scheme criterion**, display-only, and null-test it against 13 seasons.
6. **Swap `adot_redzone` in for the mislabeled `tprr_proxy`** — display first.
7. **Update `COLUMN_DICTIONARY.md`** for rounds 3–4 and correct the two mislabeled column descriptions.
8. **Do not wire** `neutral_script_role`. **Do not gate** `yac_over_expected`.

---

*End of handoff brief.*
