#!/usr/bin/env python3
"""CVS - Composite Value Score. VOR-anchored, factor-adjusted, fully explained.

Design (ADR in MODEL.md): CVS = VOR + z_point_scale * weighted-z of the
non-projection factors, computed within position over the draftable pool.
VOR stays the anchor because points-over-replacement is the only
cross-position-comparable scale in the building; the other factors modulate
it by a bounded, config-visible amount. No hidden composite: every factor's
raw value, z, weight, and point contribution ships in the payload, and the
Explain view renders them.

Walter channels (approved classification, 2026-08-18):
  Judgment tags -> percentage deltas on CVS, total clamped to walter_cap_pct.
  Evidence (figures, mechanisms) -> displayed beside the number; regression
  mechanisms cross-mapped against our independently computed TD-rate outliers.
Model flags (mechanical, thresholds in config) power the consensus signal
encoding. Conflicts are queued, never averaged away.

Reads: out/engine_2026.json, out/data/{usage_2025,team_proe_2025,
depth_charts,volatility_2025,td_rates_2025,sos_2026}.json,
data/playcallers.csv, data/walter/*, data/my_board.csv, data/cvs_weights.json
Writes: out/cvs.json

The five frozen survival functions, the engine's verdicts, and the conviction
overlay's coin-flip role are untouched - this file never imports the engine.
"""
import csv
import datetime
import json
import os
import re
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
D = os.path.join(OUT, "data")

SKILL = ("QB", "RB", "WR", "TE")


def norm(s):
    s = re.sub(r"[.'’]", "", str(s).lower())
    s = re.sub(r"\s+(jr|sr|ii|iii|iv|v)$", "", s.strip())
    return re.sub(r"\s+", " ", s)


def jload(path):
    return json.load(open(path))


def zscores(vals):
    """z per index; None stays None; degenerate spread -> all zeros."""
    present = [v for v in vals if v is not None]
    if len(present) < 3:
        return [0.0 if v is not None else None for v in vals]
    mu = statistics.mean(present)
    sd = statistics.stdev(present)
    if sd < 1e-9:
        return [0.0 if v is not None else None for v in vals]
    return [None if v is None else (v - mu) / sd for v in vals]


