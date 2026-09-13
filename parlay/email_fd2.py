"""email_fd2.py - FanDuel card built for what Gmail actually keeps.

Inspection of the stored copy of the first FanDuel email showed Gmail strips
the <style> block, every class attribute, and the `background` shorthand on
inline styles. The buttons survived as white text on a white page. This
version assumes a white background, uses only inline properties Gmail was
seen to keep (color, font-size, font-weight, padding, border, border-radius,
width, align, valign) plus the HTML bgcolor attribute for button fill, and
prints the raw URL under every button as a second, unstyled tap target.

Per ticket there is also a single whole-parlay link in FanDuel's indexed
share format (marketId[0]..[n], selectionId[0]..[n]).
"""
from urllib.parse import quote
F="Helvetica,Arial,sans-serif"
LBL={"rec_yards":"Receiving Yards","pass_yards":"Passing Yards","receptions":"Receptions",
     "rush_rec_yards":"Rush + Rec Yards"}
GAMEL={"ARI@LAC":"ARI @ LAC 4:25","GB@MIN":"GB @ MIN 4:25","WAS@PHI":"WAS @ PHI 4:25",
       "MIA@LV":"MIA @ LV 4:25","DAL@NYG":"DAL @ NYG 8:20"}
BLUE="#1493ff"; INK="#111318"; MUTE="#5a6070"; LINE="#dfe3ea"; GOLD="#9a6d00"
def odds(a): return f"+{a}" if a>0 else str(a)
def parse_ids(link):
    q=link.split("?",1)[1]; d=dict(p.split("=",1) for p in q.split("&"))
    return d["marketId"], d["selectionId"]
def bulk_link(legs):
    parts=[]
    for i,l in enumerate(legs):
        mk,sel=parse_ids(l["link"])
        parts.append(f"marketId%5B{i}%5D={mk}&selectionId%5B{i}%5D={sel}")
    return "https://sportsbook.fanduel.com/addToBetslip?"+"&".join(parts)
def button(href,label,fill=BLUE,fg="#ffffff",wide=False):
    w=' width="100%"' if wide else ''
    return (f'<table cellpadding="0" cellspacing="0" border="0"{w} style="margin-top:8px;"><tr>'
      f'<td bgcolor="{fill}" align="center" style="background-color:{fill};border-radius:8px;'
      f'border:2px solid {fill};padding:12px 16px;">'
      f'<a href="{href}" style="color:{fg};font-family:{F};font-size:15px;font-weight:bold;'
      f'text-decoration:none;display:block;">{label}</a></td></tr></table>')
def row(i,l,last):
    bd="" if last else f"border-bottom:1px solid {LINE};"
    return (f'<tr><td style="padding:12px 0 12px;{bd}">'
      f'<div style="font-family:{F};font-size:13px;color:{MUTE};">{i}. {l["player"]} &middot; {GAMEL[l["game"]]}</div>'
      f'<div style="font-family:{F};font-size:19px;font-weight:bold;color:{INK};margin-top:2px;">'
      f'Over {l["line"]} {LBL[l["stat"]]} <span style="color:{MUTE};font-size:14px;font-weight:normal;">{odds(l["price"])}</span></div>'
      f'<div style="font-family:{F};font-size:12px;color:{MUTE};margin-top:3px;">FanDuel mean {l["fd_mean"]:.0f}'
      f' &middot; cushion {l["cushion"]*100:.0f}% &middot; win {l["p"]*100:.0f}% &middot; leg EV {l["ev1"]:.2f}</div>'
      + button(l["link"],"Add this leg to FanDuel slip &rsaquo;") +
      f'<div style="font-family:{F};font-size:11px;color:{MUTE};margin-top:5px;word-break:break-all;">'
      f'<a href="{l["link"]}" style="color:{BLUE};">{l["link"]}</a></div>'
      f'</td></tr>')
