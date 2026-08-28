#!/usr/bin/env python3
"""Walter guide parser - Evidence/Judgment extraction with line-true quotes.

Reads `data/Walter Ai-2026_Advanced_Fantasy_Guide.md` (path quoted - it
contains a space) and writes structured, provenance-stamped outputs to
data/walter/. Nothing here touches CVS, VOR, verdicts, or any rank - this is
ingestion only, gated on Anthony's approval of the classification sample.

Core principle (increment 2): every extraction is classified
  evidence  - verifiable state of the world -> may feed factor groups at
              full weight once approved
  judgment  - Walter's calls -> capped adjustment layer only
Ambiguity routes to judgment (conservative).

Outputs (all carry source sha256; re-running on a changed guide emits a
diff summary instead of silently overwriting):
  data/walter/tags.json            per-player tags, quotes, line ranges
  data/walter/structural.json      Channel B non-player knowledge
  data/walter/walter_figures.json  Walter's stated ranks/ceilings/floors/PPG
  data/walter/changelog.json       revision signals per player
  data/walter/unresolved.json      names that failed resolution
  data/walter/conflicts.json       guide-vs-live disagreements (live wins)
  data/walter/extraction_report.json  the audit numbers
"""
import csv
import difflib
import hashlib
import json
import os
import re
import sys

from player_names import PlayerIdentityResolver, search_key

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDE = os.path.join(ROOT, "data", "Walter Ai-2026_Advanced_Fantasy_Guide.md")
OUTDIR = os.path.join(ROOT, "data", "walter")
ADP = os.path.join(ROOT, "out", "data", "adp.json")

FUZZY_THRESHOLD = 0.90

# guide team codes -> shard team codes (adp.json uses LAR for the Rams)
TEAM_ALIAS = {"JAC": "JAX", "WSH": "WAS", "ARZ": "ARI"}

# common-nickname resolution pass, applied in norm space before fuzzy match
NICKNAMES = {"cameron": "cam", "christopher": "chris", "michael": "mike",
             "matthew": "matt", "joshua": "josh", "kenneth": "ken",
             "jonathon": "jonathan"}


def load_players():
    adp = json.load(open(ADP))
    identity = PlayerIdentityResolver(adp["players"])
    by_search = {}
    for p in adp["players"]:
        by_search.setdefault(search_key(p["name"]), []).append(p)
    # Prose attribution and fuzzy matching must not silently pick one player
    # from a collision bucket.  Ambiguous search keys stay out of this view.
    unique_search = {key: records[0] for key, records in by_search.items()
                     if len(records) == 1}
    return adp, identity, unique_search


class Resolver:
    def __init__(self, identity, by_search):
        self.identity = identity
        self.by_search = by_search
        self.keys = list(by_search)
        self.unresolved = []

    def resolve(self, raw, context=""):
        exact = self.identity.resolve(raw)
        if exact.record is not None:
            return exact.record, "exact"
        # nickname pass: swap the first token for its common short form
        n = search_key(raw)
        parts = n.split(" ", 1)
        if len(parts) == 2 and parts[0] in NICKNAMES:
            nick = NICKNAMES[parts[0]] + " " + parts[1]
            resolved = self.identity.resolve(nick)
            if resolved.record is not None:
                return resolved.record, f"nickname:{nick}"
        # fuzzy - stdlib ratio against the normalized universe
        best = difflib.get_close_matches(n, self.keys, n=1, cutoff=FUZZY_THRESHOLD)
        if best:
            return self.by_search[best[0]], f"fuzzy:{best[0]}"
        self.unresolved.append({"name_raw": raw, "context": context})
        return None, None


# tag types whose content is verifiable world-state
EVIDENCE_TYPES = {"regression_mechanism", "rookie_note", "situation_change",
                  "injury_flag", "walter_figure"}


def first_sentences(text, limit=520):
    t = re.sub(r"\s+", " ", text.strip())
    return t[:limit] + ("..." if len(t) > limit else "")


