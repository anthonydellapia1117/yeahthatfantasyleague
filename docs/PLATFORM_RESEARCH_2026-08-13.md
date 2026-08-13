# Platform, Insight, and Data Research - 2026-08-13

**Project:** YeahThatFantasyLeague Draft Room expansion (home page, player pages, teams, depth charts)
**Scope:** Research only, per Anthony's direction. No design spec, no build order. Architecture recommendation included (Anthony delegated that call to this doc). Sequencing assumption: draft-first, in-season later.
**Verifier:** Anthony. Every load-bearing claim carries a status tag and a source. Nothing here changes the headline finding: there is no draft-day roadmap, and opponent tendencies stay display-and-simulator only.

**Status tags used throughout**

| Tag | Meaning |
|---|---|
| VERIFIED-LIVE | Endpoint or file probed from this session on 2026-08-13; response inspected |
| SOURCED | Read directly from the cited primary page this session |
| REPORTED | Secondary source claim (review, article); not independently confirmed |
| UNVERIFIED | Could not be confirmed; do not build on it |

---

## 1. Executive verdict

**Nothing on the market does what the draft room already does.** Fifteen draft tools and eight league platforms were profiled. Exactly one mainstream product models your specific leaguemates (FantasyPros Draft Intel, capped at 5 years of synced history, tendency-only). None runs a league-fitted pick-error survival model, none backtests it, and none enforces an honesty guard between tendencies and decision probabilities. The expansion opportunity is not the decision engine - it is the **insight surface around it**: player pages, team pages, and depth charts fed by verified free data, presented at Sleeper-grade UX quality.

The specific verdicts:

| Question | Answer |
|---|---|
| Best league platform | **Sleeper** - the consistent 2025-2026 pick for hosted leagues and the UX benchmark to borrow from (Draft Sharks 93/100 Aug 2026; multiple 2026 comparisons). ESPN is the scale incumbent and just absorbed NFL Fantasy, which shuts down for 2026 |
| Best draft-tool ideas worth absorbing | Leaguemate modeling (Draft Intel), value-vs-ADP framing, tier/scarcity state, floor-ceiling bands, injury risk as a value modifier, usage scores, whole-roster optimization. You already have the hardest one, tested |
| What a player page should show | Seven converged insight primitives (section 4), nearly all computable from free verified sources. The one real in-season gap: route-based metrics (routes run, YPRR, route participation) have **no free in-season path for 2026** |
| PlayerProfiler | Metric catalog is the best in class; by the family mapping in section 4.2, roughly half of it is replicable outright from free nflverse data and roughly three quarters at least partially. Their API is open but undocumented, and their Terms of Use prohibit scraping and aggregation. Compliant paths: their $45/season Data Analysis download package, or replicate the replicable subset from nflverse |
| Team situation intel | Real and buildable: 17 teams have new primary play-callers for 2026 (sourced table, section 5). PROE is directly computable from nflverse pbp (xpass and pass_oe fields verified in the 2025 file). Vacated targets/carries computable from roster diffs. All of it belongs in the **display layer** - none of it enters a decision probability until it survives a backtest, same rule as opponent tendencies |
| The three prior repos | Eagle-Draft-Hub: carry the design spec and ESPN endpoint patterns, not the code. rork-tampr-pro: carry the source-citation UI pattern and the palette (already continuous with ff-hub.html). sports-ml-engine: README scaffold only, nothing to carry |
| Architecture | **Stay static: GitHub Pages plus a GitHub Actions cron build.** Sleeper's API sends access-control-allow-origin: * (VERIFIED-LIVE), so live polling keeps working browser-side exactly as draft_room.html does today. FFC ADP sends no CORS header (VERIFIED-LIVE), so market data is fetched at build time. Add a thin serverless proxy later only if a keyed or CORS-blocked source becomes load-bearing |

---

## 2. League platform landscape

What each platform is, why people choose it, and what is worth stealing. Full UX pattern library in section 10.

| Platform | Appeal | Standout capabilities | Worth stealing | Status |
|---|---|---|---|---|
| **Sleeper** | Design-led, social-first, free; the consensus 2025-2026 hosting pick | League chat as the home feed; draft board grid with TV cast mode; unlimited undo and pausable drafts; player card as action hub; tap-any-score scoring ledger; win probability and optimal-lineup delta; public read API with trending adds/drops | Nearly everything UX: chat-as-feed, score-ledger transparency, board-first draft view, dark theme discipline, design-for-the-repeat-user | SOURCED (support.sleeper.com, sleeper.com/blog) + REPORTED (Draft Sharks 93/100 Aug 10 2026; LordSkunk Jun 2026) |
| **ESPN** | Scale incumbent; 2025 full app rebuild; now the NFL's official fantasy home | Personalized home with analyst rank badges on every starter; a roster dashboard that renders league state as a to-do list; live in-game re-projections; swipeable matchup carousel; 2024 color-coded all-teams draft board; instant post-draft grades | Rank-badge-on-lineup, action-item dashboard, live re-projection, paired add/drop comparison flow | SOURCED (espnpressroom.com Aug 2025; espn.com Aug 2024) |
| **Yahoo** | Reliable casual default; Fantasy Plus premium tier ($34.99/season) | Draft Scout with VOLS (value over last starter) framing; Min/Max floor-ceiling projection bands; one-click optimal lineup; Trade Hub | Value-over-replacement framing and floor-ceiling bands in any recommendation surface | SOURCED (sports.yahoo.com Aug 2025) |
| **NFL Fantasy** | Discontinued: NFL named ESPN exclusive season-long partner; leagues import to ESPN for 2026 | Video highlights embedded in player research was its one distinctive pattern | Embedded highlight video on player pages; also the cautionary tale - official status did not save a weaker product | REPORTED (CordCuttersNews Aug 4 2026; Scoutcast Aug 2026) |
| **CBS** | Veteran paid-commissioner product, 20+ year league archives | Auto-generated weekly matchup recap narratives; deep rule customization | Auto-recap narratives; league history as a first-class shrine page | SOURCED (cbssports.com commissioner splash) |
| **Fantrax** | Customization powerhouse, best-rated hosting by Draft Sharks websites review | Near-MFL settings depth behind sane defaults; college/devy support | Progressive disclosure of power settings | REPORTED (Draft Sharks Aug 6 2026; reviewer opinions on polish conflict) |
| **Underdog** | Best-ball category leader; the whole product is a draft room | User rankings as a first-class object (drag-drop or CSV upload) powering autopilot with hard position caps; slow drafts as async multiplayer; restrained 3-color system | Rankings-as-object, position-cap guardrails, minimal palette keeping a dense grid readable | SOURCED (help.underdogsports.com) + REPORTED (HelloRookie Jul 2026) |
| **MFL** | Maximum customization for complex leagues; UI famously dated | Conditional scoring engine; multi-decade archives; skinnable league homepage | The anti-pattern lesson: capability without information design bleeds users | SOURCED (myfantasyleague.com features) + REPORTED (Footballguys forum 2025) |

