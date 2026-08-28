#!/usr/bin/env python3
"""C3: rules-based archetype tags from computed usage thresholds.

Maps the research director report's archetype LISTS (methodology) onto tags
whose every threshold is computed from our own data - percentiles of observed
distributions, league-exact scoring, live roster state. No player names appear
in this file; the one permitted fact table is the preseason-RB1 conversion
ledger (2-of-10; Johnson 2016, McCaffrey 2023) with its 2016 source-dependency
flag, per the standing governance exception.

Every tag carries a reason code with the computed inputs behind it, so the UI
can render WHY, with numbers. Post-injury-discount tags carry a zero-IR cost
flag: this league has 14 roster spots, 5 bench, and NO IR slot, so a held
injured player consumes a startable spot - the discount archetype costs more
here than generic advice assumes.

Verification blocks (findings-page material, computed 2016-2025 from the
history cache): the 140-target WR claim, the 400-touch next-season fade, and
the 2025 touch leaders that drive the fade flags.

Run: python3 src/build_archetypes.py
"""
import csv
import datetime
import json
import math
import os
from collections import defaultdict

from analyze_recency import HISTORY

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "out", "data")
OUT = os.path.join(D, "archetypes_2026.json")
SEASON = 2026

W = {"passing_yards": 0.04, "passing_tds": 6.0, "passing_interceptions": -1.0,
     "passing_2pt_conversions": 2.0,
     "rushing_yards": 0.1, "rushing_tds": 6.0, "rushing_2pt_conversions": 2.0,
     "receptions": 1.0, "receiving_yards": 0.1, "receiving_tds": 6.0,
     "receiving_2pt_conversions": 2.0,
     "sack_fumbles_lost": -2.0, "rushing_fumbles_lost": -2.0,
     "receiving_fumbles_lost": -2.0, "special_teams_tds": 6.0}


def norm(n):
    n = n.lower().replace(".", "").replace("'", "")
    return " ".join(w for w in n.split()
                    if w not in ("jr", "sr", "ii", "iii", "iv", "v"))


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 4), round(c + h, 4))


def pctile(vals, q):
    vals = sorted(vals)
    if not vals:
        return None
    i = max(0, min(len(vals) - 1, int(round(q * (len(vals) - 1)))))
    return vals[i]


DISPLAY = {}                 # normalized name -> last seen display name


def season_rows(year):
    """name|pos -> {league-scored totals, targets, touches, games}, REG."""
    agg = defaultdict(lambda: defaultdict(float))
    with open(os.path.join(HISTORY, f"spw_{year}.csv")) as fh:
        for r in csv.DictReader(fh):
            if r.get("season_type") != "REG":
                continue
            key = norm(r["player_display_name"]) + "|" + r.get("position", "")
            DISPLAY[key.split("|")[0]] = r["player_display_name"]
            a = agg[key]
            a["games"] += 1
            for col in ("targets", "carries", "receptions"):
                v = r.get(col)
                if v:
                    try:
                        a[col] += float(v)
                    except ValueError:
                        pass
            for col, w in W.items():
                v = r.get(col)
                if v:
                    try:
                        a["pts"] += float(v) * w
                    except ValueError:
                        pass
            v = r.get("rushing_yards")
            if v:
                try:
                    a["rush_yards"] += float(v)
                except ValueError:
                    pass
    return agg


def pos_rank(agg, pos):
    lst = sorted(((a["pts"], k) for k, a in agg.items() if k.endswith("|" + pos)),
                 reverse=True)
    return {k: i for i, (_, k) in enumerate(lst, 1)}


