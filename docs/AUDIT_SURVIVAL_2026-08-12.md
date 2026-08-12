# Survival-Model Audit - 2026-08-12

**Scope: commits `1a15494`, `76a6365`, `088d8bc`, `8f23e73`, audited on the priority list A-E supplied by the desktop session. Method matches the 3B audit: reproduce every claim, then attack the parts nobody reviewed. Report only - no code changed.**

## The answer

**All three bug fixes are real and correctly diagnosed, and the claimed numbers reproduce exactly. But the headline question - is the power-law sd better out of sample - comes back NO. On the decision quantity the cards run on, the power law is modestly WORSE than the step function it replaced (10 of 13 seasons, sign p = 0.046). A third model neither commit considered - piecewise-linear interpolation of the same 12 empirical bins - beats BOTH (12 of 13 seasons vs step, p = 0.002; 10 of 13 vs power), is exactly as smooth as the power law where it matters, and expresses the non-monotone tail the power law cannot.** Recommendation at the end; per the revert-criterion stated in the request, the choice is the verifier's.

## Claims verified before anything was attacked

| Claim | Reproduced |
|---|---|
| Step-function cliff: ADP 24 vs 25 at pick 48 | 8,285x (claimed 8,284x) |
| Consensus number one 50 percent available at pick 1 | 0.50 exact |
| ADP-5 player loses 14 percent of mass below pick 1 | 14.2 percent under the new sd 3.73 |
| tests/test_survival.py | 14 of 14 pass, including the old-model counter-test |
| Tendency backtest | out/tendency_backtest.json carries the per-season Brier base/adj as quoted |
| Unconditional wait-or-reach disagreed with live mode | confirmed in the pre-fix source |

## A. Is the new sd fit better out of sample? NO - and neither is the step

Leave-one-season-out over the same 2,039 picks, every model refit per fold by its own recipe, all scored under the identical survival formula (erfc, pick-1 normalized) so only the sd shape differs. Two quantities: the conditional decision quantity P(survives to c+12 | alive at c) at every origin where the player was actually alive, and unconditional P(available at k) on a pick grid.

| Model | COND Brier | COND log loss | UNCOND Brier | UNCOND log loss |
|---|---|---|---|---|
| STEP (shipped 4-band) | 0.07709 | 0.24608 | 0.06132 | 0.20404 |
| POWER (the refit) | 0.07775 | 0.24631 | 0.06098 | 0.20580 |
| **INTERP (12-bin piecewise linear)** | **0.07642** | **0.24516** | 0.06116 | **0.20380** |

n = 42,982 conditional and 57,092 unconditional predictions. Per-season COND winners: INTERP 10, POWER 2, STEP 1. Head to head on COND: STEP beats POWER 10 of 13 (p = 0.046); INTERP beats STEP 12 of 13 (p = 0.002); INTERP beats POWER 10 of 13 (p = 0.046).

The magnitudes are small - 1.7 percent relative Brier between best and worst - but the direction is consistent, and the request's own criterion was "if the step function predicts better, say so." It does, on the quantity that sets WAIT versus TAKE NOW. **The power law bought smoothness at a small accuracy cost. It did not buy accuracy.**

Why: see C. The power law's monotone-plus-cap shape overstates sd everywhere past ADP 115, where the empirical curve has already turned down.

## B. Pick-1 normalization: CORRECT, keep it

This is not a heuristic - it is the exact truncation correction for a normal distribution bounded at pick 1, which is what pick position is. Three facts settle it:

- Conditional quantities are algebraically invariant: cond_survival is a ratio and the S(1) factor cancels. The wait-or-reach verdicts are untouched by normalization.
- The distortion is confined to where it fixes an impossibility: max effect 0.500 at ADP 1 (the bug being fixed), 0.0049 by ADP 25, 0.0008 by ADP 40, zero mid-board. Nothing at the board's middle is rescaled in any measurable way.
- At pick 1 the empirical availability of every player is 1.0 by definition. The normalized model says 1.0; the raw model said 0.50-0.86 for the top of the board. Calibration at the anchor is now exact.

## C. Floor and cap: floor defensible, cap is the real defect

The empirical bin curve (all 2,039 picks):

| mean ADP | 7 | 20 | 33 | 47 | 59 | 73 | 87 | **100** | 115 | 130 | 147 | 163 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sd | 3.7 | 8.0 | 11.1 | 14.5 | 17.4 | 20.8 | 25.3 | **27.0** | 24.1 | 25.6 | 23.0 | **20.0** |

