# Addendum: League Separation - Corrections to the Intake Report
**2026-08-11 | Supersedes sections 5 and 9 of the intake report**

You were right to push on this. Enforcing the separation surfaced four errors and two facts you need before draft day.

---

## The error I made

The real-name map (`lefty3` = Rich Nolfi, etc.) was derived from **YeahThatFantasyLeague's 2024 draft only**, by player-matching against your local CSV. When I printed the Facilities table I applied that same map globally instead of scoping it to the league it came from.

Nothing was actually mislabeled - only `antdell` collided, and that one is correct. But it was luck, not design. The map is now scoped per league and Facilities carries **no** real-name mapping, because none has been verified for it.

The near-miss that proves the point:

| | |
|---|---|
| `RobFlacc` | YTFL, user_id 1076422875726299136 |
| `domflacco` | Facilities, user_id **different** |

Name similarity 0.71. **Different people.** A fuzzy match would have merged them.

---

## Fact 1: You do not have a roster in Facilities for 2026

All 14 Facilities rosters are owned. You are in the league's user list but own nothing and co-own nothing.

Your actual Facilities history:

| Season | Rosters | Your role |
|---|---|---|
| 2022 | 12 | **Owner** |
| 2023 | 12 | **Owner** |
| 2024 | 16 | Co-owner of roster 9 |
| 2025 | 14 | Co-owner of roster 9 |
| **2026** | **14** | **None** |

Roster 9 in 2024 and 2025 is owned by **`ernie706`**, team name "Anthony's Brother". You have not owned your own Facilities team since 2023.

So the question is not what your Facilities draft slot is. It is whether you are drafting in that league at all. If you are meant to be, someone needs to add you before the draft. If you are co-managing with your brother again, then the analytics target there is *his* roster, not yours, and the survival model should be built around his slot.

---

## Fact 2: `ernie706` is on both boards, on opposite sides

Same Sleeper account, user_id `474652482639753216`, in both leagues:

| League | Role | Treat as |
|---|---|---|
| YeahThatFantasyLeague! | **Co-owner of YOUR roster 7, "Taylor Made"** | **ALLY. Never model as an opponent.** |
| Facilities Fantasy Football | **Owner of roster 9, "Anthony's Brother"** | **Opponent.** |

He is the only account that owns or co-owns in both leagues. If a survival-probability model treats "ernie706" as a single entity, it will count your own co-manager as someone who might take your target in YTFL. The profile store is now keyed on `(league_id, user_id)`, so this cannot happen.

His two profiles are also genuinely different data and should stay that way - Facilities is a 4-point-passing-TD league and YTFL is 6, so his QB timing there says nothing about his QB timing here.

---

## Fact 3: Your own 2024 YTFL profile was contaminated by autodraft

All 14 of slot 7's 2024 picks have an **empty `picked_by`**. Every other slot in that draft has an attributed drafter. That is the signature of an autodrafted team.

The local CSV credits those picks to "Anthony DellaPia", and the players match Sleeper exactly - but a queue running unattended is not a decision record. I had merged them into your profile.

**Corrected:**

| Your YTFL profile | Before | After |
|---|---|---|
| Seasons of attributed picks | 2 | **1 (2025 only)** |
| Avg first QB round | 7.5 | **10.0** |
| Avg first TE round | 9.5 | **11.0** |

You are a considerably later QB and TE drafter than I told you. In a 6-point-passing-TD league where five opponents take a QB by round 4.5, that is worth knowing about yourself.

The engine now refuses to credit any pick with an empty `picked_by` to any manager, in any league.

---

## Fact 4: The two leagues have different structures, not just different scoring

| | YeahThatFantasyLeague! | Facilities Fantasy Football |
|---|---|---|
| League ID | 1389378429505241088 | 1387959935878316032 |
| Teams | 12 | 14 |
| Pass TD / INT | **6 / -1** | **4 / -2** |
| FG 40-49 / 50+ | 4 / 5 | 3 / 3 (+0.1 per yd over 30) |
| Users listed | 20 | 15 |
| Rosters | 12 | 14 |
| **Co-owned teams** | **8 of 12** | **0 of 14** |
| Your role in 2026 | Owner, roster 7 | **none** |
| Verified real names | 12 of 12 | 0 |
| Seasons of draft history | 2 on Sleeper (+2 in local CSV) | 4 on Sleeper |

The 20-vs-12 discrepancy in YTFL is explained: **8 co-owners**, not ghost members.

| Roster | Owner | Co-owner |
|---|---|---|
| 4 | ENolan90 | gatta |
| 5 | dcambs | johngalt1957 |
| 6 | ForthepeopleEsq | jtralie1213 |
| **7** | **antdell (you)** | **ernie706** |
| 8 | FrankieSponge | JPod17 |
| 9 | pbaldino | jasonbonanno |
| 11 | rondro9 | HarrySells |
| 12 | chrisanddom | JulianoBreadman |

I checked whether co-owners actually draft: in YTFL 2025, **every roster's picks were entered by the primary owner**, zero co-owner entries. So current profiles are clean. But two accounts can enter picks for one team, so the live model must attribute picks to the **roster**, not the account, or an opponent's profile will silently split in half mid-draft.

**Open question I am not going to guess at:** `FrankieSponge` is mapped to Julian Podagrasi by the verified 2024 player match, and `JPod17` co-owns that same roster 8. Those are probably the same human with two accounts, but "probably" is not verified, so I have left them as separate entities. Confirm and I will merge them.

---

## What changed in the artifact

`league_mate_profiles_v2.json` replaces v1. Structure is now:

- Top-level keyed by **`league_id`**, not league name
- Each league carries its own `scoring` fingerprint and `realname_map_source`
- Each manager carries `user_id`, `relationship_to_anthony` (SELF / ALLY / opponent), `in_2026`, `owns_2026_roster`
- Managers who appear in history but **not in 2026** are retained but flagged, so they are excluded from live survival math - 2 in YTFL, 6 in Facilities
- No real name appears unless it was verified inside that specific league

---

## Revised asks

1. **Facilities: are you in it or not?** You have no roster. If you are co-managing with `ernie706` again, say so and I will build that league's model around roster 9. If you are supposed to have your own team, chase the commissioner now.
2. **YTFL draft slot** - still needed, order is still unset.
3. **Confirm `FrankieSponge` and `JPod17` are the same person.** Affects one opponent profile.
4. Draft dates for whichever leagues you are actually drafting in.

Everything in sections 1 through 4, 6, and 7 of the intake report - the scoring defect, the flex verification, the ADP arbitrage, the file inventory - is unaffected by any of this. Those were computed per league from the start.
