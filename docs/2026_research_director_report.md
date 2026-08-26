# YeahThatFantasyLeague 2026: Research Director's Championship Report

## TL;DR
- **Do NOT migrate off GitHub Pages before the draft.** Your static batch-pipeline architecture fits GitHub Pages perfectly; a Supabase+Vercel move two weeks out is unnecessary risk. Revisit post-draft only if you want runtime queries, persisted state, or a league-facing multi-user app. **Your working verdict is validated.**
- **Anthony's preseason-RB1 claim is essentially correct, with one correction:** since 2016, exactly two preseason ADP RB1s also finished as the actual PPR RB1 - David Johnson (2016, 407.8 PPR points) and Christian McCaffrey (2023, 391.3 PPR points), **NOT 2019**. That is a 20% conversion rate (2 of 10). The consensus 2026 RB1 is Jahmyr Gibbs with Bijan Robinson a close second, so history says drafting "the" RB1 to repeat is a coin-flip-at-best - but the elite RB tier still wins leagues.
- **Optimize for ceiling in this median-game format.** The two-results-per-week structure rewards raw weekly scoring over matchup luck, so build the highest-ceiling roster you can and treat every pick as a points-accumulation bet, not a floor-protection bet.

## Key Findings (Top 10 Actionable Takeaways)
1. Take an elite RB at 1.01-1.05 regardless of slot; the RB1-overall was on ~25.7% of championship teams last year vs an ~8% baseline in a 12-team league.
2. The consensus preseason RB1 converts to actual RB1 only ~20% of the time, so do not pay a full tier premium for "the" RB1 over RB2-RB5.
3. Early WR is not as much "safer" as folklore claims; early RB has a higher top-12 hit rate in this sample (RB1 58.3% vs WR1 44.0%), though the gap is not statistically significant.
4. Wait on QB; late-round rushing QB is evidence-supported.
5. Elite TE (Bowers/McBride) is a real edge in full PPR; if you miss the top pair, wait and take two darts late.
6. Year-2 WR breakouts and pass-catching/ambiguous-backfield RBs are the highest-ROI mid-round archetypes.
7. Your median-game format raises the value of raw weekly ceiling; draft boom players.
8. Fade Christian McCaffrey relative to Gibbs/Bijan: he led the NFL with 450 touches in 2025, and in the last 13 years only one 400+ touch RB was top-5 the next year.
9. Encode hit-rate base rates and confidence intervals into your app's big board.
10. Complete the 2014-2024 Yahoo history via authorized yfpy OAuth, not scraping.

## Details

### Workstream 1: App and Repo Review

The live app at `/out/home.html` ("YTFL Hub 2026") is a well-conceived static hub: a draft countdown (draft night 2026-09-08), a Sleeper draft link, a Big Board ("model rank, evidence beside it"), Players ("value, usage, provenance"), Teams, and a Findings page ("13 seasons, the nulls"). The engine (`src/engine_2026.py`) pre-computes static HTML into `/out/`, regenerated each morning by running the Python engine, committing, and pushing. A daily shard cron runs at 12:00 UTC after the nflverse 7AM depth-chart refresh, with a data-staleness board (fresh under 36h, aging under 7 days, stale beyond). It polls Sleeper's public read-only API client-side and shows a live trending-adds feed.

**What it does exceptionally well - intellectual honesty.** The home page states the consensus No. 1 board player has been drafted by the eventual champion **0 times in 13 seasons**, and correctly labels this "p=0.323 under random - striking, not significant, descriptive colour only." The conviction overlay is pre-registered ("a grade means nothing before roughly 25 calls") and used only as a coin-flip tie-break. Trending adds are labeled "market attention, never a projection." This statistical humility, clean provenance tracking, and honest null-result reporting are the app's biggest strengths and are rare in fantasy tools.

**What is quantitatively weak or missing:**
- Point estimates are presented without sample sizes, confidence intervals, or base rates on most metrics.
- No positional hit-rate / bust-rate tables by ADP band.
- No explicit archetype tags.
- No value-over-replacement (VOR/VORP) or tier-break logic surfaced for live snake-draft decision support.
- No translation of the league's median-game format into a ceiling-weighted ranking.

