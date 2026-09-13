import json, propmath as m, build as B, fastjoint as F
lib=json.load(open('lib5.json')); S=json.load(open('search5.json'))
TOTAL_HOLD=0.08
def book(j): return (1.0/j)/(1.0+TOTAL_HOLD)
want=[("HIGH","HIGH RISK / HIGH REWARD","#e05c5c"),
      ("MED","MEDIUM RISK / MEDIUM REWARD","#d4af5f"),
      ("LOW","LOW RISK / LOW REWARD","#5ec97b")]
chosen=[]; used=set()
for band,label,color in want:
    for mc,j1,a,idx in S[band]:
        legs=[lib[i] for i in idx]
        keys={(l['player'],l['stat']) for l in legs}
        if used and len(keys&used)/len(keys) > 0.40: continue
        # verify with the full copula
        jm=m.joint_probability([l['p'] for l in legs], B.matrix(legs), trials=250000)
        d=book(jm); am=m.decimal_to_american(d)
        lo,hi={"HIGH":(1000,2200),"MED":(500,999),"LOW":(250,499)}[band]
        if am<lo or am>hi: continue
        chosen.append({"band":band,"tier":label,"tiercolor":color,"legs":legs,
                       "joint":jm,"american":am,"decimal":d,"mincush":mc,
                       "fair":m.decimal_to_american(1.0/jm),
                       "ev":jm*d,"kelly":m.kelly_fraction(jm,d)})
        used|=keys; break
json.dump(chosen, open('card3.json','w'), indent=1)
for c in chosen:
    print(f"{c['band']:<5}{len(c['legs']):>3} legs {c['american']:+6d}  hits {c['joint']*100:5.2f}%  "
          f"fair {c['fair']:+6d}  EV {c['ev']:.3f}  min cushion {c['mincush']*100:.0f}%")
    for l in sorted(c['legs'],key=lambda x:(x['game'],x['team'])):
        print(f"      {l['player']:<22}{l['label']:<30}proj {l['mean']:>6.1f}  win {l['p']*100:>4.0f}%")
    print()
