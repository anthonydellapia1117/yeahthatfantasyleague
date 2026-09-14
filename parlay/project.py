"""
project.py - turn YTFL season fantasy projections into single-game prop means.

The YTFL engine emits one number per player: projected season fantasy
points under a known scoring system (full PPR, 6-point passing TD). That
number is a weighted sum of the underlying box-score stats. Inverting the
weighting recovers the stat line, and dividing by games recovers a
per-game mean, which is what a prop market prices.

Two adjustments are then applied:

  game environment - a player's volume scales with how many points and
  plays his team is expected to produce. The Vegas team implied total is
  the market's own estimate of that, so scaling by implied/league-average
  imports the market's game-script view without re-deriving it.

  role - receiving share for backs and rushing share for quarterbacks are
  not recoverable from a single fantasy number, so they are supplied per
  archetype and are the largest single source of model error. They are
  declared here rather than buried so they can be audited and corrected.
"""

import json

GAMES = 17
LEAGUE_AVG_IMPLIED = 22.5

# Scoring weights, full PPR with 6-point passing touchdowns.
PPR_REC = 1.0
PTS_PER_REC_YD = 0.1
PTS_PER_RUSH_YD = 0.1
PTS_PER_PASS_YD = 0.04
PTS_PER_TD = 6.0

# Per-position efficiency constants, league-wide rates.
YPR = {"WR": 12.6, "TE": 10.8, "RB": 7.9}
TD_PER_REC = {"WR": 0.058, "TE": 0.065, "RB": 0.028}
TD_PER_RUSH_YD = 0.0072          # about one rushing score per 139 yards
TD_PER_PASS_YD = 0.00755         # about one passing score per 132 yards
INT_COST_PER_GAME = 1.4          # 2 points times ~0.7 interceptions

# Fraction of a back's fantasy points that come through the air.
RB_RECEIVING_SHARE = {"passcatch": 0.42, "balanced": 0.28, "early": 0.18}
# Fraction of a quarterback's fantasy points that come on the ground.
QB_RUSH_SHARE = {"elite_runner": 0.30, "runner": 0.20,
                 "mobile": 0.12, "pocket": 0.04}


def rec_divisor(pos):
    """Fantasy points generated per reception for this position."""
    return PPR_REC + PTS_PER_REC_YD * YPR[pos] + PTS_PER_TD * TD_PER_REC[pos]


def rush_yd_value():
    """Fantasy points generated per rushing yard, touchdowns included."""
    return PTS_PER_RUSH_YD + PTS_PER_TD * TD_PER_RUSH_YD


def pass_yd_value():
    """Fantasy points generated per passing yard, touchdowns included."""
    return PTS_PER_PASS_YD + PTS_PER_TD * TD_PER_PASS_YD


def team_multiplier(implied_total):
    """Scale volume by the market's view of this team's scoring.

    Damped with a square root because volume does not move one for one
    with points: a team projected for 28 does not run 25 percent more
    plays than one projected for 22, it converts drives better.
    """
    return (implied_total / LEAGUE_AVG_IMPLIED) ** 0.5


def receiver_game(season_pts, pos, implied_total, games=GAMES):
    per_game = season_pts / games
    rec = per_game / rec_divisor(pos)
    mult = team_multiplier(implied_total)
    rec *= mult
    return {"receptions": rec, "rec_yards": rec * YPR[pos],
            "rec_td": rec * TD_PER_REC[pos]}


def back_game(season_pts, implied_total, archetype="balanced", games=GAMES):
    per_game = season_pts / games
    r = RB_RECEIVING_SHARE[archetype]
    recv_pts = per_game * r
    rush_pts = per_game * (1 - r)
    rec = recv_pts / rec_divisor("RB")
    rush_yds = rush_pts / rush_yd_value()
    mult = team_multiplier(implied_total)
    return {"receptions": rec * mult, "rec_yards": rec * YPR["RB"] * mult,
            "rush_yards": rush_yds * mult,
            "rush_att": (rush_yds * mult) / 4.3,
            "rush_rec_yards": (rush_yds + rec * YPR["RB"]) * mult}


def qb_game(season_pts, implied_total, archetype="mobile", games=GAMES):
    per_game = season_pts / games + INT_COST_PER_GAME
    r = QB_RUSH_SHARE[archetype]
    rush_pts = per_game * r
    pass_pts = per_game * (1 - r)
    pass_yds = pass_pts / pass_yd_value()
    rush_yds = rush_pts / rush_yd_value()
    mult = team_multiplier(implied_total)
    pass_yds *= mult
    return {"pass_yards": pass_yds,
            "pass_td": pass_yds * TD_PER_PASS_YD,
            "completions": pass_yds / 11.2,
            "pass_att": pass_yds / 7.1,
            "rush_yards": rush_yds * mult}


def implied_totals(spread_home, total):
    """Split a game total into the two team totals.

    spread_home is negative when the home team is favoured.
    """
    home = total / 2.0 - spread_home / 2.0
    away = total / 2.0 + spread_home / 2.0
    return away, home


def load_engine(path):
    with open(path) as f:
        e = json.load(f)
    return {p["name"]: p for p in e["players"]}