**Recommended upgrades (concrete):**
- **Base-rate columns:** for every ranked player, show the historical top-12/top-24 hit rate for that ADP band and position, with n and a Wilson 95% confidence interval.
- **VOR/tier engine:** compute value over replacement for the exact 12-team/14-round/1-flex roster and draw tier breaks; surface positional-run alerts during the live draft.
- **Archetype tags:** year-2 WR, high-draft-capital rookie RB, pass-catching RB, ambiguous backfield, late-round QB, elite/late TE, post-injury discount - driven by usage thresholds (target share, air yards, routes, carries, red-zone touches).
- **Ceiling model:** because the league awards a median result, weight projected weekly variance positively rather than penalizing it.
- **Live "best pick now" recommender** combining VOR, tier scarcity, positional need, and bye/stack logic.

### The GitHub Pages vs Supabase+Vercel Verdict

**Verdict: your working verdict is CORRECT. Stay on GitHub Pages through the draft.** The current architecture is a static batch pipeline (pre-computed HTML in `/out/`) plus client-side polling of Sleeper's public read-only API (base URL `api.sleeper.app/v1`, no auth token required, documented rate limit: stay under 1000 calls/minute). GitHub Pages is an ideal host for exactly that: it serves static assets globally for free with no server that can fail mid-draft. Migrating two weeks before a September 8 draft introduces avoidable risk (env config, CORS, build pipelines, auth) for zero functional gain, since Sleeper's read-only API is already callable directly from the browser and needs no secrets.

**When Supabase+Vercel becomes right (post-draft):** only if you want (a) **persisted state** (writing draft results, the 2014-2024 history, user notes), (b) **runtime queries** (server-side filtering/aggregation the static build cannot precompute), or (c) a **multi-user league-facing app** (auth, per-user boards, live collaboration). **Timing recommendation:** after the 2026 draft, in the offseason, migrate incrementally - keep GitHub as the repo, add Supabase as the datastore for the Yahoo+Sleeper history, and move the frontend to Vercel only when you actually need dynamic server-side rendering. Do not do this in-season.

### Completing the 2014-2024 Yahoo History via yfpy (authorized OAuth - the sanctioned path)

His fork of `uberfastman/yfpy` is the correct, ToS-compliant tool. Do not scrape. Concrete steps:
1. Create a Yahoo Developer app at `developer.yahoo.com/apps/create`: Application Type = **Installed Application**, Redirect URI = `https://localhost:8080`, API Permissions = **Fantasy Sports (Read)**. This yields a **Client ID** and **Client Secret**.
2. Because the 2014-2024 leagues are private historical leagues, read-only public access is not sufficient - you must complete the **OAuth2 three-legged handshake** once with a Yahoo account that has access to the league history. Put `YAHOO_CONSUMER_KEY` and `YAHOO_CONSUMER_SECRET` in a `.env` file (copy `.env.template`), or pass them programmatically to `YahooFantasySportsQuery`.
3. Instantiate `YahooFantasySportsQuery(league_id, game_code="nfl", game_id=<per-season game id>, ...)`. The first run opens a browser to allow access; copy the verification code back into the prompt. Set `save_token_data_to_env_file=True` with an `env_file_location` so the refresh token persists and you never re-verify.
4. Iterate over seasons: each NFL season has its own Yahoo `game_id` and `league_id`. Yahoo archives public leagues at `archive.fantasysports.yahoo.com/nfl/<year>/<league_id>`. Pull, per season: **draft results, transactions, standings, and playoff results.**
5. Persist the parsed output as JSON/CSV in the repo (or later Supabase), keyed by season, to complete the champions ledger and power historical analytics.

### Workstream 2: Historical Positional Rank-Conversion Analysis (PPR, 2016-2025)

**Verifying Anthony's RB1 claim (the analytical centerpiece).** The claim: "since 2016, only two preseason RB1s finished as the season RB1: David Johnson and Christian McCaffrey." **This is essentially correct, with one important correction: the McCaffrey conversion was 2023, not 2019.**

| Year | Preseason ADP RB1 | Actual PPR RB1 | Conversion? |
|------|-------------------|----------------|-------------|
| 2016 | David Johnson | David Johnson (407.8 PPR points) | **YES** |
| 2017 | David Johnson | Todd Gurley | No |
| 2018 | Todd Gurley | Saquon Barkley (383.8 PPR) | No |
| 2019 | Saquon Barkley | Christian McCaffrey (471.2) | No |
| 2020 | Christian McCaffrey | Alvin Kamara (377.8) | No |
| 2021 | Christian McCaffrey | Jonathan Taylor | No |
| 2022 | Jonathan Taylor | Austin Ekeler | No |
| 2023 | Christian McCaffrey | Christian McCaffrey (391.3 PPR points) | **YES** |
| 2024 | Christian McCaffrey | Saquon Barkley | No |
| 2025 | Bijan Robinson | Christian McCaffrey | No |