def parse(src_text):
    lines = src_text.split("\n")
    tags, structural, figures, conflicts = [], [], [], []
    adp, identity, by_search = load_players()
    res = Resolver(identity, by_search)

    # -- locate top-level sections: "# 8. My Targets" etc.
    sections = []
    for i, ln in enumerate(lines):
        m = re.match(r"^# (i|\d+)\. (.+)$", ln)
        if m:
            sections.append((i, m.group(2).strip()))
    sections.append((len(lines), "END"))
    sec_of = {}
    for (start, name), (end, _) in zip(sections, sections[1:]):
        sec_of[name] = (start, end)

    def section_lines(name):
        if name not in sec_of:
            return 0, []
        s, e = sec_of[name]
        return s, lines[s:e]

    def add_tag(player_raw, tag_type, cls, quote, l0, l1, section, confidence,
                extra=None):
        p, how = res.resolve(player_raw, context=f"{section} L{l0+1}")
        row = {"player_raw": player_raw, "tag": tag_type, "class": cls,
               "quote": quote, "line_start": l0 + 1, "line_end": l1 + 1,
               "section": section, "confidence": confidence,
               "resolved": bool(p)}
        if p:
            row["player_id"] = p["player_id"]
            row["player"] = p["name"]
            row["pos"] = p["pos"]
            row["team_live"] = p.get("team")
        if extra:
            row.update(extra)
        tags.append(row)
        return row

    def check_team(row, guide_team, l0, section):
        if not row.get("resolved") or not guide_team:
            return
        g = TEAM_ALIAS.get(guide_team, guide_team)
        live = row.get("team_live") or ""
        if g and live and g != live:
            conflicts.append({
                "player": row["player"], "field": "team",
                "guide_value": guide_team, "live_value": live,
                "line": l0 + 1, "section": section,
                "resolution": "live source wins; guide value logged only"})

    # -- headed player blocks: ###/####/##### Name then **POS · TEAM [· Rookie]**
    def headed_blocks(seclines, sec_start):
        out = []
        i = 0
        while i < len(seclines):
            m = re.match(r"^#{3,5}\s+(?:\d+\.\s+)?(.+?)\s*$", seclines[i])
            if m and i + 1 < len(seclines):
                b = re.match(r"^\*\*([A-Z/]{1,4})\s*·\s*([A-Z]{2,3})"
                             r"(?:\s*·\s*Rookie)?\*\*",
                             seclines[i + 1].strip())
                if b:
                    j = i + 2
                    body = []
                    while j < len(seclines) and not re.match(r"^#{1,5}\s", seclines[j]):
                        body.append(seclines[j])
                        j += 1
                    out.append({
                        "name": m.group(1).strip(), "pos": b.group(1),
                        "team": b.group(2),
                        "rookie": "Rookie" in seclines[i + 1],
                        "body": "\n".join(body).strip(),
                        "l0": sec_start + i, "l1": sec_start + j - 1})
                    i = j
                    continue
            i += 1
        # paired headings (two rookies, one shared paragraph): an empty body
        # inherits the next block's body, marked shared, line range extended
        for k in reversed(range(len(out) - 1)):
            if len(out[k]["body"]) < 20 and len(out[k + 1]["body"]) >= 20:
                out[k]["body"] = out[k + 1]["body"]
                out[k]["l1"] = out[k + 1]["l1"]
                out[k]["shared_note"] = True
        return out

    # extract Walter's own stated figures from a text block
    FIG_PATS = [
        (r"ceiling of ([A-Z]{1,3}\d{1,3})", "ceiling"),
        (r"ceiling:?\s*([A-Z]{1,3}\d{1,3})", "ceiling"),
        (r"floor \(([A-Z]{1,3}\d{1,3})\)", "floor"),
        (r"[Ww]alter[’']?s ([A-Z]{1,3}\d{1,3})", "rank"),
        (r"projected? (?:him )?as (?:the )?(?:overall )?([A-Z]{1,3}\d{1,3})", "rank"),
        (r"ranked (?:him )?(?:as )?(?:the )?(?:inside the )?([A-Z]{1,3}\d{1,3})", "rank"),
        (r"projects as the overall ([A-Z]{1,3}\d{1,3})", "rank"),
        (r"(\d+\.?\d*) (?:PPR )?(?:fantasy )?points per game", "ppg_mention"),
    ]

    HISTORICAL = re.compile(r"last season|would have|in 202[0-5]|rookie season",
                            re.I)

    def harvest_figures(name_raw, row, body, l0, section):
        for pat, kind in FIG_PATS:
            for m in re.finditer(pat, body):
                val = m.group(1)
                ctx = body[max(0, m.start() - 90):m.end() + 40]
                if HISTORICAL.search(ctx):
                    continue    # a stated 2025 fact is history, not a figure
                if kind == "ppg_mention" and not re.search(
                        r"project", body[max(0, m.start() - 80):m.start()], re.I):
                    continue    # only projection-context PPG, not history
                figures.append({
                    "player_raw": name_raw,
                    "player": row.get("player"),
                    "player_id": row.get("player_id"),
                    "kind": kind, "value": val,
                    "line": l0 + 1, "section": section,
                    "quote": first_sentences(ctx, 220)})

    # ---- section 3: regression tables (evidence, mechanism = td_rate)
    s3start, s3 = section_lines("Regression")
    direction = None
    for i, ln in enumerate(s3):
        if "### Negative Regression" in ln:
            direction = "negative"
        elif "### Positive Regression" in ln:
            direction = "positive"
        m = re.match(r"^\|\s*([A-Za-z][^|]+?)\s*\|\s*(QB|RB|WR|TE)\s*\|"
                     r"\s*([A-Z]{2,3})\s*\|\s*([\d.]+%)\s*\|\s*([\d.]+%)\s*\|"
                     r"\s*\*\*([+\-][\d.]+%)\*\*\s*\|", ln)
        if m and direction:
            row = add_tag(
                m.group(1), "regression_mechanism", "evidence",
                f"{direction} TD-rate regression: 2025 rate {m.group(4)}, "
                f"2026 projected {m.group(5)}, expected regression {m.group(6)}",
                s3start + i, s3start + i, "Regression", "explicit",
                {"mechanism": "td_rate", "direction": direction,
                 "rate_2025": m.group(4), "rate_2026_proj": m.group(5),
                 "expected_regression": m.group(6),
                 "routes_to_factor": "baseline_projection"})
            check_team(row, m.group(3), s3start + i, "Regression")
            # the CALL that the player is over/under-priced stays judgment
            add_tag(m.group(1),
                    "regression_candidate", "judgment",
                    f"listed as a 2026 {direction} TD-rate regression candidate",
                    s3start + i, s3start + i, "Regression", "explicit",
                    {"direction": direction})

    # ---- section 4: recency-bias targets (judgment) + injury facts
    s4start, s4 = section_lines("Injuries + Recency Bias")
    for b in headed_blocks(s4, s4start):
        row = add_tag(b["name"], "recency_bias_target", "judgment",
                      first_sentences(b["body"]), b["l0"], b["l1"],
                      "Injuries + Recency Bias", "explicit")
        check_team(row, b["team"], b["l0"], "Injuries + Recency Bias")
        harvest_figures(b["name"], row, b["body"], b["l0"],
                        "Injuries + Recency Bias")
    structural.append({
        "kind": "injury_base_rates", "class": "evidence",
        "routes_to_factor": "historical_priors",
        "data": {"RB": {"rate_per_game": 0.052, "pct_miss_one": 0.62, "games_per_injury": 3.9},
                 "WR": {"rate_per_game": 0.045, "pct_miss_one": 0.50, "games_per_injury": 3.2},
                 "TE": {"rate_per_game": 0.049, "pct_miss_one": 0.49, "games_per_injury": 2.6},
                 "QB": {"rate_per_game": 0.025, "pct_miss_one": 0.31, "games_per_injury": 3.1}},
        "quote": "NFL Position Injury Rates table - 15 years of data per the guide",
        "section": "Injuries + Recency Bias",
        "attribution": "Walter guide section 4"})

    # ---- section 5: strategies -> structural; the four named strategy picks
    s5start, s5 = section_lines("Draft Strategies")
    strat_names = [re.sub(r"\*\*", "", m.group(1)).strip()
                   for m in (re.match(r"^## (.+)$", ln) for ln in s5) if m]
    structural.append({
        "kind": "draft_strategies", "class": "evidence",
        "routes_to_factor": "pick_engine_conditioning",
        "data": strat_names,
        "quote": "strategy definitions incl. Robust/Hero/Zero RB, Elite TE or "
                 "PUNT, Patient QB, Josh Allen strategy, Ignore Bye Weeks",
        "section": "Draft Strategies", "attribution": "Walter guide section 5"})
    for nm in ("Brock Bowers", "Trey McBride", "Colston Loveland"):
        add_tag(nm, "strategy_pick", "judgment",
                "Elite Tight End or PUNT: draft one of these three with one of "
                "your first four picks; steep drop-off after them",
                s5start, s5start, "Draft Strategies", "inferred")
    add_tag("Josh Allen", "strategy_pick", "judgment",
            "The Josh Allen Strategy: draft him in the 3rd round as the first "
            "quarterback taken; a tier of his own on floor and ceiling",
            s5start, s5start, "Draft Strategies", "inferred")

    # ---- section 6: offseason changes -> evidence situation_change per bolded player
    s6start, s6 = section_lines("Offseason Changes")
    sub = None
    substart = s6start
    for i, ln in enumerate(s6):
        m = re.match(r"^## (.+)$", ln)
        if m:
            sub = m.group(1)
            substart = s6start + i
            continue
        if sub is None:
            continue
        for bm in re.finditer(r"\*\*([A-Z][A-Za-z.'’ ]+?)\*\*", ln):
            cand = bm.group(1).strip()
            words = cand.split()
            if not (2 <= len(words) <= 3):
                continue
            if search_key(cand) not in by_search:
                continue    # inline pass: only exact player names, no fuzz
            sent = first_sentences(ln, 300)
            add_tag(cand, "situation_change", "evidence", sent,
                    s6start + i, s6start + i, f"Offseason Changes / {sub}",
                    "inferred", {"routes_to_factor": "team_context+coaching"})

    # ---- section 7: rookies (evidence: capital + landing spot + role)
    s7start, s7 = section_lines("Rookies")
    tier = None
    for i, ln in enumerate(s7):
        tm = re.match(r"^#### Tier (\d)", ln)
        if tm:
            tier = int(tm.group(1))
    for b in headed_blocks(s7, s7start):
        if not b["rookie"]:
            continue
        row = add_tag(b["name"], "rookie_note", "evidence",
                      first_sentences(b["body"]) or "listed rookie, minimal note",
                      b["l0"], b["l1"], "Rookies", "explicit",
                      {"routes_to_factor": "historical_priors+surrounding"})
        check_team(row, b["team"], b["l0"], "Rookies")
        harvest_figures(b["name"], row, b["body"], b["l0"], "Rookies")

    # ---- section 8: targets (judgment, round context) + figures
    s8start, s8 = section_lines("My Targets")
    round_ctx = None
    rounds_by_line = {}
    for i, ln in enumerate(s8):
        rm = re.match(r"^### (Round .+)$", ln)
        if rm:
            round_ctx = rm.group(1)
        rounds_by_line[i] = round_ctx
    for b in headed_blocks(s8, s8start):
        rc = rounds_by_line.get(b["l0"] - s8start)
        row = add_tag(b["name"], "target", "judgment",
                      first_sentences(b["body"]), b["l0"], b["l1"],
                      "My Targets", "explicit",
                      {"round_context": rc})
        check_team(row, b["team"], b["l0"], "My Targets")
        harvest_figures(b["name"], row, b["body"], b["l0"], "My Targets")
    # inline multi-player endorsements in the targets chapter
    for i, ln in enumerate(s8):
        if re.search(r"(justify taking|cannot go wrong with|favorite running "
                     r"backs to target|round out my running back targets)", ln):
            for bm in re.finditer(r"\*\*([^*]+)\*\*", ln):
                for cand in re.split(r",| and ", bm.group(1)):
                    cand = cand.strip()
                    if search_key(cand) in by_search:
                        add_tag(cand, "target", "judgment",
                                first_sentences(ln, 300), s8start + i,
                                s8start + i, "My Targets", "inferred")

    # ---- section 9: do NOT draft (judgment, explicit)
    s9start, s9 = section_lines("Do NOT Draft")
    for b in headed_blocks(s9, s9start):
        row = add_tag(b["name"], "do_not_draft", "judgment",
                      first_sentences(b["body"]), b["l0"], b["l1"],
                      "Do NOT Draft", "explicit")
        check_team(row, b["team"], b["l0"], "Do NOT Draft")
        harvest_figures(b["name"], row, b["body"], b["l0"], "Do NOT Draft")

    # ---- section 10: sleepers (judgment, depth from ## heading)
    s10start, s10 = section_lines("Sleepers")
    depth = None
    depth_by_line = {}
    for i, ln in enumerate(s10):
        dm = re.match(r"^## (.+)$", ln)
        if dm:
            depth = dm.group(1)
        depth_by_line[i] = depth
    for b in headed_blocks(s10, s10start):
        row = add_tag(b["name"], "sleeper", "judgment",
                      first_sentences(b["body"]), b["l0"], b["l1"],
                      "Sleepers", "explicit",
                      {"depth": depth_by_line.get(b["l0"] - s10start)})
        check_team(row, b["team"], b["l0"], "Sleepers")
        harvest_figures(b["name"], row, b["body"], b["l0"], "Sleepers")

    # ---- document-wide figures pass: high-precision patterns only, attached
    # to a player named on the same line or to the enclosing headed block
    GLOBAL_FIGS = [
        (re.compile(r"Walter Ceiling:\s*([A-Z]{1,3}\d{1,3})"), "ceiling"),
        (re.compile(r"ceiling of (?:overall )?([A-Z]{1,3}\d{1,3})"), "ceiling"),
        (re.compile(r"([A-Z]{1,3}\d{1,3}) (?:overall )?ceiling"), "ceiling"),
        (re.compile(r"projects? [A-Za-z ]{0,24}as the (?:overall )?([A-Z]{1,3}\d{1,3})"), "rank"),
    ]
    seen_figs = {(f.get("player_id"), f["kind"], f["value"]) for f in figures}
    block_player = None
    for i, ln in enumerate(lines):
        hm = re.match(r"^#{1,6}\s+(?:\d+\.\s+)?(.+?)\s*$", ln)
        if hm:
            # a heading that names a player sets the block context; any other
            # heading AT ANY LEVEL clears it so context never leaks across
            # sections
            block_player = by_search.get(search_key(hm.group(1)))
        if not any(pt.search(ln) for pt, _ in GLOBAL_FIGS):
            continue
        # sentence scope: a line can name several players with a figure each;
        # attribution order: unique name in the sentence, then the enclosing
        # headed block, then a unique name on the line - else skip as ambiguous
        line_named = [p for key, p in by_search.items()
                      if len(p["name"]) > 7 and p["name"] in ln.replace("**", "")]
        line_ids = {p["player_id"] for p in line_named}
        for sent in re.split(r"(?<=[.!?])\s+", ln):
            if HISTORICAL.search(sent):
                continue
            clean = sent.replace("**", "")
            named = [p for key, p in by_search.items()
                     if len(p["name"]) > 7 and p["name"] in clean]
            ids = {p["player_id"] for p in named}
            owner = named[0] if len(ids) == 1 else None
            if owner is None and not ids:
                owner = block_player or (
                    line_named[0] if len(line_ids) == 1 else None)
            if owner is None:
                continue
            for pt, kind in GLOBAL_FIGS:
                for m in pt.finditer(sent):
                    key = (owner["player_id"], kind, m.group(1))
                    if key in seen_figs:
                        continue
                    seen_figs.add(key)
                    figures.append({
                        "player_raw": owner["name"], "player": owner["name"],
                        "player_id": owner["player_id"], "kind": kind,
                        "value": m.group(1), "line": i + 1,
                        "section": "document-wide pass",
                        "quote": first_sentences(sent, 220)})

    # ---- section 12: change log -> per-player revision signals
    s12start, s12 = section_lines("Change Log")
    changelog_entries = []
    for i, ln in enumerate(s12):
        m = re.match(r"^\*\*(August \d+\w*):\*\*\s*(.+)$", ln)
        if not m:
            continue
        date_raw, body = m.group(1), m.group(2)
        day = int(re.search(r"\d+", date_raw).group())
        iso = f"2026-08-{day:02d}"
        low = body.lower()
        if "do not draft" in low.replace("not d", "not d") or "not draft" in low:
            direction = "down" if low.startswith("added") else (
                "up" if low.startswith("removed") else "neutral")
        elif "targets" in low or "sleeper" in low:
            direction = "up" if low.startswith("added") else (
                "down" if low.startswith("removed") else "neutral")
        elif low.startswith("updated"):
            direction = "neutral"
        else:
            direction = "neutral"
        nb = search_key(body)
        def present(p):
            return re.search(r"(?<![a-z0-9])" + re.escape(search_key(p["name"]))
                             + r"s?(?![a-z0-9])", nb)
        subj = re.match(r"(?:Added|Removed) (.+?) (?:to|from|as)", body) or \
               re.match(r"Updated (?:the )?(.+?) writeup", body)
        named = []
        if subj:
            for cand in re.split(r",| and ", subj.group(1)):
                pp = by_search.get(search_key(cand.strip()))
                if pp:
                    named.append((pp["name"], direction))
        if not named:
            # no resolvable subject: fall back to mentions, direction from the
            # verb in a +-70 char window around each name
            for key, pp in by_search.items():
                m2 = present(pp)
                if not m2:
                    continue
                before = nb[max(0, m2.start() - 25):m2.start()]
                after = nb[m2.end():m2.end() + 25]
                if "callout for" in before or "added" in before:
                    d = "up"
                elif "was removed" in after or "removed" in before[-12:]:
                    d = "down"
                else:
                    d = direction
                named.append((pp["name"], d))
        changelog_entries.append({
            "date": iso, "direction": direction,
            "players": sorted({n for n, _ in named}),
            "player_directions": {n: d for n, d in named},
            "entry": body, "line": s12start + i + 1})
    by_player = {}
    for e in changelog_entries:
        for nm in e["players"]:
            d = e.get("player_directions", {}).get(nm, e["direction"])
            r = by_player.setdefault(nm, {"revision_count": 0,
                                          "last_revised": None,
                                          "revision_direction": None,
                                          "entries": []})
            r["revision_count"] += 1
            if r["last_revised"] is None or e["date"] >= r["last_revised"]:
                r["last_revised"] = e["date"]
                r["revision_direction"] = d
            r["entries"].append({"date": e["date"], "direction": d,
                                 "entry": e["entry"], "line": e["line"]})

    # figures are evidence (Walter's stated numbers - a named comparison series)
    for f in figures:
        f["class"] = "evidence"

    return {"tags": tags, "structural": structural, "figures": figures,
            "conflicts": conflicts, "unresolved": res.unresolved,
            "changelog": {"entries": changelog_entries, "by_player": by_player},
            "adp": adp}


