# Draft-night queue - 2026-09-08 - slot 4

Docs only. No artifact, model, or deployed byte changes. Written 2026-09-08 13:30 ET by the
draft-advisor session for Anthony's Sleeper autodraft queue (draft 1389378429505241089, 8:00 PM ET).

## Provenance

- Engine payload: content SHA-256 `8432b49ed880773b9009e92460b6e2287e5e2289b46bbb2b51d33889fe7f9796`, generated 2026-09-08. This is the
  digest the live site has served since PR #81 (11:47 ET); it was reproduced independently in a scratch
  rebuild at 11:33 ET with identical projections and digest. Projections are byte-identical to the 08-31
  build; only Sleeper ADP and injury flags moved.
- Sleeper ADP snapshot: 2026-09-08 11:33 ET (scratch rebuild) and the live build at 11:05 ET; both agree
  to within 0.1 on every player in the top 60. The Codex list cited digest `0645ac64...` from an 11:19 ET
  reproduction; the ordering differences below are not ADP-driven.
- Availability haircuts (expected missed games, judgment from 2026-09-08 reporting, applied as
  missed x (ppg minus weekly replacement); replacement QB 20.44, RB 9.48, WR 10.95, TE 9.56 from
  `out/data/ceiling_2026.json`): McCaffrey 3.5, Puka 2.0, Taylor 1.5, Chase 1.0, Nabers 2.0, Jeanty 1.5,
  Kittle 3.0, Bowers 1.5, Walker 2.0, Nico 2.0, Hampton 1.5, Hall 1.5, LaPorta 2.0, Evans 3.0, Love 2.0,
  Henderson 2.5, Rice 2.0, Olave 2.0, Burrow 2.0, Daniels 2.0, Mahomes 3.0. Every other player carries only
  the position base rate in the season evaluator. The ceiling lens's own `avail_adj_proj` was not used: it
  subtracts replacement points per missed week instead of crediting them, which triples the haircut.