The curve peaks near ADP 100 and declines 26 percent by ADP 163 - partly a real market effect, partly compression against the end of the draft (picks cannot exceed 168). The power law is structurally unable to say this; its cap holds sd at 26.87 across the whole 115-200 range where the truth falls to 20. That is where its out-of-sample loss comes from. The floor at 3.73 is fine: it is the lowest observed bin, and extrapolating the power law below it asserts precision (sd 1.30 at ADP 1) the data never showed. **INTERP makes both clamps unnecessary: its ends are the observed end bins, and its interior follows the turn the data actually takes.**

## D. Is cond_survival right for a PRE-draft card? Yes - both sides argued

Against: pre-draft, nothing is observed, so conditioning on "available at your pick" injects an assumption about a state of the world that has not happened; the honest pre-draft number is the unconditional joint probability of the scenario.

For: the card's verdict is not a forecast of the scenario - it is an instruction for the moment you are ON that pick, and in that moment availability at the current pick is observed by construction (you cannot take a player who is not there). Charging the hazard already survived is double-counting, which is exactly the bias that made the old cards reach. The scenario's own likelihood is a different number, and the card already displays it separately as p_available_now.

Verdict: the current design is correct BECAUSE it shows both numbers - unconditional "will this situation arise" and conditional "what to do if it does." Note the comparable's survival is also conditioned on its own availability at the current pick, so the two sides of every wait-or-reach comparison are on the same footing. Consistent.

## E. The tests: sound, one real gap, thresholds honest with one caveat

- The cliff guard discriminates rather than rubber-stamps: smooth peaks 2.5x, old step 10.5x, threshold 4.0 sits between, and the old-model counter-test proves the guard bites. The 2 percent floor is justified - the original 8,284x lived entirely below it, in probabilities that all read as "gone."
- Guard 7's lift bounds are acknowledged in-file as set from observed output. That makes them regression tripwires, not validation - fine, as long as nobody cites them as evidence the lifts are right.
- Guard 6 (lift reaches no probability) is a source grep - a tripwire, not a proof. Keep it, but it is brittle to renames.

**The gap the tests missed, and this audit's one new finding: the JS mirror still contains the 1-erf bug that commit `088d8bc` fixed in Python.** `rawSurvival` in out/draft_room.html computes `0.5 * (1 - erf(z))` with the Abramowitz-Stegun erf, which saturates to exactly 1.0 near z = 6, collapsing the JS deep tail to a hard 0.0 while Python's erfc keeps it. Live mode can therefore display "0 percent" for a player who is demonstrably on the board (an ADP-5 faller alive 22+ picks past his ADP). Same defect class as bug 2 - two surfaces disagreeing - and no test compares them. Fix is one line (compute the A-S product form directly as erfc instead of subtracting), plus the missing test: have the engine emit reference survival values into the JSON and have the smoke test assert the JS reproduces them.

Also missing, cheaper to add than to argue about: cond_survival monotone non-increasing in the target pick; the normalization-invariance identity on conditional ratios; and a frozen-fixture calibration test so the NEXT sd "improvement" cannot ship without beating the incumbent out of sample - which is precisely the check that would have flagged the power law.

## The tendency feature (context only, per instructions)

Not re-litigated. The design - real effect, kept out of the arithmetic, shipped as display - is the correct call on its own evidence, and the guard that enforces it is the most important test in the file. Verified present and passing.

## Recommendation, in order of preference

1. **Replace the power-law sd with the 12-bin piecewise-linear empirical curve** (refit by the same recipe, embedded as 12 (adp, sd) pairs in the JSON for the JS mirror). It is continuous, beats both predecessors out of sample on the decision quantity, needs no floor or cap, and honestly expresses the non-monotone tail. Add the calibration fixture test at the same time.
2. If keeping a closed form matters more than the last 1.7 percent of Brier: keep the power law - the cliff it removed was worse than the accuracy it costs - but document that it lost the backtest to both alternatives past ADP 115.
3. Reverting to the step function is NOT recommended despite its backtest edge over the power law: the cliff is a decision-driving defect at exactly the ADP boundaries where wait-or-reach verdicts flip, and INTERP strictly dominates it anyway.

Either way, fix the JS 1-erf residue - that one is not a judgement call.

## Basis

All computations this session from out/picks.csv (2,039 picks with recoverable ADP, 2013-2025), leave-one-season-out, seeds not required (deterministic). Evaluation script preserved in the session scratchpad; the recommendation, if accepted, lands with the fixture test that re-runs it.