**Corrected count: 2 conversions in 10 seasons = 20% base rate.** The two players are David Johnson (2016, verified 407.8 PPR points via StatMuse; ESPN noted his 393 points were 28 more than anyone else) and Christian McCaffrey (2023, verified 391.3 PPR points via StatMuse). Two caveats to flag for Anthony:
1. **In 2019 McCaffrey WAS the actual RB1 (471.2 points) but was drafted as RB2 behind Saquon Barkley**, so it is not a conversion - Anthony likely conflated McCaffrey's monster 2019 with a "preseason RB1" label he did not hold that year.
2. **The 2016 designation is the one genuinely contestable cell:** FantasyFootballCalculator's late-preseason PPR ADP had David Johnson as the first RB off the board, but ESPN's 2016 ranking had Adrian Peterson as RB1. Using the standard citable PPR ADP consensus (FFC), the conversion holds.

**Positional top-12 hit rates (RB vs WR), 2016-2025 (n=84 per position, 168 total, per The IDP Center):** RBs drafted top-12 at the position finished top-12 at **58.3%**; WRs drafted top-12 finished top-12 at **44.0%** - a ~14 percentage-point RB edge, meaning a top-12 RB has been ~32% more likely to return a top-12 finish than a similarly drafted WR. **However, the Z-test for two proportions did NOT reach conventional significance**, so treat this as suggestive, not proven. In 2025 specifically, 9 of 12 top-drafted RBs finished as RB1s (a durability-driven outlier - top-12 RBs averaged 16.08 games) vs only 4 of 12 top-drafted WRs (33%).

**RB round-band conversion (illustrative, 2023 representative year):** RB1s (picks 1-12) finished top-12 at 5/12 (42%); RB2s (13-24) top-24 at 5/12; RB3s (25-36) top-36 at 7/12; RB4s (37-48) top-48 at 8/12. Clear pattern: **the later the band, the higher the rate of beating expectation**, because expectation is lower and downside is capped.

**The RB1 "curse" the following year (Full PPR PPG, per Yahoo Sports):** 2018 Gurley 26.6 to 14.6 (-45%); 2020 Kamara 25.2 to 18.1 (-28%); 2021 Taylor 22.0 to 13.3 (-40%); 2022 Ekeler 21.9 to 13.2 (-40%); 2023 McCaffrey injured; 2024 Barkley 22.2 to 14.6 (-34%). The prior-year RB1 has disappointed in each of the past seven seasons except Kamara. This supports fading last year's RB1 - **already partly priced, since 2025 RB1 McCaffrey is going at RB3.**

**Value of the elite RB (per Yahoo Sports):** RB1 PPG since 2016 = 24.9 vs RB12 = 15.1, a **+9.7 gap.** Last year the RB1 (McCaffrey) was on ~25.7% of championship teams vs an ~8% baseline; Bijan Robinson was on ~27.4%. Elite RB upside is the single biggest league-winning lever. Historically, overall RB1s are almost never found after Round 2 (only three since 2005, 14%, came from outside the top-24).

**WR archetypes that outperform (with numbers, per FantasyPros/Sharp Football):** Since 2022, about one new WR1 per season has come from outside the top-50 WRs in ADP (Puka Nacua, Nico Collins, Jerry Jeudy, Michael Wilson). **13 of the last 21 first-time WR1 finishers (62%) came from the WR18-WR50 ADP range.** 96% of WRs with 140+ targets since 2000 finished top-24; 74% (186/250) finished top-12 - **target volume is the strongest WR predictor.** The profile: rookie WRs being underrated, high-route-volume players, and WRs attached to improved QBs.

**QB strategy (per DraftSharks):** Late-round QB is evidence-supported. Since 2019 the overall QB1 has run for at least 350 yards and 4 rushing TDs every year; top-12 QBs averaged 360 rushing yards and 4.2 rushing TDs over the past five years. Rushing QBs are systematically underpriced. Recent late-round breakouts: Jayden Daniels (2024), plus Stafford/Maye/Lawrence/Goff climbs. **Target a rushing QB in rounds 10-12.**

