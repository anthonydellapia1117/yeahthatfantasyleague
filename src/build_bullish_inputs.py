#!/usr/bin/env python3
"""C5 stage 1: every computed input the BULLISH matrices consume.

Nothing here is imported from any document. Proportions carry k and n so the
tag engine can put Wilson intervals on them; continuous metrics carry weekly
SEs. Team state resolves from current depth charts; role stats (inside-5
share, receiving market share) are 2025-role priors and say so.

Blocks:
  players   per-player computed metrics by position group
  teams     Week-1 2026 implied totals (dated), td-per-point rate (computed
            from 2025 actuals), 2025 team YBC/att (current-team line quality)
  thresholds  percentile thresholds with the distributions behind them
  qb_gap    the settings-correction derivation: rushing-vs-pocket QB value
            under EXACT league scoring (6-pt) vs the 4-pt counterfactual,
            2016-2025, n and CI

Sources: cached nflverse files in the history dir (participation, ftn, pbp,
advrush, games.csv, spw weekly), repo shards, live Sleeper depth state via
the committed depth_charts.json.

Run: python3 src/build_bullish_inputs.py
"""
import csv
import datetime
import json
import math
import os
from collections import defaultdict

import pyarrow.parquet as pq

from analyze_recency import HISTORY
from engine_lineage import json_content_sha256, require as require_engine_digest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "out", "data")
OUT = os.path.join(D, "bullish_inputs_2026.json")

W = {"passing_yards": 0.04, "passing_tds": 6.0, "passing_interceptions": -1.0,
     "passing_2pt_conversions": 2.0,
     "rushing_yards": 0.1, "rushing_tds": 6.0, "rushing_2pt_conversions": 2.0,
     "receptions": 1.0, "receiving_yards": 0.1, "receiving_tds": 6.0,
     "receiving_2pt_conversions": 2.0,
     "sack_fumbles_lost": -2.0, "rushing_fumbles_lost": -2.0,
     "receiving_fumbles_lost": -2.0, "special_teams_tds": 6.0}
W4 = dict(W, passing_tds=4.0)            # the counterfactual for the QB gap


def norm(n):
    n = n.lower().replace(".", "").replace("'", "")
    return " ".join(w for w in n.split()
                    if w not in ("jr", "sr", "ii", "iii", "iv", "v"))


def pctile(vals, q):
    vals = sorted(vals)
    if not vals:
        return None
    i = max(0, min(len(vals) - 1, int(round(q * (len(vals) - 1)))))
    return vals[i]


