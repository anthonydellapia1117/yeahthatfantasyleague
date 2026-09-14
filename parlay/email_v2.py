"""email_v2.py - mobile-first card renderer.

Every style is inline. Gmail on iOS strips or ignores much of a <style>
block, and flexbox and grid are unsupported across most mail clients, so
the layout is nested tables and the selection text is sized to be the
largest element on the row. The pick is what the reader needs at a
glance; the maths sits underneath it, not around it.
"""

INK   = "#0d0f13"
CARD  = "#161a21"
LINE  = "#262b35"
GOLD  = "#d4af5f"
GREEN = "#5ec97b"
AMBER = "#e0a33c"
WHITE = "#f5f6f7"
MUTE  = "#8a8f99"
DIM   = "#666c77"

def odds(a):
    return f"+{a}" if a > 0 else str(a)

def _leg_row(i, leg, last=False):
    border = "" if last else f"border-bottom:1px solid {LINE};"
    link = leg.get("link")
    sel = leg["label"]
    if link:
        sel = (f'<a href="{link}" style="color:{GOLD};text-decoration:none;">'
               f'{sel} <span style="font-size:13px;color:{DIM};">&rsaquo;</span></a>')
    return f"""
<tr><td style="padding:13px 0 12px 0;{border}">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
    <td width="26" valign="top" style="width:26px;padding-top:3px;">
      <div style="width:20px;height:20px;border-radius:10px;background:{LINE};
        color:{MUTE};font:700 11px/20px -apple-system,Helvetica,Arial,sans-serif;
        text-align:center;">{i}</div></td>
    <td valign="top">
      <div style="font:600 13px/1.3 -apple-system,Helvetica,Arial,sans-serif;
        color:{MUTE};letter-spacing:.2px;">{leg['player']}</div>
      <div style="font:700 19px/1.3 -apple-system,Helvetica,Arial,sans-serif;
        color:{GOLD};margin:2px 0 4px 0;">{sel}</div>
      <div style="font:400 11.5px/1.4 -apple-system,Helvetica,Arial,sans-serif;color:{DIM};">
        {leg['game']} &nbsp;&middot;&nbsp; projection <span style="color:{MUTE};">{leg['mean']:.0f}</span>
        &nbsp;&middot;&nbsp; cushion <span style="color:{MUTE};">{leg['cushion']*100:.0f}%</span>
        &nbsp;&middot;&nbsp; win <span style="color:{MUTE};">{leg['p']*100:.0f}%</span></div>
    </td></tr></table>
</td></tr>"""

def _ticket(t):
    rows = "".join(_leg_row(i + 1, l, i == len(t["legs"]) - 1)
                   for i, l in enumerate(t["legs"]))
    evcol = GREEN if t["ev"] >= 1.0 else AMBER
    return f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
  style="background:{CARD};border:1px solid {LINE};border-radius:10px;margin:0 0 16px 0;">
<tr><td style="padding:16px 16px 4px 16px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
    <td valign="top">
      <div style="font:700 10px/1 -apple-system,Helvetica,Arial,sans-serif;
        letter-spacing:1.6px;color:{t['tiercolor']};text-transform:uppercase;">{t['tier']}</div>
      <div style="font:700 17px/1.2 -apple-system,Helvetica,Arial,sans-serif;
        color:{WHITE};margin-top:5px;">{t['name']}</div>
      <div style="font:400 11.5px/1.4 -apple-system,Helvetica,Arial,sans-serif;
        color:{DIM};margin-top:3px;">{t['n']} legs &middot; enter as one SGP</div>
    </td>
    <td valign="top" align="right" style="white-space:nowrap;">
      <div style="font:700 27px/1 -apple-system,Helvetica,Arial,sans-serif;color:{GREEN};">{odds(t['american'])}</div>
      <div style="font:400 11px/1.4 -apple-system,Helvetica,Arial,sans-serif;
        color:{DIM};margin-top:5px;">${t['stake']:.0f} returns ${t['ret']:.0f}</div>
    </td></tr></table>
</td></tr>
<tr><td style="padding:6px 16px 14px 16px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table>
</td></tr>
<tr><td style="padding:0 16px 15px 16px;">
  <div style="background:{INK};border-radius:7px;padding:11px 13px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td style="font:400 11px/1.5 -apple-system,Helvetica,Arial,sans-serif;color:{DIM};">
        hits<br><span style="font:700 15px/1.3;color:{WHITE};">{t['joint']*100:.1f}%</span></td>
      <td style="font:400 11px/1.5 -apple-system,Helvetica,Arial,sans-serif;color:{DIM};">
        my fair price<br><span style="font:700 15px/1.3;color:{WHITE};">{odds(t['fair'])}</span></td>
      <td style="font:400 11px/1.5 -apple-system,Helvetica,Arial,sans-serif;color:{DIM};">
        EV per $1<br><span style="font:700 15px/1.3;color:{evcol};">{t['ev']:.2f}</span></td>
      <td style="font:400 11px/1.5 -apple-system,Helvetica,Arial,sans-serif;color:{DIM};">
        min cushion<br><span style="font:700 15px/1.3;color:{WHITE};">{t['mincush']*100:.0f}%</span></td>
    </tr></table>
  </div>
  <div style="font:400 12px/1.6 -apple-system,Helvetica,Arial,sans-serif;
    color:{MUTE};margin-top:11px;">{t['why']}</div>
</td></tr></table>"""

def render(meta, tickets, notes_html):
    cards = "".join(_ticket(t) for t in tickets)
    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
 style="background:{INK};margin:0;padding:0;"><tr><td align="center" style="padding:20px 12px 34px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;">
<tr><td style="padding-bottom:16px;border-bottom:2px solid {GOLD};">
  <div style="font:700 22px/1.15 -apple-system,Helvetica,Arial,sans-serif;color:{WHITE};">Sunday Prop Card</div>
  <div style="font:400 12px/1.5 -apple-system,Helvetica,Arial,sans-serif;color:{MUTE};margin-top:6px;">
    {meta['date']}<br>{meta['slate']} &nbsp;&middot;&nbsp; built {meta['built']}</div>
</td></tr>
<tr><td style="padding-top:20px;">{cards}</td></tr>
<tr><td>{notes_html}</td></tr>
<tr><td style="padding-top:18px;border-top:1px solid {LINE};
  font:400 10.5px/1.6 -apple-system,Helvetica,Arial,sans-serif;color:#555a64;">
  Model output, not advice. Expected value describes a long run of identical decisions, never one
  Sunday. Confirm every line and price in your own app before placing. Confirm inactives after the
  official list posts 90 minutes before kickoff. Must be 21+. Bet only what you can lose.
  Gambling problem? Call 1-800-GAMBLER.</td></tr>
</table></td></tr></table>"""

def note(title, body, color=GOLD):
    return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
 style="background:{CARD};border-left:3px solid {color};border-radius:0 8px 8px 0;margin:0 0 13px 0;">
<tr><td style="padding:14px 15px;">
  <div style="font:700 13px/1.3 -apple-system,Helvetica,Arial,sans-serif;color:{WHITE};margin-bottom:7px;">{title}</div>
  <div style="font:400 12.5px/1.7 -apple-system,Helvetica,Arial,sans-serif;color:{MUTE};">{body}</div>
</td></tr></table>"""