**TE strategy (per Draft Sharks/ESPN/CBS):** Elite TE is a genuine full-PPR edge. Trey McBride led all TEs at **18.6 PPR PPG in 2025** (126 receptions - an NFL single-season record for a TE - on 169 targets, 1,239 yards, 11 TDs); Bowers was second in PPG. The reception point widens the elite-vs-streamer gap. **Either pay up for Bowers/McBride/Loveland, or punt and take two darts late - do not draft a mid-tier TE.**

### HOLDS WATER vs FOLKLORE

| Belief | Verdict | n / effect / confidence |
|--------|---------|-------------------------|
| The preseason RB1 rarely repeats as actual RB1 | **HOLDS WATER** | 2/10 conversions 2016-2025 (20%); high confidence on count |
| Last year's RB1 declines the next year ("RB1 curse") | **HOLDS WATER** | 6 of last 7 seasons declined; avg drop ~35-45% PPG |
| Early RB is safer than early WR (top-12) | **HOLDS WATER (suggestive)** | RB1 58.3% vs WR1 44.0% over n=84 each; Z-test NOT significant |
| The elite RB1-overall wins leagues | **HOLDS WATER** | RB1 on ~25.7% of 2025 titles vs ~8% baseline; +9.7 PPG over RB12 |
| Late-round rushing QB is a winning strategy | **HOLDS WATER** | QB1 every year since 2019 hit 350+ rush yds and 4+ rush TDs |
| Year-2 / sub-WR50 WR breakouts are findable | **HOLDS WATER** | ~1 WR1/yr from outside top-50 since 2022; 62% of new WR1s from WR18-50 |
| 140+ targets = safe WR | **HOLDS WATER** | 96% top-24, 74% top-12 since 2000 (n=250) |
| Team success is required for a top RB | **FOLKLORE** | only 4 of top-12 2025 RBs made playoffs; avg 8.75 wins |
| You must draft "the" consensus RB1 specifically | **FOLKLORE** | consensus No.1 board player drafted by champion 0/13 seasons in this league |
| Chasing 400+ touch RBs the next year | **FOLKLORE (fade it)** | only 1 of last 13 such RBs was top-5 the next year |

### Workstream 3: 2026 Application and Analog Mapping

**Current late-August 2026 consensus (PPR).** Jahmyr Gibbs is the consensus No. 1 overall pick by ADP per Mike Clay (ESPN) and NFL Fantasy Edge; ESPN's Field Yates ranks Bijan Robinson RB1 / Gibbs RB2. FantasyPros frames Bijan Robinson, Jahmyr Gibbs, and Ja'Marr Chase as all defensible No. 1 overall picks and the top three by ADP. Christian McCaffrey is RB3 (~1.05). Top WRs: Ja'Marr Chase, Puka Nacua, Jaxon Smith-Njigba. Approximate ADPs: Gibbs ~1.5, Bijan ~2.1, Nacua ~2.5. **Anthony's belief (Gibbs RB1, Bijan in the conversation) is confirmed as the current consensus.**

**The 2026 RB1 debate through the historical lens.** History says the consensus RB1 (Gibbs) converts to actual RB1 only ~20% of the time, and the prior-year RB1 (McCaffrey 2025) usually declines - and McCaffrey specifically led the NFL with 450 touches in 2025, with only one of the last 13 such 400+ touch RBs finishing top-5 the next year (FantasyPros: "Fade CMC in 2026"). But the elite RB tier still wins titles at ~3x baseline. **Implication for 1.01-1.05: take the best RB available; do not agonize over Gibbs vs Bijan vs McCaffrey vs Taylor vs Achane - the tier matters more than the exact name.** Gibbs has the best environment (Lions averaged over 31 RB fantasy PPG in 2025) and inherits David Montgomery's goal-line work (16 five-zone attempts vacated). Bijan has the safest workload (300 to 376 to 390 total-opportunity trend, never missed a game). Both are defensible 1.01s; **prefer Gibbs or Bijan over McCaffrey.**

**2026 player-to-analog mapping (selected; all mappings are INFERENCE):**

