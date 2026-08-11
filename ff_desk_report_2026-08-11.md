# Analytics Desk - Intake Report
**2026-08-11 | Both leagues pre-draft | NFL state: 2026 preseason, week 1**

---

## 1. MCP servers

| Server | Tools registered | Tools I actually called | Result |
|---|---|---|---|
| sleeper | 13 | 5 (`get_nfl_state`, `get_league_info`, `get_league_users`, `get_league_draft`, `get_user_leagues`) | all responded |
| ff-hub | 3 | 3 (`draft_board`, `position_tiers`, `wait_or_reach`) | all responded |

Registered count matches the brief for both. I exercised 5 of 13 sleeper tools; the other 8 are registered but untested, so I am not claiming they work.

**Calibration check against your verified findings - all confirmed:**

| Claim | Computed | Match |
|---|---|---|
| Replacement = TE12 at 162.5 | TE12 = 162.5 | yes |
| Bowers 253.5 proj, 91.0 VOR, ADP 20.2 | identical | yes |
| Wait cost from 29: RB 8.9 / WR 7.0 / QB 15.5 / TE 18.9 | identical | yes |
| Henry 12th most valuable at ADP 24.6 | rank 12, ADP 24.6 | yes |
| Chase Brown 9th at ADP 19.0 | rank 9, ADP 19.0 | yes |
| Kelce ADP 107 same tier as Kraft ADP 67 | 107.1 vs 67.3, VOR 8.9 vs 11.9 | yes |

---

## 2. Engine defect: scoring is not actually applied

`draft_board.py` reads only `scoring_settings["rec"]` to pick a bucket (`ppr` / `half_ppr` / `std`), then pulls Sleeper's **generic** `pts_ppr` projection. It never touches the other 40 scoring keys. Both leagues are labeled `scoring: ppr` and both get the same projection numbers.

The two leagues do not have the same scoring:

| Key | YeahThatFantasyLeague! | Facilities |
|---|---|---|
| `pass_td` | **6.0** | **4.0** |
| `pass_int` | -1.0 | -2.0 |
| `fgm_40_49` | 4.0 | 3.0 |
| `fgm_50p` | 5.0 | 3.0 |
| `fgm_yds_over_30` | none | 0.1 |

**Sleeper's generic `pts_ppr` uses 4-point passing TDs.** Verified on Josh Allen: 3650 pass yd, 27 pass TD, 10 INT, 535 rush yd, 11 rush TD, 3 fum, 2 two-pt. Manual at 4-pt TD = 361.5, which is exactly Sleeper's `pts_ppr`. At 6-pt TD it is 415.5.

**Consequence:** every QB in the 12-team is under-projected by roughly `2 x pass_td`, which is 40 to 66 points. Facilities QBs are fine on TDs but wrong on interceptions; Facilities kickers are over-valued by up to 25 points.

**What it actually changes.** Cross-position ranks barely move, because the QB replacement baseline shifts with everyone else (QB12 baseline goes 295.7 -> 347.5). What moves is the **order within QB** - in a 6-point-TD league, volume passers gain on rushing QBs:

| Player | Engine rank | Corrected rank | Move |
|---|---|---|---|
| Jaxson Dart | 101 | 137 | -36 |
| Matthew Stafford | 155 | 124 | +31 |
| Jayden Daniels | 64 | 91 | -27 |
| Jalen Hurts | 61 | 85 | -24 |
| Joe Burrow | outside top 5 QB | 4th QB by VOR | up |
| Dak Prescott | outside top 5 QB | 5th QB by VOR | up |

Judgment call, reversible: I recompute points as a dot product of the league's full `scoring_settings` over Sleeper's projected stat line, which is how Sleeper itself scores. Kept everything else in the engine identical.

**Second, smaller defect:** `position_tiers` returns every player at the position including ADP 999 unranked ones. The `draftable(limit=40)` cap in `draft_board.py` is not being applied by the MCP wrapper. TE "tier 5" comes back as 25 players and tiers 6-7 are noise.

---