def card(t):
    rows="".join(row(i+1,l,i==len(t["legs"])-1) for i,l in enumerate(t["legs"]))
    bl=bulk_link(t["legs"])
    return (f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="border:1px solid {LINE};border-radius:10px;margin:0 0 18px;">'
      f'<tr><td style="padding:16px 16px 6px;">'
      f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
      f'<td valign="top"><div style="font-family:{F};font-size:11px;font-weight:bold;letter-spacing:1px;color:{t["tiercolor"]};">{t["tier"]}</div>'
      f'<div style="font-family:{F};font-size:18px;font-weight:bold;color:{INK};margin-top:4px;">{t["name"]} &middot; {t["n"]} legs</div></td>'
      f'<td valign="top" align="right" style="white-space:nowrap;"><div style="font-family:{F};font-size:28px;font-weight:bold;color:#0b8f3a;">{odds(t["american"])}</div>'
      f'<div style="font-family:{F};font-size:11px;color:{MUTE};">${t["stake"]:.0f} returns ${t["ret"]:.0f}</div></td></tr></table>'
      + button(bl,f"Add all {t['n']} legs to FanDuel slip in one tap &rsaquo;",fill="#0b8f3a",wide=True) +
      f'<div style="font-family:{F};font-size:11px;color:{MUTE};margin-top:5px;">One-tap link uses FanDuel\'s own share-slip format. If it opens FanDuel with an empty slip, use the per-leg buttons below.</div>'
      f'</td></tr><tr><td style="padding:4px 16px 12px;"><table width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table></td></tr>'
      f'<tr><td style="padding:0 16px 16px;"><table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f3f5f8" style="background-color:#f3f5f8;border-radius:8px;"><tr>'
      f'<td style="padding:10px 12px;font-family:{F};font-size:11px;color:{MUTE};">hits<br><b style="font-size:15px;color:{INK};">{t["joint"]*100:.1f}%</b></td>'
      f'<td style="padding:10px 12px;font-family:{F};font-size:11px;color:{MUTE};">my fair price<br><b style="font-size:15px;color:{INK};">{odds(t["fair"])}</b></td>'
      f'<td style="padding:10px 12px;font-family:{F};font-size:11px;color:{MUTE};">EV per $1<br><b style="font-size:15px;color:{GOLD};">{t["ev"]:.2f}</b></td>'
      f'<td style="padding:10px 12px;font-family:{F};font-size:11px;color:{MUTE};">worst cushion<br><b style="font-size:15px;color:{INK};">{t["mincush"]*100:.0f}%</b></td>'
      f'</tr></table><div style="font-family:{F};font-size:12px;color:{MUTE};margin-top:10px;line-height:1.55;">{t["why"]}</div></td></tr></table>')
def note(title,body,color=BLUE):
    return (f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-left:4px solid {color};margin:0 0 14px;">'
      f'<tr><td style="padding:10px 14px;"><div style="font-family:{F};font-size:14px;font-weight:bold;color:{INK};margin-bottom:6px;">{title}</div>'
      f'<div style="font-family:{F};font-size:13px;color:#3a3f4a;line-height:1.6;">{body}</div></td></tr></table>')
def render(meta,tickets,notes):
    cards="".join(card(t) for t in tickets)
    return (f'<table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#ffffff" style="background-color:#ffffff;"><tr><td align="center" style="padding:18px 12px 30px;">'
      f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">'
      f'<tr><td style="padding-bottom:14px;border-bottom:3px solid {BLUE};"><div style="font-family:{F};font-size:23px;font-weight:bold;color:{INK};">Sunday Prop Card &middot; FanDuel</div>'
      f'<div style="font-family:{F};font-size:12px;color:{MUTE};margin-top:5px;">{meta["date"]}<br>{meta["slate"]} &middot; {meta["built"]}</div></td></tr>'
      f'<tr><td style="padding-top:18px;">{cards}</td></tr><tr><td>{notes}</td></tr>'
      f'<tr><td style="padding-top:16px;border-top:1px solid {LINE};font-family:{F};font-size:11px;color:#7a808c;line-height:1.55;">'
      f'Model output, not advice. Prices are FanDuel posted prices at build time and move. Confirm the slip total before placing. '
      f'Confirm inactives after the official list posts 90 minutes before kickoff. Must be 21+. Bet only what you can lose. '
      f'Gambling problem? Call 1-800-GAMBLER.</td></tr></table></td></tr></table>')