**Market context worth logging:** NFL Fantasy's shutdown consolidates casual players onto ESPN for 2026 (REPORTED, two independent Aug 2026 sources). Underdog was acquired by IG Group for up to ~$1.3B announced Jul 30 2026 (SOURCED, IG press release). BeerSheets is discontinued for 2026 per its own distribution page (SOURCED, footballabsurdity.com).

---

## 3. Draft tool landscape

Verified pricing and capabilities as of 2026-08-13. Source register in section 13.

| Tool | Core capability | Verified price | Per-player insights surfaced | Gap relative to your app |
|---|---|---|---|---|
| FantasyPros Draft Wizard + Draft Intel | Mock sim, live assistant, post-draft grades; Draft Intel profiles each leaguemate from up to 5 years of synced drafts (round-by-round position tendencies, runs, repeat picks) | PRO $3.99/mo annual to GOAT ~$15/mo annual (page-source JSON) | ECR vs ADP value, tiers, expert notes | Tendency display only; no survival model, no backtest, no honesty guard |
| Draft Sharks War Room | Live-sync value board recalculated every pick; ML injury model (risk rating, projected games missed) framed as 1 of 17 indicators | $72/yr traditional; $96/yr +dynasty; $192/yr +advice | Projections, injury risk, trade values, ADP market movement | Generic league model; injury model is the one capability with no free equivalent |
| 4for4 Draft Hero | Whole-roster optimization (not best-available), browser-extension live sync | Lite $39, Pro $59, DFS $99 per season | Scoring-adjusted projections, durability, consistency, SOS | No league-mate modeling |
| Fantasy Life | Usage reporting and a proprietary usage score (Dwain McFarland's framework; product names on fantasylife.com); ADP Tracker; Draft Companion | FL+ T1 $39.99/yr, T2 $99.99/yr | Usage trends, usage score, ADP movement | Insight layer without a decision engine |
| RotoViz | Screener (self-serve historical querying), Range of Outcomes distributional projections | $129.99/yr (also monthly tiers) | Historical splits, outcome ranges, cohort comps | Analyst workbench, not a draft room |
| Establish The Run | Rankings/tiers content with continuous updates, O-line rankings, site-specific best-ball values | Draft Kit Pro $54.99; In-Season $274.99 | Written capsules, tiers, auction values | No software; rankings only |
| PFF+ | Mock sim, live assist, grades, premium charting stats | $119.99/yr (early-bird sale observed) | Grades, charted usage | Charting depth is paid-only; generic advice |
| DraftEdge | AI recommendation engine, hands-free Sleeper auto-sync | Draft Kit $34.95 one-time; Pro $39.95/mo | Projections, VORP, scarcity, ceiling/floor/bye comparisons | Opaque model, no league history |
| WalterPicks | App-first league sync, personalized ROS ranks, trade finder | $64.99/yr Pro (App Store) | ML projections vs your roster context | No public methodology |
| RotoWire / FTN / Stokastic | News wire + draft kit / charting-data shop / DFS sims | Not verified this session (bot-gated or JS-rendered pricing) | Projections, news, comparisons | - |

**What the field converges on (the seven primitives, section 4) and what nobody has:** no tool combines league-specific behavioral modeling with a calibration benchmark. Draft Intel is the closest competitor to the tendency work and it is strictly shallower than what already shipped (no survival probabilities, no walk-forward backtest, no display-only guard). The moat is real; keep it.

---

## 4. The player insight layer

### 4.1 The seven converged primitives

Across the strongest 2026 tools, per-player insight converges on: **(1)** league-scoring-personalized projection, **(2)** value vs market (projection or rank vs live ADP), **(3)** tier and positional scarcity state, **(4)** injury risk as a value modifier, **(5)** outcome distribution (floor/ceiling), not point estimate, **(6)** usage and opportunity analytics, **(7)** draft-room context (roster construction fit, opponent behavior). The draft room already covers 1, 2, 3, and 7 with tested machinery. 4 has no free source (Draft Sharks' model is proprietary; nflverse injuries data carries a flagged continuity risk). 5 is limited by the projection feed carrying no variance measure (already documented in engine_2026.py). 6 is the genuinely new surface a player page adds.

### 4.2 The metric catalog, mapped to free sources

The full PlayerProfiler glossary was pulled (SOURCED, playerprofiler.com/terms/), their live per-player API response was inspected (roughly 250 fields per season per player, session probe), and each metric family was mapped against verified free data. Summary by family:

| Metric family | Examples | Free path | Cadence in-season | Status |
|---|---|---|---|---|
| Volume and opportunity | Target Share, Opportunity Share, Weighted Opportunities, Air Yards, aDOT, Red Zone Share, End Zone Targets, Carries Inside 5/10, Snap Share, Hog Rate (targets per snap) | nflverse pbp + stats_player + snap_counts; many precomputed (target_share, air_yards_share, wopr are literal columns) | Nightly after game days; snap counts 4x daily | VERIFIED-LIVE (2025 stats_player: 19,421 rows x 145 cols; snap_counts schema read) |
| Efficiency | EPA splits, CPOE, YAC and xYAC, RACR, True YPC, Stuffed Runs, Deep Balls, AY/A, QB Rating When Targeted, Dominator Rating (share of team yards+TDs), Game Script, Pace | nflverse pbp (epa, cpoe, xyac_*, air_yards, yardline_100, score_differential all present) | Nightly | VERIFIED-LIVE (2025 pbp: 48,771 plays x 372 cols) |
| Expected fantasy points | xFP, points above expectation | ffverse ffopportunity releases (ep_weekly: 159 cols incl. total_fantasy_points_exp and diff columns); model trained 2006-2020, so treat older calibration as a caveat | Automated releases, weekly-ish | VERIFIED-LIVE (2025 file probed) |
| Tracking-derived | Rush Yards Over Expected, avg separation, avg cushion, time to throw, aggressiveness, % share of intended air yards | nflverse Next Gen Stats mirror (ngs_passing / ngs_receiving / ngs_rushing, 2016-2025, week 0 = season row) | Nightly 3-5am ET | VERIFIED-LIVE (files probed) |
| Charting-derived | drops, catchable targets, contested targets, INT-worthy throws, play-action, RPO, screens, motion, blitzers, pressure | nflverse ftn_charting (2022+, play-level flags, CC-BY-SA, 48h after each game) plus participation file (formations, personnel, coverage type) | ftn_charting 4x daily in-season; participation is POST-SEASON ONLY since 2023 | VERIFIED-LIVE (2025 ftn_charting: 47,316 plays x 29 cols) |
| Route-based | Routes Run, YPRR, Route Participation, Slot Rate, Wins vs Man/Zone | **No free in-season path for 2026.** nflverse route data (participation file) lands after the postseason; in-season routes are paid charting (FTN/PFF subscriptions) | Historical only through 2025 | SOURCED (nflreadr docs state participation "does not update during the season") |
| Athletic and prospect | Speed Score, Burst Score, Agility Score, Height-adjusted Speed Score, BMI, College Dominator, Breakout Age, draft capital | Formulas are public; nflverse combine (2000-2026), draft_picks (1980-2026), players (birth dates); college production from collegefootballdata.com | Static | VERIFIED-LIVE (combine and draft_picks probed) |
| Proprietary models | Fragility/Injury Risk, Breakout Rating, Best Comparable Player, Yards Created, Accuracy Rating, coverage-split wins, Lifetime Value | Not replicable: their charting, injury model, and prospect models | - | SOURCED (glossary) |

**The honest read:** a player page can carry the volume, efficiency, expected-points, tracking, and athletic families with full provenance at nightly cadence, plus charting flags at 48-hour cadence, entirely free. It cannot honestly show in-season YPRR or route participation in 2026, and it cannot show an injury-risk number without buying one or building one. Label the gaps instead of faking them - that is already this project's house style.

### 4.3 PlayerProfiler specifically

| Question | Finding | Status |
|---|---|---|
| What they publish | The deepest public per-player metric encyclopedia: workout percentiles, prospect profile, Best Comparable Player, multi-season usage/efficiency tables, injury timeline, premium-gated charts | SOURCED (live player page walked: header, workout panel, prospect panel, comps, stats, injury history, news) |
| Their API | api.playerprofiler.com is live and unauthenticated: /v1/players returned 5,190 players; /v1/player/{id} returns the full profile JSON. **No official documentation exists anywhere** | Session probe 2026-08-13 |
| Their Terms of Use | RotoUnderworld ToU (updated Sep 18 2023) bans scraping and "similar techniques to aggregate, repurpose, republish"; republication requires "Courtesy of PlayerProfiler.com" attribution | SOURCED (playerprofiler.com/terms-of-use/) |
| Compliant access paths | Data Analysis package: $45/season, sells browse, sort, and **download** of the advanced-stat database. All-In package $135/season. Or: replicate the replicable families from nflverse and skip them entirely | SOURCED (membership page) |
| Verdict | Do not build a pipeline on their open API - it is undocumented, unlicensed for that use, and their ToS forbids it. If their proprietary families matter enough, the $45 package is the clean route: manual download, provenance recorded, attribution shown. Otherwise nflverse covers the majority of the catalog with a better license (CC-BY-4.0) | - |

---

## 5. Team situation intel

The request: a team-context layer that explains whether a player's environment helps or hurts. The research verdict: this layer is buildable from sourced, mostly free inputs, and 2026 is an unusually rich year for it - **17 of 32 teams have a new primary play-caller**.

### 5.1 New play-callers for 2026 (sourced, compiled Aug 13 2026)

Cross-checked across the NFL.com coaching tracker, FOX's tracker (updated Feb 20 2026), CBS's OC-hire grades (Feb 23 2026), and a 32-team play-caller rundown (Acme Packing Company). Team-site confirmations cited where play-calling was explicitly announced.

| Team | New play-caller 2026 | Replaces | Notes |
|---|---|---|---|
| ARI | Mike LaFleur (HC) | Petzing (under Gannon) | Ex-Rams OC; Hackett is non-calling OC |
| ATL | Tommy Rees (OC) | Zac Robinson | Stefanski (new HC) confirmed Rees calls plays (PFT, falcons.com) |
| BAL | Declan Doyle (OC) | Todd Monken | First-time caller, under new HC Minter |
| BUF | Joe Brady (HC) | (was OC) | Keeps calling as HC; Carmichael non-calling OC |
| CLE | Todd Monken (HC) | Stefanski/Rees | espn.com, ravens.com confirmations |
| DET | Drew Petzing (OC) | John Morton | Ex-Cardinals OC |
| LAC | Mike McDaniel (OC) | Greg Roman | Ex-Dolphins HC |
| LV | Klint Kubiak (HC) | Chip Kelly | Ex-Seahawks OC |
| MIA | Bobby Slowik (OC) | Mike McDaniel | Under new HC Hafley (defensive) |
| NYG | Matt Nagy (OC) | Daboll/Kafka | Under new HC John Harbaugh (nfl.com, giants.com) |
| NYJ | Frank Reich (OC) | Tanner Engstrand | Hired Feb 4 |
| PHI | Sean Mannion (OC) | Kevin Patullo | First-time caller |
| PIT | Mike McCarthy (HC) | Arthur Smith | steelers.com confirmation |
| SEA | Brian Fleury (OC) | Klint Kubiak | First-time caller, ex-49ers run-game coordinator |
| TB | Zac Robinson (OC) | Josh Grizzard | Ex-Falcons OC |
| TEN | Brian Daboll (OC) | Nick Holz | Under new HC Saleh (nfl.com, tennesseetitans.com) |
| WAS | David Blough (OC) | Kliff Kingsbury | First-time caller, promoted Jan 9 |

Watch item: Denver returns Payton but CBS flagged new OC Davis Webb as a possible play-caller (REPORTED, single source). First-time-ever callers flagged by the rundown: Blough, Mannion, Doyle, Fleury - no prior play-calling history exists to profile, which is itself display-worthy context.

### 5.2 The four situation instruments and how each is computed

| Instrument | Method | Free source | Status |
|---|---|---|---|
| Play-caller pass/run tendency (PROE) | Actual pass rate minus expected pass rate given down, distance, field position, clock, score. nflverse pbp ships the model outputs per play: xpass and pass_oe. Aggregate by team-season or by play-caller tenure | nflverse pbp (pass_oe non-null on 36,019 of 48,771 plays in the 2025 file); free published versions at rbsdm.com, nfelo team tendencies, ETR's free PROE page | VERIFIED-LIVE (fields inspected) |
| Vacated opportunity | Sum departed players' prior-season targets/carries and shares (roster diff x prior-year usage). FTN's published definition; 4for4 runs a free tracker (updated Jun 2 2026) | Computable from stats_player + rosters diffs; free published versions at 4for4, Yahoo, PFF articles | SOURCED (method); computable path VERIFIED-LIVE (both inputs probed) |
| O-line context | Free proxies: RB yards before contact (pfr_advstats, 2018+), sack/pressure context (pbp + ftn_charting blitzer/pressure fields). ESPN publishes pass/run block win rates as periodic articles only - no API. PFF grades are paywalled | pfr_advstats VERIFIED-LIVE (schema read); ESPN win-rate articles SOURCED | Attributed evidence it matters: 4for4 (Jul 3 2026) reports a 0.462 correlation between its composite O-line metric and team fantasy output (their study, their n) |
| Pace and neutral tendencies | Plays per game and seconds per snap in neutral game states (win-probability band filter), red-zone pass rate, personnel and motion rates (participation historical, ftn_charting in-season) | All from pbp fields already verified (half_seconds_remaining, wp, yardline_100, goal_to_go) | VERIFIED-LIVE (fields inspected) |

**Evidence discipline note:** analyst consensus holds that play-caller tendencies persist across stops (ETR, FantasyLife, 4for4 all publish on this; 4for4's Aug 4 2026 piece profiles all new-caller teams and reports scheme effects like play-action passes at +0.06 EPA/att vs roughly 0.00 without). No rigorous public year-over-year stability coefficient was found - treat persistence as attributed analyst consensus, not an established constant. In-league, this project's own parallel finding stands: drafting tendencies persist (r=+0.813, p<0.00002, 2,039 picks) yet made forecasts worse inside probabilities (48,399-prediction backtest, p=0.99). The same skepticism applies to NFL situation intel: it earns display placement now and probability placement never, unless a backtest someday says otherwise.

---

## 6. From insight to edge: the conviction overlay

This section folds in the side-chat architecture discussion and connects it to everything above. It is the answer to "why build player and team pages at all."

### 6.1 The two engines, restated in one paragraph

The app's rank order is arithmetic, not opinion: Sleeper's raw stat projections (external input 1) x this league's exact scoring -> VOR against replacement levels that fall out of the lineup structure -> tiers from gaps in the VOR curve, with a COIN FLIP label when two players sit within 8 VOR. Availability is separate: Sleeper ADP (external input 2) as the market's center of gravity, corrected by the league's own measured pick-error distribution (2,039 picks, 2013-2025; sd tight early at roughly 3.7, loosest near pick 100 at roughly 27), which survived a leave-one-season-out backtest against two rival models (12/13 seasons, p=0.0034) and is guarded by tests. The verdict multiplies them: wait only when a within-one-tier alternative is at least 60 percent likely to survive to your next pick.

### 6.2 The trading-desk principle

**Keep the market's numbers for predicting the market. Apply conviction to value, never to availability.** ADP is the price. A bullish call is a private valuation. Edge lives in the gap: if you are bullish on a player the market prices in round 7, the survival model - which runs on their behavior, not your opinion - says whether he lasts to your pick. If he does, you wait, bank the round, and get him anyway. This is strengthened, not weakened, by the fact that leaguemates draft off consensus.

One correction the side chat already made, preserved here for the record: leaguemate tendencies are NOT in the probabilities and must not be. That was tested and it made forecasts worse. Survival runs on market ADP plus measured league pick error. Nothing in this research changes that.

### 6.3 The overlay mechanism (the clean way to be bullish)

The wrong way is editing projections - it silently poisons every downstream number. The right way is a first-class overlay you own, shown beside the math, never replacing it:

| my_board.csv column | Example |
|---|---|
| player | Cam Skattebo |
| call | BULL |
| move | +1 tier |
| reason | new OC ran RB-heavy at prior stop; O-line added two starters |
| source | the analyst piece or film breakdown that convinced you |

App behavior around the overlay, exactly as scoped in the side chat: show both numbers on every card (model VOR and your tilt, labeled YOUR CALL); break coin flips toward your bulls - the one place conviction should decide, because the model already admits it cannot separate the players; re-sort within tiers by preference but never across tiers; and price every target through survival ("your bull: X percent he lasts to pick 42" - illustrative framing, the real number comes from the fitted model at draft time).

### 6.4 What this research contributes to the overlay

**The player and team pages are the evidence desk for the reason column.** Every factor named in the side chat - coaching scheme fit, QB-to-receiver fit, O-line changes, target competition, free-agency and draft-capital effects - maps to a verified instrument in sections 4 and 5:

| Conviction factor | The page surface that informs it | Verified source |
|---|---|---|
| New play-caller runs more or passes more | Team page: play-caller card with career PROE by stop | nflverse pbp xpass/pass_oe (VERIFIED-LIVE) |
| Vacated targets and carries | Team page: vacated-opportunity block from roster diffs | stats_player + rosters (VERIFIED-LIVE) |
| O-line help or harm | Team page: yards-before-contact and pressure context; ESPN win-rate articles linked as attributed sources | pfr_advstats (VERIFIED-LIVE) |
| Target competition | Depth chart page: ranked usage shares at each position group | depth_charts + stats_player (VERIFIED-LIVE) |
| Draft capital and athletic profile | Player page: prospect block | draft_picks, combine (VERIFIED-LIVE) |
| Market disagreement | Player page: model VOR rank vs ADP with the gap highlighted | Sleeper ADP (session probe) + FFC ADP (VERIFIED-LIVE) |

**The falsifiability loop is mandatory.** Every call gets scored after the season: did bulls beat their ADP-implied finish, did bears trail it. This is quality rule 6 applied to opinion - a call that cannot survive being scored does not earn weight next year. Eight beautiful narratives died by exactly this discipline; analyst narratives are the most seductive kind. And the honest caveat stands: Sleeper's projections already price most offseason news, so the overlay records **disagreement with the market**, and disagreement is only edge if it is right. The scoring loop is what separates edge from vibes.

**Guardrail preserved:** wait-or-reach verdicts stay on the audited math. The overlay tilts which name you take when the math says the choice is free.

---

## 7. Verified data-source register

Everything below was probed from this session on 2026-08-13 unless marked otherwise.

| # | Source | Endpoint / asset | Result | Use |
|---|---|---|---|---|
| 1 | Sleeper state | api.sleeper.app/v1/state/nfl | 200; season 2026, season_type "pre", week 1 | Season/phase detection (already in engine) |
| 2 | Sleeper trending | /v1/players/nfl/trending/add | 200; live counts | Add/drop social proof (attribution requested by Sleeper docs) |
| 3 | Sleeper projections + ADP | api.sleeper.app/projections/nfl/2026?season_type=regular&position[]=... | 200; per-player season projections incl. adp_ppr, adp_half_ppr, pts_ppr and granular stat lines | **UNDOCUMENTED.** The engine's two external inputs ride this. Keep the fallback below |
| 4 | Sleeper CORS | Origin header probe | access-control-allow-origin: * | Live browser polling stays viable on GitHub Pages (draft_room already proves this in production) |
| 5 | FFC ADP | fantasyfootballcalculator.com/api/v1/adp/ppr?teams=12&year=2026 | 200; 6,160 real mock drafts in the Aug 6-13 window; stdev, high/low, bye per player | **DOCUMENTED and free incl. commercial with attribution.** The natural ADP fallback and cross-check. No CORS header -> build-time fetch only |
| 6 | nflverse depth charts | releases/download/depth_charts/depth_charts_2026.parquet | 200; 429,851 rows; latest dt 2026-08-13T08:15:32Z (same-day fresh); daily 7AM UTC | Depth chart pages (ESPN-derived; espn_id + gsis_id per row) |
| 7 | nflverse player stats | stats_player/stats_player_week_2025.parquet | 200; 19,421 rows x 145 cols | Usage and efficiency families. NOTE: old player_stats release naming is dead (404) - use stats_player |
| 8 | nflverse pbp | play_by_play_2025.parquet | 200; 48,771 plays x 372 cols; epa, cpoe, air_yards, xpass, pass_oe confirmed | PROE, red zone, pace, game script |
| 9 | ESPN depth charts | sports.core.api.espn.com/v2/.../seasons/2026/teams/{id}/depthcharts | 200; live 2026 | UNDOCUMENTED. Redundant with #6 (nflverse mirrors ESPN) - prefer #6 |
| 10 | PlayerProfiler API | api.playerprofiler.com/v1/players, /v1/player/{id} | 200; 5,190 players; ~250 fields/season | Open but undocumented AND ToS-prohibited for scraping. Do not build on it (section 4.3) |
| 11 | NGS mirror | nextgen_stats/ngs_{passing,receiving,rushing}.parquet | 200; 2016-2025 | Tracking family. Direct nextgenstats.nfl.com API is unofficial and fragile - use the mirror |
| 12 | ffopportunity | ep_weekly_2025.parquet | 200; 159 cols | Expected fantasy points |
| 13 | ftn_charting | ftn_charting_2025.parquet | 200; 47,316 plays x 29 cols; CC-BY-SA, 48h charting lag | Charting flags family |
| 14 | pfr_advstats, snap_counts, combine, draft_picks, rosters, players, schedules, injuries | release assets | all 200 | Remaining families |

**Risk register (build around these):**

| Risk | Detail | Mitigation |
|---|---|---|
| Route data in-season | participation file lands post-season only since 2023 (FTN-sourced). No free in-season routes/YPRR in 2026 | Show 2025 route metrics labeled as prior-season; do not fake in-season YPRR |
| nflverse injuries continuity | nflreadr docs say the source died after 2024, yet a complete 2025 file exists (6,068 rows, weeks 1-22 - conflict flagged). 2026 in-season reliability unknown | Treat injuries as at-risk; degrade to "no data" gracefully |
| Undocumented endpoints | Sleeper projections/ADP (#3), ESPN (#9) can change without notice | FFC ADP as documented fallback; nflverse mirrors for ESPN-derived data; staleness badges everywhere |
| Sleeper licensing note | docs.sleeper.com says commercial use requires a licensing discussion | This is a private single-league tool, not a commercial product; note kept for the record |
| K/DEF projections | Feed omits 21 scoring keys this league pays - projections are floors | Existing engine note stands; label on any K/DEF surface |

---

## 8. The three prior repos, audited honestly

All four repos cloned and inspected this session. Verdicts are about what is worth carrying into THIS app, not about the projects' own merits.

| Repo | What it actually is | Carry forward | Leave behind |
|---|---|---|---|
| **Eagle-Draft-Hub** (Apr 2026) | Replit-built full-stack Next.js hub for the real 2026 NFL Draft, Eagles-centric. 250 files; the product spec (replit.md) is detailed and disciplined | **The spec, not the code.** Its information architecture (Home / Live / Big Board / Prospects / Compare / Depth Chart / Capital) maps almost one-to-one onto this expansion. Its rules are house rules already: source provenance visible on every record, no fake data in production UI, premium-executive visual language (neutral palette, one accent, big type, restrained motion), command palette, drawer-based player quick views. Its data-reconciliation pipeline concept (source precedence, name normalization, fuzzy matching with review) is the right mental model for joining Sleeper/nflverse/FFC IDs. Its ESPN endpoint inventory overlaps what was verified here | The Next.js/Replit-coupled implementation, shadcn boilerplate, Replit SQL dependency, and 236MB of attached assets. Porting code into a static single-file app is negative value |
| **rork-tampr-pro** (Mar 2026) | TAMPR Pro: NFL front-office intelligence app spec v5 (salary cap, transactions, 90-reporter feed), Hono/tRPC backend + SwiftUI client | The **Data Source Bar** pattern: every surface shows its sources, refresh time, and citations - this is quality rule 1 rendered as UI. The 32-team identity system (logos/colors). The palette continuity: TAMPR's dark-navy ground with taupe-gold and teal accents (iOS Theme.swift) is the same family as ff-hub.html's locked tokens (#0b1120 ground, #C7A26B gold, #2EC4A8 teal) - the brand system already exists across your projects, with TAMPR's exact hexes since superseded by the locked set | The scrapers (scraper-feed, scraper-cap, scraper-transactions) - scraping-based feeds fail the source-quality bar here. The chatbot. The native iOS layer |
| **sports-ml-engine** (Nov 2025) | README + LICENSE + .gitignore. Three files. An MLOps pipeline description (MLflow, FastAPI, drift monitoring) with zero implementation | Nothing concrete. The README's discipline list (validate schemas, track experiments, monitor drift) is already practiced better in the fantasy repo's guard tests | Everything else - there is nothing to port. If an ML engine ever matters here, it starts from the fantasy repo's tested harness, not from this scaffold |
| **yeahthatfantasyleague** (current) | The live app: engine_2026.py + draft_room.html + ff-hub.html findings page + plugin skill + guard tests + the full verified dataset | Baseline. Note for the expansion research: **ff-hub.html already exists as a findings page on the brand tokens** - a home page has a seed, and out/app_data.json + engine_2026.json show the JSON-payload pattern the expansion would extend | - |

---

## 9. Architecture recommendation

**Recommendation: stay static. GitHub Pages + a GitHub Actions scheduled build. Add nothing server-side until a keyed or CORS-blocked source becomes load-bearing.**

| Consideration | Static (Pages + Actions cron) | Hosted backend (Vercel or similar) |
|---|---|---|
| Fits current stack | Yes - engine already runs as a local build step producing out/*.json + HTML; Actions just schedules it | Migration: second deploy surface, new mental model |
| Live draft polling | Proven in production: draft_room polls Sleeper browser-side at 10s; Sleeper sends access-control-allow-origin: * (VERIFIED-LIVE) | No advantage - polling is already client-side |
| Daily data (stats, depth charts, ADP) | Actions cron (daily in-season, manual dispatch draft morning) pulls Sleeper + nflverse parquet + FFC ADP with Python (pyarrow), writes JSON shards, commits, Pages redeploys | Same fetches, plus a server to keep alive |
| CORS-blocked sources (FFC) | Handled at build time - irrelevant in the browser | Proxy works but is unnecessary for daily-cadence data |
| Secrets | None needed - every verified source is keyless | Needed the moment FantasyPros HOF or similar enters |
| Cost | $0 | Small but nonzero, plus maintenance and a second failure surface |
| Failure mode | Stale data with a visible as-of timestamp | Downtime |
| Honest constraint | Data is as fresh as the last build; anything intraday must be Sleeper (CORS-open) or wait for the next cron | Real-time everything, which nothing in scope needs |

**Trigger conditions for revisiting:** (1) a paid keyed source is adopted (FantasyPros API, SportsDataIO - see the Aug 11 stack research doc, which reached the same local-first conclusion for the MCP layer); (2) a live in-season surface genuinely needs a CORS-blocked source intraday; (3) write behavior appears (none is planned; Sleeper is read-only anyway). The response is a thin proxy for that one source, not a platform migration.

**Sequencing note (per Anthony's direction):** draft-first. The surfaces this research supports - home, players, teams, depth charts - are draft-prep surfaces on daily cadence. In-season surfaces (start-sit context, live scoring) stay a later phase, consistent with the deliberate decision to leave the RB start-sit tool unbuilt until after the draft.

---

## 10. Design research: the pattern library for this app

Research-level findings only (the design spec is deferred by choice). Patterns filtered to what fits a single-league insight-and-decision product - league hosting patterns (chat, matchups) excluded.

| # | Pattern | Origin | Why it earns a place here |
|---|---|---|---|
| 1 | Draft board grid as the primary draft view, color-coded, castable to a TV | Sleeper; ESPN 2024 | The snake board wall already exists in Mode 2; research confirms it is the industry-converged answer |
| 2 | One huge answer, details beneath | Your own Mode 2 design; echoed by every "single recommendation" tool (DraftEdge) | On the clock, hierarchy is the feature. League rule 3.2 makes the 2-minute clock a hard constraint |
| 3 | Player card as action hub - any player name anywhere opens the same card | Sleeper; ESPN 2025 | Kills dead-end pages; the card is where model VOR, YOUR CALL, and survival percent live together |
| 4 | Tap-any-number provenance | Sleeper's scoring ledger; TAMPR's source bar | Quality rule 1 as UI: every number opens its source, as-of time, and computation note |
| 5 | Value framing, never bare ranks | Yahoo VOLS; the app's own VOR | Recommendations state value over replacement and cost-of-waiting, not "he's ranked 12th" |
| 6 | Floor-ceiling bands instead of point estimates | Yahoo Min/Max; RotoViz Range of Outcomes | Honest constraint: the Sleeper feed carries no variance measure, so bands require a source that has one - display only what exists |
| 7 | Rankings-as-object with hard guardrails | Underdog (drag-drop rankings + position caps feeding autopilot) | The my_board.csv overlay is exactly this pattern, with the added scoring loop |
| 8 | Depth chart as ranked-value grid, not official-listing order | FantasyPros depth charts; ESPN player cards embed them | Depth chart pages should order by usage share and VOR, with official slot shown as metadata |
| 9 | Trending adds/drops as social proof | Sleeper trending API (attribution requested) | Free, live, CORS-open, one call |
| 10 | Action-item home - state rendered as a to-do list | ESPN 2025 roster dashboard | Home page answers "what needs my attention before Sept 8" (draft countdown, missing overlay calls, stale data warnings) |
| 11 | Instant post-draft grades as a shareable moment | ESPN 2024 | Post-draft: score the room against the model's board; league banter fuel with real math behind it |
| 12 | Design for the repeat user | Sleeper's stated redesign lesson | Optimize screen-to-screen flow for the person who lives in the app, not the first-run tour |
| 13 | Restrained palette keeping dense grids readable | Underdog's 3-color system; the existing token family | Navy surfaces, one teal accent, gold for thin rules only, semantic go/stop/warn - already the house system across draft_room, ff-hub, and TAMPR |
| 14 | Anti-patterns to refuse | ESPN pre-2025 case studies; MFL | Promo-cluttered home, buried primary actions, fake-affordance menus; and MFL's lesson - capability without information design loses |

**Brand continuity finding:** three of your artifacts already share one visual family - draft_room.html (#0A0E1A ground, semantic go/stop/warn/info), ff-hub.html on the locked tokens (#0b1120 ground, teal #2EC4A8, gold #C7A26B), and TAMPR's dark-navy/taupe-gold/teal theme (its exact hexes are superseded pre-decision values, so they are cited by file - ios Theme.swift - not reprinted here). The Eagle-Draft-Hub spec adds the typographic rules (big type, fluid clamp sizes, mono for numbers). Consolidating on one token set is a build-phase decision, but the research finding is that the system already exists - nothing new needs inventing.

---

## 11. What this research does not change

| Guard | Status after this research |
|---|---|
| No draft-day roadmap. Eight hypotheses tested, all null (waiting on QB p=0.252, avoiding early QB p=0.266, RB-heavy, WR-heavy, slot, construction, drafted share, FAAB p=0.197). No champion pattern-matching in any recommendation | Unchanged. Nothing found in any tool or platform contradicts it, and no surface researched here recommends strategy from champion patterns |
| Consensus #1 board player: drafted by the eventual champion 0 times in 13 years | Unchanged; a display-worthy fact for the home page, never a strategy input |
| Lineup efficiency is a lead, not a finding: champions 89.75% vs field 88.44%, permutation p=0.078, n=13. Discipline (fewer swaps) recovers roughly 10 pts/season; 65% of lost RB points were hindsight spikes | Unchanged. In-season surfaces stay a later phase by design |
| Opponent tendencies: real (r=+0.813, p<0.00002) and banned from probabilities (48,399-prediction backtest, p=0.99). Display and simulator only, SIM-badged | Unchanged, and extended: NFL team situation intel obeys the same law - display and overlay-evidence only, probability placement never, unless a backtest earns it |
| Survival model: league-fitted 12-bin pick-error curve, beat both rivals out of sample (12/13 seasons, p=0.0034), guarded by 22 tests + 42-anchor parity suite | Unchanged. The undocumented-endpoint risk on its ADP input now has a documented fallback (FFC) on the record |
| K/DEF projections are floors (feed omits 21 scoring keys) | Unchanged; label required on any K/DEF surface |
| Yahoo-era (2013-2024) point totals are bonus-exclusive, understated ~5%, ratios unaffected | Noted wherever era totals appear |

---

## 12. Claims register for sign-off

The load-bearing NEW claims this document introduces, for Anthony's verification:

| # | Claim | Status | Where |
|---|---|---|---|
| 1 | Sleeper API state/trending/projections endpoints live for 2026; projections endpoint is undocumented and carries ADP + granular stat projections | Session probes 2026-08-13 | Sec 7 #1-3 |
| 2 | Sleeper API sends access-control-allow-origin: * ; FFC ADP API sends no CORS header | Session probes (curl with Origin header) | Sec 7 #4-5 |
| 3 | FFC ADP is documented, free incl. commercial with attribution, daily-updated; 6,160 drafts in the Aug 6-13 2026 PPR window | VERIFIED-LIVE + SOURCED (help page) | Sec 7 #5 |
| 4 | nflverse depth_charts_2026 is same-day fresh (dt 2026-08-13T08:15) with 429,851 rows; stats_player replaced the dead player_stats naming; pbp 2025 carries xpass/pass_oe | VERIFIED-LIVE (parquet reads) | Sec 7 #6-8 |
| 5 | Route participation has no free in-season path for 2026 (post-season delivery since 2023, FTN-sourced) | SOURCED (nflreadr docs quote) | Sec 4.2, 7 |
| 6 | nflverse injuries: docs say source died after 2024, yet a complete 2025 file exists (6,068 rows) - conflict flagged, 2026 reliability unknown | VERIFIED-LIVE + SOURCED, conflict noted | Sec 7 risk register |
| 7 | PlayerProfiler API is open (5,190 players) and undocumented; their ToU bans scraping/aggregation; Data Analysis package $45/season sells downloads | Session probe + SOURCED (ToU, membership pages) | Sec 4.3 |
| 8 | 17 teams have new primary 2026 play-callers (table), incl. 4 first-time callers | SOURCED (NFL.com, FOX, CBS trackers + team sites, Jan-Feb 2026) | Sec 5.1 |
| 9 | BeerSheets discontinued for 2026 | SOURCED (footballabsurdity.com) | Sec 2 |
| 10 | NFL Fantasy shuts down; ESPN becomes exclusive NFL season-long partner with league import | REPORTED (two independent Aug 2026 outlets) - verify before quoting externally | Sec 2 |
| 11 | Draft tool prices as tabled (FantasyPros, Draft Sharks, 4for4, ETR, PFF, RotoViz, Fantasy Life, DraftEdge, WalterPicks) | SOURCED (official pricing pages / page source / App Store, this session) | Sec 3 |
| 12 | FantasyPros Draft Intel is the only mainstream leaguemate-tendency product; capped at 5 synced years | SOURCED (fantasypros support docs) | Sec 1, 3 |
| 13 | 4for4's O-line composite correlates 0.462 with team fantasy output; play-action +0.06 EPA/att | REPORTED (4for4 studies, their n) - attributed, not house numbers | Sec 5.2 |
| 14 | Analyst consensus says play-caller tendencies persist; no rigorous public stability coefficient found | REPORTED + explicitly UNVERIFIED for the coefficient | Sec 5.2 |

**Approval gate:** Approve / Request changes. Nothing here ships into the app, the repo docs, or a build plan until Anthony signs off. Suggested next session on approval: the design spec + build order for the insight surfaces (deferred from this session by choice).

---

## 13. Source register (primary)

Platforms: support.sleeper.com (switch, drafts, intro, cross-league, points articles) - sleeper.com/blog (redesign, 2022 features) - docs.sleeper.com - espnpressroom.com (Aug 2025 app rebuild) - espn.com/fantasy (Aug 2024 draft board) - sports.yahoo.com (Aug 2025 Fantasy Plus) - cbssports.com commissioner splash - myfantasyleague.com/features - help.underdogsports.com (rankings/autopilot) - fantrax.com.
Reviews 2025-2026: draftsharks.com/kb/best-fantasy-football-websites (Aug 6 2026) and /kb/best-fantasy-football-app (Aug 10 2026) - lordskunk.com (Jun 2026) - scoutcast.ai (Jul-Aug 2026) - cordcuttersnews.com (Aug 4 2026) - fantasypros.com 2026 platform roundup - dynastyleaguefootball.com (May 2026) - footballguys forum (2025).
Tools: draftwizard.fantasypros.com - support.fantasypros.com (Draft Intel) - fantasypros.com/premium/plans - draftsharks.com/subscribe and /injury-predictor - 4for4.com/plans and /draft-hero - rotoviz.com membership - establishtherun.com/subscribe - pff.com/subscribe - fantasylife.com/pricing - walterpicks.com + App Store listing - fantasy.draftedge.com - footballabsurdity.com (BeerSheets).
PlayerProfiler: playerprofiler.com/terms/ (glossary) - /terms-of-use/ - /membership-account/membership-levels/ - /data-analysis/ - live player page - api.playerprofiler.com (session probe only).
Data: github.com/nflverse/nflverse-data (releases, CC-BY-4.0) - nflreadr.nflverse.com (reference + update schedule) - ffopportunity.ffverse.com - raw.githubusercontent.com/nflverse/nfldata (games.csv) - docs.sleeper.com - api.sleeper.app (probes) - help.fantasyfootballcalculator.com/article/42-adp-rest-api - sports.core.api.espn.com (probe) - nextgenstats.nfl.com.
2026 coaching: nfl.com coaching tracker - foxsports.com tracker (Feb 20 2026) - cbssports.com OC grades (Feb 23 2026) - acmepackingcompany.com 32-team play-caller rundown - team sites (falcons, ravens, steelers, giants, titans) - espn.com (Monken) - nbcsports.com PFT (Rees).
Methods: establishtherun.com/pass-rate-over-expectation - nfeloapp.com team tendencies - rbsdm.com/stats - 4for4.com play-calling study (Aug 4 2026), O-line study (Jul 3 2026), available targets tracker (Jun 2 2026) - ftnfantasy.com vacated opportunities (Mar 5 2026) - fantasylife.com PROE explainer.
Prior internal work: Anthony_2026_Claude_Fantasy_Football_Stack_Research.md (Aug 11 2026, project doc) - docs/VISION.md, HANDOFF.md, DRAFT_ROOM_BUILD_ORDER.md, AUDIT_3B and AUDIT_SURVIVAL (repo) - the side-chat architecture discussion (Aug 13 2026, provided by Anthony).

*AI drafts, Anthony verifies. Prepared 2026-08-13 in the Cowork research session; claims register above is the sign-off surface.*
