# Franchise Lineage and the Person-vs-Franchise Distinction

**Source: league owner testimony, 2026-08-11. Franchise spans verified against `out/picks.csv`. Person composition is testimony only and cannot be verified from any data source.**

---

## The finding that changes how every historical table reads

**The archive labels franchises with their CURRENT names, applied retroactively to every season.**

Proof: the 2013 draft contains both `Nolan & Vinny` and `GaTTa` as separate franchises. Vincent Gatta did not join Nolan Lawrence until 2017. So the 2013 row labelled "Nolan & Vinny" was Nolan alone.

**Consequence:** `member_name` is a **franchise continuity key**, not a description of who was managing that season. Never read a franchise label as its roster of humans at that point in time. This applies to every table in `out/`.

---

## The twelve active franchises

| # | Franchise | People | Partnership history | Sleeper | Franchise titles |
|---|---|---|---|---|---|
| 1 | Cambrias | Dante Cambria, Gaetano Cambria | Always together | `dcambs` | **3** (2019, 2022, 2025) |
| 2 | Phil Baldino | Phil Baldino | Always solo | `pbaldino` | **3** (2018, 2023, 2024) |
| 3 | Chris & Dom | Chris Juliano, Dom Novelli | Always together | `chrisanddom` | **2** (2015, 2016) |
| 4 | Ronnie | Ron Malandro, + Harry (recent) | Solo or with another Ron; Harry recent | `rondro9` | **2** (2013, 2020) |
| 5 | Richie | Rich Nolfi (aka Lefty, Nolfi) | **Was "Lefty & Long" with Mike Long through 2020. Solo from 2021** | `lefty3` | **1** (2017, won as Lefty & Long) |
| 6 | Rob & GregBo | Rob Flacco, Gregory DellaPia (Bo) | **Partnered 5-10 years ago.** Rob solo before; Gregory was with Ernie and Anthony | `RobFlacc` | **1** (2021) |
| 7 | Antdell & Ernie | Anthony DellaPia, Ernie DellaPia | Always together. **Third brother Gregory left for Rob & GregBo** | `antdell` | 0 |
| 8 | Frank & Julian | Frank Auddino, Julian Podagrasi (JPod) | Separate, then partnered 5-10 years ago | `FrankieSponge` | 0 |
| 9 | Nolan & Vinny | Nolan Lawrence, Vincent Gatta | **Separate until Vinny merged in from the GaTTa franchise** | `ENolan90` | 0 |
| 10 | Pung & Tralie | Michael Pungitore, Joseph Tralie | Always together | `ForthepeopleEsq` | 0 |
| 11 | John Juliano | John Juliano (aka Beetle) | Solo. Newest member, joined 2021 | `juliano89` | 0 |
| 12 | Mike Long | Michael Long | **Half of "Lefty & Long" through 2020. Sat out 2021. Own franchise from 2022** | `Rocksolid1018` | 0 as a franchise, **1 as a person** (2017) |

## The three departed franchises

| Franchise | Span (verified) | People | Fate |
|---|---|---|---|
| **GaTTa** | 2013-2016 | Vincent Gatta | **Merged into Nolan & Vinny in 2017.** Won 2014 |
| **LFTLR** | 2013-2020 | Blaise DiGregorio, Vincent Angelo | Left the league. Forfeited 2018 pick 38 |
| **Team JoeBa** | 2013-2021 | Joseph Biancanello (inferred) | Left the league |

---

## Person-level title carriage, which the franchise table hides

Three champions sit in franchises whose title count does not reflect them.

| Person | Title | Won with | Now in | Franchise shows |
|---|---|---|---|---|
| **Vincent Gatta** | 2014 | GaTTa | **Nolan & Vinny** | **0 titles** |
| **Gregory DellaPia** | 2021 | Rob & GregBo | Rob & GregBo | 1 title, correctly |
| **Mike Long** | **2017, CONFIRMED** | Richie, as Lefty & Long | **Mike Long, solo** | **0 titles** |

**Nolan & Vinny is not a title-less franchise. It contains a champion.** Vincent Gatta won 2014 with a franchise that no longer exists, and has drafted for Nolan since 2017.

**Mike Long is resolved.** Owner confirmed 2026-08-11: he and Rich Nolfi were **"Lefty & Long" through 2020**, separated from 2021. Richie won 2017, inside that era, so **Mike Long shares the 2017 title**. His solo franchise's 0 is a franchise fact, not a person fact.