def main():
    cfg = jload(os.path.join(ROOT, "data", "cvs_weights.json"))
    eng = jload(os.path.join(OUT, "engine_2026.json"))
    usage = {norm(u["name"]): u for u in jload(os.path.join(D, "usage_2025.json"))["players"]}
    proe = {t["team"]: t["proe_2025"] for t in jload(os.path.join(D, "team_proe_2025.json"))["teams"]}
    vol = {norm(v["name"]): v for v in jload(os.path.join(D, "volatility_2025.json"))["players"]}
    tdr = {norm(t["name"]): t for t in jload(os.path.join(D, "td_rates_2025.json"))["players"]}
    sos = {t["team"]: t for t in jload(os.path.join(D, "sos_2026.json"))["teams"]}
    depth = {}
    for e in jload(os.path.join(D, "depth_charts.json"))["entries"]:
        depth[(norm(e["player"]), e["team"])] = e["rank"]
    callers = {}
    for r in csv.DictReader(open(os.path.join(ROOT, "data", "playcallers.csv"))):
        callers[r["team"]] = r
    wtags = jload(os.path.join(ROOT, "data", "walter", "tags.json"))["data"]
    wfigs = jload(os.path.join(ROOT, "data", "walter", "walter_figures.json"))["data"]
    wchange = jload(os.path.join(ROOT, "data", "walter", "changelog.json"))["data"]["by_player"]
    wsha = jload(os.path.join(ROOT, "data", "walter", "extraction_report.json"))["source_sha256"]
    board = {}
    bpath = os.path.join(ROOT, "data", "my_board.csv")
    if os.path.exists(bpath):
        rows = [ln for ln in open(bpath) if not ln.lstrip().startswith("#")]
        for r in csv.DictReader(rows):
            if (r.get("player") or "").strip() and (r.get("call") or "").strip().upper() in ("BULL", "BEAR"):
                board[norm(r["player"])] = r["call"].strip().upper()

    tags_by_player = {}
    for t in wtags:
        if t.get("resolved"):
            tags_by_player.setdefault(norm(t["player"]), []).append(t)
    figs_by_player = {}
    for f in wfigs:
        if f.get("player"):
            figs_by_player.setdefault(norm(f["player"]), []).append(
                {k: f[k] for k in ("kind", "value", "line", "quote")})

    W = cfg["factor_weights"]
    wsum_all = sum(W.values())
    scale = cfg["z_point_scale"]

    # ---- pool per position, factor raws, z within position
    players_out = []
    adp_pos_rank = {}
    for pos in SKILL:
        pool = sorted([p for p in eng["players"] if p["pos"] == pos],
                      key=lambda p: -p["vor"])[:cfg["pool_sizes"][pos]]
        by_adp = sorted([p for p in pool if p["adp"] < 900], key=lambda p: p["adp"])
        for i, p in enumerate(by_adp):
            adp_pos_rank[(p["name"], pos)] = i + 1

        def raws(p):
            n = norm(p["name"])
            u = usage.get(n)
            opp = None
            if u and u.get("weeks"):
                if pos == "RB":
                    opp = (u["carries"] + u["receptions"]) / u["weeks"]
                elif pos == "QB":
                    opp = (u.get("pass_att") or 0) / u["weeks"] if u.get("pass_att") else None
                else:
                    opp = u.get("wopr_mean")
            tc = proe.get(p.get("team"))
            if tc is not None and pos == "RB":
                tc = -tc
            cal = callers.get(p.get("team"))
            coach = None
            if cal:
                coach = -1.0 if str(cal.get("first_time", "0")) in ("1", "True", "true") else 0.0
            slot = depth.get((n, p.get("team") or ""))
            surr = -(slot - 1) if slot else None
            srow = sos.get(p.get("team"))
            sched = srow.get(f"sos_{pos.lower()}") if srow else None
            return {"baseline_projection": p["vor"], "opportunity": opp,
                    "team_context": tc, "coaching_scheme": coach,
                    "surrounding_talent": surr, "schedule": sched,
                    "historical_priors": None}

        raw_rows = [raws(p) for p in pool]
        zcols = {}
        for f in W:
            if f == "baseline_projection":
                continue
            zcols[f] = zscores([r[f] for r in raw_rows])

        for idx, p in enumerate(pool):
            n = norm(p["name"])
            factors = []
            present = [f for f in W if f != "baseline_projection"
                       and zcols[f][idx] is not None]
            w_present = sum(W[f] for f in present)
            w_other_all = wsum_all - W["baseline_projection"]
            for f in W:
                if f == "baseline_projection":
                    factors.append({"factor": f, "raw": round(p["vor"], 1),
                                    "z": None, "weight": W[f],
                                    "contribution": round(p["vor"], 1),
                                    "note": "VOR anchor - cross-position scale"})
                    continue
                z = zcols[f][idx]
                if z is None:
                    factors.append({"factor": f, "raw": None, "z": None,
                                    "weight": W[f], "contribution": 0.0,
                                    "note": "null - weight redistributed"})
                    continue
                contrib = (W[f] / w_present) * z * scale if w_present else 0.0
                factors.append({"factor": f,
                                "raw": round(raw_rows[idx][f], 3),
                                "z": round(z, 3), "weight": W[f],
                                "contribution": round(contrib, 2)})
            cvs_base = p["vor"] + sum(x["contribution"] for x in factors
                                      if x["factor"] != "baseline_projection")
            confidence = round((W["baseline_projection"] + w_present) / wsum_all, 3)

            # ---- Walter judgment layer (capped)
            wt = tags_by_player.get(n, [])
            applied, proposed_pct = [], 0.0
            if cfg["walter_enabled"]:
                for t in wt:
                    if t["class"] != "judgment":
                        continue
                    key = t["tag"]
                    if key == "regression_candidate":
                        key = f"regression_candidate_{t.get('direction')}"
                    dpct = cfg["walter_tag_deltas_pct"].get(key)
                    if dpct is None:
                        continue
                    if t["confidence"] == "inferred":
                        dpct *= cfg["inferred_multiplier"]
                    proposed_pct += dpct
                    applied.append({"tag": t["tag"], "class": t["class"],
                                    "delta_pct": round(dpct, 2),
                                    "confidence": t["confidence"],
                                    "quote": t["quote"][:240],
                                    "lines": f"L{t['line_start']}-{t['line_end']}"})
            cap = cfg["walter_cap_pct"]
            capped_pct = max(-cap, min(cap, proposed_pct))
            was_capped = abs(proposed_pct) > cap + 1e-9
            # sign-safe scale: the percentage applies to the magnitude, so an
            # endorsement never pushes a negative-CVS player further down
            walter_delta = abs(cvs_base) * capped_pct / 100.0
            cvs = cvs_base + walter_delta

            evid = [t for t in wt if t["class"] == "evidence"]
            v = vol.get(n)
            srow2 = sos.get(p.get("team"))
            wk1517 = srow2.get(f"sos_{pos.lower()}_wk15_17") if srow2 else None
            wk1517_rank = srow2.get(f"sos_{pos.lower()}_wk15_17_rank") if srow2 else None
            players_out.append({
                "name": p["name"], "sleeper_id": p.get("sleeper_id", ""),
                "pos": pos, "team": p.get("team"), "tier": p.get("tier"),
                "adp": p["adp"], "injury": p.get("injury"),
                "vor": round(p["vor"], 1),
                "cvs": round(cvs, 2), "cvs_base": round(cvs_base, 2),
                "confidence": confidence,
                "volatility": ({"sd": v["ppr_sd"], "boom_rate": v["boom_rate"],
                                "bust_rate": v["bust_rate"], "p90": v["p90"],
                                "p25": v["p25"], "games": v["games"]} if v else None),
                "factors": factors,
                "playoff_sos": wk1517, "playoff_sos_rank": wk1517_rank,
                "walter": {"applied": applied,
                           "proposed_pct": round(proposed_pct, 2),
                           "capped_pct": round(capped_pct, 2),
                           "was_capped": was_capped,
                           "delta_points": round(walter_delta, 2),
                           "evidence": [{"tag": t["tag"],
                                         "quote": t["quote"][:240],
                                         "lines": f"L{t['line_start']}-{t['line_end']}"}
                                        for t in evid],
                           "figures": figs_by_player.get(n, []),
                           "revision": wchange.get(p["name"])},
                "personal": board.get(n),
            })

    # ---- ranks (cross-position: VOR-anchored CVS is points-comparable)
    players_out.sort(key=lambda x: -x["cvs"])
    for i, p in enumerate(players_out):
        p["cvs_rank"] = i + 1
    for pos in SKILL:
        grp = [p for p in players_out if p["pos"] == pos]
        for i, p in enumerate(grp):
            p["cvs_pos_rank"] = i + 1
    for p in players_out:
        p["adp_pos_rank"] = adp_pos_rank.get((p["name"], p["pos"]))
    for pos in SKILL:
        grp = [p for p in players_out if p["pos"] == pos]
        zs = zscores([p["playoff_sos"] for p in grp])
        for p, z in zip(grp, zs):
            p["playoff_sos_z"] = round(z, 3) if z is not None else None

    # ---- model flags (mechanical, thresholds in config)
    th = cfg["model_flag_thresholds"]
    p90_rank = {}
    for pos in SKILL:
        p90s = sorted([p["volatility"]["p90"] for p in players_out
                       if p["pos"] == pos and p["volatility"]], reverse=True)
        thr_idx = min(th["sleeper_p90_pos_rank"], len(p90s)) - 1
        p90_rank[pos] = p90s[thr_idx] if p90s else None
    for p in players_out:
        gap = (p["adp_pos_rank"] - p["cvs_pos_rank"]) if p["adp_pos_rank"] else None
        p["model_flags"] = {
            "target": bool(gap is not None and gap >= th["target_rank_gap"]),
            "do_not_draft": bool(gap is not None and -gap >= th["dnd_rank_gap"]
                                 and p["adp"] <= th["dnd_adp_universe"]),
            "sleeper": bool((p["adp"] > th["sleeper_min_adp"] or p["adp"] >= 900)
                            and p["volatility"] and p90_rank[p["pos"]] is not None
                            and p["volatility"]["p90"] >= p90_rank[p["pos"]]),
        }

    # ---- consensus signals + precedence + conflicts (encoded server-side so
    # the UI renders one field; the UI adds treatment, icon, and label)
    def walter_has(p, tag):
        return any(a["tag"] == tag for a in p["walter"]["applied"])
    signal_conflicts = []
    for p in players_out:
        w_dnd = walter_has(p, "do_not_draft")
        w_tgt = walter_has(p, "target") or walter_has(p, "recency_bias_target") \
            or walter_has(p, "strategy_pick")
        w_slp = walter_has(p, "sleeper")
        m = p["model_flags"]
        sig = None
        if p["personal"] == "BEAR":
            sig = "personal_dnd"
        elif w_dnd and m["do_not_draft"]:
            sig = "consensus_dnd"
        elif w_dnd or m["do_not_draft"]:
            sig = "single_dnd"
        elif w_tgt and m["target"]:
            sig = "consensus_target"
        elif w_tgt or m["target"]:
            sig = "single_target"
        elif w_slp and m["sleeper"]:
            sig = "consensus_sleeper"
        elif w_slp or m["sleeper"]:
            sig = "single_sleeper"
        p["signal"] = sig
        neg = (p["personal"] == "BEAR") or w_dnd or m["do_not_draft"]
        posv = w_tgt or w_slp or m["target"] or m["sleeper"] or p["personal"] == "BULL"
        p["signal_conflict"] = bool(neg and posv)
        if p["signal_conflict"]:
            signal_conflicts.append({
                "name": p["name"], "pos": p["pos"], "signal": sig,
                "positions": {
                    "walter": ("do_not_draft" if w_dnd else
                               "target" if w_tgt else "sleeper" if w_slp else None),
                    "model": ("do_not_draft" if m["do_not_draft"] else
                              "target" if m["target"] else
                              "sleeper" if m["sleeper"] else None),
                    "personal": p["personal"]}})

    # ---- model conflict queue: capped deltas and direct opposition
    model_conflicts = []
    for p in players_out:
        reasons = []
        if p["walter"]["was_capped"]:
            reasons.append(f"walter delta proposed {p['walter']['proposed_pct']}% "
                           f"exceeds the {cfg['walter_cap_pct']}% cap")
        if walter_has(p, "do_not_draft") and p["model_flags"]["target"]:
            reasons.append("walter do-not-draft vs model target")
        if (walter_has(p, "target") or walter_has(p, "sleeper")) \
                and p["model_flags"]["do_not_draft"]:
            reasons.append("walter endorsement vs model do-not-draft")
        if reasons:
            model_conflicts.append({"name": p["name"], "pos": p["pos"],
                                    "cvs_pos_rank": p["cvs_pos_rank"],
                                    "adp_pos_rank": p["adp_pos_rank"],
                                    "reasons": reasons})

    # ---- regression cross-map: Walter candidates vs our TD-rate outliers
    crossmap = []
    for t in wtags:
        if t["tag"] != "regression_candidate" or not t.get("resolved"):
            continue
        ours = tdr.get(norm(t["player"]))
        model_says = None
        if ours:
            model_says = ("high_outlier" if ours.get("outlier") == "high" else
                          "low_outlier" if ours.get("outlier") == "low" else
                          "not_outlier")
        if not ours:
            agreement = "no_data"
        elif (t["direction"] == "negative" and model_says == "high_outlier") \
                or (t["direction"] == "positive" and model_says == "low_outlier"):
            agreement = "agree"
        elif model_says == "not_outlier":
            agreement = "disagree"
        else:
            agreement = "disagree_strong"   # outlier in the OPPOSITE direction
        crossmap.append({
            "name": t["player"], "pos": t.get("pos"),
            "walter_direction": t["direction"],
            "model_2025_td_rate": ours["td_rate"] if ours else None,
            "model_pos_percentile": ours.get("pos_percentile") if ours else None,
            "model_says": model_says or "no_data",
            "agreement": agreement,
            "mechanism": "td_rate",
        })

    payload = {
        "generated": datetime.date.today().isoformat(),
        "config": cfg,
        "walter_source_sha256": wsha,
        "players": players_out,
        "model_conflicts": model_conflicts,
        "signal_conflicts": signal_conflicts,
        "regression_crossmap": crossmap,
        "notes": {
            "anchor": "CVS = VOR + z_point_scale x weighted-z of non-projection "
                      "factors (within position, draftable pool); Walter "
                      "judgment applied as a capped percentage on top",
            "kdef": "K and DST are excluded from CVS - their projections are "
                    "floors (missing scoring keys); the VOR board covers them",
            "priors_null": "historical_priors is null for every player; weight "
                           "redistributed; confidence reflects it",
            "validation": "the guide layer is prospectively unvalidated - no "
                          "historical guide files exist to backtest; the cap "
                          "and the walter_enabled kill-switch are the risk "
                          "bounds, per the increment 2 report",
        },
    }
    with open(os.path.join(OUT, "cvs.json"), "w") as fh:
        json.dump(payload, fh, separators=(",", ":"))
    print(f"cvs.json: {len(players_out)} players | "
          f"{len(model_conflicts)} model conflicts | "
          f"{len(signal_conflicts)} signal conflicts | "
          f"crossmap {sum(1 for c in crossmap if c['agreement']=='agree')} agree / "
          f"{sum(1 for c in crossmap if c['agreement']=='disagree')} disagree")


if __name__ == "__main__":
    main()
