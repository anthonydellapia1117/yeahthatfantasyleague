"""email_v3.py - compact mobile-first renderer.

A <style> block for repeated typography, inline styles only where a mail
client is likely to strip the class. Short class names keep the payload
small enough to pass through the mail API in one piece.
"""
F = "system-ui,-apple-system,Helvetica,Arial,sans-serif"
CSS = f"""<style>
.w{{background:#0d0f13;margin:0;padding:0;font-family:{F};}}
.c{{background:#161a21;border:1px solid #262b35;border-radius:10px;margin:0 0 16px;}}
.t1{{font:700 22px/1.15 {F};color:#f5f6f7;}}
.t2{{font:400 12px/1.5 {F};color:#8a8f99;margin-top:6px;}}
.tag{{font:700 10px/1 {F};letter-spacing:1.6px;text-transform:uppercase;}}
.nm{{font:700 17px/1.2 {F};color:#f5f6f7;margin-top:5px;}}
.sub{{font:400 11.5px/1.4 {F};color:#666c77;margin-top:3px;}}
.od{{font:700 27px/1 {F};color:#5ec97b;}}
.ret{{font:400 11px/1.4 {F};color:#666c77;margin-top:5px;}}
.num{{width:20px;height:20px;border-radius:10px;background:#262b35;color:#8a8f99;
 font:700 11px/20px {F};text-align:center;}}
.pl{{font:600 13px/1.3 {F};color:#8a8f99;}}
.sel{{font:700 20px/1.25 {F};color:#d4af5f;margin:2px 0 4px;}}
.met{{font:400 11.5px/1.4 {F};color:#666c77;}}
.met b{{color:#8a8f99;font-weight:600;}}
.box{{background:#0d0f13;border-radius:7px;padding:11px 13px;}}
.kl{{font:400 11px/1.5 {F};color:#666c77;}}
.kv{{font:700 15px/1.3 {F};color:#f5f6f7;}}
.why{{font:400 12px/1.6 {F};color:#8a8f99;margin-top:11px;}}
.nt{{background:#161a21;border-radius:0 8px 8px 0;margin:0 0 13px;}}
.nh{{font:700 13px/1.3 {F};color:#f5f6f7;margin-bottom:7px;}}
.nb{{font:400 12.5px/1.7 {F};color:#8a8f99;}}
.nb b{{color:#f5f6f7;}}
.ft{{font:400 10.5px/1.6 {F};color:#555a64;}}
a{{color:#d4af5f;text-decoration:none;}}
</style>"""

def odds(a): return f"+{a}" if a > 0 else str(a)

def _row(i, l, last):
    bd = "" if last else "border-bottom:1px solid #262b35;"
    sel = l["label"]
    if l.get("link"):
        sel = f'<a href="{l["link"]}">{sel} &rsaquo;</a>'
    return (f'<tr><td style="padding:13px 0 12px;{bd}">'
      f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
      f'<td width="26" valign="top" style="width:26px;padding-top:3px;"><div class="num">{i}</div></td>'
      f'<td valign="top"><div class="pl">{l["player"]}</div>'
      f'<div class="sel">{sel}</div>'
      f'<div class="met">{l["game"]} &middot; projection <b>{l["mean"]:.0f}</b>'
      f' &middot; cushion <b>{l["cushion"]*100:.0f}%</b>'
      f' &middot; win <b>{l["p"]*100:.0f}%</b></div>'
      f'</td></tr></table></td></tr>')

def _card(t):
    rows = "".join(_row(i+1, l, i == len(t["legs"])-1) for i, l in enumerate(t["legs"]))
    ec = "#5ec97b" if t["ev"] >= 1.0 else "#e0a33c"
    return (f'<table width="100%" cellpadding="0" cellspacing="0" border="0" class="c">'
      f'<tr><td style="padding:16px 16px 4px;">'
      f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
      f'<td valign="top"><div class="tag" style="color:{t["tiercolor"]};">{t["tier"]}</div>'
      f'<div class="nm">{t["name"]}</div>'
      f'<div class="sub">{t["n"]} legs &middot; enter as one SGP</div></td>'
      f'<td valign="top" align="right" style="white-space:nowrap;">'
      f'<div class="od">{odds(t["american"])}</div>'
      f'<div class="ret">${t["stake"]:.0f} returns ${t["ret"]:.0f}</div></td></tr></table></td></tr>'
      f'<tr><td style="padding:6px 16px 14px;">'
      f'<table width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table></td></tr>'
      f'<tr><td style="padding:0 16px 15px;"><div class="box">'
      f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
      f'<td class="kl">hits<br><span class="kv">{t["joint"]*100:.1f}%</span></td>'
      f'<td class="kl">my fair price<br><span class="kv">{odds(t["fair"])}</span></td>'
      f'<td class="kl">EV per $1<br><span class="kv" style="color:{ec};">{t["ev"]:.2f}</span></td>'
      f'<td class="kl">worst cushion<br><span class="kv">{t["mincush"]*100:.0f}%</span></td>'
      f'</tr></table></div><div class="why">{t["why"]}</div></td></tr></table>')

def note(title, body, color="#d4af5f"):
    return (f'<table width="100%" cellpadding="0" cellspacing="0" border="0" class="nt" '
      f'style="border-left:3px solid {color};"><tr><td style="padding:14px 15px;">'
      f'<div class="nh">{title}</div><div class="nb">{body}</div></td></tr></table>')

def render(meta, tickets, notes):
    cards = "".join(_card(t) for t in tickets)
    return (CSS + f'<table width="100%" cellpadding="0" cellspacing="0" border="0" class="w">'
      f'<tr><td align="center" style="padding:20px 12px 34px;">'
      f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">'
      f'<tr><td style="padding-bottom:16px;border-bottom:2px solid #d4af5f;">'
      f'<div class="t1">Sunday Prop Card</div>'
      f'<div class="t2">{meta["date"]}<br>{meta["slate"]} &middot; built {meta["built"]}</div></td></tr>'
      f'<tr><td style="padding-top:20px;">{cards}</td></tr><tr><td>{notes}</td></tr>'
      f'<tr><td style="padding-top:18px;border-top:1px solid #262b35;" class="ft">'
      f'Model output, not advice. Expected value describes a long run of identical decisions, '
      f'never one Sunday. Confirm every line and price in your own app before placing. Confirm '
      f'inactives after the official list posts 90 minutes before kickoff. Must be 21+. Bet only '
      f'what you can lose. Gambling problem? Call 1-800-GAMBLER.</td></tr>'
      f'</table></td></tr></table>')
