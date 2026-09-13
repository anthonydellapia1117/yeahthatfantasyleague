import json, random, fastjoint as F, propmath as m, build as B
lib=json.load(open('lib4.json'))
HOLD=0.07   # measured against Anthony's real 9-leg Fanatics ticket
def price(legs):
    d=1.0
    for l in legs: d*=1.0/min(0.985,l['p']*(1+HOLD))
    return d
def one_per(legs):
    s=set()
    for l in legs:
        if l['player'] in s: return False
        s.add(l['player'])
    return True
def maxgame(legs,cap=5):
    c={}
    for l in legs:
        c[l['game']]=c.get(l['game'],0)+1
        if c[l['game']]>cap: return False
    return True
BANDS=[("HIGH",1000,2600,(8,9,10,11),300000),
       ("MED",500,999,(6,7,8),240000),
       ("LOW",250,499,(4,5,6),200000)]
rng=random.Random(2026); out={}
for name,lo,hi,ns,iters in BANDS:
    pool=[]; seen=set()
    for _ in range(iters):
        k=rng.choice(ns)
        idx=tuple(sorted(rng.sample(range(len(lib)),k)))
        if idx in seen: continue
        seen.add(idx)
        legs=[lib[i] for i in idx]
        if not one_per(legs) or not maxgame(legs): continue
        a=m.decimal_to_american(price(legs))
        if a<lo or a>hi: continue
        j=F.joint_one_factor(legs); d=price(legs)
        ev=j*d
        if ev<1.0: continue
        mincush=min(l['cushion'] for l in legs)
        pool.append((ev, j, a, mincush, idx))
    pool.sort(key=lambda x:-x[0]); out[name]=pool[:60]
    if pool:
        print(f"{name}: {len(pool)} candidates | best EV {pool[0][0]:.3f} at {pool[0][2]:+d} | min cushion {pool[0][3]*100:.0f}%", flush=True)
    else:
        print(f"{name}: NO candidates cleared EV 1.0", flush=True)
json.dump({k:[(a,b,c,d,list(e)) for a,b,c,d,e in v] for k,v in out.items()}, open('search3.json','w'))
print("DONE")