The roster record corroborates the timeline exactly:

| Season | Entered | Exited |
|---|---|---|
| 2021 | John Juliano | LFTLR |
| 2022 | **Mike Long** | Team JoeBa |

Mike Long holds **no franchise in 2021**. He split from Nolfi after 2020 and sat out a year before taking Team JoeBa's vacated seat in 2022. So the Richie franchise is two distinct entities: **Lefty & Long, 2013-2020** and **Rich Nolfi solo, 2021-2025**. Any tendency model that pools them is averaging two different decision-makers.

One more that matters to the principal directly: **Gregory DellaPia left Antdell & Ernie for Rob & GregBo.** Rob & GregBo won in 2021. Whether Gregory was already partnered by then is **unverified** - testimony puts the partnership "within the past 5-10 years," which straddles 2021. If he was, the brother who left has a ring and the two who stayed do not. **Owner confirmation needed on the year Rob and Bo partnered.**

---

## The analytical decision this forces

| Level | Use for | Why |
|---|---|---|
| **Franchise** | Phases 3, 4, 5. All draft-day analysis | **The franchise is the drafting entity.** A co-owned team makes one pick from one seat. Picks cannot be attributed to individuals within a franchise, in any season, from any available source |
| **Person** | Interpretation and caveats only | Skill travels with people, but the data cannot separate co-owners. Any person-level claim is testimony, not measurement |

**Phase 3 runs at franchise level.** Person-level movement is documented here as a caveat and applied where it changes interpretation, specifically the Gatta and Mike Long cases.

### Era splits: behavioural versus nominal

`out/franchise_eras.csv` carries 20 eras across 15 franchises. Five franchises split mid-history, but they are not all the same kind of split, and treating them identically would be wrong.

| Franchise | Split at | Kind | Phase 4 treatment |
|---|---|---|---|
| **Richie** | 2021 | **Behavioural.** Lefty & Long, two decision-makers, becomes Nolfi alone | **Split.** Two units |
| **Rob & GregBo** | 2015 | **Behavioural.** Rob alone becomes Rob plus Gregory | **Split.** Two units |
| **Nolan & Vinny** | 2017 | **Behavioural.** Nolan alone becomes Nolan plus Gatta, a champion arriving from a dissolved franchise | **Split.** Two units |
| **Antdell & Ernie** | 2015 | **Behavioural.** Three Amigos becomes Two Amigos when Gregory leaves | **Split.** Two units |
| **Ronnie** | 2024 | **Nominal only.** Harry is described by the owner as a silent partner who "doesn't do much" | **Pool.** One unit across 2013-2026 |

The Ronnie case is the instructive one. A roster change is not automatically a decision-maker change. Splitting Ronnie at 2024 would cut a 13-season profile down to 11 plus 2 and add noise without adding signal, because the person making the picks did not change. Both Ronnie titles, 2013 and 2020, sit in the pre-Harry span regardless.

**Effective Phase 4 unit count: 19, not 20.**

### One owner self-correction on the record

Frank & Julian was first described as "separated and partnered 5-10 years ago" and later as "always together, never separated, as far as I know and remember." The later statement is taken as authoritative and the franchise is modelled as a single era, 2013-2025. Confidence is marked `testimony, owner self-corrected` in `franchise_eras.csv`. If a positional-tendency discontinuity ever shows up mid-history for this franchise, revisit it - that would be evidence the first statement was the right one.

---

## Verified against data

| Claim | Result |
|---|---|
| GaTTa franchise ends 2016 | **Verified** - 2013-2016, 4 seasons |
| Nolan & Vinny spans the whole era | **Verified** - 2013-2025, 13 seasons |
| Mike Long is recent and solo | **Verified** - 2022-2025, 4 seasons |
| John Juliano is the newest | **Verified** - 2021-2025, 5 seasons |
| LFTLR departed | **Verified** - 2013-2020, absent after |
| Team JoeBa departed | **Verified** - 2013-2021, absent after |
| Phil Baldino joined mid-era | **Verified** - 2017-2025, 9 seasons |
| No franchise skips a season inside its span | **Verified** - zero gaps across all 15 |
| Who sat in a co-owned franchise in a given season | **Not verifiable.** No source carries it |
