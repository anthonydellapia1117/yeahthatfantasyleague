# External Review: Gemini "BULLISH" Identification Algorithm

**Reviews:** `docs/research/Gemini_ Fantasy Football Player Value Analysis.md`
**Author:** External critique (Claude), 2026-08-26
**Usage rule:** Read this ONLY AFTER writing an independent assessment of the Gemini report. This document prescribes resolutions; where your independent analysis disagrees, surface the disagreement at a checkpoint rather than silently choosing either side.

---

## 1. Build-breaking spec defect

The Gemini report defines the algorithm twice and the two definitions conflict. Resolve before implementation.

| Element | Narrative section ("The 'BULLISH' Identification Algorithm") | Embedded Phase 2 prompt | Conflict |
|---|---|---|---|
| Logic | 4-of-5 criteria per position | "ONLY if a player meets the following" - implies ALL | Different pass logic |
| RB criteria | 5, includes Goal-Line Monopoly >65% inside-10 and >60 target pace | 4, drops goal-line, swaps target pace for HVT >4.5/gm | Different criteria sets |
| QB | Requires top-10 Vegas implied total | Drops it | Different gate |
| TE | Route participation >80% AND top-2 Receiving YMS | Drops YMS | Different gate |

**Prescribed resolution:** implement the 5-criterion matrices with 4-of-5 logic, amended per Section 3 below. Do not implement the embedded Phase 2 prompt as written.

## 2. Statistical bookkeeping errors (systematic)

1. **r and R² mixed without labels.** TPRR stability cited as R² = 0.41 (r ~= 0.64); target share cited as "~0.70" (r, implying R² ~= 0.49). Standardize on one form, label every coefficient, recompute all on nflverse 2016-2025 with n.
2. **Same-season correlations presented as predictive.** Pass TD 0.881, total TD 0.6115, passer rating 0.80, "TD this week -> top-24 this week" - all descriptive and partly circular (TDs are components of the fantasy points they correlate with). Only two correlation classes qualify for a predictive tagger: year-over-year stability of an input, and input-to-NEXT-season output.
3. **Top-3 finishes are the wrong calibration target for stable metrics.** Stable opportunity metrics predict the top-6/top-12 baseline; the leap to top-3 is disproportionately TD-tail variance positioned for via the Vegas layer, not predicted by any stable metric. Frame the tag as "highest probability of elite-range outcomes." The phrase "mathematically guaranteed" must not survive into the repo.

## 3. Criterion-level verdicts and amendments

### RB