| 2026 Player | ADP band | Historical analog | Analog outcome | Implication (INFERENCE) |
|-------------|----------|-------------------|----------------|-------------------------|
| Jahmyr Gibbs | 1.01-1.02 | 2021 Jonathan Taylor (year-2 ascending RB, elite offense) | Converted to RB1 overall | Strong RB1 case; elite environment |
| Bijan Robinson | 1.01-1.03 | 2023-24 CMC (bell-cow pass-catcher, healthy) | Elite when healthy | Safest floor+ceiling combo |
| Christian McCaffrey | RB3/~1.05 | Prior-year RB1 curse + 400+ touch fade | Usually declines; 1/13 top-5 next year | Fade vs Gibbs/Bijan; age-30, 450 touches |
| Omarion Hampton | R2 | 2023 Bijan / 2021 Taylor year-2 breakout | Breakout | New OC Mike McDaniel run scheme boosts ceiling |
| Kenneth Walker III | R2-3 | Ambiguous-usage RB, improving offense | Mixed | Bieniemy-return explosive-play thesis is speculative |
| Jeremiyah Love | R2 | 2025 Ashton Jeanty (rookie RB, weak team, committee) | RB1 but volatile (5 sub-7pt games) | High bust risk: 3-way backfield, weak Cardinals, new HC LaFleur |
| Puka Nacua | Top-4 | Repeat elite WR1 (28.8% target share, 3.80 YPRR) | Elite | Safe WR1; identical 2026 setup |
| Emeka Egbuka | mid | Year-2 WR w/ vacated targets (Mike Evans gone) | TBD | Matches successful archetype |
| Luther Burden III | mid-late | Year-2 WR, new scheme (Ben Johnson), ~150 vacated targets | TBD | Matches successful archetype |

**2026 coaching/scheme context that alters value.** 21 teams are expected to have a new offensive coordinator in 2026 (per The Spun), alongside roughly 10 new head coaches. Key fantasy-relevant moves: **Mike McDaniel to Chargers OC** (boosts Omarion Hampton and the run game); **Klint Kubiak to Raiders HC** (heavy personnel, helps Ashton Jeanty and Brock Bowers); **Kevin Stefanski to Falcons** (historically RB/TE friendly); **Brian Daboll to Titans OC** (Cam Ward sleeper); **Zac Robinson to Buccaneers OC** (McVay tree, Egbuka boost); **Mike LaFleur to Cardinals HC** (Marvin Harrison Jr. slated for the "Davante Adams role"); **Joe Brady stays as Bills HC** (James Cook stable). Arizona's LaFleur hire plus a crowded, well-paid backfield (Conner, Allgeier, Love) makes **Jeremiyah Love a notable early-round bust candidate.**

**Archetype flags for 2026:**
- **SUCCESSFUL archetypes (target):** Gibbs/Bijan (elite bell-cow RB), Hampton (year-2 RB + new run scheme), year-2/sub-WR50 WR breakouts (Egbuka, Burden), rushing QBs late, Bowers/McBride (elite TE), 140+ target WRs.
- **FAILING archetypes (fade):** the prior-year RB1 at a premium (mitigated since CMC is RB3), 400+ touch RBs the next year (McCaffrey), ambiguous multi-back committees at a high price (Love), mid-tier TEs, early non-rushing QBs.

## Recommendations (staged, slot-conditional)

**Universal.** In this 12-team full-PPR median-game league, optimize for ceiling and title probability, not floor. Because you get two results per week (H2H plus league-median, pending confirmation - see Caveats), raw weekly points matter more than schedule luck, so draft boom players and accumulate scoring.

**Slot-conditional draft strategy (slot not yet drawn; Sleeper draft id 1389378429505241089):**
- **Early (picks 1-4):** Take the best elite RB (Gibbs, Bijan, or McCaffrey/Taylor). At 1.01-1.02 take **Gibbs or Bijan**. This locks the single biggest league-winning asset, then pivot to elite WR or Bowers on the turn.
- **Middle (picks 5-8):** The elite RB tier will likely be gone by 5-6; take a top-5 WR (Chase/Nacua/JSN) or a falling elite RB. Consider Bowers/McBride on the 2-3 turn. Build a WR-heavy spine and attack RB value in rounds 3-6 (Hampton, Walker).
- **Late (picks 9-12):** With ~22 picks between turns, this is "get your guy" territory. Consider elite-RB + elite-WR back-to-back at the 1-2 turn, or elite WR + Bowers. Prioritize the highest-ceiling players; ADP precision matters less this deep.

**Rounds 3-6 targets:** year-2 WR breakouts, pass-catching RBs, ambiguous-backfield RBs with paths to volume, and Bowers/McBride if you punted TE.
**Rounds 7-11:** rushing QB (Kyler Murray-type upside), high-ceiling sub-WR50 WR darts, handcuffs to your elite RB.
**Rounds 12-14:** league-winning lottery tickets (rookie RBs in ambiguous backfields, deep WRs attached to improved QBs); take K and DEF last.

