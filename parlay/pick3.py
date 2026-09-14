import json, random, fastjoint as F, propmath as m, build as B
lib=json.load(open('lib5.json'))
TOTAL_HOLD=0.08
def book(j): return (1.0/j)/(1.0+TOTAL_HOLD)
def gamecap(legs,cap=4):
    c={}
    for l in legs:
        c[l['game']]=c.get(l['game'],0)+1
        if c[l['game']]>cap: return False
    return True
BAND=[("HIGH",1000,2200,(8,9,10),"HIGH RISK / HIGH REWARD","#e05c5c",260000),
      ("MED",500,999,(6,7,8),"MEDIUM RISK / MEDIUM REWARD","#d4af5f",220000),
      ("LOW",250,499,(4,5,6),"LOW RISK / LOW REWARD","#5ec97b",180000)]
rng=random.Random(404); chosen=[]; used=set()
for band,lo,hi,ns,label,color,iters in BAND:
    avail=[l for l in lib if l['player'] not in used]
    best=None; seen=set()
    for _ in range(iters):
        k=rng.choice(ns)
        if k>len(avail): continue
        idx=tuple(sorted(rng.sample(range(len(avail)),k)))
        if idx in seen: continue
        seen.add(idx)
        legs=[avail[i] for i in idx]
        if len({l['player'] for l in legs})!=k: continue
        if not gamecap(legs): continue
        j=F.joint_one_factor(legs)
        if j<=0: continue
        a=m.decimal_to_american(book(j))
        if a<lo or a>hi: continue
        mc=min(l['cushion'] for l in legs)
        if best is None or (mc,j)>(best[0],best[1]): best=(mc,j,a,legs)
    if best is None:
        print(f"{band}: none found"); continue
    mc,_,_,legs=best
    jm=m.joint_probability([l['p'] for l in legs], B.matrix(legs), trials=250000)
    d=book(jm)
    chosen.append({"band":band,"tier":label,"tiercolor":color,"legs":legs,"joint":jm,
        "american":m.decimal_to_american(d),"decimal":d,"mincush":mc,
        "fair":m.decimal_to_american(1/jm),"ev":jm*d,"kelly":m.kelly_fraction(jm,d)})
    used |= {l['player'] for l in legs}
    print(f"{band:<5}{len(legs):>3} legs {m.decimal_to_american(d):+6d}  hits {jm*100:5.2f}%  "
          f"fair {m.decimal_to_american(1/jm):+6d}  worst cushion {mc*100:.0f}%", flush=True)
json.dump(chosen, open('card3.json','w'), indent=1)
print("DONE")
