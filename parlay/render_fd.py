import json, propmath as m, email_fd as E, email_v3 as V
C=json.load(open('fdcard.json'))
NAMES={"HIGH":("Ticket A","HIGH RISK / HIGH REWARD","#e05c5c",5),
       "MED":("Ticket B","MEDIUM RISK / MEDIUM REWARD","#d4af5f",5),
       "LOW":("Ticket C","LOW RISK / LOW REWARD","#5ec97b",10)}
WHY={"HIGH":"Built only so you can compare like for like with the Fanatics card. At FanDuel's posted "
            "prices this is the worst value on the page: the per-leg margin compounds eight times.",
     "MED":"Six legs, five different games, every line at least 27 percent under FanDuel's own "
           "projected mean. Still negative at posted prices, and less so than Ticket A.",
     "LOW":"Four legs, four games, the widest cushion on the card. If you only place one, this is it, "
           "and the honest size is small."}
tick=[]
for t in C:
    nm,tier,col,stake=NAMES[t['band']]
    lg=sorted(t['legs'],key=lambda x:(x['game'],x['player']))
    tick.append({"name":nm,"tier":tier,"tiercolor":col,"n":len(lg),"american":t['american'],
      "joint":t['p_ind'],"fair":t['fair'],"ev":t['ev'],"mincush":t['mincush'],"legs":lg,
      "why":WHY[t['band']],"stake":stake,"ret":stake*t['decimal']})
def note(title,body,color="#1493ff"): return V.note(title,body,color)
notes=(
 note("How the links work",
  "Every leg has an <b>Add to FanDuel slip</b> button. Each tap opens FanDuel and adds that one "
  "selection to your slip; come back to this email and tap the next. When all legs are in, the slip "
  "shows the parlay price and you place it once. The links are FanDuel's own share-bet format, "
  "returned by the odds feed, and every one here is live as of 2:15 PM ET. <b>I could not tap-test "
  "them from where I sit</b>: FanDuel blocks this server's location, so the first tap is the test. "
  "If a link opens the app but the slip is empty, tell me and the email goes back to search-and-tap.")
 + note("The number that matters: the slip total, not this page",
  "The price on each ticket is the straight product of FanDuel's posted prices. FanDuel groups legs "
  "from the same game into a same-game parlay and reprices them, so your slip total will differ. "
  "<b>The decisive platform test takes two minutes:</b> build the same legs in both apps and compare "
  "the two slip totals. Whichever pays more for identical legs wins on price. FanDuel wins on "
  "convenience either way.")
 + note("A correction, and it is a big one",
  "FanDuel's alternate ladders let me read the book's own view of how spread out each outcome is, "
  "and it is wider than my model assumed: receiving yards vary about 27 percent more than I had. "
  "That means every deep alternate line is less likely to hit than I have been telling you, on both "
  "books. Re-pricing your 9-leg Fanatics slip with those spreads gives a 4.4 percent hit rate and a "
  "fair price near +2200 against the +1237 you were paid. <b>The 8 percent hold I quoted you earlier "
  "today was wrong; the honest figure is far higher.</b> Long alternate-line parlays are steeply "
  "negative on both books. Fewer legs, wider cushions, smaller stakes is the only defensible play.",
  "#e0a33c")
 + note("Card maths, honest version",
  '<table width="100%" cellpadding="0" cellspacing="0" border="0" class="nb">'
  f'<tr><td>Ticket A expected value per $1</td><td align="right" style="color:#e0a33c;font-weight:700;">{C[0]["ev"]:.2f}</td></tr>'
  f'<tr><td>Ticket B expected value per $1</td><td align="right" style="color:#e0a33c;font-weight:700;">{C[1]["ev"]:.2f}</td></tr>'
  f'<tr><td>Ticket C expected value per $1</td><td align="right" style="color:#e0a33c;font-weight:700;">{C[2]["ev"]:.2f}</td></tr>'
  '<tr><td>Kelly stake on any of them</td><td align="right" style="color:#f5f6f7;font-weight:700;">zero</td></tr>'
  '</table><br>The dollar figures on the tickets are for comparing against the Fanatics card, not a '
  'recommendation. Probabilities here are FanDuel\'s own, read from their ladders, with no credit '
  'taken for my model. Every leg still sits at least 20 percent below the book\'s projected mean, '
  'the three tickets share no players, and no player with an injury designation is on the card.')
)
html=E.render({"date":"Sunday, September 13, 2026","slate":"Week 1 &middot; 4:25 ET window and Sunday night",
               "built":"2:15 PM ET from live FanDuel prices"}, tick, notes)
open('email_fd.html','w').write(html)
txt=["SUNDAY PROP CARD - FANDUEL - Sept 13, 2026",""]
for t in tick:
    txt.append(f"{t['name']} [{t['tier']}] {('+' if t['american']>0 else '')+str(t['american'])} | {t['n']} legs | hit {t['joint']*100:.1f}% | EV {t['ev']:.2f} | fair {('+' if t['fair']>0 else '')+str(t['fair'])}")
    for i,l in enumerate(t['legs'],1):
        txt.append(f"  {i}. {l['player']} - Over {l['line']} {E.LBL[l['stat']]} ({('+' if l['price']>0 else '')+str(l['price'])})  {E.GAMEL[l['game']]} | FD mean {l['fd_mean']:.0f} | cushion {l['cushion']*100:.0f}% | win {l['p']*100:.0f}%")
        txt.append(f"     add to slip: {l['link']}")
    txt.append("")
open('email_fd.txt','w').write("\n".join(txt))
print(f"html {len(html)} bytes; tickets: " + ", ".join(f"{t['name']} {t['american']:+d} EV {t['ev']:.2f}" for t in tick))