def main():
    src_text = open(GUIDE, encoding="utf-8").read()
    sha = hashlib.sha256(src_text.encode()).hexdigest()
    os.makedirs(OUTDIR, exist_ok=True)

    prev_sha = None
    rp = os.path.join(OUTDIR, "extraction_report.json")
    if os.path.exists(rp):
        prev_sha = json.load(open(rp)).get("source_sha256")

    out = parse(src_text)

    # audit numbers
    adp = out.pop("adp")
    top200 = sorted([p for p in adp["players"]
                     if (p.get("adp_sleeper") or 999) < 900],
                    key=lambda p: p["adp_sleeper"])[:200]
    tagged_ids = {t.get("player_id") for t in out["tags"] if t.get("player_id")}
    fig_ids = {f.get("player_id") for f in out["figures"] if f.get("player_id")}
    covered = [p for p in top200 if p["player_id"] in (tagged_ids | fig_ids)]
    ev = [t for t in out["tags"] if t["class"] == "evidence"]
    jd = [t for t in out["tags"] if t["class"] == "judgment"]
    by_type = {}
    for t in out["tags"]:
        by_type[t["tag"]] = by_type.get(t["tag"], 0) + 1
    by_pos = {}
    for t in out["tags"]:
        if t.get("pos"):
            by_pos[t["pos"]] = by_pos.get(t["pos"], 0) + 1

    report = {
        "source": "data/Walter Ai-2026_Advanced_Fantasy_Guide.md",
        "source_sha256": sha,
        "previous_sha256": prev_sha,
        "changed_since_last_parse": bool(prev_sha and prev_sha != sha),
        "tag_total": len(out["tags"]),
        "tags_by_type": by_type,
        "tags_by_pos": by_pos,
        "evidence_count": len(ev),
        "judgment_count": len(jd),
        "figures_count": len(out["figures"]),
        "structural_count": len(out["structural"]),
        "top200_coverage_pct": round(100 * len(covered) / 200, 1),
        "top200_covered": len(covered),
        "unresolved_count": len(out["unresolved"]),
        "resolved_tag_count": sum(1 for t in out["tags"] if t["resolved"]),
        "conflict_count": len(out["conflicts"]),
        "changelog_entries": len(out["changelog"]["entries"]),
        "changelog_players": len(out["changelog"]["by_player"]),
    }

    def dump(name, obj):
        with open(os.path.join(OUTDIR, name), "w") as fh:
            json.dump({"source_sha256": sha, "data": obj}, fh, indent=1)

    dump("tags.json", out["tags"])
    dump("structural.json", out["structural"])
    dump("walter_figures.json", out["figures"])
    dump("changelog.json", out["changelog"])
    dump("unresolved.json", out["unresolved"])
    dump("conflicts.json", out["conflicts"])
    with open(rp, "w") as fh:
        json.dump(report, fh, indent=1)

    print(json.dumps(report, indent=1))
    if report["changed_since_last_parse"]:
        print("NOTE: source changed since last parse - outputs rewritten, "
              "old sha " + prev_sha[:12])


if __name__ == "__main__":
    main()
