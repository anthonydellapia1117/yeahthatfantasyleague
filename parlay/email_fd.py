"""email_fd.py - FanDuel card renderer with tappable add-to-slip links."""
import email_v3 as E
F=E.F
LBL={"rec_yards":"Receiving Yards","pass_yards":"Passing Yards","receptions":"Receptions",
     "rush_rec_yards":"Rush + Rec Yards"}
GAMEL={"ARI@LAC":"ARI @ LAC 4:25","GB@MIN":"GB @ MIN 4:25","WAS@PHI":"WAS @ PHI 4:25",
       "MIA@LV":"MIA @ LV 4:25","DAL@NYG":"DAL @ NYG 8:20"}
BTN=("display:inline-block;background:#1493ff;color:#ffffff;font:700 13px/1 "+F+";"
     "padding:10px 14px;border-radius:7px;text-decoration:none;margin-top:7px;")
def odds(a): return f"+{a}" if a>0 else str(a)
def row(i,l,last):
    bd="" if last else "border-bottom:1px solid #262b35;"
    sel=f"Over {l['line']} {LBL[l['stat']]}"
    return (f'<tr><td style="padding:13px 0 12px;{bd}"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
      f'<td width="26" valign="top" style="width:26px;padding-top:3px;"><div class="num">{i}</div></td>'
      f'<td valign="top"><div class="pl">{l["player"]}</div>'
      f'<div class="sel">{sel} <span style="color:#8a8f99;font-size:15px;">{odds(l["price"])}</span></div>'
      f'<div class="met">{GAMEL[l["game"]]} &middot; FanDuel line <b>{l["mkt_mean"]:.0f}</b>'
      f' &middot; cushion <b>{l["cushion"]*100:.0f}%</b> &middot; win <b>{l["p"]*100:.0f}%</b>'
      f' &middot; leg EV <b>{l["ev1"]:.2f}</b></div>'
      f'<a href="{l["link"]}" style="{BTN}">Add to FanDuel slip &rsaquo;</a>'
      f'</td></tr></table></td></tr>')
def card(t):
    rows="".join(row(i+1,l,i==len(t["legs"])-1) for i,l in enumerate(t["legs"]))
    ec="#5ec97b" if t["ev"]>=1.0 else "#e0a33c"
    return (f'<table width="100%" cellpadding="0" cellspacing="0" border="0" class="c"><tr><td style="padding:16px 16px 4px;">'
      f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td valign="top">'
      f'<div class="tag" style="color:{t["tiercolor"]};">{t["tier"]}</div><div class="nm">{t["name"]}</div>'
      f'<div class="sub">{t["n"]} legs &middot; tap each leg, then place as one parlay</div></td>'
      f'<td valign="top" align="right" style="white-space:nowrap;"><div class="od">{odds(t["american"])}</div>'
      f'<div class="ret">${t["stake"]:.0f} returns ${t["ret"]:.0f}</div></td></tr></table></td></tr>'
      f'<tr><td style="padding:6px 16px 14px;"><table width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table></td></tr>'
      f'<tr><td style="padding:0 16px 15px;"><div class="box"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
      f'<td class="kl">hits<br><span class="kv">{t["joint"]*100:.1f}%</span></td>'
      f'<td class="kl">my fair price<br><span class="kv">{odds(t["fair"])}</span></td>'
      f'<td class="kl">EV per $1<br><span class="kv" style="color:{ec};">{t["ev"]:.2f}</span></td>'
      f'<td class="kl">worst cushion<br><span class="kv">{t["mincush"]*100:.0f}%</span></td>'
      f'</tr></table></div><div class="why">{t["why"]}</div></td></tr></table>')
def render(meta,tickets,notes):
    cards="".join(card(t) for t in tickets)
    return (E.CSS+f'<table width="100%" cellpadding="0" cellspacing="0" border="0" class="w"><tr><td align="center" style="padding:20px 12px 34px;">'
      f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">'
      f'<tr><td style="padding-bottom:16px;border-bottom:2px solid #1493ff;"><div class="t1">Sunday Prop Card &middot; FanDuel</div>'
      f'<div class="t2">{meta["date"]}<br>{meta["slate"]} &middot; built {meta["built"]}</div></td></tr>'
      f'<tr><td style="padding-top:20px;">{cards}</td></tr><tr><td>{notes}</td></tr>'
      f'<tr><td style="padding-top:18px;border-top:1px solid #262b35;" class="ft">Model output, not advice. '
      f'Prices are FanDuel posted prices at build time and move. Confirm the slip total before placing. '
      f'Confirm inactives after the official list posts 90 minutes before kickoff. Must be 21+. Bet only '
      f'what you can lose. Gambling problem? Call 1-800-GAMBLER.</td></tr></table></td></tr></table>')
