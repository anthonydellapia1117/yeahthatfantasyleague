"""fdfinal.py - price legs from FanDuel's own ladder, no model probabilities.

For each player and stat, the alternate ladder is a set of (line, implied)
points. Fitting a two-parameter distribution to it recovers the book's own
view of mean and spread. Each rung's hit probability is then read from that
fitted curve, so p is the market's number, not mine. The only thing a rung
can then have going for it is being priced below the book's own smooth
curve, which is a real and model-free inefficiency.

Ticket EV is computed with NO correlation credit, because FanDuel groups
same-game legs into an SGP and strips it. That makes the emailed EV a
floor, not a promise.
"""
import json, random, propmath as m, build as B
from collections import defaultdict
CAL=json.load(open('fdcal.json')); ALT=CAL['alt_margin_mult']
legs=json.load(open('fdlegs2.json'))
lib4=json.load(open('lib4.json')); POS={l['player']:l['pos'] for l in lib4}
for l in legs:
    if l['alt']: l['q']=l['implied']/(1.0+ALT)
grp=defaultdict(list)
for l in legs:
    if POS.get(l['player'])=="RB" and l['stat']!="rush_rec_yards": continue
    grp[(l['player'],l['stat'])].append(l)

def fit(ls, stat):
    pts=[(l['line'],l['q']) for l in ls if 0.04<l['q']<0.97]
    if len(pts)<3: return None
    top=max(x for x,_ in pts)*2.5+5
    count = stat in ("receptions",)
    best=None
    grid_m=[0.5+i*(top/120.0) for i in range(120)]
    grid_s=([1.1,1.25,1.45,1.7,2.0,2.4] if count else [0.35,0.42,0.5,0.55,0.62,0.7,0.8,0.9,1.0])
    for mu in grid_m:
        for sp in grid_s:
            e=0.0
            for line,q in pts:
                p=(m.prob_over_count(mu,line,sp) if count else m.prob_over_continuous(mu,line,sp))
                e+=(p-q)**2
            if best is None or e<best[0]: best=(e,mu,sp)
    e,mu,sp=best
    # refine mean
    lo,hi=max(0.3,mu-top/120),mu+top/120
    for _ in range(30):
        m1=lo+(hi-lo)/3; m2=hi-(hi-lo)/3
        def E(x): return sum(((m.prob_over_count(x,line,sp) if count else m.prob_over_continuous(x,line,sp))-q)**2 for line,q in pts)
        if E(m1)<E(m2): hi=m2
        else: lo=m1
    mu=(lo+hi)/2
    return mu,sp,len(pts)

FIT={}; out=[]
for (pl,st),ls in grp.items():
    f=fit(ls,st)
    if f is None: continue
    mu,sp,n=f; FIT[f"{pl}|{st}"]={"mean":mu,"spread":sp,"n":n}
    count = st=="receptions"
    for l in ls:
        p=(m.prob_over_count(mu,l['line'],sp) if count else m.prob_over_continuous(mu,l['line'],sp))
        d=dict(l); d['fd_mean']=mu; d['fd_spread']=sp; d['p']=p
        d['resid']=l['q']-p                 # negative = rung cheap vs its own ladder
        d['ev1']=p*l['decimal']
        d['cushion']=(mu-l['line'])/mu
        d['kind']={"pass_yards":"QBpass","rush_rec_yards":"RBrush"}.get(st,"TErec" if POS.get(pl)=="TE" else "WRrec")
        out.append(d)
json.dump(FIT,open('fdfit.json','w'),indent=1); json.dump(out,open('fdlegs4.json','w'))
print(f"{len(FIT)} ladders fitted | {len(out)} rungs priced from FanDuel's own curve")
cheap=[l for l in out if l['resid']<-0.015 and l['cushion']>=0.25]
print(f"{len(cheap)} rungs priced >=1.5 pts below their own ladder curve with cushion>=25%")
print()
print("FanDuel-implied spread vs my fixed assumption (yards CV 0.55 rec / 0.28 pass; receptions disp 1.45):")
import statistics
for st,lab in (("rec_yards","rec yards CV"),("pass_yards","pass yards CV"),("receptions","receptions dispersion")):
    v=[f['spread'] for k,f in FIT.items() if k.endswith("|"+st)]
    if v: print(f"   {lab:<24} median {statistics.median(v):.2f}   range {min(v):.2f}-{max(v):.2f}   n={len(v)}")

pool=[l for l in out if l['cushion']>=0.25 and 0.62<=l['p']<=0.95 and l['link'] and l['price']>=-700]
poolH=[l for l in out if l['cushion']>=0.25 and 0.62<=l['p']<=0.95 and l['link'] and l['price']>=-800]
def ok(ls,cap):
    pl=set(); g={}
    for l in ls:
        if l['player'] in pl: return False
        pl.add(l['player']); g[l['game']]=g.get(l['game'],0)+1
        if g[l['game']]>cap: return False
    return True
def price(ls):
    d=1.0
    for l in ls: d*=l['decimal']
    return d
BANDS=[("LOW",250,499,(3,4,5,6),160000,2),("MED",500,999,(5,6,7,8),220000,2),("HIGH",1000,2600,(8,9,10,11),320000,3)]
rng=random.Random(2113); chosen=[]; used=set()
for band,lo,hi,ns,iters,cap in BANDS:
    avail=[l for l in (poolH if band=="HIGH" else pool) if l['player'] not in used]
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
        pind=1.0
        for l in ls: pind*=l['p']
        ev=pind*d
        if best is None or ev>best[0]: best=(ev,pind,a,ls)
    if best is None: print(f"{band}: none in band"); continue
    ev,pind,a,ls=best
    jm=m.joint_probability([l['p'] for l in ls], B.matrix(ls), trials=150000)
    d=price(ls)
    chosen.append({"band":band,"legs":ls,"p_ind":pind,"joint":jm,"american":a,"decimal":d,
                   "ev":pind*d,"ev_corr":jm*d,"fair":m.decimal_to_american(1/pind),
                   "mincush":min(l['cushion'] for l in ls)})
    used|={l['player'] for l in ls}
    print(f"{band:<5}{len(ls):>2} legs  posted product {a:+6d}  hit {pind*100:5.1f}% (with corr {jm*100:4.1f}%)  fair {m.decimal_to_american(1/pind):+6d}  EV {pind*d:.3f}  worst cushion {min(l['cushion'] for l in ls)*100:.0f}%")
    for l in sorted(ls,key=lambda x:(x['game'],x['player'])):
        print(f"      {l['player']:<20}{l['stat'].replace('_',' '):<14}over {l['line']:<6}{l['price']:>6}  FD mean {l['fd_mean']:>6.1f}  cush {l['cushion']*100:>3.0f}%  p {l['p']*100:>3.0f}%  legEV {l['ev1']:.3f}  resid {l['resid']*100:+.1f}pts")
order={'HIGH':0,'MED':1,'LOW':2}; chosen.sort(key=lambda c:order[c['band']])
json.dump(chosen,open('fdcard.json','w'),indent=1)