**In-season.** Use FAAB ($100) with discipline - hoard for the in-season breakout RB (the Javonte Williams / Travis Etienne type), which is where titles are won. Trade deadline is week 11; buy ceiling before it. Six-team playoffs start week 15.

**Benchmark to beat: Dante Cambria** (3 titles, beat you in the 2025 final despite you outscoring him on the season). The median-game format is your ally - it rewards the season-long scoring you already demonstrated.

**Thresholds that change the plan:** If your slot draws 1-2, strongly prefer Gibbs/Bijan. If McCaffrey's camp "tightness" becomes a real injury, drop him a further tier. If Sleeper ADP shifts an elite RB into your reach, take it. If the median-game structure is confirmed false (pure H2H), re-weight slightly toward consistency over pure ceiling.

## Two-Week Pre-Draft Action Plan (draft expected 2026-09-08)
1. **Days 1-2:** Regenerate the engine (`python3 src/engine_2026.py`, commit, push); confirm provenance is fresh. Lock the current consensus ADP snapshot.
2. **Days 3-4:** Add base-rate and confidence-interval columns to the big board (top-12/top-24 hit rate by ADP band and position, with n and Wilson CI).
3. **Days 5-6:** Add archetype tags and the HOLDS WATER vs FOLKLORE flags to each player card.
4. **Days 7-8:** Build the VOR/tier engine and positional-run alerts for the live draft room.
5. **Days 9-10:** Run 5+ mock drafts from early, middle, and late slots; save the resulting rosters.
6. **Days 11-12:** Finalize three slot-conditional cheat sheets (early/middle/late) and a tier-break board.
7. **Day 13:** Complete the 2014-2024 Yahoo history pull via yfpy OAuth so the champions ledger and historical analytics land in the app.
8. **Draft morning (Day 14):** Regenerate the engine one last time for fresh injuries/ADP, confirm your drawn slot, load the matching cheat sheet.

## How to Encode These Findings in the Draft App (concrete features)
- **Base-rate engine:** per-player top-12/top-24 hit and bust rate by ADP band and position, each with n and a Wilson 95% CI.
- **VOR/tier model:** value over replacement for the exact roster (QB/RB/RB/WR/WR/TE/FLEX/K/DEF/5 bench), with visible tier breaks and scarcity alerts.
- **Ceiling weighting:** a variance-positive projection mode for the median-game format.
- **Archetype tagger:** rules-based tags from usage thresholds (target share, air yards, routes, carries, red-zone touches) mapped to the successful/failing archetype lists.
- **Prior-year-RB1 curse flag** and **400+ touch fade flag.**
- **Live recommender:** best-pick-now combining VOR, tier scarcity, need, bye/stack logic, and the trending-adds feed.
- **Slot-conditional boards:** three cheat sheets (early/middle/late) generated from the same engine.
- **Historical module:** yfpy-pulled 2014-2024 Yahoo data plus 2025 Sleeper, powering champion/rivalry context (Cambria benchmark).

## Caveats
- **Median-game format is "likely but needs confirmation."** The 28-games-over-14-weeks pattern is consistent with H2H-plus-median, but confirm in Sleeper's league settings before committing fully to the ceiling-over-floor weighting.
- **2026 data is a moving target.** ADP, injuries (e.g., McCaffrey "tightness"), and depth charts shift daily through early September; regenerate the engine before drafting. Player-movement effects (A.J. Brown to Patriots, George Pickens to Cowboys, DK Metcalf) were noted in sources but not fully verified in this pass - confirm depth-chart impacts before finalizing.
- **The RB-over-WR top-12 edge is suggestive, not statistically significant** (Z-test did not reach significance at n=84 each).
- **The 2016 preseason-RB1 designation is contestable** (FantasyFootballCalculator = David Johnson; ESPN = Adrian Peterson). Anthony's claim holds under the standard PPR ADP consensus.
- **All 2026 analog mappings are explicitly labeled INFERENCE** - they describe historical comparables, not guarantees.
- **Round-band conversion percentages** are illustrated with a representative year (2023) rather than a full 2016-2025 aggregate, which the app should compute directly from the assembled yfpy/Sleeper data.
- **The 2024-labeled Sleeper league is an empty trial shell and must be ignored**, per league context.