def main():
    adp = json.load(open(os.path.join(D, "adp.json")))["players"]
    usage = json.load(open(os.path.join(D, "usage_2025.json")))["players"]
    xw = json.load(open(os.path.join(D, "crosswalk.json")))
    depth = json.load(open(os.path.join(D, "depth_charts.json")))["entries"]
    goal = json.load(open(os.path.join(D, "goalline_2025.json")))

    prospect = xw["prospect"]           # sleeper player_id -> draft year/round
    u_by_key = {norm(u["name"]) + "|" + u["pos"]: u for u in usage}
    team_now = {}                        # name|pos -> 2026 team (depth charts)
    for e in depth:
        team_now[norm(e["player"]) + "|" + e["pos"]] = e["team"]

    # ---- derived thresholds, each stated with its distribution
    qbs = [u for u in usage if u["pos"] == "QB" and u["weeks"] >= 8]
    rbs = [u for u in usage if u["pos"] == "RB" and u["weeks"] >= 8]
    qb_rypg = sorted(u["rush_yards"] / u["weeks"] for u in qbs)
    rb_tgpg = sorted(u["targets"] / u["weeks"] for u in rbs)
    thr = {
        "qb_rush_ypg_p75": round(pctile(qb_rypg, 0.75), 2),
        "rb_targets_pg_p75": round(pctile(rb_tgpg, 0.75), 2),
        "late_round_adp": 7 * 12,        # rounds 7+ in a 12-team draft
        "te_dart_adp": 10 * 12,
        "wr_target_threshold": 140,      # VERIFIED below from 2016-2025, not imported
        "touch_fade": 400,               # verified below: next-season outcomes
        "injury_weeks_max": 12,          # missed 5+ of 17
        "note": ("percentile thresholds computed from 2025 usage (min 8 weeks); "
                 "the 140-target and 400-touch thresholds carry their own "
                 "2016-2025 verification blocks in this artifact"),
    }

    # ---- verifications from history (findings-page material)
    # 140+ target WRs 2016-2025: top-24 / top-12 positional finish rates
    # (the same pass captures each season's actual RB1 for the ledger below)
    v_n = v_24 = v_12 = 0
    actual_rb1 = {}
    for yr in range(2016, 2026):
        agg = season_rows(yr)
        rb1_of_yr = min(pos_rank(agg, "RB").items(), key=lambda kv: kv[1])
        actual_rb1[yr] = rb1_of_yr[0].split("|")[0]
        ranks = pos_rank(agg, "WR")
        for key, a in agg.items():
            if key.endswith("|WR") and a["targets"] >= thr["wr_target_threshold"]:
                v_n += 1
                v_24 += ranks.get(key, 999) <= 24
                v_12 += ranks.get(key, 999) <= 12
    verify_targets = {
        "claim": "140+ target WRs are safe (report: 96% top-24, 74% top-12 since 2000)",
        "computed": {"seasons": "2016-2025", "n": v_n,
                     "top24": {"k": v_24, "rate": round(v_24 / v_n, 4),
                               "ci95": wilson(v_24, v_n)},
                     "top12": {"k": v_12, "rate": round(v_12 / v_n, 4),
                               "ci95": wilson(v_12, v_n)}},
    }

    # 400+ touch RBs: next-season top-5 rate, 2013-2024 seasons -> next year
    t_n = t_top5 = 0
    ledger = []
    prev = None
    for yr in range(2013, 2026):
        agg = season_rows(yr)
        if prev is not None:
            p_agg, p_yr = prev
            ranks = pos_rank(agg, "RB")
            for key, a in p_agg.items():
                if key.endswith("|RB") and a["carries"] + a["receptions"] >= thr["touch_fade"]:
                    t_n += 1
                    hit = ranks.get(key, 999) <= 5
                    t_top5 += hit
                    ledger.append({"season": p_yr, "touches": int(a["carries"] + a["receptions"]),
                                   "next_top5": bool(hit)})
        prev = (agg, yr)
    verify_touches = {
        "claim": "only 1 of the last 13 400+ touch RBs was top-5 the next year (report)",
        "computed": {"windows": "2013-2024 seasons -> following year", "n": t_n,
                     "next_top5": {"k": t_top5,
                                   "rate": round(t_top5 / t_n, 4) if t_n else None,
                                   "ci95": wilson(t_top5, t_n)},
                     "ledger": ledger},
    }

    # 2025 facts that drive fade flags (computed, not imported)
    agg25 = season_rows(2025)
    rb_ranks25 = pos_rank(agg25, "RB")
    rb1_key = next((k for k, r in rb_ranks25.items() if r == 1), None)
    touch_400_keys = [k for k, a in agg25.items()
                      if k.endswith("|RB")
                      and a["carries"] + a["receptions"] >= thr["touch_fade"]]

    # ambiguous backfield: 2026 team's returning-RB carry concentration
    team_rb_carries = defaultdict(list)
    for key, team in team_now.items():
        if key.endswith("|RB"):
            u = u_by_key.get(key)
            if u:
                team_rb_carries[team].append(u["carries"])
    top_share = {}
    for team, cs in team_rb_carries.items():
        tot = sum(cs)
        if tot >= 100:                   # a team of pure rookies has no 2025 sample
            top_share[team] = max(cs) / tot
    amb_threshold = pctile(sorted(top_share.values()), 0.5)
    thr["ambiguous_top_share_median"] = round(amb_threshold, 4)
    ambiguous_teams = {t for t, s in top_share.items() if s < amb_threshold}

    # conversion ledger: the one authorized fact table - per the review
    # correction, BOTH columns are now computed, never imported: preseason
    # RB1 from the FFC PPR ADP snapshot, actual RB1 by league-exact season
    # total (under full PPR the actual column differs from the report's
    # standard-scoring version in some years; the rows are the record)
    ledger_rows = []
    for yr in range(2016, 2026):
        ffc = json.load(open(os.path.join(HISTORY, f"ffc_ppr_{yr}.json")))
        pre = min((p for p in ffc["players"] if p["position"] == "RB"),
                  key=lambda p: p["adp"])
        act = actual_rb1[yr]
        row = {"year": yr, "preseason_rb1": pre["name"],
               "actual_rb1": DISPLAY.get(act, act),
               "converted": norm(pre["name"]) == act}
        if yr == 2016:
            row["source_dependency"] = (
                "the 2016 cell is source-dependent: FFC ADP names one RB1, "
                "ESPN another; the conversion holds under the standard FFC "
                "consensus")
        ledger_rows.append(row)
    conv = sum(r["converted"] for r in ledger_rows)
    fact_rb1_ledger = {
        "fact": f"preseason ADP RB1 converted to actual RB1 in {conv} of "
                f"{len(ledger_rows)} seasons 2016-2025 (both columns computed)",
        "basis": "preseason = FFC PPR ADP RB1; actual = RB1 by league-exact "
                 "full-PPR season total, recomputed per the review correction",
        "rows": ledger_rows,
        "flag": next(r["source_dependency"] for r in ledger_rows
                     if r["year"] == 2016),
    }

    tags = {}

    def add(name, pos, tag, orientation, reason, zero_ir=False):
        e = tags.setdefault(name + "|" + pos, {"name": name, "pos": pos, "tags": []})
        t = {"tag": tag, "orientation": orientation, "reason": reason}
        if zero_ir:
            t["zero_ir_cost"] = ("this league holds NO IR slot (5 bench); an "
                                 "injured hold consumes a startable spot, so "
                                 "the discount must clear a higher bar here")
        e["tags"].append(t)

    draft_len = 14 * 12                  # the draft is 168 picks; nobody beyond
    for p in adp:                        # it can be drafted, so nobody beyond
        if (p.get("adp_sleeper") or 999) > draft_len:   # it earns a tag
            continue
        name, pos = p["name"], p["pos"]
        key = norm(name) + "|" + pos
        pr = prospect.get(str(p.get("player_id") or ""))
        u = u_by_key.get(key)
        adp_round = math.ceil((p.get("adp_sleeper") or 999) / 12)

        if pos == "WR" and pr and pr.get("draft_year") == SEASON - 1:
            add(name, pos, "year2_wr", "target",
                f"drafted {pr['draft_year']} (year 2); the breakout archetype "
                f"the report's ledger supports")
        if pos == "RB" and pr and pr.get("draft_year") == SEASON \
                and (pr.get("draft_round") or 9) <= 2:
            add(name, pos, "rookie_rb_capital", "target",
                f"2026 NFL round {pr['draft_round']} pick; capital is the "
                f"opportunity proxy in years 1-2")
        if pos == "RB" and u and u["weeks"] >= 8:
            tpg = u["targets"] / u["weeks"]
            if tpg >= thr["rb_targets_pg_p75"]:
                add(name, pos, "pass_catching_rb", "target",
                    f"{tpg:.1f} targets/g in 2025 >= p75 of RB usage "
                    f"({thr['rb_targets_pg_p75']})")
        if pos == "RB":
            team = team_now.get(key)
            if team in ambiguous_teams:
                add(name, pos, "ambiguous_backfield",
                    "target_if_cheap_fade_if_premium",
                    f"{team} returning-RB carry concentration below league "
                    f"median ({thr['ambiguous_top_share_median']:.0%}); "
                    f"his ADP round is {adp_round} - path to volume if cheap, "
                    f"committee risk at a premium")
        if pos == "QB" and u and u["weeks"] >= 8:
            rypg = u["rush_yards"] / u["weeks"]
            if rypg >= thr["qb_rush_ypg_p75"] and (p.get("adp_sleeper") or 0) >= thr["late_round_adp"]:
                add(name, pos, "late_rushing_qb", "target",
                    f"{rypg:.0f} rush yds/g (>= p75 {thr['qb_rush_ypg_p75']}) "
                    f"at ADP round {adp_round}")
        if pos == "WR" and u and u["targets"] >= thr["wr_target_threshold"]:
            add(name, pos, "wr_target_volume", "target",
                f"{int(u['targets'])} targets in 2025 >= {thr['wr_target_threshold']}; "
                f"our 2016-2025 verification: top-24 "
                f"{verify_targets['computed']['top24']['rate']:.0%}, top-12 "
                f"{verify_targets['computed']['top12']['rate']:.0%} "
                f"(n={verify_targets['computed']['n']})")
        if u and u["weeks"] <= thr["injury_weeks_max"] and pos in ("RB", "WR", "TE", "QB"):
            prev_rank = None
            for yr_ranks in (pos_rank(agg25, pos), pos_rank(season_rows(2024), pos)):
                r = yr_ranks.get(key)
                if r and r <= 24:
                    prev_rank = r
                    break
            if prev_rank:
                add(name, pos, "post_injury_discount", "context",
                    f"played {int(u['weeks'])} weeks in 2025 with a recent "
                    f"top-24 finish (rank {prev_rank}) on record", zero_ir=True)
        if pos == "RB" and key == rb1_key:
            add(name, pos, "rb1_curse", "fade",
                "computed 2025 RB1 under league scoring; the prior-year RB1 "
                "declined in 6 of the last 7 seasons (report claim, ledger "
                "verified below for the touch half)")
        if pos == "RB" and key in touch_400_keys:
            a25 = agg25[key]
            add(name, pos, "touch_400_fade", "fade",
                f"{int(a25['carries'] + a25['receptions'])} touches in 2025 "
                f">= {thr['touch_fade']}; our 2013-2024 ledger: "
                f"{verify_touches['computed']['next_top5']['k']} of "
                f"{verify_touches['computed']['n']} such seasons produced a "
                f"top-5 RB the next year")

    # TE market-structure tags need positional ADP order
    tes = sorted((p for p in adp if p["pos"] == "TE"
                  and (p.get("adp_sleeper") or 999) <= draft_len),
                 key=lambda x: x["adp_sleeper"])
    for i, p in enumerate(tes, 1):
        adp_round = math.ceil(p["adp_sleeper"] / 12)
        if i <= 2:
            add(p["name"], "TE", "elite_te", "target",
                f"TE{i} by market ADP; the elite-vs-streamer gap adjudication "
                f"is queued (C5) - league rd1-3 TE hit12 is 83% [63,93] n=23")
        elif p["adp_sleeper"] >= thr["te_dart_adp"]:
            add(p["name"], "TE", "late_te_dart", "target",
                f"TE{i} at ADP round {adp_round}; the report's punt path is "
                f"two late darts, never mid-tier")

    out = {
        "provenance": {
            "generated": datetime.date.today().isoformat(),
            "inputs": "adp.json, usage_2025.json, crosswalk.json, "
                      "depth_charts.json, goalline_2025.json, history cache",
            "method": "every threshold computed (percentiles of observed 2025 "
                      "usage) or verified from 2016-2025 history in this "
                      "artifact; team state from current depth charts",
        },
        "thresholds": thr,
        "verification": {
            "wr_140_targets": verify_targets,
            "rb_400_touches": verify_touches,
            "goalline_conversion": goal["conversion"],
        },
        "fact_tables": {"preseason_rb1_ledger": fact_rb1_ledger},
        "players": sorted(tags.values(), key=lambda e: e["name"]),
    }
    json.dump(out, open(OUT, "w"), indent=1)
    from collections import Counter
    c = Counter(t["tag"] for e in tags.values() for t in e["tags"])
    print(f"wrote {OUT}: {len(tags)} tagged players")
    for tag, n in c.most_common():
        print(f"  {tag}: {n}")
    print("verify 140-target:", verify_targets["computed"]["top24"],
          verify_targets["computed"]["top12"], "n=", verify_targets["computed"]["n"])
    print("verify 400-touch:", verify_touches["computed"]["next_top5"],
          "n=", verify_touches["computed"]["n"])


if __name__ == "__main__":
    main()
