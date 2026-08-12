# Draft Room v2 - Master Build Order

**For the Claude Code Web session. Execute top to bottom. All git work is yours: branch, commit, PR, merge on green. Anthony merges and pushes nothing. Report at each gate.**

Draft is 2026-09-08. This order was assembled from three research streams: a feature inventory of FantasyPros Draft Wizard, Draft Sharks War Room, WalterPicks, PlayerProfiler, RotoBaller, DraftKick, and Footballguys Draft Dominator; a design pass for broadcast-grade live sports UI; and a gap audit of this repo mapping every candidate feature to the exact data source that powers it. Their data is paid and untouchable. Their feature concepts, rebuilt on our verified data, are the target - and one feature none of them have (opponents who are the actual league mates, modelled from 13 seasons) is the edge.

## THE IRON RULES - read before any code

1. **No number appears anywhere that cannot be computed from this repo's verified data or the free Sleeper feed.** No invented stats, no fabricated variance, no scraped paid content.
2. **No champion mimicry.** Eight draft-day hypotheses are null. Nothing in the UI implies champions share a pattern.
3. **Tendency lifts never enter a displayed availability probability.** Backtested: fold-in made forecasts worse (p=0.99). Lifts are display chips and simulator sampling only. Guard 6 in tests/test_survival.py enforces this - it must survive every commit.
4. **The calibration benchmark guard stands**: no change to the survival math ships without beating the frozen step baseline out of sample.
5. **All 18 Python guards and the full smoke suite (incl. 42 JS-parity anchors) pass at every merge.** Regenerating with `python3 src/engine_2026.py` must stay the single rebuild command.
6. Hyphens only, no em dashes, no emojis in repo files.

## THE EXPLICIT REJECT LIST - do not build these, the data does not exist

Ceiling/floor or boom/bust probabilities (single point projection only; COIN FLIP is the sanctioned substitute). Expert consensus ranks. Bye-week planner (no reliable bye field in the free feed - do not hardcode a table). Strength of schedule. News blurbs. Advanced usage metrics (target share, snap counts - paid data). Weekly projections (feed is season-total). Auction values. Trade evaluator. ML "+EV" branding - the transparent VOR + survival math IS the differentiator; keep every number explainable.

---

## PHASE 1 - Design system rebuild of out/draft_room.html

The app is functional but reads as a spreadsheet. Rebuild the presentation layer to broadcast grade without touching the math functions (survival, condSurvival, sdFor are frozen; the parity anchors will catch drift).

- **Palette**: dark-first navy. `--bg:#0A0E1A --s1:#111827 --s2:#1A2332 --s3:#0D1424 --line:#243044 --ink:#F2F5FA --ink2:#9BA8BC`, with the existing light-mode fallback kept. Verdict colors (`--go`/`--stop`) are reserved EXCLUSIVELY for verdicts, clock states, and seat hot/cold - nothing decorative.
- **Typography**: system stacks only, no CDN (CSP and offline). Display weight 800, letter-spacing -0.03em. ALL numerals tabular (`ui-monospace`/`tabular-nums`) so polling updates do not jitter layout.
- **Verdict-first pre-draft cards, not tables**: player name 17px/700 left, verdict word right (WAIT green / TAKE NOW red / COIN FLIP amber, uppercase 800). A 4px survival bar under each row, width = probability. Color is never the only signal - the word carries the meaning (colorblind users).
- **Mobile-first at 390px design width**, 4pt spacing grid, safe-area insets. Breakpoints 640/1024. Sticky bottom control bar in the thumb zone: the 12-seat chips at 44px tall (currently ~26px and unusable on a phone).
- **iOS home screen**: `viewport-fit=cover`, `apple-mobile-web-app-capable`, black-translucent status bar, `apple-touch-icon` (generate a simple monogram PNG in-repo). Opening from the home screen must look like an app, not a webpage.
- **Provenance footer** on every screen: `13 seasons - 2,339 picks - Sleeper live feed - generated <date>`. Contextual caveats (K/DEF floor, thin priors) move NEXT TO the numbers they qualify.

**Gate 1**: screenshots of both modes at 390px and 1280px, smoke suite green, zero changes to any math function (diff proof).

## PHASE 2 - Live mode rebuilt for the two-minute clock

- **One answer per screen, fixed stack**: clock strip; ON THE CLOCK lower-third (kicker 11px uppercase, franchise 20px/700, pick number monospace); THE NAME at 64px clamped with fixed min-height; verdict chip; one-line why; two next-best rows. Everything else behind accordions.
- **Kill the innerHTML rebuild** on every 10s poll. Patch text nodes only. A name change must not reflow the page.
- **Clock**: 56px tabular monospace, ink >= 60s, amber < 60s, red < 30s, broadcast blink (steps(2), behind prefers-reduced-motion) < 10s. Counts down client-side between polls.
- **New-pick transition**: 300ms background flash + 150ms name crossfade. The flash is the haptic - navigator.vibrate is dead on iOS.
- **Alerts**: tab-title flash + a short WebAudio beep when Anthony goes on the clock and again at 30 seconds. No audio assets, generate the tone.
- **Freshness dot** by the LIVE pill: green pulse per successful poll, amber "reconnecting" past 25s, red past 60s. Under a two-minute clock the user must know at a glance whether the number is current.
- **Wake lock** (`navigator.wakeLock`) in live mode; on visibilitychange, re-request and refetch immediately so returning from the group chat repaints fresh, not 10 seconds later.
- **Spectator fallback**: when the seat is unknown, show the board wall and ticker with a manual seat picker - never a blank panel.

