"""Objective: maximise the WORST leg's cushion inside each payout band.

With the book pricing at my correlated fair minus a flat total hold,
expected value is the same for every ticket and cannot discriminate. What
still differs is robustness: how wrong the projection can be before a leg
fails. Maximising the minimum cushion produces the ticket most likely to
survive my own model error, which is the honest thing to optimise when the
book's per-leg prices are not visible.
"""
import json, random, fastjoint as F, propmath as m, build as B
lib=json.load(open('lib5.json'))
TOTAL_HOLD=0.08      # measured from two real Fanatics tickets
def book(joint): return (1.0/joint)/(1.0+TOTAL_HOLD)
def one_per(legs):
    s=set()
    for l in legs:
        if l['player'] in s: return False
        s.add(l['player'])
    return True
def gamecap(legs,cap=5):
    c={}
    for l in legs:
        c[l['game']]=c.get(l['game'],0)+1
        if c[l['game']]>cap: return False
    return True
BANDS=[("HIGH",1000,2200,(7,8,9,10),300000),
       ("MED",500,999,(5,6,7,8),260000),
       ("LOW",250,499,(4,5,6),220000)]
rng=random.Random(77); out={}
for name,lo,hi,ns,iters in BANDS:
    pool=[]; seen=set()
    for _ in range(iters):
        k=rng.choice(ns)
        idx=tuple(sorted(rng.sample(range(len(lib)),k)))
        if idx in seen: continue
        seen.add(idx)
        legs=[lib[i] for i in idx]
        if not one_per(legs) or not gamecap(legs): continue
        j=F.joint_one_factor(legs)
        if j<=0: continue
        a=m.decimal_to_american(book(j))
        if a<lo or a>hi: continue
        mc=min(l['cushion'] for l in legs)
        pool.append((mc, j, a, idx))
    pool.sort(key=lambda x:(-x[0],-x[1])); out[name]=pool[:60]
    if pool:
        print(f"{name}: {len(pool)} in band | best worst-leg cushion {pool[0][0]*100:.0f}% "
              f"at {pool[0][2]:+d}, hits {pool[0][1]*100:.1f}%", flush=True)
    else:
        print(f"{name}: none in band", flush=True)
json.dump({k:[(a,b,c,list(d)) for a,b,c,d in v] for k,v in out.items()}, open('search5.json','w'))
print("DONE")
