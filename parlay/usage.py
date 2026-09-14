"""usage.py - a usage-based second opinion on receiving and rushing legs.

The ladder fit says what FanDuel thinks a player's mean is. This module says
what the player's recent role implies: target share times the team's pass
attempts gives expected targets, and catch rate and yards per target turn
that into expected receptions and receiving yards; carries do the same for
rushing yards. The week-one post-mortem showed every ticket-killing miss
was a usage failure (2, 4, 6 and 6 targets), which the market's mean did
not warn about. A leg's probability is the lower of the market's number
and the usage number, and a leg whose expected targets cannot cover the
line is dropped as fragile.

Logs come from data/gamelogs_*.json (gamelogs.py). Current-season games on
the player's current team count first; last season counts only for a
player who is still on the same team, and only when current-season games
are scarce.
"""
import glob, json, os
import espn, propmath as m

SEASON_START = "2026-09-01"
RECENT = 6                       # games in the usage window
SPREAD = {"receptions": 1.25, "rec_yards": 0.80, "rush_yards": 0.55}     # FanDuel-implied spreads
MIN_TGT_BUFFER = 3.5             # receptions legs need expected targets >= line + this
MIN_TGT_YARDS = 4.5              # receiving-yard legs need at least this many expected targets
MIN_CARRIES = 8.0                # rushing-yard legs need at least this many expected carries


def _played(r):
    return (r["tgt"] + r["carries"] + r["pass_att"]) > 0


class Usage:
    def __init__(self, files=None):
        rows = []
        for f in sorted(files or glob.glob(os.path.join(os.path.dirname(__file__) or ".", "data", "gamelogs_*.json"))):
            rows += json.load(open(f))["rows"]
        rows.sort(key=lambda r: r["date"])
        self.by_player = {}
        self.team_att = {}
        for r in rows:
            self.by_player.setdefault(espn.norm(r["player"]), []).append(r)
            if r["team_pass_att"]:
                self.team_att.setdefault(r["team"], {})[(r["date"], r["event"])] = r["team_pass_att"]
        self.n_rows = len(rows)

    def team_attempts(self, team):
        g = sorted(self.team_att.get(team, {}).items())
        cur = [v for (d, _), v in g if d >= SEASON_START]
        prev = [v for (d, _), v in g if d < SEASON_START]
        use = cur[-RECENT:] if len(cur) >= 3 else (prev[-(RECENT - len(cur)):] + cur if prev else cur)
        return sum(use) / len(use) if use else None

    def profile(self, player, team):
        rows = [r for r in self.by_player.get(espn.norm(player), []) if r["team"] == team and _played(r)]
        cur = [r for r in rows if r["date"] >= SEASON_START]
        prev = [r for r in rows if r["date"] < SEASON_START]
        use = cur[-RECENT:] if len(cur) >= 3 else (prev[-(RECENT - len(cur)):] + cur)
        att_mean = self.team_attempts(team)
        if not use or not att_mean:
            return None
        tgt = sum(r["tgt"] for r in use)
        att = sum(r["team_pass_att"] for r in use) or 1
        rec = sum(r["rec"] for r in use)
        ryd = sum(r["rec_yards"] for r in use)
        car = sum(r["carries"] for r in use)
        rush = sum(r["rush_yards"] for r in use)
        share = tgt / att
        exp_tgt = share * att_mean
        catch = (rec + 6.5) / (tgt + 10.0)            # shrunk toward 65 percent
        ypt = (ryd + 80.0) / (tgt + 10.0)             # shrunk toward 8.0 yards per target
        ypc = (rush + 42.0) / (car + 10.0)            # shrunk toward 4.2 yards per carry
        exp_car = car / len(use)
        return {"games": len(use), "cur_games": len(cur), "share": share, "exp_tgt": exp_tgt,
                "catch": catch, "ypt": ypt, "exp_rec": exp_tgt * catch, "exp_rec_yards": exp_tgt * ypt,
                "exp_carries": exp_car, "exp_rush_yards": exp_car * ypc,
                "tgt_by_game": [r["tgt"] for r in use], "dates": [r["date"] for r in use]}

    def p_over(self, prof, stat, line):
        if stat == "receptions":
            return m.prob_over_count(max(prof["exp_rec"], 0.05), line, SPREAD["receptions"])
        if stat == "rec_yards":
            return m.prob_over_continuous(max(prof["exp_rec_yards"], 0.5), line, SPREAD["rec_yards"])
        if stat == "rush_yards":
            return m.prob_over_continuous(max(prof["exp_rush_yards"], 0.5), line, SPREAD["rush_yards"])
        return None

    def fragile(self, prof, stat, line):
        if stat == "receptions":
            return prof["exp_tgt"] < line + MIN_TGT_BUFFER
        if stat == "rec_yards":
            return prof["exp_tgt"] < MIN_TGT_YARDS
        if stat == "rush_yards":
            return prof["exp_carries"] < MIN_CARRIES
        return False