## 3. Flex split assumption - verified, low risk

You flagged `replacement_ranks()` as untrusted. I tested it:

| Assumption | RB baseline | WR baseline | TE baseline | Bowers VOR |
|---|---|---|---|---|
| 50/50 RB-WR (current) | RB30 = 161.1 | WR30 = 195.4 | TE12 = 162.5 | 91.0 |
| 60/40 | RB31 = 160.2 | WR29 = 197.6 | TE12 = 162.5 | 91.0 |
| 40/60 | RB29 = 162.9 | WR31 = 192.5 | TE12 = 162.5 | 91.0 |
| 45/45/10 with TE | RB29 = 162.9 | WR29 = 197.6 | TE13 = 161.0 | 92.5 |
| No flex counted | RB24 = 179.5 | WR24 = 212.4 | TE12 = 162.5 | 91.0 |

**Finding:** how you split flex between RB and WR barely matters - baselines move 2 to 5 points across the whole 40/60 to 60/40 range. **Whether you count flex at all** matters enormously: 18 points at RB, 17 at WR. The current code counts it. The assumption is safe, leave it.

Bowers' VOR is completely insensitive to the RB/WR split. His edge is structural, not an artifact.

---

## 4. League settings, verified from the API

| | YeahThatFantasyLeague! | Facilities Fantasy Football |
|---|---|---|
| League ID | 1389378429505241088 | 1387959935878316032 |
| Teams | 12 | 14 |
| Status | pre_draft | pre_draft |
| Draft type | snake | snake (2025 was snake) |
| Draft order | **not yet set** | **not yet set** |
| Starters | QB RB RB WR WR TE FLEX K DEF | identical |
| Bench | 5 | 5 |
| Reception | 1.0 full PPR | 1.0 full PPR |
| Pass TD | 6 | 4 |
| Pass INT | -1 | -2 |

You asked me to confirm the Facilities scoring myself rather than trust it. It is full PPR, but it is **not** the same league as the 12-team. Four-point passing TDs meaningfully de-prioritizes QB there.

---

## 5. League-mate profiles - v1, built from real drafts

### Data actually found

| League | Seasons of draft data | Picks | Source |
|---|---|---|---|
| YeahThatFantasyLeague! | 2022, 2023, 2024, 2025 | 528 (local CSV) + 336 (Sleeper) | Sleeper chain back to 2024, local CSV covers 2022-2024 |
| Facilities | 2022, 2023, 2024, 2025 | 756 | Sleeper chain, league was named "Code 10200" in 2022-23 |

The Sleeper `previous_league_id` chain works and goes back further than expected on Facilities. That is four real seasons.

### Identity resolution - computed, not guessed

The local CSV uses real names; Sleeper uses display names. I matched them by comparing the 2024 CSV round 1 against the 2024 Sleeper draft player-by-player: **24 of 24 exact matches** across picks 1-24. The mapping is verified, not inferred from name similarity - and it would have fooled a guess: `lefty3` is Rich Nolfi, not Mike Long. Mike Long is `Rocksolid1018`.

| Sleeper | Real name | | Sleeper | Real name |
|---|---|---|---|---|
| juliano89 | John Juliano | | lefty3 | Rich Nolfi |
| Rocksolid1018 | Mike Long | | pbaldino | Phil Baldino |
| FrankieSponge | Julian Podagrasi | | dcambs | Dante Cambria |
| mpung | Michael Pungitore | | chrisanddom | Chris Juliano |
| RobFlacc | Rob Flacco | | antdell | Anthony DellaPia |
| ENolan90 | Nolan Lawrence | | rondro9 / RondroEnterprise | Ron Malandro |

`ForthepeopleEsq` is new in 2025 and has no CSV history. `mpung` drafted in 2024 but not 2025.

### YeahThatFantasyLeague! - avg round of first pick at each position

