"""fdbuild.py - price FanDuel legs with adaptive shrinkage, then build tickets.

Shrinkage rule: where my projection and the market-implied mean disagree by
more than 20 percent, the market is almost certainly right and mine is used
with zero weight. Inside 20 percent, the blend is 70 percent market, 30 mine.
This stops the optimiser from harvesting my own errors as 'edge'.

Ticket price is the straight product of POSTED FanDuel prices. FanDuel
groups same-game legs into an SGP and reprices them, so legs per game are
capped at two and the emailed price is described as the pre-SGP product.
"""
import json, random, propmath as m, build as B, fastjoint as F

legs=json.load(open('fdlegs2.json'))
CAL=json.load(open('fdcal.json')); ALT_M=CAL['alt_margin_mult']
for l in legs:
    if l['alt']:
        l['q']=l['implied']/(1.0+ALT_M)
lib4=json.load(open('lib4.json')); POS={l['player']:l['pos'] for l in lib4}
KIND={"pass_yards":"QBpass","rush_rec_yards":"RBrush"}
def kind(l):
    if l['stat'] in KIND: return KIND[l['stat']]
    return "TErec" if POS.get(l['player'])=="TE" else "WRrec"

out=[]
for l in legs:
    if POS.get(l['player'])=="RB" and l['stat']!="rush_rec_yards": continue   # split unreliable
    gap=abs(l['mean']-l['mkt_mean'])/l['mkt_mean']
    w_model = 0.0 if gap>0.20 else 0.30
    bm=(1-w_model)*l['mkt_mean']+w_model*l['mean']
    d=dict(l); d['kind']=kind(l); d['team']=l.get('team','?')
    d['blend_mean']=bm; d['w_model']=w_model
    d['p']=B.prob({'stat':l['stat'],'mean':bm,'line':l['line']})
    d['p_mkt']=B.prob({'stat':l['stat'],'mean':l['mkt_mean'],'line':l['line']})
    d['ev1']=d['p']*l['decimal']
    d['ladder_ev']=d['p_mkt']*l['decimal']      # model-free: is this rung cheap vs FD's own ladder?
    d['cushion']=(l['mkt_mean']-l['line'])/l['mkt_mean']
    out.append(d)
json.dump(out,open('fdlegs3.json','w'))

pool=[l for l in out if l['cushion']>=0.25 and 0.62<=l['p']<=0.95 and l['link'] and l['price']>=-700]
poolH=[l for l in out if l['cushion']>=0.25 and 0.62<=l['p']<=0.95 and l['link'] and l['price']>=-800]
print(f"{len(out)} legs priced | {len(pool)} in the buildable pool (cushion>=25%, p 62-95%, has link)")
cheap=[l for l in pool if l['ladder_ev']>=1.0]
print(f"{len(cheap)} rungs priced better than FanDuel's own ladder implies (model-free edge)")
print()
def ok(legs_,cap=2):
    pl=set(); g={}
    for l in legs_:
        if l['player'] in pl: return False
        pl.add(l['player']); g[l['game']]=g.get(l['game'],0)+1
        if g[l['game']]>cap: return False
    return True
def price(legs_):
    d=1.0
    for l in legs_: d*=l['decimal']
    return d
BANDS=[("LOW",250,499,(3,4,5,6),160000),("MED",500,999,(5,6,7,8),200000),("HIGH",1000,2600,(8,9,10,11),300000)]
rng=random.Random(913); chosen=[]; used=set()
for band,lo,hi,ns,iters in BANDS:
    avail=[l for l in (pool if band!='HIGH' else poolH) if l['player'] not in used]
    cap=3 if band=='HIGH' else 2
    best=None; seen=set()
    for _ in range(iters):
        k=rng.choice(ns)
        if k>len(avail): continue
        idx=tuple(sorted(rng.sample(range(len(avail)),k)))
        if idx in seen: continue
        seen.add(idx)
        ls=[avail[i] for i in idx]
        if not ok(ls,cap): continue
        d=price(ls); a=m.decimal_to_american(d)
        if a<lo or a>hi: continue
        j=F.joint_one_factor(ls)
        ev=j*d
        if best is None or ev>best[0]: best=(ev,j,a,ls)
    if best is None: print(f"{band}: none"); continue
    ev,j,a,ls=best
    jm=m.joint_probability([l['p'] for l in ls], B.matrix(ls), trials=200000)
    d=price(ls)
    chosen.append({"band":band,"legs":ls,"joint":jm,"american":a,"decimal":d,"ev":jm*d,
                   "fair":m.decimal_to_american(1/jm),"mincush":min(l['cushion'] for l in ls),
                   "kelly":m.kelly_fraction(jm,d)})
    used|={l['player'] for l in ls}
    print(f"{band:<5}{len(ls):>3} legs  posted product {a:+6d}  hits {jm*100:5.2f}%  fair {m.decimal_to_american(1/jm):+6d}  EV {jm*d:.3f}  worst cushion {min(l['cushion'] for l in ls)*100:.0f}%")
    for l in sorted(ls,key=lambda x:(x['game'],x['player'])):
        print(f"      {l['player']:<20}{l['stat'].replace('_',' '):<14}over {l['line']:<6}{l['price']:>6}  mkt {l['mkt_mean']:>6.1f}  cush {l['cushion']*100:>3.0f}%  p {l['p']*100:>4.0f}%  legEV {l['ev1']:.2f}")
    print()
order={'HIGH':0,'MED':1,'LOW':2}; chosen.sort(key=lambda c:order[c['band']])
json.dump(chosen,open('fdcard.json','w'),indent=1)