- Josh Jacobs excluded (commissioner's exempt list). No K or DEF; rounds 13 and 14 are manual.

## Method

Three independent top-100 lists were produced from the same brief (Claude Code session that shipped #81,
Codex, and this session). 96 names overlap; the top five agree. This session's list came from a 500-draw
autodraft-queue optimization against ADP-chalk opponents using the engine's frozen pick-error sd curve
(`sd_for`), scored on adjusted optimal-starter points, then re-scored with an injury-aware weekly season
evaluator (position base rates from `data/walter/structural.json`, byes, waiver-level fill). The
adjudicated list below trades 3.5 injury-aware points (1730.2 to 1726.7 over 500 common draws) against the
optimizer's raw order for three rules all three sources agree on: the tier-4 RB block ahead of the WR3
shelf, Loveland below the RB block, and McBride behind the round-2 shelf.

## Adjudication

| Question | Claude Code | Codex | This session | Final and reason |
|---|---|---|---|---|
| McCaffrey | 13 | 6 | 10 | **6.** With a 3.5-game haircut his first-pick lineup gain (264 adj minus RB baseline 161 = 103) still beats JSN (98), Cook (100 unadjusted), Achane (96). The 13 placement uses the mechanical 2-year rate (6.5), which double-counts 2024. Only matters if Chase, Puka, and Taylor are all gone. |
| Taylor vs Puka | Taylor | Taylor | Puka | **Puka.** Both queues use the 2-year rate (3.5 missed) that includes the 2024 knee; today's status is healthy, not suspended, no charges, McVay expects Thursday. Full-draft simulation: Puka-first beats Taylor-first by 21.7 raw and 15.4 injury-aware with a 2.0 haircut; Taylor passes Puka only if Puka misses 4.4 or more games, i.e. a six-game suspension at 45 percent odds. Their own formula (VOR x (17-m)/17) is algebraically the same haircut; the disagreement is only the missed-games input. WalterPicks has Puka 5, Taylor 9. |
| McBride | 31 | 58 | 29 | **24.** Even holding Bowers, McBride at FLEX is 235 points, 49 over the FLEX phantom, which matches a tier-4 RB2's 51 over RB baseline; at pick 28 he beats Javonte, Love, Hall by 13 on the same draws. Bowers is gone by 28 in 55 percent of draws, where McBride is a plain TE1. Not dead value. |
| Loveland | 46 | 71 | 24 | **35.** The optimizer prefers 24 (worth 3 to 6 points as a linear blend) because Bowers is gone in 45 percent of states. Under the never-second-TE rule and Bowers held, his FLEX value (215, 29 over phantom) sits below the tier-4 RBs and the WR3 shelf. 35 is the compromise; edit live (see below). |
| Nabers | 44 | 35 | 27 | **34.** Today: never on PUP, full contact since Aug 24, ESPN "good to go for Sunday night", Slayton release consistent; first official report Wednesday; he is noncommittal. 2.0-game haircut leaves him 231 adjusted, level with Olave and above DeVonta, but behind the tier-4 RB block on the RB2 deadline. 44 uses the 7.5-game mechanical rate that is his 2025 ACL season. |
| Tail | Godwin, Hubbard, Downs, Addison | Kelce, Kincaid, Andrews, Kittle | Likely, Strange, Ferguson, Hockenson | Immaterial: ranks 95 to 100 are round-13 bench names behind K and DEF. This list keeps the TE2 tail because a second TE is the cheapest zero-IR bye cover. |

Other placements: Bowers above Allen (matrix: Bowers beats Allen by 1 to 5 at 21 and by 11 to 16 at 28);
Hampton 13 (healthy, RB8 on WalterPicks; the 30 placement uses his rookie-year ankle as an 8-game rate);
Jeanty 23 (ankle, no confirmed practice through Sep 2, Week 1 55 to 65 percent); Love 32 (high ankle sprain,
Week 1 50-50); RB block Javonte, Hall, Kyren, Etienne, Swift, Montgomery, Love in ADP order so the first
one still on the board fires at 45; QBs Allen 16, Lamar 43, Maye 44, Burrow 59, Prescott 61, Purdy 62.

## What the list encodes at each decision point

- Pick 4: Chase, Puka, Taylor, McCaffrey, then JSN as the fallback on a strange board.
- Pick 21: Achane, Chase Brown, then Henry, Hampton, then Bowers, Allen, Saquon, Nico. Same-draw matrix: an
  RB from the first pair beats Bowers by 10 to 16; Henry and Bowers are even; Bowers beats Walker and
  Hampton by 0 to 2 and Allen by 1 to 5.
- Pick 28: Bowers, Henry, Walker, Nico, Allen, London, Pickens, Jeanty, McBride before any tier-4 RB;
  forcing Javonte, Love, or Hall at 28 costs 23 to 29 on the same draws, Nabers 27 to 32, Loveland 29 to 34.
- Pick 45: the first tier-4 RB still there; Loveland only if the block is gone.
- Picks 52 to 69: WR3 shelf, then Evans, Washington, McLaurin; no QB.
- Picks 76 and 93: Prescott, else Purdy (survives to 93 at 91 percent frozen).
- Later: TE2 or handcuff depth; no second QB above Nix at 85.

## Live edits Anthony should make in the Sleeper queue editor

- If Bowers is taken (by anyone) before 28: drag McBride to 12 and Loveland to 25.
- If Anthony holds Bowers: drag McBride to 45 and Loveland to 55.
- The moment Anthony holds a QB: delete every other QB from the queue.
- If Anthony holds two RBs by 45: drag Olave, DeVonta, Flowers above the remaining RB block.

## Still uncertain

- Puka's NFL review has no timeline and no priced probability; the Puka-over-Taylor call rests on it
  staying under roughly 45 percent odds of a six-game suspension.
- McCaffrey's three undisclosed absences since August are unexplained; the 3.5-game haircut is judgment.
- The opponent model is ADP chalk with the league's own noise. Manager tendencies are description only
  (fold-in rejected, p=0.9932). Slots 3 and 7 have no history.
- The simulator scores season starter points with an injury layer; it does not model waiver or trade value.

## Final top-100

| # | Player | Pos | Team | ADP | VOR | Bye |
|---|---|---|---|---|---|---|
| 1 | Jahmyr Gibbs | RB | DET | 1.9 | 170.3 | 6 |
| 2 | Bijan Robinson | RB | ATL | 2.3 | 163.8 | 11 |
| 3 | Ja'Marr Chase | WR | CIN | 3.4 | 124.9 | 6 |
| 4 | Puka Nacua | WR | LAR | 4.9 | 126.3 | 11 |
| 5 | Jonathan Taylor | RB | IND | 7.1 | 111.2 | 13 |
| 6 | Christian McCaffrey | RB | SF | 5.4 | 129.9 | 8 |
| 7 | Amon-Ra St. Brown | WR | DET | 8.2 | 94.3 | 6 |
| 8 | Jaxon Smith-Njigba | WR | SEA | 5.5 | 98.4 | 11 |
| 9 | De'Von Achane | RB | MIA | 13.3 | 96.3 | 6 |
| 10 | Chase Brown | RB | CIN | 14.6 | 94.1 | 6 |
| 11 | James Cook | RB | BUF | 9.5 | 99.7 | 7 |
| 12 | Derrick Henry | RB | BAL | 17.5 | 85.8 | 13 |
| 13 | Omarion Hampton | RB | LAC | 15.1 | 81.8 | 7 |
| 14 | CeeDee Lamb | WR | DAL | 10.6 | 84.3 | 14 |
| 15 | Brock Bowers | TE | LV | 23.4 | 91.0 | 13 |
| 16 | Josh Allen | QB | BUF | 21.2 | 68.0 | 7 |
| 17 | Saquon Barkley | RB | PHI | 11.6 | 85.6 | 10 |
| 18 | Nico Collins | WR | HOU | 23.8 | 75.8 | 8 |
| 19 | Justin Jefferson | WR | MIN | 11.9 | 64.2 | 6 |
| 20 | Drake London | WR | ATL | 20.2 | 64.0 | 11 |
| 21 | Kenneth Walker | RB | KC | 19.9 | 82.9 | 5 |
| 22 | George Pickens | WR | DAL | 22.3 | 59.5 | 14 |
| 23 | Ashton Jeanty | RB | LV | 16.9 | 72.8 | 13 |
| 24 | Trey McBride | TE | ARI | 25.5 | 72.4 | 14 |
| 25 | A.J. Brown | WR | NE | 17.7 | 61.0 | 11 |
| 26 | Javonte Williams | RB | DAL | 32.5 | 50.9 | 14 |
| 27 | Breece Hall | RB | NYJ | 34.3 | 49.9 | 13 |
| 28 | Kyren Williams | RB | LAR | 27.6 | 46.9 | 11 |
| 29 | Travis Etienne | RB | NO | 43.3 | 46.6 | 8 |
| 30 | D'Andre Swift | RB | CHI | 50.9 | 46.9 | 10 |
| 31 | David Montgomery | RB | HOU | 46.9 | 45.0 | 8 |
| 32 | Jeremiyah Love | RB | ARI | 28.0 | 50.7 | 14 |
| 33 | Chris Olave | WR | NO | 30.0 | 49.7 | 8 |
| 34 | Malik Nabers | WR | NYG | 26.2 | 50.5 | 8 |
| 35 | Colston Loveland | TE | CHI | 39.3 | 52.9 | 10 |
| 36 | DeVonta Smith | WR | PHI | 33.6 | 43.0 | 10 |
| 37 | Zay Flowers | WR | BAL | 41.9 | 42.0 | 13 |
| 38 | Rashee Rice | WR | KC | 29.5 | 43.1 | 5 |
| 39 | Ladd McConkey | WR | LAC | 35.2 | 42.0 | 7 |
| 40 | Bucky Irving | RB | TB | 41.1 | 36.2 | 10 |
| 41 | Cam Skattebo | RB | NYG | 40.6 | 40.1 | 8 |
| 42 | Tyler Warren | TE | IND | 49.8 | 38.6 | 13 |
| 43 | Lamar Jackson | QB | BAL | 31.9 | 32.5 | 13 |
| 44 | Drake Maye | QB | NE | 47.4 | 31.3 | 11 |
| 45 | Tee Higgins | WR | CIN | 35.2 | 38.2 | 6 |
| 46 | Emeka Egbuka | WR | TB | 38.6 | 37.8 | 10 |
| 47 | Garrett Wilson | WR | NYJ | 45.9 | 38.7 | 13 |
| 48 | Jaylen Waddle | WR | DEN | 44.5 | 34.8 | 10 |
| 49 | Mike Evans | WR | SF | 63.7 | 36.0 | 8 |
| 50 | Parker Washington | WR | JAX | 73.0 | 26.2 | 7 |
| 51 | Terry McLaurin | WR | WAS | 55.4 | 27.6 | 7 |
| 52 | Tetairoa McMillan | WR | CAR | 37.6 | 36.8 | 5 |
| 53 | Sam LaPorta | TE | DET | 57.1 | 34.0 | 6 |
| 54 | Rome Odunze | WR | CHI | 65.0 | 21.7 | 10 |
| 55 | Christian Watson | WR | GB | 68.4 | 21.4 | 11 |
| 56 | Quinshon Judkins | RB | CLE | 53.9 | 34.9 | 11 |
| 57 | Jaylen Warren | RB | PIT | 71.9 | 9.5 | 9 |
| 58 | Jameson Williams | WR | DET | 59.2 | 20.0 | 6 |
| 59 | Joe Burrow | QB | CIN | 52.8 | 24.6 | 6 |
| 60 | Harold Fannin | TE | CLE | 71.3 | 17.9 | 11 |
| 61 | Dak Prescott | QB | DAL | 77.1 | 18.4 | 14 |
| 62 | Brock Purdy | QB | SF | 122.7 | 15.7 | 8 |
| 63 | Bhayshul Tuten | RB | JAX | 61.9 | 13.7 | 7 |
| 64 | TreVeyon Henderson | RB | NE | 59.1 | 9.9 | 11 |
| 65 | Luther Burden | WR | CHI | 56.1 | 22.8 | 10 |
| 66 | Jalen Hurts | QB | PHI | 58.4 | 5.0 | 10 |
| 67 | Tucker Kraft | TE | GB | 64.6 | 11.9 | 11 |
| 68 | Jayden Reed | WR | GB | 107.4 | 11.4 | 11 |
| 69 | Trevor Lawrence | QB | JAX | 102.0 | 7.9 | 7 |
| 70 | Kyle Pitts | TE | ATL | 67.3 | 9.1 | 11 |
| 71 | Rhamondre Stevenson | RB | NE | 77.9 | 7.9 | 11 |
| 72 | Jadarian Price | RB | SEA | 62.2 | 8.9 | 11 |
| 73 | Caleb Williams | QB | CHI | 70.5 | 7.8 | 10 |
| 74 | Davante Adams | WR | LAR | 51.0 | 6.3 | 11 |
| 75 | Jayden Daniels | QB | WAS | 65.5 | 3.2 | 7 |
| 76 | Brian Thomas | WR | JAX | 74.7 | 9.2 | 7 |
| 77 | Travis Kelce | TE | KC | 89.7 | 8.9 | 5 |
| 78 | Justin Herbert | QB | LAC | 83.3 | 0.0 | 7 |
| 79 | Tony Pollard | RB | TEN | 83.9 | -1.0 | 9 |
| 80 | Kyle Monangai | RB | CHI | 105.7 | -6.5 | 10 |
| 81 | George Kittle | TE | SF | 82.8 | 6.8 | 8 |
| 82 | Mark Andrews | TE | BAL | 125.9 | 0.0 | 13 |
| 83 | Rico Dowdle | RB | PIT | 86.4 | 0.0 | 9 |
| 84 | Isaiah Likely | TE | NYG | 106.9 | -5.2 | 8 |
| 85 | Bo Nix | QB | DEN | 117.9 | 0.2 | 10 |
| 86 | Marvin Harrison | WR | ARI | 76.6 | 0.0 | 14 |
| 87 | Jordan Mason | RB | MIN | 109.0 | -7.4 | 6 |
| 88 | Dalton Kincaid | TE | BUF | 88.4 | 1.1 | 7 |
| 89 | J.K. Dobbins | RB | DEN | 91.8 | -0.9 | 10 |
| 90 | Brenton Strange | TE | JAX | 161.6 | -1.5 | 7 |
| 91 | Jake Ferguson | TE | DAL | 99.7 | -2.7 | 14 |
| 92 | Patrick Mahomes | QB | KC | 110.9 | -2.8 | 5 |
| 93 | DK Metcalf | WR | PIT | 75.7 | -2.9 | 9 |
| 94 | Alec Pierce | WR | IND | 97.3 | -8.3 | 13 |
| 95 | Matthew Stafford | QB | LAR | 94.5 | -3.3 | 11 |
| 96 | Jared Goff | QB | DET | 131.9 | -4.0 | 6 |
| 97 | Jonathon Brooks | RB | CAR | 98.5 | -6.2 | 5 |
| 98 | Jaxson Dart | QB | NYG | 95.2 | -7.0 | 8 |
| 99 | DJ Moore | WR | BUF | 53.1 | -7.2 | 7 |
| 100 | T.J. Hockenson | TE | MIN | 164.3 | -7.5 | 6 |