| Sleeper | Real name | Yrs | 1st QB | 1st TE | 1st K | 1st DEF | Reach '25 |
|---|---|---|---|---|---|---|---|
| ForthepeopleEsq | - | 1 | **3.0** | 6.0 | 14 | 13 | +4.2 |
| juliano89 | John Juliano | 2 | **3.5** | 6.0 | 11.5 | 13.5 | +4.9 |
| pbaldino | Phil Baldino | 2 | **3.5** | 6.0 | 14 | 12 | -2.7 |
| Rocksolid1018 | Mike Long | 2 | 4.5 | 7.5 | 11 | 11 | **+20.0** |
| FrankieSponge | Julian Podagrasi | 2 | 5.5 | 5.5 | 12.5 | 11 | **-5.5** |
| chrisanddom | Chris Juliano | 2 | 5.5 | 5.0 | 11 | 11 | +0.8 |
| ENolan90 | Nolan Lawrence | 2 | 6.0 | **4.0** | 11 | 11.5 | +6.5 |
| lefty3 | Rich Nolfi | 2 | 7.0 | 9.5 | 13 | 12.5 | +0.4 |
| RobFlacc | Rob Flacco | 2 | 7.5 | **3.0** | 13 | 13 | -1.9 |
| **antdell** | **Anthony DellaPia** | 2 | 7.5 | 9.5 | 14 | 13 | +4.0 |
| rondro9 | Ron Malandro | 2 | 9.5 | 6.0 | 12 | 12.5 | +13.6 |
| dcambs | Dante Cambria | 2 | **10.0** | 5.0 | 12.5 | 11.5 | -3.7 |
| mpung | Michael Pungitore | 1 | 12.0 | 9.0 | 14 | 10 | - |

`Reach '25` = mean (ADP - actual pick) across that manager's 2025 picks, using Sleeper's own 2025 ADP. Positive = lets value come to him. Negative = reaches ahead of market. Blank = fewer than 8 matched picks.

### Facilities Fantasy Football - same table

| Sleeper | Yrs | 1st QB | 1st TE | 1st K | 1st DEF | Reach '25 |
|---|---|---|---|---|---|---|
| TheMottman | 2 | **1.5** | 4.5 | **5.0** | **5.0** | +13.6 |
| zmohn | 2 | **2.0** | 6.5 | 11 | 10.5 | **-5.4** |
| CapeMayDrive | 3 | 3.0 | 3.7 | 12 | 14 | - |
| mperri12 | 3 | 4.0 | 6.0 | 13.3 | 12 | +11.7 |
| cmhamlett | 4 | 4.5 | 6.2 | 11 | 12.3 | +5.8 |
| LeonSandcastle0917 | 4 | 5.0 | 5.5 | 11.8 | 11.5 | -3.7 |
| stevienelson | 4 | 5.2 | 4.8 | 13 | 13.2 | +9.7 |
| rtaggart26 | 4 | 5.5 | 9.3 | 13.8 | 13.2 | -3.7 |
| domflacco | 2 | 6.0 | 6.0 | 11.5 | 12 | +5.8 |
| **antdell** | 2 | 6.5 | 7.5 | 12.5 | 11 | - |
| Hismael | 2 | 6.5 | 6.5 | 11.5 | 12.5 | +4.5 |
| steelcheeks | 4 | 6.8 | 9.5 | 12.7 | 11.7 | **+17.3** |
| TirEoghainExtreme | 2 | 8.5 | 3.5 | 12 | 11 | +6.4 |
| ernie706 | 2 | 8.5 | 4.5 | 14 | 12.5 | -5.2 |
| IIIIllIIllI | 4 | 8.8 | **3.5** | 12.8 | 13 | +6.6 |
| ELGSES | 2 | 11.5 | 7.0 | - | - | -0.8 |

Eight more managers appear in 1 season only and are listed in the JSON but omitted here as too thin to profile.

### What is usable right now