**Gate 2**: mocked-live screenshots, smoke suite green including the seat-detection scenarios.

## PHASE 3 - The feature build. Priority order, each with its data source

The gap audit found the single most valuable miss: **the live recommendation is roster-blind. It will tell Anthony to take a fourth RB while WR2 sits empty.** Fix that first.

1. **My-roster tracker + roster-need-aware recommendation** - live picks filtered to my slot vs `E.league.starters`; when max-VOR duplicates a filled slot, surface best-at-needed-position beside it with both VORs. Pure slot arithmetic, no new math.
2. **Best-available-by-position row** - top QB/RB/WR/TE each with VOR and P(survives to my next pick), from `E.players` + existing `condSurvival()`.
3. **Live tier-cliff countdown** - per position: players left in the current tier and P(tier survives my next pick). This is Draft Sharks' 3D-value concept grounded in our own tier + survival math.
4. **Snake board wall** - rounds x 12 grid, color-coded by position, filled from the live picks feed. The between-picks screen everyone at the party will look at.
5. **Opponent roster panels + needs** - per-seat positional counts from live picks; flag seats whose QB/TE priors say they act before my next turn (existing urgency data, now cross-checked against what they have actually drafted).
6. **Position-run detector** - banner when N of the last M picks are one position, with the affected tier's cliff count.
7. **Live pick ticker with reach/value tags** - each pick tagged (overall minus ADP), the exact `adp_differential` definition already in out/picks.csv, computed live.
8. **Survival toggle 1-3 rounds out** - FantasyPros' Pick Predictor concept on our own fitted curve: extend the survival table to my next TWO picks.
9. **Queue/targets list** - localStorage, crossed off as taken, with each target's survival to my next pick.
10. **Manual override** - mark-any-player-drafted search for feed hiccups at a live party.
11. **Full sortable player board** - search + position filter + tier grouping over the 306 embedded players.
12. **Value-vs-ADP sleeper list** - widest vor_rank-beats-ADP margins per round band; one sort, zero new data.
13. **Sleeper trending badge** - free CORS-open `/v1/players/nfl/trending/add`; label it as market heat, not a projection.
14. **Opponent dossier drilldown** - tap a seat chip -> full prior card (first-position rounds, n_eff, tendency lifts with thin markers) from out/opponent_priors.csv + out/positional_tendency.csv. The payload currently drops most of these columns; add them.
15. **League-history flavor** - "this pick slot has historically been RB 61% of the time" from out/picks.csv, aggregated at build time.
16. **Post-draft recap export** - roster, per-pick value tags, positional shape vs the league's 13-season norms; Blob download. FantasyPros' instant-grade concept, honestly scoped to what we can measure.

**Gate 3**: each feature demonstrated in the mocked-live smoke test; suite green.

## PHASE 4 - The signature feature: the league-mate mock simulator

No commercial tool has this: **mock drafts where the 11 opponents are the actual league mates**, sampling each seat's positional choice from their measured tendency lifts (out/positional_tendency.csv) and their pick-error distribution (the fitted sd curve), then picking within-position by ADP order. Run N sims from Anthony's seat, show: distribution of his likely roster, which targets most often survive to each of his picks, and where the board typically breaks.

**QUARANTINE RULE**: everything simulator-powered gets a dashed border, a `SIM` badge in amber, and the caption "scenario, not a forecast". Sampling from tendencies for illustration is legitimate; presenting it as calibrated probability is the exact thing the backtest rejected. The decision numbers on the main cards remain the audited survival model only. Add a guard test asserting simulator output never feeds the verdict logic.

**Gate 4**: sim runs client-side in under 2s for 500 drafts, quarantine styling verified in the smoke test.

## PHASE 5 - Ship it as a real app

1. **Enable GitHub Pages** on main via the API (repo is public, Pages is off). Serve the repo root; the app lands at `https://anthonydellapia1117.github.io/yeahthatfantasyleague/out/draft_room.html`. Add a root `index.html` that redirects there.
2. **Draft-morning flow** becomes: `python3 src/engine_2026.py && git commit -am "draft morning rebuild" && git push` - Pages redeploys in about a minute. Document it in README. The local file remains the offline fallback; note both in the app footer.
3. **Verify the live URL** loads on mobile viewport, passes the smoke suite pointed at the deployed page, and that Sleeper CORS works from the Pages origin (it is `*`, but verify, do not assume).

**Gate 5**: the URL, loading, with a screenshot from a 390px viewport.

## PHASE 6 - Full review before final merge

1. Run the repo's code-review at high effort on the complete diff. Fix what it finds or document why not.
2. Re-run every guard: 18 Python + full smoke + parity anchors + calibration benchmark.
3. Confirm `python3 src/engine_2026.py` regenerates everything (markdown, JSON, app injection) byte-stable on a second consecutive run.
4. Update docs/HANDOFF.md, plugin/skills/ff-hub/SKILL.md (routing table), and README.md to reflect v2 and the live URL.
5. Merge to main. Report the final state: URL, feature list shipped, anything deliberately deferred with reasons.

## Definition of done

Anthony opens a URL on his phone, adds it to his home screen, and on 2026-09-08 it tells him - in under five seconds, with numbers that trace to files in this repo - who to take, what waiting costs, who is about to sniper him, and what his roster still needs. Nothing on screen is invented. Everything survives its own tests.
