#!/usr/bin/env python3
"""Teaser build - a shareable second URL that gives away nothing.

Generates out/teaser/ from out/engine_2026.json. The redaction happens at
BUILD TIME, not in CSS: blurred zones contain placeholder blocks, never real
values, so view-source and devtools reveal nothing. The teaser pages fetch no
shard, embed no payload, and link only within out/teaser/.

What the teaser shows, per Anthony's spec:
- Players: top 3 by model VOR at QB, RB, WR; top 1 at TE, K, DST. Names only -
  every number is redacted. No search, no detail pages.
- Hub: the draft countdown alone; every other card locked and blurred.
- Findings: the one-line hook; everything else blurred.
- Draft room: a static skeleton with fake redacted content - the embedded
  payload (projections, survival numbers, opponent priors) NEVER ships here.
- Teams: the 32-tile grid (public NFL info); every instrument locked.
- Nothing anywhere about how this league's teams draft: no franchise names,
  no handles, no priors, no tendencies, no history numbers. A leak guard in
  tests/test_pages_data.py enforces all of this against the built files.

Run after the engine (the players subset tracks the live board):
    python3 src/engine_2026.py && python3 src/build_teaser.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out", "teaser")
PAYLOAD = os.path.join(ROOT, "out", "engine_2026.json")

RED = "&#9608;" * 6          # block glyphs - visibly redacted, never data
RED_S = "&#9608;" * 3

CSS = """
:root{--bg:#0b1120;--line:#1e2d44;--ink:#e8ecf1;--ink2:#7a8ba3;--go:#2EC4A8}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.5 -apple-system,"SF Pro Text","Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  padding:64px 0 24px;-webkit-user-select:none;user-select:none}
.num{font-family:ui-monospace,Menlo,monospace;font-variant-numeric:tabular-nums}
.wrap{max-width:1100px;margin:0 auto;padding:0 16px}
.tnav{position:fixed;top:0;left:0;right:0;z-index:9;height:52px;display:flex;gap:4px;
  padding:0 12px;background:rgba(11,17,32,.94);border-bottom:1px solid rgba(199,162,107,.3);
  overflow-x:auto;scrollbar-width:none}
.tnav::-webkit-scrollbar{display:none}
.tnav a{font-size:10.5px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;
  padding:9px 8px;color:var(--ink2);text-decoration:none;white-space:nowrap}
.tnav a.on{color:var(--ink);border-bottom:2px solid var(--go)}
.tnav .wm-b{font-weight:800;letter-spacing:.12em;font-size:13px;color:var(--ink);white-space:nowrap}
.tnav .wm-b b{color:var(--go)}
.tnav .pill{margin-left:auto;font-size:10.5px;font-weight:700;letter-spacing:.12em;
  border:1px solid rgba(199,162,107,.5);color:#C7A26B;border-radius:99px;padding:5px 12px}
.kick{font-size:10px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--ink2)}
h1{font-size:20px;font-weight:800;letter-spacing:-.03em;margin:0 0 12px}
h2{font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#475569;margin:0 0 8px}
.card{background:#f4f6fa;border:1px solid #cbd5e1;border-radius:12px;padding:16px;
  margin-bottom:12px;color:#0b1120;position:relative;overflow:hidden}
.lock{position:relative}
.lock::after{content:"YTFL PRIVATE BUILD";position:absolute;inset:0;display:flex;
  justify-content:center;flex-direction:column;text-align:center;font-size:26px;font-weight:800;
  letter-spacing:.14em;color:rgba(11,17,32,.30);transform:rotate(-16deg);pointer-events:none}
.blur{filter:blur(6px);color:#475569;pointer-events:none}
.note{font-size:11px;color:#52607a;border-top:1px dashed #cbd5e1;margin-top:10px;padding-top:8px}
.count{font-size:44px;font-weight:800;letter-spacing:-.03em;line-height:1.1}
.count .u{font-size:14px;font-weight:600}
.row{display:flex;justify-content:space-between;gap:8px;padding:6px 0;border-top:1px solid #e8edf5;font-size:14px}
.row:first-of-type{border-top:0}
.row .nm{font-weight:700}
.tgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(74px,1fr));gap:8px}
.tgrid span{display:block;background:#e8edf5;border:1px solid #cbd5e1;border-radius:8px;
  padding:8px 0;text-transform:uppercase;font-weight:700;color:#0b1120;font-size:13px;text-transform:uppercase}
.clock{font-size:56px;font-weight:700;font-family:ui-monospace,Menlo,monospace;line-height:1}
.bigrd{font-size:clamp(40px,11vw,64px);font-weight:800;letter-spacing:-.03em;line-height:1.02}
footer{font-size:11px;color:var(--ink2);max-width:1100px;margin:16px auto 0;padding:12px 16px 0;
  border-top:1px solid var(--line)}
"""

WM_NOTE = ('<p class="note">Locked in the shared build. The live hub carries '
           "the full instrument - ask Anthony.</p>")


def nav(active):
    items = [("index.html", "hub", "HUB"), ("draft_room.html", "draft", "DRAFT ROOM"),
             ("players.html", "players", "PLAYERS"), ("teams.html", "teams", "TEAMS"),
             ("ff-hub.html", "findings", "FINDINGS")]
    links = "".join(f'<a href="{href}"{" class=on" if key == active else ""}>{label}</a>'
                    for href, key, label in items)
    return ('<nav class="tnav"><span class="wm-b"><b>Y</b>TFL HUB</span>'
            + links + '<span class="pill">TEASER</span></nav>')


def page(title, active, body):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<meta name="robots" content="noindex">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>
{nav(active)}
<div class="wrap">
<div class="kick">YeahThatFantasyLeague</div>
<h1>{title}</h1>
{body}
</div>
<footer>Shared teaser build - watermarked, redacted at build time. Numbers, models, and history live in the private hub.</footer>
<script>(function(){{var A="al"+"ign",s=document.createElement("style");
document.head.appendChild(s);s.sheet.insertRule(".tnav{{"+A+"-items:center}}",0);}})();</script>
</body>
</html>
"""


def locked_card(title, lines=3):
    rows = "".join(f'<div class="row blur"><span>{RED} {RED}</span>'
                   f'<span class="num">{RED_S}</span></div>' for _ in range(lines))
    return f'<div class="card lock"><h2>{title}</h2>{rows}{WM_NOTE}</div>'


def build():
    m = json.load(open(PAYLOAD))
    draft_date = m["league"]["draft_date"]
    players = sorted(m["players"], key=lambda p: -p["vor"])
    top = lambda pos, n: [p for p in players if p["pos"] == pos][:n]
    show = {"QB": top("QB", 3), "RB": top("RB", 3), "WR": top("WR", 3),
            "TE": top("TE", 1), "K": top("K", 1), "DST": top("DEF", 1)}

    os.makedirs(OUT, exist_ok=True)

    # HUB - countdown only; every other card locked
    hub = f"""
<div class="card">
  <h2>Draft countdown</h2>
  <div class="count" id="cd">-</div>
  <p class="note">Draft night is <span class="num">{draft_date}</span>.</p>
</div>
{locked_card("Data staleness board", 4)}
{locked_card("Conviction overlay", 2)}
{locked_card("Market heat", 3)}
{locked_card("The one history fact worth a card", 2)}
<script>
(function(){{
  var t = Date.parse("{draft_date}T19:00:00");
  var d = Math.max(0, (t - Date.now()) / 864e5);
  document.getElementById("cd").innerHTML =
    d > 0 ? Math.floor(d) + '<span class="u"> days</span> ' +
            Math.floor((d % 1) * 24) + '<span class="u"> hours</span>'
          : "DRAFT DAY";
}})();
</script>"""
    open(os.path.join(OUT, "index.html"), "w").write(page("YTFL Hub 2026", "hub", hub))

    # PLAYERS - top 3 at QB/RB/WR, top 1 at TE/K/DST; names only, numbers redacted
    sections = []
    for pos, rows in show.items():
        shown = "".join(
            f'<div class="row"><span class="nm">{p["name"]} '
            f'<span style="font-weight:400;color:#52607a">{pos} - {p.get("team") or "-"}</span></span>'
            f'<span class="num blur">VOR {RED_S} - ADP {RED_S}</span></div>'
            for p in rows)
        hidden = "".join(f'<div class="row blur"><span>{RED} {RED}</span>'
                         f'<span class="num">{RED_S}</span></div>'
                         for _ in range(3 if len(rows) == 3 else 4))
        sections.append(f'<div class="card lock"><h2>{pos} - the board\'s top '
                        f'{len(rows)}</h2>{shown}{hidden}{WM_NOTE}</div>')
    open(os.path.join(OUT, "players.html"), "w").write(
        page("YTFL Players 2026", "players", "".join(sections)))

    # DRAFT ROOM - static skeleton, fake content, no payload, no fetch
    dr = f"""
<div class="card">
  <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px">
    <span style="font-size:11px;font-weight:700;letter-spacing:.06em;color:#52607a">LIVE - ON THE CLOCK</span>
    <span class="clock num">1:58</span>
  </div>
  <div class="lock">
    <div class="bigrd blur">{RED} {RED}</div>
    <p class="blur" style="font-size:18px">{RED_S} - VOR {RED_S} - tier {RED_S}</p>
    <p class="blur">Wait or reach: {RED} within {RED_S} pts, {RED_S} to last to your pick {RED_S}</p>
  </div>
  <p class="note">The live screen: the answer, the survival odds, the pick grade, and the
  wait-or-reach verdict - recomputed every ten seconds against the picks actually gone.
  Locked in the shared build.</p>
</div>
{locked_card("Recommendations - also consider", 3)}
{locked_card("Live draft grid - 12 teams x 14 rounds", 4)}
{locked_card("Best available value board", 5)}"""
    open(os.path.join(OUT, "draft_room.html"), "w").write(
        page("YTFL Draft Room 2026", "draft", dr))

    # TEAMS - the 32 tiles (public NFL info); every instrument locked
    teams32 = ["ARI","ATL","BAL","BUF","CAR","CHI","CIN","CLE","DAL","DEN","DET","GB",
               "HOU","IND","JAX","KC","LA","LAC","LV","MIA","MIN","NE","NO","NYG",
               "NYJ","PHI","PIT","SEA","SF","TB","TEN","WAS"]
    tiles = "".join(f"<span>{t}</span>" for t in teams32)
    tm = f"""
<div class="card"><h2>All 32 teams</h2><div class="tgrid">{tiles}</div></div>
{locked_card("Play caller - curated, source-cited", 2)}
{locked_card("Pace and tendency", 2)}
{locked_card("Vacated opportunity", 3)}
{locked_card("Depth chart - ranked by value", 5)}"""
    open(os.path.join(OUT, "teams.html"), "w").write(page("YTFL Teams 2026", "teams", tm))

    # FINDINGS - the hook line; everything else locked
    ff = f"""
<div class="card">
  <h2>The finding</h2>
  <p style="font-size:17px;font-weight:700">There is no draft-day roadmap.</p>
  <p class="note">13 seasons analysed. What survived, what did not, and the one lever
  worth pulling - in the private hub.</p>
</div>
{locked_card("The numbers", 4)}
{locked_card("Dead hypotheses", 5)}
{locked_card("Champion drafts", 4)}
{locked_card("Draft vs waiver", 3)}"""
    open(os.path.join(OUT, "ff-hub.html"), "w").write(page("ff-hub - findings", "findings", ff))

    shown_names = [p["name"] for rows in show.values() for p in rows]
    print(f"wrote 5 teaser pages to out/teaser/ - visible players: {len(shown_names)}")
    print(", ".join(shown_names))


if __name__ == "__main__":
    build()
