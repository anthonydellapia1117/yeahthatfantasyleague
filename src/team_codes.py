#!/usr/bin/env python3
"""Canonical NFL team codes at provider boundaries.

Sleeper and the shipped engine use LAR/JAX/WAS/ARI. nflverse and external
guide sources can use LA/JAC/WSH/ARZ for the same clubs. Normalize once as
data enters the app; cross-source joins then speak the engine's codes.
"""

CANONICAL_NFL_TEAMS = (
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
    "LAR", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG",
    "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
)

TEAM_CODE_ALIASES = {
    "LA": "LAR",
    "JAC": "JAX",
    "WSH": "WAS",
    "ARZ": "ARI",
}


def canonical_team(team):
    """Return the engine/Sleeper code while preserving null and blank input."""
    if team is None:
        return None
    code = str(team).strip().upper()
    return TEAM_CODE_ALIASES.get(code, code)