- **YTFL: three managers take a QB by round 3.5** - ForthepeopleEsq, juliano89, pbaldino. Two more by 4.5. If you want an elite QB in a 6-point-TD league, five teams are ahead of you on that clock.
- **YTFL: RobFlacc (rd 3.0) and ENolan90 (rd 4.0) are the TE-early managers.** Bowers and McBride are one-man tiers. Those two are your competition for them.
- **Facilities: TheMottman is a genuine outlier** - QB rd 1.5, K rd 5, DEF rd 5. He punts skill positions early. That is exploitable and it is free value for everyone behind him.
- **You are a late-QB, late-TE drafter in both leagues** (YTFL QB 7.5 / TE 9.5). That is structurally fine, but it is the exact profile that gets burned by Bowers going at ADP 20.
- **Reach discipline:** Rocksolid1018 (+20.0) and steelcheeks (+17.3) consistently let value fall. FrankieSponge (-5.5) and zmohn (-5.4) reach. Reachers are who make players fall to you.

### What is NOT yet built
Survival probability to your next pick. That needs your draft slot and the draft order, neither of which exists yet. This is the input for edge 5 and the gate on Phase 1.

---

## 6. Top 3 ADP arbitrage, per league

Computed on **corrected** league scoring. **K and DEF excluded** - their VOR-vs-ADP gaps look enormous (LAR DEF shows +60.5 in the 12-team) but that is an artifact: the market correctly discounts them because weekly DEF/K projection is close to noise. Reporting them as "arbitrage" would be a fabricated edge.

### YeahThatFantasyLeague! (12 team)

| Player | Pos | Proj | VOR | Value rank | ADP | Edge |
|---|---|---|---|---|---|---|
| **Brock Purdy** | QB SF | 363.2 | 15.7 | 63 (rd 6) | 103.5 (rd 9) | **+40.5** |
| **Sam LaPorta** | TE DET | 196.5 | 34.0 | 40 (rd 4) | 76.4 (rd 7) | **+36.4** |
| **Dak Prescott** | QB DAL | 365.9 | 18.4 | 56 (rd 5) | 90.3 (rd 8) | **+34.3** |

Two of the three only exist because of the scoring fix. Purdy and Prescott are 6-point-TD beneficiaries the market is pricing at 4-point-TD value. This is your single cleanest edge in this league and no one else in it is computing it.

### Facilities Fantasy Football (14 team)

| Player | Pos | Proj | VOR | Value rank | ADP | Edge |
|---|---|---|---|---|---|---|
| **Jayden Reed** | WR GB | 197.6 | 17.2 | 70 (rd 5) | 116.0 (rd 9) | **+46.0** |
| **D'Andre Swift** | RB CHI | 205.7 | 53.4 | 33 (rd 3) | 65.1 (rd 5) | **+32.1** |
| **Sam LaPorta** | TE DET | 196.5 | 36.7 | 52 (rd 4) | 76.4 (rd 6) | **+24.4** |

### Traps in both leagues

Malik Nabers (ADP 25.2, value rank 46 / 41) and Rashee Rice (ADP 22.7, value rank 41 / 37) are the two clearest overpays on both boards.

### TE structure confirms your read
Bowers (VOR 91) / McBride (72) / Loveland (53) are three one-man tiers, gaps of 18.6 and 19.5. Then Warren + LaPorta, then a cliff. LaPorta at ADP 76.4 sitting in the same tier as Warren at ADP 50.1 is the actual TE arbitrage, not Kelce.

---

## 7. Inventory - what is there and what is empty

### Local, has content

