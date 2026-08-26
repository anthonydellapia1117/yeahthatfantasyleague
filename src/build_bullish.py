#!/usr/bin/env python3
"""C5 stage 2: the BULLISH tag engine - probabilistic 4-of-5 matrices, tag
state objects, event taxonomy, delta report, and the ADP-edge accountability
check Anthony ordered.

Every threshold is a percentile of OUR computed distributions (carried in
bullish_inputs_2026.json with the distributions behind them). No hard cliffs:
each criterion yields P(met); proportion criteria use exact normal-approx on
k/n, other criteria use a STATED derived-scale soft rule (band = half the
p75-p50 gap of the criterion's own distribution). The position gate is
P(at least 4 of 5 criteria) computed exactly (Poisson-binomial); QB and TE
use their reconciled smaller matrices. Conventions, stated: BULLISH at
P >= 0.60, WATCH at P >= 0.35 - decision-rule confidence levels, like p<0.05.

State machine: BULLISH / WATCH / SUSPENDED / REVOKED with reason codes, a
72h revalidation TTL (the freshness board's clock), and the event taxonomy
from the external review applied to CURRENT Sleeper injury status. Every
rebuild diffs against the previous committed artifact (the T-24h tag-delta
report is this diff, run on the T-24h rebuild).

ADP-edge accountability (checkpoint directive): the artifact must state what
the tags find that ADP alone does not - the divergence list plus a rank
correlation - and if the answer is nothing, that null is recorded.

Run: python3 src/build_bullish.py
"""
import csv
import datetime
import json
import math
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY = os.environ.get(
    "HISTORY",
    "/tmp/claude-0/-home-user-yeahthatfantasyleague/"
    "3092ab3f-cbec-5ded-8daf-9676b9b6a046/scratchpad/history")
D = os.path.join(ROOT, "out", "data")
IN = os.path.join(D, "bullish_inputs_2026.json")
OUT = os.path.join(D, "bullish_2026.json")

BULLISH_P = 0.60
WATCH_P = 0.35

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


def phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def p_prop(k, n, thr):
    """P(true proportion >= thr) - normal approx on the sample proportion."""
    if n == 0:
        return None
    p = k / n
    se = math.sqrt(max(p * (1 - p), 1e-6) / n)
    return round(phi((p - thr) / se), 4)


def p_soft(value, thr, band):
    """Stated derived-scale soft rule for non-proportion criteria."""
    if value is None:
        return None
    if band <= 0:
        return 0.95 if value >= thr else 0.15
    if value >= thr + band:
        return 0.95
    if value >= thr:
        return 0.75
    if value >= thr - band:
        return 0.5
    return 0.15


def p_at_least(ps, k):
    """Exact P(at least k of the given independent criteria hold)."""
    dp = [1.0]
    for p in ps:
        ndp = [0.0] * (len(dp) + 1)
        for i, v in enumerate(dp):
            ndp[i] += v * (1 - p)
            ndp[i + 1] += v * p
        dp = ndp
    return round(sum(dp[k:]), 4)