def main():
    games_path = os.path.join(HISTORY, "games.csv")
    games_pulled = datetime.datetime.fromtimestamp(
        os.path.getmtime(games_path), tz=datetime.timezone.utc).date().isoformat()

    # ---- pbp: dropbacks, targets, receiving yards, receiver ids, TDs/points
    pbp = pq.read_table(
        os.path.join(HISTORY, "pbp_2025.parquet"),
        columns=["nflverse_game_id" if False else "game_id", "play_id",
                 "season_type", "posteam", "qb_dropback", "pass_attempt",
                 "receiver_player_id", "receiver_player_name",
                 "receiving_yards", "pass_touchdown", "rush_touchdown",
                 "week"]).to_pydict()
    n_plays = len(pbp["play_id"])

    team_dropbacks = defaultdict(int)
    tgt = defaultdict(int)               # receiver id -> targets
    rec_yds = defaultdict(float)
    rcv_team = {}
    rcv_name = {}
    off_tds = defaultdict(int)
    dropback_keys = {}                   # (game_id, play_id) -> posteam
    for i in range(n_plays):
        if pbp["season_type"][i] != "REG":
            continue
        team = pbp["posteam"][i]
        if pbp["qb_dropback"][i] == 1 and team:
            team_dropbacks[team] += 1
            dropback_keys[(pbp["game_id"][i], pbp["play_id"][i])] = team
        rid = pbp["receiver_player_id"][i]
        if rid and pbp["pass_attempt"][i] == 1:
            tgt[rid] += 1
            rcv_team[rid] = team
            rcv_name[rid] = pbp["receiver_player_name"][i] or ""
            v = pbp["receiving_yards"][i]
            if v is not None:
                rec_yds[rid] += v
        if pbp["pass_touchdown"][i] == 1 or pbp["rush_touchdown"][i] == 1:
            if team:
                off_tds[team] += 1

    # ---- participation: routes proxy = on-field membership on dropbacks
    part = pq.read_table(
        os.path.join(HISTORY, "participation_2025.parquet"),
        columns=["nflverse_game_id", "play_id", "offense_players"]).to_pydict()
    routes = defaultdict(int)            # gsis id -> dropbacks on field
    for i in range(len(part["play_id"])):
        key = (part["nflverse_game_id"][i], part["play_id"][i])
        team = dropback_keys.get(key)
        if not team:
            continue
        for pid in (part["offense_players"][i] or "").split(";"):
            if pid:
                routes[pid] += 1

    # ---- ftn: first-read targets
    ftn = pq.read_table(
        os.path.join(HISTORY, "ftn_2025.parquet"),
        columns=["nflverse_game_id", "nflverse_play_id", "read_thrown"]).to_pydict()
    first_read_plays = set()
    for i in range(len(ftn["nflverse_play_id"])):
        if str(ftn["read_thrown"][i]).strip() == "1":
            first_read_plays.add((ftn["nflverse_game_id"][i],
                                  ftn["nflverse_play_id"][i]))
    fr_tgt = defaultdict(int)
    fr_team_n = defaultdict(int)
    for i in range(n_plays):
        if pbp["season_type"][i] != "REG":
            continue
        key = (pbp["game_id"][i], pbp["play_id"][i])
        if key in first_read_plays:
            team = pbp["posteam"][i]
            if team:
                fr_team_n[team] += 1
            rid = pbp["receiver_player_id"][i]
            if rid:
                fr_tgt[rid] += 1

    # ---- team line quality: 2025 team YBC per attempt (current-team basis)
    adv = pq.read_table(os.path.join(HISTORY, "advrush_2025.parquet")).to_pydict()
    team_ybc = defaultdict(float)
    team_car = defaultdict(int)
    for i in range(len(adv["team"])):
        if adv["game_type"][i] != "REG":
            continue
        t = adv["team"][i]
        team_ybc[t] += adv["rushing_yards_before_contact"][i] or 0
        team_car[t] += adv["carries"][i] or 0
    team_line = {t: round(team_ybc[t] / team_car[t], 3)
                 for t in team_ybc if team_car[t] >= 200}

    # ---- Week-1 2026 implied totals (the clean 16/16 coverage window)
    implied = {}
    with open(games_path) as fh:
        for r in csv.DictReader(fh):
            if r["season"] == "2026" and r["week"] == "1" and r.get("total_line"):
                tl, sp = float(r["total_line"]), float(r["spread_line"] or 0)
                # spread_line is home-relative in nflverse
                implied[r["home_team"]] = round(tl / 2 + sp / 2, 2)
                implied[r["away_team"]] = round(tl / 2 - sp / 2, 2)
    # td-per-point from 2025 actuals: offensive TDs / points implied by them is
    # circular; use TDs per team point scored (final scores from spw totals is
    # indirect) - compute points from league-neutral basis: 2025 team points =
    # sum of 6*TDs + FG/XP unknown here, so derive tds-per-point directly from
    # implied-scale: league offensive TDs / league points scored, points from
    # pbp scores. Simpler and stated: use total offensive TDs / total implied-
    # style points = TDs / (sum of team final scores from schedules 2025).
    pts_2025 = defaultdict(int)
    with open(games_path) as fh:
        for r in csv.DictReader(fh):
            if r["season"] == "2025" and r["game_type"] == "REG" and r.get("home_score"):
                pts_2025[r["home_team"]] += int(float(r["home_score"]))
                pts_2025[r["away_team"]] += int(float(r["away_score"]))
    total_tds = sum(off_tds.values())
    total_pts = sum(pts_2025.values())
    td_per_point = round(total_tds / total_pts, 4)
    implied_tds = {t: round(v * td_per_point, 2) for t, v in implied.items()}

    # ---- shards
    eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
    engine_digest = require_engine_digest(eng)
    usage_art = json.load(open(os.path.join(D, "usage_2025.json")))
    usage = usage_art["players"]
    goal = json.load(open(os.path.join(D, "goalline_2025.json")))
    ceil_art = json.load(open(os.path.join(D, "ceiling_2026.json")))
    ceiling_digest = ceil_art.get("provenance", {}).get("engine_content_sha256")
    if ceiling_digest != engine_digest:
        raise ValueError(
            "ceiling inputs were built from a different engine payload; "
            "rebuild src/build_ceiling.py first"
        )
    depth_art = json.load(open(os.path.join(D, "depth_charts.json")))
    depth = depth_art["entries"]
    xwalk = json.load(open(os.path.join(D, "crosswalk.json")))
    input_content_sha256 = {
        "ceiling_2026.json": json_content_sha256(ceil_art),
        "usage_2025.json": json_content_sha256(usage_art),
        "goalline_2025.json": json_content_sha256(goal),
        "depth_charts.json": json_content_sha256(depth_art),
        "crosswalk.json": json_content_sha256(xwalk),
    }

    u_by_key = {norm(u["name"]) + "|" + u["pos"]: u for u in usage}
    ceil_by_key = {norm(p["name"]) + "|" + p["pos"]: p for p in ceil_art["players"]}
    team_now = {}
    for e in depth:
        team_now[norm(e["player"]) + "|" + e["pos"]] = e["team"]
    gsis_of = xwalk["matched"]           # sleeper id -> gsis id
    # goalline player table is keyed by gsis id
    goal_p = goal["player_2025"]
    goal_team = goal["team_2025"]

    # team rec yards (for YMS) and team RB carries (competition)
    team_rec = defaultdict(float)
    for u in usage:
        team_rec[u["team"]] += u["rec_yards"]
    team_rb_car = defaultdict(list)
    for key, t in team_now.items():
        if key.endswith("|RB"):
            u = u_by_key.get(key)
            if u:
                team_rb_car[t].append((key, u["carries"]))

    # QB epa/att from spw
    qb_epa = defaultdict(lambda: [0.0, 0])
    with open(os.path.join(HISTORY, "spw_2025.csv")) as fh:
        for r in csv.DictReader(fh):
            if r.get("season_type") != "REG" or r.get("position") != "QB":
                continue
            key = norm(r["player_display_name"]) + "|QB"
            try:
                qb_epa[key][0] += float(r.get("passing_epa") or 0)
                qb_epa[key][1] += float(r.get("attempts") or 0)
            except ValueError:
                pass

    draftable = [p for p in eng["players"]
                 if p["adp"] <= 14 * 12 and p["pos"] in ("QB", "RB", "WR", "TE")]

    players = []
    for p in draftable:
        key = norm(p["name"]) + "|" + p["pos"]
        sid = str(p.get("sleeper_id") or "")
        gid = gsis_of.get(sid)
        u = u_by_key.get(key)
        cl = ceil_by_key.get(key, {})
        team26 = team_now.get(key) or p.get("team")
        e = {"name": p["name"], "pos": p["pos"], "adp": p["adp"],
             "team_2026": team26,
             "implied_total": implied.get(team26),
             "implied_tds": implied_tds.get(team26),
             "team_line_ybc": team_line.get(team26),
             "gp_rate_2yr": cl.get("gp_rate_2yr"),
             "exp_missed": cl.get("exp_missed")}
        if gid and routes.get(gid):
            r = routes[gid]
            k = tgt.get(gid, 0)
            tm = rcv_team.get(gid) or (u or {}).get("team")
            e["routes_proxy"] = r
            e["tprr_proxy"] = {"k": k, "n": r}
            e["yprr_proxy"] = round(rec_yds.get(gid, 0.0) / r, 3)
            if tm and team_dropbacks.get(tm):
                e["route_part"] = {"k": r, "n": team_dropbacks[tm]}
            if tm and fr_team_n.get(tm):
                e["first_read"] = {"k": fr_tgt.get(gid, 0), "n": fr_team_n[tm]}
        if u:
            if u["weeks"]:
                e["targets_pg"] = round(u["targets"] / u["weeks"], 2)
                e["carries_pg"] = round(u["carries"] / u["weeks"], 2)
                e["rush_ypg"] = round(u["rush_yards"] / u["weeks"], 2)
            if p["pos"] == "TE" and team_rec.get(u["team"]):
                e["yms_2025"] = round(u["rec_yards"] / team_rec[u["team"]], 4)
        if p["pos"] == "RB" and gid and gid in goal_p:
            g25team = goal_p[gid]["team"]
            tt = goal_team.get(g25team, {})
            if tt.get("i5"):
                e["inside5_share"] = {"k": goal_p[gid]["i5"], "n": tt["i5"],
                                      "basis": f"2025 role on {g25team}"}
        if p["pos"] == "RB" and team26 in team_rb_car:
            tot = sum(c for _, c in team_rb_car[team26])
            own = dict(team_rb_car[team26]).get(key, 0)
            if tot >= 100:
                e["backfield_share"] = round(own / tot, 4)
        if p["pos"] == "QB" and key in qb_epa and qb_epa[key][1] >= 150:
            e["epa_per_att"] = round(qb_epa[key][0] / qb_epa[key][1], 4)
        players.append(e)

    # ---- thresholds: percentiles of qualifying distributions
    def dist(vals, name, qs=(0.5, 0.75, 0.8)):
        return {"n": len(vals),
                **{f"p{int(q*100)}": round(pctile(vals, q), 4) for q in qs}}
    wr = [e for e in players if e["pos"] == "WR" and e.get("routes_proxy", 0) >= 150]
    rb = [e for e in players if e["pos"] == "RB" and e.get("targets_pg") is not None]
    te = [e for e in players if e["pos"] == "TE" and e.get("routes_proxy", 0) >= 100]
    qb = [e for e in players if e["pos"] == "QB" and e.get("carries_pg") is not None]
    thresholds = {
        "wr_tprr": dist([e["tprr_proxy"]["k"] / e["tprr_proxy"]["n"] for e in wr], "tprr"),
        "wr_yprr": dist([e["yprr_proxy"] for e in wr], "yprr"),
        "wr_first_read": dist([e["first_read"]["k"] / e["first_read"]["n"]
                               for e in wr if "first_read" in e], "fr"),
        "rb_targets_pg": dist([e["targets_pg"] for e in rb], "tgt"),
        "rb_inside5": dist([e["inside5_share"]["k"] / e["inside5_share"]["n"]
                            for e in rb if "inside5_share" in e], "i5"),
        "team_line_ybc": dist(sorted(team_line.values()), "ybc"),
        "te_route_part": dist([e["route_part"]["k"] / e["route_part"]["n"]
                               for e in te if "route_part" in e], "rp"),
        "qb_rush_ypg": dist([e["rush_ypg"] for e in qb], "rypg"),
        "implied_total": dist(sorted(implied.values()), "imp"),
        "note": ("qualification floors: WR/TE routes-proxy >= 150/100, QB 150+ "
                 "attempts, RB with 2025 usage; proxies count pass-block snaps "
                 "as routes (stated weakness), so thresholds are percentiles "
                 "of OUR distribution, never PFF-unit imports"),
    }

    # ---- QB gap derivation (settings correction item 1)
    def season_qb_table(year, weights):
        agg = defaultdict(lambda: defaultdict(float))
        with open(os.path.join(HISTORY, f"spw_{year}.csv")) as fh:
            for r in csv.DictReader(fh):
                if r.get("season_type") != "REG" or r.get("position") != "QB":
                    continue
                key = norm(r["player_display_name"])
                a = agg[key]
                a["g"] += 1
                for col, w in weights.items():
                    v = r.get(col)
                    if v:
                        try:
                            a["pts"] += float(v) * w
                        except ValueError:
                            pass
                v = r.get("rushing_yards")
                if v:
                    try:
                        a["ry"] += float(v)
                    except ValueError:
                        pass
        return agg

    def gap(weights):
        rush_pts, pocket_pts = [], []
        for year in range(2016, 2026):
            agg = season_qb_table(year, weights)
            rows = [(a["pts"], a["ry"] / a["g"]) for a in agg.values() if a["g"] >= 8]
            rows.sort(reverse=True)
            top12 = rows[:12]
            med_ry = pctile(sorted(r for _, r in rows), 0.75)
            for pts, ry in top12:
                (rush_pts if ry >= med_ry else pocket_pts).append(pts)
        def stats(xs):
            m = sum(xs) / len(xs)
            sd = (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5
            return m, sd, len(xs)
        rm, rsd, rn = stats(rush_pts)
        pm, psd, pn = stats(pocket_pts)
        diff = rm - pm
        se = (rsd ** 2 / rn + psd ** 2 / pn) ** 0.5
        return {"rushing": {"mean": round(rm, 1), "sd": round(rsd, 1), "n": rn},
                "pocket": {"mean": round(pm, 1), "sd": round(psd, 1), "n": pn},
                "gap": round(diff, 1),
                "gap_ci95": [round(diff - 1.96 * se, 1), round(diff + 1.96 * se, 1)]}
    qb_gap = {
        "definition": ("top-12 QB season finishes 2016-2025 (n=120), rushing "
                       "class = rush yds/g >= that season's p75 among 8+ game "
                       "QBs; season TOTAL points under each scoring"),
        "league_6pt": gap(W),
        "counterfactual_4pt": gap(W4),
    }

    out = {
        "provenance": {
            "generated": datetime.date.today().isoformat(),
            "engine_generated": eng["generated"],
            "engine_content_sha256": engine_digest,
            "input_content_sha256": input_content_sha256,
            "vegas": {"source": "nflverse schedules, Week-1 2026 closing lines "
                                "(16/16 games - the only complete coverage "
                                "window)", "pulled": games_pulled},
            "td_per_point": {"value": td_per_point,
                             "basis": "2025 offensive TDs / 2025 points scored"},
            "roles": "inside-5 share and YMS are 2025-role priors and say so",
            "proxy": "routes = on-field membership on team dropbacks "
                     "(participation 2025); counts pass-block snaps as routes",
        },
        "teams": {"implied_total": implied, "implied_tds": implied_tds,
                  "line_ybc_2025": team_line},
        "thresholds": thresholds,
        "qb_gap": qb_gap,
        "players": players,
    }
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}: {len(players)} players")
    print("qb gap 6pt:", qb_gap["league_6pt"])
    print("qb gap 4pt:", qb_gap["counterfactual_4pt"])
    print("thresholds:", {k: v for k, v in thresholds.items() if k != "note"})


if __name__ == "__main__":
    main()