| Criterion (narrative) | Verdict | Amendment |
|---|---|---|
| >60 target pace | Sound | Keep. Compute the league-exact target-vs-carry point ratio from league scoring (rec 1.0, 0.1/yd) and nflverse play data; do not import 2.55x. |
| Goal-line monopoly >65% inside-10 | Right idea, wrong construction | Replace this AND the Vegas binary with one multiplicative construct: **expected-TD equity = team implied TDs x inside-5 carry share.** Inside-10 pools two zones with very different conversion; compute the inside-5 vs 6-10 split from nflverse. The report's "42% of green-zone touches score" is an inside-5-flavored figure applied to inside-10 - verify. |
| Vegas implied total >23.5 | Sound as gate | Subsumed into expected-TD equity above. |
| R1-2 capital, years 1-4 | Prior misapplied as career-long filter | Demote to tiebreak for years 1-2 only. Demonstrated NFL usage supersedes pedigree once observed. |
| YBC >3.0/att (trailing season) | Weakest criterion | Replace with **current-team offensive line quality** (returning starters, line metrics). Trailing player YBC is an O-line metric, breaks on team change (the report's own Walker example), and is partially circular with the explosive plays it claims to predict. Keep explosiveness as a small weight; volume dominates. |
| Missing | - | Add an availability/durability input (see Section 5) and a backfield-competition delta. |

### WR

TPRR-over-Y/T decomposition, route participation, first-read share, adjusted-vacated-targets: **sound, keep.** Recompute all stability coefficients on nflverse. First-downs-per-route-run cited at 0.729 to next-season FPPG: strong single-source claim, verify before weighting.

### QB

Replace "projected >2.0 pass TD/gm" (projecting the output and calling it an input) with stable inputs only: rush attempts/game, team implied total, prior-season EPA-based passing efficiency.

### TE

Route participation >80% + top-2 Receiving YMS: **sound pair, keep both.** The report's claim that TE1-TE3 gap is now <1.0 PPG conflicts with `docs/research/2026_research_director_report.md`, which found elite TE a genuine full-PPR edge. Compute actual TE1/TE3/TE6/TE12 PPG gaps for 2023-2025 from nflverse and log the adjudication on the findings page.

### DST

The Phase 2 streaming formula ((Pressure x 1.5) + (TO x 2)) - Opp EPA uses arbitrary unvalidated weights. Backtest on 2023-2025 before draft-day use, or ship as clearly-labeled heuristic.

## 4. Vegas x league-history integration

1. **Repricing-delta feature:** delta(Vegas-implied value rank) minus delta(ADP rank) over trailing 21 days; run draft morning. Vegas reprices daily, home leagues anchor on stale ADP.
2. **Edge x survival:** actionable edge = Vegas edge x P(available at Anthony's next pick), from the manager-tendency survival model. Rank by the product, never by edge alone.
3. **Trap-player routing:** high-ADP players on bottom-tier implied-total offenses are overdraft bait; use per-manager reach profiles (computed, never assumed) to predict who takes them, feeding run timing.
4. **Props as third ensemble member:** convert season-long props to fantasy points with league-exact scoring; disagreement with consensus >1 round = investigate list.
5. **Median-game amplifier:** two-results-per-week format (confirm from Sleeper settings; implement behind a flag until confirmed) monetizes weekly ceiling twice - weight team implied totals above pure-H2H norms.
6. **Backtest gate:** verify on 2016-2025 that preseason implied totals out-predicted prior-year points before trusting the layer; log result.

All Vegas numbers and roster claims in the Gemini report are a perishable snapshot with unverifiable post-cutoff roster assertions (e.g., the Kenneth Walker team situation). Resolve teams from nflverse at compute time; pull lines fresh. Hardcode nothing.

## 5. Dynamic tag state machine

- **Tag = object,** not boolean: continuous score 0-100, per-criterion hit vector with uncertainty, reason codes, source, timestamp, TTL, status in {BULLISH, WATCH, SUSPENDED, REVOKED}.
- **No cliffs.** The report's "23.9% TPRR fails, 24.0% passes" rule is indefensible: TPRR on ~400 routes carries roughly +/-2pp sampling error. Criterion met = P(true value clears threshold) above a set confidence, using the same Wilson-interval machinery as the base-rate columns. Near-misses render as WATCH.
- **Event taxonomy -> default actions:** RB lower-body soft tissue + limited practice = demote to WATCH, penalize volume, re-eval at final injury report. High-ankle/Lisfranc/Achilles/ACL = SUSPENDED or REVOKED by severity table. Official depth-chart change or 2+ independent beat sources = recompute vacated targets and goal-line priors for the team. Transactions = immediate recompute. Coach quotes = log only, zero weight. Preseason first-team usage = weak Bayesian role update.
- **Staleness decay:** any BULLISH not revalidated within 72h auto-degrades to WATCH; wire to the existing 36h/7d freshness board.
- **T-minus protocol:** T-7d full recompute; T-24h recompute + tag-delta diff report (who gained, lost, why); T-2h final-designations sweep.
- **UI:** tag + age + reason code. Existing repo color law governs; the Gemini prompt's "bright green" directive is void.

## 6. Findings-page verification queue

Recompute and log agreement/disagreement for: TPRR YoY stability; target-share YoY stability; xYPRR vs YPRR stability (declare r or R²); first-downs-per-route-run predictiveness; inside-5 vs 6-10 TD conversion split; league-exact target-vs-carry ratio; TE positional scarcity (the two-report conflict); WR/RB draft-capital hit-rate curves; the DST streaming formula backtest; preseason implied totals vs prior-year points as environment predictor.