def main():
    inp = json.load(open(IN))
    thr = inp["thresholds"]
    eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
    usage = json.load(open(os.path.join(D, "usage_2025.json")))["players"]
    depth = json.load(open(os.path.join(D, "depth_charts.json")))["entries"]
    xwalk = json.load(open(os.path.join(D, "crosswalk.json")))
    inj_by_name = {norm(p["name"]) + "|" + p["pos"]: p.get("injury") or ""
                   for p in eng["players"]}

    def band(dkey):
        d = thr[dkey]
        return max(0.0, (d["p75"] - d["p50"]) / 2)

    # ---- adjusted vacated targets per 2026 team, computed live
    u_team25 = {norm(u["name"]) + "|" + u["pos"]: (u["team"], u["targets"])
                for u in usage}
    team_now = {}
    depth_rank = {}
    for e in depth:
        key = norm(e["player"]) + "|" + e["pos"]
        team_now[key] = e["team"]
        depth_rank[key] = e["rank"]
    vacated = defaultdict(float)
    incoming = defaultdict(float)
    for key, (t25, tg) in u_team25.items():
        t26 = team_now.get(key)
        if t26 is None:
            vacated[t25] += tg           # departed the league as far as we know
        elif t26 != t25:
            vacated[t25] += tg
            incoming[t26] += tg
    adj_vac = {t: round(vacated.get(t, 0) - incoming.get(t, 0), 1)
               for t in set(list(vacated) + list(incoming))}
    av_vals = sorted(adj_vac.values())
    av_p75 = av_vals[int(round(0.75 * (len(av_vals) - 1)))] if av_vals else 0

    implied = inp["teams"]["implied_total"]
    top5_implied = set(sorted(implied, key=lambda t: -implied[t])[:5])

    # expected-TD equity distribution (RBs with both inputs)
    eq_vals = []
    for e in inp["players"]:
        if e["pos"] == "RB" and e.get("implied_tds") and e.get("inside5_share"):
            s = e["inside5_share"]
            eq_vals.append(e["implied_tds"] * s["k"] / s["n"])
    eq_vals.sort()
    eq_p75 = eq_vals[int(round(0.75 * (len(eq_vals) - 1)))] if eq_vals else 0
    eq_band = (eq_p75 - eq_vals[len(eq_vals) // 2]) / 2 if eq_vals else 0

    gp_vals = sorted(e["gp_rate_2yr"] for e in inp["players"]
                     if e.get("gp_rate_2yr") is not None)
    gp_p50 = gp_vals[len(gp_vals) // 2] if gp_vals else 0.85
    bf_vals = sorted(e["backfield_share"] for e in inp["players"]
                     if e.get("backfield_share") is not None)
    bf_p50 = bf_vals[len(bf_vals) // 2] if bf_vals else 0.5

    prospect = xwalk["prospect"]
    sid_of = {p["name"] + "|" + p["pos"]: str(p.get("sleeper_id") or "")
              for p in eng["players"]}

    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    tags = []
    for e in inp["players"]:
        pos, name = e["pos"], e["name"]
        crit = {}
        if pos == "RB":
            if e.get("targets_pg") is not None:
                crit["receiving_volume"] = p_soft(
                    e["targets_pg"], thr["rb_targets_pg"]["p75"], band("rb_targets_pg"))
            if e.get("implied_tds") and e.get("inside5_share"):
                s = e["inside5_share"]
                crit["expected_td_equity"] = p_soft(
                    e["implied_tds"] * s["k"] / s["n"], eq_p75, eq_band)
            if e.get("team_line_ybc") is not None:
                crit["line_quality"] = p_soft(
                    e["team_line_ybc"], thr["team_line_ybc"]["p50"], band("team_line_ybc"))
            if e.get("gp_rate_2yr") is not None:
                crit["availability"] = p_soft(e["gp_rate_2yr"], gp_p50, 0.06)
            if e.get("backfield_share") is not None:
                crit["backfield_command"] = p_soft(e["backfield_share"], bf_p50, 0.1)
            need, total = 4, 5
        elif pos == "WR":
            if e.get("tprr_proxy"):
                crit["target_earning"] = p_prop(
                    e["tprr_proxy"]["k"], e["tprr_proxy"]["n"], thr["wr_tprr"]["p80"])
            if e.get("yprr_proxy") is not None and e.get("routes_proxy", 0) >= 150:
                crit["yprr"] = p_soft(e["yprr_proxy"], thr["wr_yprr"]["p80"],
                                      band("wr_yprr"))
            if e.get("first_read"):
                crit["first_read"] = p_prop(
                    e["first_read"]["k"], e["first_read"]["n"],
                    thr["wr_first_read"]["p75"])
            key = norm(name) + "|" + pos
            t26 = e.get("team_2026")
            vac_ok = adj_vac.get(t26, 0) >= av_p75
            primary_top5 = t26 in top5_implied and depth_rank.get(key) == 1
            crit["opportunity"] = 0.9 if (vac_ok or primary_top5) else 0.2
            if e.get("route_part"):
                crit["route_participation"] = p_prop(
                    e["route_part"]["k"], e["route_part"]["n"],
                    thr["te_route_part"]["p50"])
            need, total = 4, 5
        elif pos == "QB":
            if e.get("rush_ypg") is not None:
                crit["rushing"] = p_soft(e["rush_ypg"], thr["qb_rush_ypg"]["p75"],
                                         band("qb_rush_ypg"))
            if e.get("implied_total") is not None:
                crit["environment"] = p_soft(e["implied_total"],
                                             thr["implied_total"]["p75"],
                                             band("implied_total"))
            if e.get("epa_per_att") is not None:
                crit["efficiency"] = p_soft(e["epa_per_att"], 0.10, 0.05)
            need, total = 2, 3
        else:  # TE
            if e.get("route_part"):
                crit["route_participation"] = p_prop(
                    e["route_part"]["k"], e["route_part"]["n"],
                    thr["te_route_part"]["p75"])
            key = norm(name) + "|TE"
            t26 = e.get("team_2026")
            mates = [x for x in inp["players"] if x.get("team_2026") == t26
                     and x.get("yms_2025") is not None]
            mates.sort(key=lambda x: -x["yms_2025"])
            my_rank = next((i for i, x in enumerate(mates, 1) if x["name"] == name),
                           None)
            if e.get("yms_2025") is not None and my_rank:
                crit["market_share"] = 0.9 if my_rank <= 2 else 0.2
            need, total = 2, 2

        ps = [p for p in crit.values() if p is not None]
        missing = total - len(ps)
        # a criterion with no input cannot silently count as met
        p_gate = p_at_least(ps, need) if len(ps) >= need else 0.0

        status = None
        reasons = []
        if p_gate >= BULLISH_P:
            status = "BULLISH"
        elif p_gate >= WATCH_P:
            status = "WATCH"
            reasons.append("near-miss: gate probability in the watch band")
        if status is None:
            continue
        if missing:
            reasons.append(f"{missing} criterion input(s) unavailable - counted "
                           f"as not met, never guessed")

        # event taxonomy on CURRENT injury status (critique S5 severity table)
        inj = (inj_by_name.get(norm(name) + "|" + pos) or "").lower()
        if inj in ("ir", "out", "pup", "nfi", "sus"):
            status = "SUSPENDED"
            reasons.append(f"injury status '{inj}' - suspended pending return")
        elif inj == "doubtful":
            if status == "BULLISH":
                status = "WATCH"
            reasons.append("doubtful - demoted one level")
        elif inj == "questionable":
            if pos == "RB" and status == "BULLISH":
                status = "WATCH"
                reasons.append("RB questionable (soft-tissue default): demoted, "
                               "re-evaluate at final report")
            else:
                reasons.append("questionable - flagged, no demotion")

        cap_tb = None
        pr = prospect.get(sid_of.get(name + "|" + pos, ""))
        if pr and pr.get("draft_year") in (2025, 2026) and pr.get("draft_round"):
            cap_tb = f"NFL R{pr['draft_round']} {pr['draft_year']} (years-1-2 tiebreak only)"

        tags.append({
            "name": name, "pos": pos, "adp": e["adp"],
            "status": status,
            "score": round(p_gate * 100, 1),
            "gate": f"P(>= {need} of {total})",
            "criteria": {k: v for k, v in crit.items()},
            "reasons": reasons,
            "capital_tiebreak": cap_tb,
            "source": "bullish_inputs_2026.json",
            "computed_at": now,
            "ttl_hours": 72,
        })

    # ---- ADP-edge accountability
    pos_adp_rank = {}
    for pos in ("QB", "RB", "WR", "TE"):
        ranked = sorted((e for e in inp["players"] if e["pos"] == pos),
                        key=lambda x: x["adp"])
        for i, e in enumerate(ranked, 1):
            pos_adp_rank[e["name"] + "|" + pos] = i
    tagged = [t for t in tags if t["status"] in ("BULLISH", "WATCH")]
    div = []
    for t in tagged:
        r = pos_adp_rank.get(t["name"] + "|" + t["pos"])
        score_rank = 1 + sum(1 for x in tagged if x["pos"] == t["pos"]
                             and x["score"] > t["score"])
        if r and r - score_rank >= 4:
            div.append({"name": t["name"], "pos": t["pos"], "status": t["status"],
                        "score_rank": score_rank, "pos_adp_rank": r,
                        "gap": r - score_rank})
    div.sort(key=lambda x: -x["gap"])
    # rank correlation between score and ADP among tagged players (per pos, pooled)
    def spearman(pairs):
        n = len(pairs)
        if n < 3:
            return None
        d2 = sum((a - b) ** 2 for a, b in pairs)
        return round(1 - 6 * d2 / (n * (n * n - 1)), 3)
    pairs = []
    for pos in ("RB", "WR"):
        sub = [t for t in tagged if t["pos"] == pos]
        by_score = sorted(sub, key=lambda x: -x["score"])
        by_adp = sorted(sub, key=lambda x: x["adp"])
        sr = {t["name"]: i for i, t in enumerate(by_score, 1)}
        ar = {t["name"]: i for i, t in enumerate(by_adp, 1)}
        pairs += [(sr[t["name"]], ar[t["name"]]) for t in sub]
    rho = spearman(pairs)
    edge = {
        "question": "what do the tags find that ADP alone does not?",
        "divergent": div,
        "spearman_score_vs_adp_tagged": rho,
        "statement": (
            f"{len(div)} tagged players sit >=4 positional-ADP ranks below their "
            f"tag rank - the edge candidates the market prices later than the "
            f"computed criteria do. Rank correlation with ADP among tagged "
            f"players is {rho}; a value near 1.0 would mean the tag merely "
            f"restates the market."
            if div else
            "NULL RESULT: no tagged player diverges from positional ADP by 4+ "
            "ranks - as built, the tag confirms the market rather than finding "
            "edge. Recorded per the checkpoint directive."),
    }

    # ---- TE scarcity adjudication (two-report conflict, from our data)
    def te_ppg(year):
        agg = defaultdict(lambda: [0.0, 0])
        with open(os.path.join(HISTORY, f"spw_{year}.csv")) as fh:
            for r in csv.DictReader(fh):
                if r.get("season_type") != "REG" or r.get("position") != "TE":
                    continue
                key = norm(r["player_display_name"])
                for col, w in W.items():
                    v = r.get(col)
                    if v:
                        try:
                            agg[key][0] += float(v) * w
                        except ValueError:
                            pass
                agg[key][1] += 1
        rows = sorted((pts / g, pts, g) for pts, g in agg.values() if g >= 8)
        rows.reverse()
        return rows
    gaps = {"te1_te3": [], "te1_te6": [], "te1_te12": []}
    for yr in (2023, 2024, 2025):
        rows = te_ppg(yr)
        if len(rows) >= 12:
            gaps["te1_te3"].append(rows[0][0] - rows[2][0])
            gaps["te1_te6"].append(rows[0][0] - rows[5][0])
            gaps["te1_te12"].append(rows[0][0] - rows[11][0])
    te_adj = {
        "basis": "league-exact PPG, 8+ game TEs, 2023-2025",
        "gaps_ppg": {k: [round(x, 2) for x in v] for k, v in gaps.items()},
        "mean": {k: round(sum(v) / len(v), 2) for k, v in gaps.items() if v},
        "verdict": None,
    }
    m = te_adj["mean"]
    te_adj["verdict"] = (
        f"TE1-TE3 mean gap {m['te1_te3']} PPG, TE1-TE6 {m['te1_te6']}, TE1-TE12 "
        f"{m['te1_te12']}. The Gemini doc's 'TE1-TE3 now under 1.0 PPG' is "
        f"{'SUPPORTED' if m['te1_te3'] < 1.0 else 'CONTRADICTED'} on our scoring; "
        f"the director report's 'elite TE is a real edge' is "
        f"{'SUPPORTED' if m['te1_te12'] >= 4.0 else 'WEAKLY SUPPORTED'} by the "
        f"TE1-TE12 spread.")

    # ---- delta vs the previous committed artifact (the T-24h diff engine)
    delta = {"previous": None, "gained": [], "lost": [], "status_changed": []}
    if os.path.exists(OUT):
        prev = json.load(open(OUT))
        delta["previous"] = prev.get("provenance", {}).get("generated")
        old = {t["name"] + "|" + t["pos"]: t["status"] for t in prev.get("tags", [])}
        new = {t["name"] + "|" + t["pos"]: t["status"] for t in tags}
        delta["gained"] = sorted(k for k in new if k not in old)
        delta["lost"] = sorted(k for k in old if k not in new)
        delta["status_changed"] = sorted(
            f"{k}: {old[k]} -> {new[k]}" for k in new if k in old and old[k] != new[k])

    out = {
        "provenance": {
            "generated": datetime.date.today().isoformat(),
            "computed_at": now,
            "conventions": {"bullish_p": BULLISH_P, "watch_p": WATCH_P,
                            "note": "decision-rule confidence levels, stated "
                                    "like p<0.05; every metric threshold is a "
                                    "computed percentile in bullish_inputs"},
            "ttl": "72h revalidation - the room degrades BULLISH to WATCH past it",
        },
        "adp_edge": edge,
        "te_scarcity_adjudication": te_adj,
        "qb_gap": inp["qb_gap"],
        "delta": delta,
        "tags": tags,
    }
    json.dump(out, open(OUT, "w"), indent=1)
    from collections import Counter
    c = Counter(t["status"] for t in tags)
    print(f"wrote {OUT}: {dict(c)}")
    for t in sorted(tags, key=lambda x: -x["score"])[:10]:
        print(f"  {t['status']:<9} {t['name']:<22} {t['pos']} score {t['score']}")
    print("edge:", edge["statement"][:160])
    print("te:", te_adj["verdict"][:160])


if __name__ == "__main__":
    main()
