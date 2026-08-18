# Changelog

## Red-team pass on the pick engine and CVS (2026-08-18, after merge of #28)

Adversarial review (general-purpose agent standing in for the named
red-team subagent, which does not exist in this environment). Two HIGH
findings, both real, both fixed same-day:

- SIGN INVERSION (HIGH): the walter multiplier `cvs_base * (1 + pct/100)`
  inverted the judgment for the 29 players with negative cvs_base - an
  endorsement pushed them further down. Now sign-safe:
  `cvs = cvs_base + |cvs_base| * pct/100`; a dedicated direction guard
  pins it (test_cvs "walter sign safety").
- ON-THE-CLOCK DEGENERATE (HIGH): on your own pick the card computed
  survival to the current pick (trivially 100%), zeroing scarcity and the
  cost of waiting exactly at decision time. The card now targets your NEXT
  turn (mirrors the verdict card's isMe index); a new on-the-clock smoke
  fixture pins it.
- MED fixes: cost-of-waiting relabelled "score margin at risk (composite
  scale, not projected points)" and suppressed when degenerate; the
  single-candidate case no longer invents a 99-point margin; the card
  warns when cvs.json and the engine payload carry different generated
  dates; determinism guard no longer rewrites cvs.json or fails across
  midnight; adp_pos_rank keyed by (name, pos).
- Accepted (LOW, noted not fixed): numeric payload fields interpolated
  unescaped (builder-controlled, guarded); drafted-player joins by
  normalized name rather than sleeper_id (page-wide pre-existing
  convention, follow-up candidate).

## Increment 2 - CVS wired, signal encoding, pick engine (2026-08-18)

Classification approved by Anthony (stop condition 1 cleared); the guide
layer is live, capped, and kill-switchable.

- New input shards (`src/build_cvs_inputs.py`, literal nflverse columns
  only): `volatility_2025.json` (511 players - weekly PPR mean/sd, boom/bust,
  p90/p25), `td_rates_2025.json` (193 players - TD per opportunity with
  positional outlier deciles), `sos_2026.json` (2026 schedule x 2025 points
  allowed by position, season + weeks 15-17 slices).
- `src/build_cvs.py` + `data/cvs_weights.json`: the CVS anchor law
  (cvs_base = VOR + weighted within-position z of five wired factors;
  Walter judgment as a capped percent multiplier, 10%, never raised without
  approval). 190 players; nulls redistribute and confidence reports the
  covered share; K/DST excluded as floors. Every applied Walter delta
  carries its verbatim quote and line reference into the Explain view.
- Big board rewritten as the CVS board: seven signal states, three channels
  each (container treatment + icon + text label, WCAG-verified colors),
  precedence personal > consensus > single with conflicts kept visible;
  views BOARD / CVS vs WALTER (sparse figure deltas + regression cross-map)
  / CONFLICTS (model conflict queue - live: Jayden Daniels); filters with
  localStorage persistence; live drafted-removal poll.
- Pick engine card in the draft room (additive, PICKENGINE-quarantined):
  the pick + two alternates with conditions, three-line why, cost of
  waiting from the frozen survival model, confidence band, weeks 15-17
  tilt labelled "a schedule proxy for title odds, not a title-odds
  simulation". The wait-or-reach verdict stays the audited VOR model.
- Verification: `tests/test_cvs.py` (12 guards), pages guard suite extended
  (CVS board section, signal-color contrast, cvs teaser leak tokens), smoke
  scenarios 15 (CVS board) and 16 (pick engine) - all suites ALL PASS;
  five frozen survival functions byte-identical to main; engine regen
  touches only its sentinel payload (proven).
- HONESTY: the with/without-guide backtest cannot run - no historical guide
  files exist. The cap and the walter_enabled kill-switch are the risk
  bounds, stated in MODEL.md and on the board.

## Increment 2 - guide integration groundwork (2026-08-18)

- Ingested `data/Walter Ai-2026_Advanced_Fantasy_Guide.md` (sha-stamped) and
  built `src/parse_walter.py`: Evidence/Judgment extraction with verbatim,
  line-referenced quotes; 167 tags across 9 types; 19 Walter rank/ceiling/
  floor figures as a comparison series; Channel B structural knowledge
  (injury base rates, strategy definitions); change-log revision signals per
  player (last_revised, revision_direction, revision_count, subject-attributed).
- Name resolution: exact + nickname + fuzzy(0.90) against the ADP shard;
  0 unresolved, 0 guide-vs-live team conflicts on this parse.
- Extraction audit: 51.0% of the top 200 by ADP carry at least one tag
  (floor: 40%); 50 evidence / 117 judgment; quote fidelity mechanically
  verified against source line ranges (0 mismatches on prose quotes).
- Wrote MODEL.md: routing rule, channel caps, changelog signals, CVS and
  championship-objective designs of record.
- NOT DONE by design: nothing from the guide touches any rank. Gated on
  Anthony's approval of the classification sample (stop condition 1).

## Prior increments (summary)

- Phase 0 discovery: repo map, data inventory, factor availability, change
  contract (reported in-session, gated).
- Existing shipped surfaces: audited VOR engine + frozen survival math, draft
  room, big board (VOR + evidence chips), players/teams/hub pages, conviction
  overlay, teaser build, app shell. See docs/HANDOFF.md.