| Path | Contents | Useful? |
|---|---|---|
| `Fantasy Football/2022 - 2024_historical_draft_data.csv` | 528 picks, 12 managers, real names, 2022-24 | **Yes - highest value item found.** Used for identity mapping |
| `Fantasy Football/Fantasy/fantasy analysis/` | `team_tendencies_from_history.csv` (209 rows), `league_positional_frequencies_by_round.csv`, `draft_order_2025.csv` | **Partly - see warning below** |
| `Fantasy Football/Fantasy/2025 Fantasy/` | FantasyPros, PFF, FantasyNerds, PlayerProfiler, Fantasy Life 2025 rankings CSVs + cheat sheets | Yes for 2026, once refreshed. All are 2025 vintage |
| `Fantasy Football/Fantasy/sleeper_fantasy_football_adps.csv` | 1207 players, rank order, 2025 | Superseded - Sleeper's API serves the same ADP live |
| `Fantasy Football/Fantasy/NFL Fantasy Football/` | 2022, 2023, 2024, 2025, Archive, Colab Notebooks | Not yet opened |
| `Fantasy Football/Fantasy/Yahoo! League/` | 2022, 2023, Y!'24, `Yahoo League Historical Data_2025 Prep.xlsx` | Different league, not yet opened |
| `Fantasy Football/Fantasy/Drafting/` | `fantasy_league_historical_draft_data.csv`, 2023 big boards, SmartDraft v2.4 | Not yet opened |
| `~/Downloads/` | The 6 ChatGPT markdown files + `Anthony_2026_Claude_Fantasy_Football_Stack_Research.md` | Present, same as the Fantasy project docs |

**Warning on `team_tendencies_from_history.csv`.** It has `risk_tolerance` and `stack_wr_qb_bias` columns. `stack_wr_qb_bias` is 0.0 for every manager. `risk_tolerance` ranges 0 to 1 with no documented derivation and Dante Cambria sits at exactly 0.0 while Mike Long sits at exactly 1.0, which is what a min-max rescale of something arbitrary looks like. Its `avg_reach_picks` also disagrees with mine (it has Rob Flacco at -7.18; my 2025 number is -1.9, though different years). **I did not use it.** Treat those two columns as unsourced until someone can point at the code that produced them.

### Local, empty or useless

| Path | Finding |
|---|---|
| `~/Downloads/leaguelegacy.csv` | **Not league data.** It is a scrape of leaguelegacy.io's marketing page - 31 rows of feature descriptions and URLs |
| `Fantasy Football/1622/` | TNF block pool PDFs, not fantasy draft data |
| `Fantasy Football/Survivor and Pools/` | Survivor pools, out of scope |

### Google Drive
`My Drive/04 - Sports/Fantasy Football` is a **mirror of the Desktop folder, uploaded today (2026-08-11)**. Same `Fantasy/`, `2025 Fantasy/`, `fantasy analysis/`, `NFL Fantasy Football/` subtree. No content that is not already local. Two Sheets versions exist of `sleeper_fantasy_football_adps` and the `Yeah that fantasy league 2025 sleeper - Sleeper Data Import v8` workbook.

### LeagueLegacy
Not accessed. Login-gated, and the CSV in Downloads is not an export. Needs you signed in.

### MCP filesystem access, for the record
The `Filesystem` MCP server is scoped to `/Users/anthony/CardinalHealth` only and cannot see any of this. Everything above came through Desktop Commander. No Cowork folder is connected to this session either. Not a problem, just worth knowing which door works.

---

## 8. What I need from you

**Blocking Phase 1:**

1. **Draft slot in each league.** Neither draft order is set on Sleeper yet (`draft_order: null`, 0 picks). Survival probability is meaningless without knowing who picks between your turns. If the order is random-on-the-day, say so and I will build it to read the order live at draft start instead.
2. **Draft dates and times, both leagues.** Determines what has to be finished and what can be cut.

**Not blocking, but next:**

3. **LeagueLegacy:** sign in yourself at `leaguelegacy.io/leagues/totallyheterosexualmensffl-id-42081` in Chrome, then tell me the tab is authenticated and I will read the history from it. Also worth knowing: is that league one of these two, or a third? The URL name matches neither.
4. **Decision on the scoring fix.** I have it computed but have not touched `draft_board.py`. Per the architecture split, that edit belongs in a Claude Code session. Want me to hand it over as a patch spec, or do you want me to make the change here?

**One thing I did not do:** external skill vetting. Nothing in this intake surfaced a new candidate, and your prior survey stands. Not re-litigating it.

---

## Security note

You pasted your Sleeper and LeagueLegacy passwords into chat. I did not store them and did not use them. **Rotate both** - they are identical to each other, guessable from your username, and now in a log. Sleeper was never needed: every number in this report came from unauthenticated public endpoints.
