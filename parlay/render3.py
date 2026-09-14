import json, random, propmath as m, build as B, email_v3 as E
C=json.load(open('card3.json'))
GAMEL={"ARI@LAC":"ARI @ LAC 4:25","GB@MIN":"GB @ MIN 4:25","WAS@PHI":"WAS @ PHI 4:25",
       "MIA@LV":"MIA @ LV 4:25","DAL@NYG":"DAL @ NYG 8:20"}
NAMES={"HIGH":"Ticket A","MED":"Ticket B","LOW":"Ticket C"}
WHY={"HIGH":"Ten legs, none closer than a third below its projection. The payout comes "
  "from leg count, not from any single unlikely outcome. Spread across four games so no "
  "one script takes it down.",
 "MED":"The middle of the card. Same discipline, fewer legs, roughly double the hit rate "
  "of Ticket A.",
 "LOW":"The steadiest of the three and the one to size largest. Every leg sits at least "
  "40 percent below its projection, so it survives a badly wrong number."}
STAKE={"HIGH":10,"MED":15,"LOW":25}
# card-level simulation with shared legs moving together
legs={}
for t in C:
    for l in t['legs']: legs[(l['player'],l['stat'],l['line'])]=l
keys=list(legs); A=[legs[k] for k in keys]
M=B.matrix(A); L=m._cholesky(M); thr=[m.norm_ppf(1-l['p']) for l in A]
rng=random.Random(9); N=80000; wins=[0]*len(C); anyhit=0; ret=0.0
stakes=[STAKE[t['band']] for t in C]; tot=sum(stakes)
for _ in range(N):
    z=[rng.gauss(0,1) for _ in range(len(A))]
    x=[sum(L[i][j]*z[j] for j in range(i+1)) for i in range(len(A))]
    hit={keys[i]: x[i]>thr[i] for i in range(len(A))}
    r=-tot; any_=False
    for ti,t in enumerate(C):
        if all(hit[(l['player'],l['stat'],l['line'])] for l in t['legs']):
            wins[ti]+=1; r+=stakes[ti]*m.american_to_decimal(t['american']); any_=True
    anyhit+=1 if any_ else 0; ret+=r
tick=[]
for i,t in enumerate(C):
    lg=[dict(l, game=GAMEL[l['game']]) for l in sorted(t['legs'],key=lambda x:(x['game'],x['team']))]
    tick.append({"name":NAMES[t['band']],"tier":t['tier'],"tiercolor":t['tiercolor'],
      "n":len(lg),"american":t['american'],"joint":t['joint'],"fair":t['fair'],
      "ev":t['ev'],"mincush":t['mincush'],"legs":lg,"why":WHY[t['band']],
      "stake":stakes[i],"ret":stakes[i]*m.american_to_decimal(t['american'])})
MUTE="#8a8f99"; WHITE="#f5f6f7"; AMBER="#e0a33c"
stat_rows = (
  '<tr><td>Total staked across all three</td><td align="right" style="color:%s;font-weight:700;">$%d</td></tr>'
  '<tr><td>Chance at least one cashes</td><td align="right" style="color:%s;font-weight:700;">%.0f%%</td></tr>'
  '<tr><td>Chance all three miss</td><td align="right" style="color:%s;font-weight:700;">%.0f%%</td></tr>'
  '<tr><td>Expected return on the $%d</td><td align="right" style="color:%s;font-weight:700;">%+.2f</td></tr>'
) % (WHITE, tot, WHITE, anyhit/N*100, WHITE, (1-anyhit/N)*100, tot, AMBER, ret/N)
notes = (
 E.note("How to read a leg",
  "<b>Cushion</b> is how far below my projection the line sits, and it is the number that "
  "matters most. Your Skattebo leg had 4 percent cushion and was a coin flip. Every other leg "
  "you took had 20 to 35 percent. Nothing on this card is under 30 percent."
  "<br><br><b>My fair price</b> is what the ticket is worth by my model. If your app offers "
  "meaningfully less, skip it. Your 9-leg was priced within 8 percent of fair, which is fine. "
  "Your 7-leg was 35 percent worse than fair.")
 + E.note("What your two slips taught the model",
  "They were the first real prices I have had, and they changed two things. "
  "<b>One:</b> Fanatics already prices the correlation inside an SGP. Stacking a game does not "
  "buy free probability the way I said last time. No ticket structure beats their pricing, so "
  "you are paying roughly 8 percent either way and the expected return on this card is negative. "
  "What I can still do is stop you buying coin flips and tell you when a price is bad. "
  "<b>Two:</b> my Skattebo projection was 17 percent under the market, because the engine runs "
  "preseason numbers and had not repriced the Giants for Nabers being questionable. Corrected today.",
  "#e0a33c")
 + E.note("On the tappable links you asked for",
  "Fanatics has no way to do this. No URL scheme, no documented betslip link, and the developer "
  "community that already knows the DraftKings and FanDuel formats has no answer for Fanatics. "
  "<b>DraftKings and FanDuel can both do it</b> - their share-bet features use real working "
  "formats - but each leg needs that book\'s internal market and selection id, which needs an "
  "odds feed. There is a free tier that returns exactly those links. Say the word and next "
  "week\'s card has tappable legs for DraftKings and FanDuel.", "#6d727c")
 + E.note("Card maths",
  '<table width="100%" cellpadding="0" cellspacing="0" border="0" class="nb">' + stat_rows +
  "</table><br>The three tickets share no players, so they are three independent bets rather "
  "than one bet in three costumes. That is the fix from last week.")
)
html=E.render({"date":"Sunday, September 13, 2026",
  "slate":"Week 1 &middot; 4:25 ET window and Sunday night","built":"1:45 PM ET"}, tick, notes)
open('email3.html','w').write(html)
txt=["SUNDAY PROP CARD - Sept 13, 2026","Week 1, 4:25 ET window and Sunday night",""]
for t in tick:
    txt.append(f"{t['name']}  [{t['tier']}]  {m.decimal_to_american(m.american_to_decimal(t['american'])):+d}"
               f"   {t['n']} legs   hits {t['joint']*100:.1f}%   ${t['stake']:.0f} returns ${t['ret']:.0f}")
    txt.append(f"   my fair price {t['fair']:+d}   worst cushion {t['mincush']*100:.0f}%")
    for i,l in enumerate(t['legs'],1):
        txt.append(f"   {i}. {l['player']} - {l['label']}")
        txt.append(f"      {l['game']} | projection {l['mean']:.0f} | cushion {l['cushion']*100:.0f}% | win {l['p']*100:.0f}%")
    txt.append("")
txt.append(f"Total staked ${tot} | at least one cashes {anyhit/N*100:.0f}% | all three miss {(1-anyhit/N)*100:.0f}%")
open('email3.txt','w').write("\n".join(txt))
print(f"html {len(html)} bytes | staked ${tot} | anyhit {anyhit/N*100:.0f}% | exp return {ret/N:+.2f}")
print("\n".join(txt[:9]))
