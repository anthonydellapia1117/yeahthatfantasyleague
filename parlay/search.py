import json, random, sys
import fastjoint as F, propmath as m
lib=json.load(open('library.json'))
HOLD=1.045
def bdec(legs):
    d=1.0
    for l in legs: d*=1.0/min(0.985,l['p']*HOLD)
    return d
def ok(legs,maxp=2):
    seenk=set(); c={}
    for l in legs:
        k=(l['player'],l['stat'])
        if k in seenk: return False
        seenk.add(k)
        c[l['player']]=c.get(l['player'],0)+1
        if c[l['player']]>maxp: return False
    return True
BANDS=[("HIGH",1000,3000,(10,11,12,13,14),260000),
       ("MED",500,999,(7,8,9,10,11),200000),
       ("LOW",250,499,(5,6,7,8),160000)]
rng=random.Random(7); best={}
for name,lo,hi,ns,iters in BANDS:
    pool=[]; seen=set()
    for _ in range(iters):
        k=rng.choice(ns)
        idx=tuple(sorted(rng.sample(range(len(lib)),k)))
        if idx in seen: continue
        seen.add(idx)
        legs=[lib[i] for i in idx]
        if not ok(legs): continue
        d=bdec(legs); am=m.decimal_to_american(d)
        if am<lo or am>hi: continue
        j=F.joint_one_factor(legs)
        pool.append((j*d,j,am,idx))
    pool.sort(key=lambda x:-x[0]); best[name]=pool[:25]
    if not pool:
        print(f"{name}: no ticket lands in the band", flush=True); continue
    print(f"{name}: {len(pool)} tickets in band | best EV {pool[0][0]:.3f} at {pool[0][2]:+d} | hit {pool[0][1]*100:.2f}%", flush=True)
json.dump({k:[(e,j,a,list(i)) for e,j,a,i in v] for k,v in best.items()}, open('search.json','w'))
print("DONE")
