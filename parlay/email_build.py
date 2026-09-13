"""email_build.py - render the five tickets as an executive HTML email."""

CSS = """
body{margin:0;padding:0;background:#0f1115;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;}
.wrap{max-width:760px;margin:0 auto;background:#0f1115;padding:28px 18px 40px;}
.hd{border-bottom:2px solid #c8a94b;padding-bottom:14px;margin-bottom:6px;}
.hd h1{margin:0;font-size:21px;letter-spacing:.4px;color:#f4f4f5;font-weight:700;}
.hd .sub{color:#8b8f98;font-size:12px;margin-top:5px;letter-spacing:.3px;}
.tier{margin-top:26px;}
.tier .lbl{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;color:#c8a94b;font-weight:700;margin-bottom:8px;}
.card{background:#171a21;border:1px solid #252932;border-radius:7px;padding:16px 16px 12px;margin-bottom:12px;}
.card .top{display:block;border-bottom:1px solid #252932;padding-bottom:10px;margin-bottom:10px;}
.tid{font-size:15px;color:#f4f4f5;font-weight:700;}
.odds{float:right;font-size:19px;color:#5ec97b;font-weight:700;}
.meta{color:#8b8f98;font-size:11.5px;margin-top:4px;}
table{width:100%;border-collapse:collapse;font-size:12.5px;}
th{text-align:left;color:#6d727c;font-weight:600;font-size:10px;letter-spacing:.9px;
   text-transform:uppercase;padding:0 6px 6px 0;border-bottom:1px solid #252932;}
td{padding:6px 6px 6px 0;color:#d4d6db;border-bottom:1px solid #1c1f26;}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;}
.pl{color:#f4f4f5;font-weight:600;}
.tm{color:#6d727c;font-size:10.5px;}
.stat{color:#a9adb6;}
.hi{color:#5ec97b;font-weight:700;}
.warn{color:#e0a33c;}
.foot{margin-top:9px;font-size:11.5px;color:#8b8f98;line-height:1.65;}
.note{background:#171a21;border-left:3px solid #c8a94b;padding:13px 15px;margin-top:24px;
      color:#a9adb6;font-size:12.5px;line-height:1.7;border-radius:0 5px 5px 0;}
.note b{color:#f4f4f5;}
.note table{margin-top:9px;}
.note td{font-size:12px;border-bottom:1px solid #21242c;}
.disc{margin-top:22px;padding-top:14px;border-top:1px solid #252932;
      color:#5c6069;font-size:10.5px;line-height:1.65;}
"""

def odds_str(a):
    return f"+{a}" if a > 0 else str(a)

def render(meta, tickets, notes_html):
    tiers = {}
    for t in tickets:
        tiers.setdefault(t["tier"], []).append(t)
    parts = [f"<style>{CSS}</style>", "<div class='wrap'>",
             "<div class='hd'><h1>Sunday Prop Card</h1>",
             f"<div class='sub'>{meta['date']} &nbsp;|&nbsp; {meta['slate']} &nbsp;|&nbsp; "
             f"built {meta['built']}</div></div>"]
    order = ["HIGH RISK / HIGH REWARD", "MEDIUM RISK / MEDIUM REWARD", "LOW RISK / LOW REWARD"]
    for tier in order:
        if tier not in tiers:
            continue
        parts.append(f"<div class='tier'><div class='lbl'>{tier}</div>")
        for t in tiers[tier]:
            ev_cls = "hi" if t["ev"] >= 1.0 else "warn"
            parts.append("<div class='card'><div class='top'>")
            parts.append(f"<span class='tid'>{t['id']} &nbsp;<span class='tm'>{t['n']} legs</span></span>"
                         f"<span class='odds'>{odds_str(t['american'])}</span>")
            parts.append(f"<div class='meta'>hit probability <b style='color:#d4d6db'>{t['joint']*100:.1f}%</b>"
                         f" &nbsp;&middot;&nbsp; correlation lift {t['lift']*100:+.0f}%"
                         f" &nbsp;&middot;&nbsp; EV per $1 <span class='{ev_cls}'>{t['ev']:.2f}</span>"
                         f" &nbsp;&middot;&nbsp; stake {t['stake']}</div>")
            parts.append("</div><table><tr><th>Player</th><th>Prop</th>"
                         "<th class='num'>Take</th><th class='num'>Model</th>"
                         "<th class='num'>Win %</th><th class='num'>Min price</th></tr>")
            for l in t["legs"]:
                parts.append(
                    f"<tr><td class='pl'>{l['player']}<div class='tm'>{l['team']} &middot; {l['game']}</div></td>"
                    f"<td class='stat'>{l['label']}</td>"
                    f"<td class='num'><b style='color:#f4f4f5'>o{l['line']}</b></td>"
                    f"<td class='num tm'>{l['mean']:.1f}</td>"
                    f"<td class='num'>{l['p']*100:.0f}%</td>"
                    f"<td class='num'>{odds_str(l['minprice'])}</td></tr>")
            parts.append("</table>")
            parts.append(f"<div class='foot'>{t['why']}</div></div>")
        parts.append("</div>")
    parts.append(notes_html)
    parts.append("<div class='disc'>Model output, not advice. Expected value describes a long run of "
                 "identical decisions, never one Sunday. Verify every line and price at your book before "
                 "placing; a leg taken below its minimum price turns the ticket negative. Confirm inactives "
                 "after the official list drops 90 minutes before kickoff. Bet only what you can lose.</div>")
    parts.append("</div>")
    return "".join(parts)
