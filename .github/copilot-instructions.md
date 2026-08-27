# YeahThatFantasyLeague! (YTFL)

## Project Overview
Live fantasy football draft-decision engine on 13 seasons of league history. VONA decision trees, survival models, league-mate tendency profiles. Live draft Sept 8, 2026.

## Tech Stack
- Backend: Python (Flask, server.py)
- Frontend: Static HTML/JS (index.html) served by Flask
- Data: JSON files (league_mate_profiles.json, ytfl_entities.json, ytfl_entity_profiles.json)

## Critical Files - Read Before Writing Code
1. docs/AGENT_HANDOFF_SPEC.md - the rulebook. Read first.
2. docs/SELF_AUDIT_2026-08-26.md - diagnosed defects and known issues.
3. docs/HANDOFF.md - current state pointer. Update as final commit.
4. YTFL_2026_DRAFT_DOCTRINE.md - draft strategy and decision logic.

## Architecture Notes
- Draft engine compares player value against league-mate tendencies, not generic ADP.
- VONA (Value Over Next Available) drives pick recommendations. Do not replace with generic rankings.
- League-mate profiles are hand-curated. Do not auto-generate.
- PII protection: real names and financial balances scrubbed. Never re-introduce. Repo stays public.
- App must render cleanly on mobile for live draft use.

## Coding Conventions
- Python PEP 8 with type hints on public functions.
- Data files are JSON - never hardcode data that exists in a JSON file.
- Pareto frontier replaced old p25 branch rule. Do not revert.
- Document all changes in HANDOFF.md as final commit.

## What NOT To Do
- Do not verify against your own intent - verify against source of truth (league data)
- Do not add PII to any file in a public repo
- Do not break mobile rendering
- Do not replace VONA or Pareto logic with simpler heuristics without approval
- Do not add heavyweight dependencies
