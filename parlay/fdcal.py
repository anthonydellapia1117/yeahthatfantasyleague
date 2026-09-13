"""Calibrate the one-sided margin on FanDuel's alternate ladders.

Main lines are two-way, so their hold is measurable. Where an alternate
rung sits on the same line as the main line for the same player and stat,
the alternate's implied probability minus the main line's de-vigged
probability is the alternate margin. That measured margin replaces the 5
percent guess and is the number that decides whether per-leg edge is real.
"""
import json, re, glob, statistics
import propmath as m
STAT={"player_receptions":"receptions","player_receptions_alternate":"receptions",
      "player_reception_yds":"rec_yards","player_reception_yds_alternate":"rec_yards",
      "player_pass_yds":"pass_yards","player_pass_yds_alternate":"pass_yards"}
mains={}; alts={}
for f in glob.glob('ev_*.json'):
    d=json.load(open(f))
    if not isinstance(d,dict) or 'bookmakers' not in d: continue
    for bk in d['bookmakers']:
        for mk in bk['markets']:
            st=STAT.get(mk['key']); 
            if not st: continue
            alt=mk['key'].endswith('_alternate')
            pair={}
            for o in mk['outcomes']:
                pair.setdefault((o['description'],o['point']),{})[o['name']]=o['price']
            for (pl,pt),sides in pair.items():
                if alt and 'Over' in sides:
                    alts[(pl,st,pt)]=m.american_to_implied(sides['Over'])
                elif not alt and 'Over' in sides and 'Under' in sides:
                    p,h=m.devig_two_way(sides['Over'],sides['Under'])
                    mains[(pl,st,pt)]=(p,h,m.american_to_implied(sides['Over']))
holds=[h for (_,h,_) in mains.values()]
print(f"main lines: {len(mains)} two-way | median two-way hold {statistics.median(holds)*100:.2f}%  (per side ~{statistics.median(holds)*50:.2f}%)")
diffs=[]
for k,(p_novig,h,imp_main) in mains.items():
    if k in alts:
        diffs.append((alts[k]-p_novig, k, alts[k], p_novig, imp_main))
print(f"alt rungs sitting exactly on a main line: {len(diffs)}")
if diffs:
    ds=[x[0] for x in diffs]
    print(f"alt implied minus no-vig main:  median {statistics.median(ds)*100:+.2f} pts   mean {statistics.mean(ds)*100:+.2f} pts")
    print(f"as a multiplicative margin on p: median {statistics.median([a/p-1 for _,_,a,p,_ in diffs])*100:+.2f}%")
    for d_,k,a,p,im in sorted(diffs,key=lambda x:-abs(x[0]))[:6]:
        print(f"   {k[0]:<20}{k[1]:<12}{k[2]:>6}  alt {a:.3f}  main-novig {p:.3f}  main-implied {im:.3f}  diff {d_*100:+.1f}pts")
json.dump({"alt_margin_mult": statistics.median([a/p-1 for _,_,a,p,_ in diffs]) if diffs else 0.05,
           "main_hold_two_way": statistics.median(holds)}, open('fdcal.json','w'))
