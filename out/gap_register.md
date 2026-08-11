# Gap Register - Phase 1

Nothing here has been backfilled. Missing stays missing.

| ID | Season | Gap | Impact | Resolution |
|---|---|---|---|---|
| ~~G-001~~ | 2018 | **RESOLVED - not a gap.** Overall pick 38 does not exist. LFTLR exceeded the 2-minute clock (rule 3.2) and **forfeited the pick**; under league rules a timed-out manager gets no pick and waits for free agency. Confirmed by the league owner 2026-08-11 | None. The data is correct; the invariant was wrong | Assertion changed from `picks == teams x rounds` to `picks <= teams x rounds with forfeits enumerated` |
| G-002 | 2013-2025 | `04_draft/keeper_results.csv` is empty (0 rows) | None. `is_keeper` on draft_results is the authoritative field | No action. Not a keeper league |
| G-003 | 2013 | No transactions rows (transactions start 2014) | Drafted-vs-acquired split cannot be computed for 2013 | Exclude 2013 from Phase 2 acquisition analysis. 12 of 13 seasons remain |
| G-004 | 2026 | Draft order unset; `slot_to_roster_id` is Sleeper's identity placeholder | Phase 5 must run all 12 slots | Resolves when the order posts, near 2026-09-08 |
| G-005 | all | Archive `value` and `adp_consensus_score` have no published derivation | Cannot be used as ground truth | Quarantined. `adp_effective_pick` and `adp_differential` validated against 2025 Sleeper and are usable |

| G-006 | 2013-2024 | Yahoo draft PDFs in `Yahoo Draft Results - 2014 to 2024/` are **image-only**. `pdftotext` extracts 1 character from the 2018 file | Cannot be machine-read without OCR | Not needed. The archive already reconciles 168/168 against Sleeper for 2025 and carries all 13 seasons. Hold as a visual audit source |
| G-007 | 2026 | **Written rule 3.3 (draft order = reverse prior finish) is not followed.** Tested across 141 slot assignments, 2014-2025: **17 match, 12.1 percent**, versus 8.3 percent expected at random (z = 1.6, not significant) | Draft slot cannot be predicted from standings. Phase 5 must run all 12 slots | Resolves only when the order posts near 2026-09-08 |

---

## G1 - CLOSED as accepted limitation, 2026-08-11

**Cause identified and confirmed by the league owner:** the six 40-yard long-play bonuses
were a deliberate rule change to make the league harder. They are a real scoring rule,
not a data defect. LeagueLegacy dropped them from per-player rows while keeping them in
team totals.

| | |
|---|---|
| Bonuses | 40 Yd Comp +1, 40 Yd Pass TD +2, 40 Yd Rush +1, 40 Yd Rush TD +2, 40 Yd Rec +1, 40 Yd Rec TD +2 |
| Active | Yahoo seasons 2013-2024. Zero in Sleeper 2025-2026 |
| Size | 6.14 pts per team-week, 4.99 percent of scoring, 2,256 team-weeks |
| Game outcomes affected | 47 of 1,128, 4.17 percent |

**Recovery attempted and abandoned.** Yahoo removed Fantasy Sports scope from the
developer console entirely; both owner apps offer only OpenID Connect and TW Auction.
A valid OAuth token returns `oauth_problem="additional_authorization_required"`. Yahoo
now requires a written application and review for API access. No Python wrapper can
route around this - the block is on Yahoo's grant, not in client code.

Browser scraping was proven to work (2013 weeks 1-7, 2,464 rows, bonus-inclusive) but is
rate-limited at roughly 50 fetches per window with HTTP 999.

**Decision: accept and disclose.** All downstream analysis states a 5 percent
bonus-exclusive basis for 2013-2024. Phase 2's drafted-vs-acquired ratio is unaffected
because numerator and denominator are both bonus-exclusive.

**Product note for a future app build:** the bonus structure is a real competitive lever
this league pulled. A rules-evolution timeline is a genuinely interesting feature later,
and the scoring history to build it already sits in `00_league/seasons.csv` stat_modifiers.
