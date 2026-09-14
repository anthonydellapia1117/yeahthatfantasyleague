"""fdrender.py - render the FanDuel card email for today's slate.

Reads fdcard.json, fdsummary.json and pull_meta.json. Writes email_fd2.html
(the Gmail-safe HTML body), email_fd2.txt (plain-text alternative),
part1.html and part2.html (the HTML split in two so a tool with a small
read window can load it), and subject.txt.
"""
import json, os, datetime, zoneinfo
import email_fd2 as E
import propmath as m

ET = zoneinfo.ZoneInfo("America/New_York")
C = json.load(open("fdcard.json"))
S = json.load(open("fdsummary.json"))
META = json.load(open("pull_meta.json")) if os.path.exists("pull_meta.json") else {}
now = datetime.datetime.now(ET)
today = now.date()


def clock(dt):
    return f"{dt.hour % 12 or 12}:{dt.minute:02d}"


def et(iso):
    return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ET)


E.GAMEL.clear()
for g, v in S["games"].items():
    E.GAMEL[g] = f"{g.replace('@', ' @ ')} {clock(et(v['commence']))}"
windows = sorted({clock(et(v["commence"])) for v in S["games"].values()},
                 key=lambda s: (int(s.split(":")[0]) % 12, s))
if today.month == 11 and today.weekday() == 3 and 22 <= today.day <= 28:
    label = "Thanksgiving"
elif today.month == 12 and today.day == 25:
    label = "Christmas"
else:
    label = today.strftime("%A")
title = f"{label} Prop Card"
datestr = today.strftime("%A, %B %-d, %Y")
NAMES = {"HIGH": ("Ticket A", "HIGH RISK / HIGH REWARD", "#e05c5c"),
         "MED": ("Ticket B", "MEDIUM RISK / MEDIUM REWARD", "#d4af5f"),
         "LOW": ("Ticket C", "LOW RISK / LOW REWARD", "#5ec97b")}


def why(t):
    n, g = len(t["legs"]), t["games"]
    lo = min(l["p"] for l in t["legs"]) * 100
    checked = sum(1 for l in t["legs"] if l.get("p_usage") is not None)
    base = (f"{n} legs across {g} game{'s' if g != 1 else ''}, the fewest that reach this payout. Every leg is at least "
            f"{lo:.0f} percent to hit on the lower of FanDuel's number and the player's recent usage"
            f"{' (' + str(checked) + ' of ' + str(n) + ' usage-checked)' if checked else ''}. ")
    if t["band"] == "HIGH":
        s = base + ("Fewer legs is the whole edge here: FanDuel takes about 7 percent on every leg, so a 4-leg +1000 "
                    "hits about a quarter more often than an 8-leg +1000 built from safer-looking legs.")
    elif t["band"] == "MED":
        s = base + "Middle of the card. Three or four legs at a real multiple, with the least margin compounding the band allows."
    else:
        s = base + "The shortest ticket on the page and the one most likely to cash. If you only place one, this is it."
    if t.get("relaxed"):
        s += f" Small slate: legs per game were relaxed {t['relaxed']} step{'s' if t['relaxed'] > 1 else ''} to fill the band."
    return s


tick = []
for t in C:
    nm, tier, col = NAMES[t["band"]]
    stake = t.get("stake", 25)
    lg = sorted(t["legs"], key=lambda x: (x["game"], x["player"]))
    tick.append({"name": nm, "tier": tier, "tiercolor": col, "n": len(lg), "american": t["american"],
                 "joint": t.get("p_use", t["p_ind"]), "fair": t["fair"], "ev": t["ev"], "mincush": t["mincush"],
                 "legs": lg, "why": why(t), "stake": stake, "ret": stake * t["decimal"]})
missing = [b for b in ("HIGH", "MED", "LOW") if b not in S["bands_built"]]
# last week's scorecard and the running ledger
import glob
prior = [json.load(open(f)) for f in sorted(glob.glob("results/*.json")) if os.path.basename(f)[:10] < today.isoformat()]
last_week = ""
if prior:
    lw = prior[-1]
    lines_ = []
    for t in lw["tickets"]:
        miss = [f"{x['player']} {x['actual']} ({x['note']})" for x in t["legs"] if x["hit"] is False]
        void = [x["player"] for x in t["legs"] if x.get("void")]
        lines_.append(f"<b>Ticket {t['name']}</b> {'pushed' if t['won'] is None else ('won' if t['won'] else 'lost')}, {t['legs_hit']} of {len(t['legs']) - len(void)} legs"
                      + (f". Missed: {'; '.join(miss)}." if miss else ".")
                      + (f" Void (no stat line, verify inactives): {', '.join(void)}." if void else ""))
    played = sum(1 for r in prior for t in r["tickets"] if t["won"] is not None)
    won = sum(1 for r in prior for t in r["tickets"] if t["won"])
    net = 0.0
    for r_ in prior:
        for t in r_["tickets"]:
            if t["won"] is None:
                continue                                   # pushed: stake returned
            stake = t.get("stake", 25)
            price = t.get("settled_price") or t.get("slip_price") or t.get("page_price") or 0
            dec = 1 + price / 100 if price > 0 else (1 + 100 / -price if price else 1)
            net += stake * (dec - 1) if t["won"] else -stake
    legs_all = [l for r_ in prior for t in r_["tickets"] for l in t["legs"] if l["hit"] is not None]
    last_week = E.note(f"Last card, {datetime.date.fromisoformat(lw['date']).strftime('%b %-d')}",
                       "<br>".join(lines_) + f"<br><br>Running record: {won} of {played} tickets, "
                       f"{sum(l['hit'] for l in legs_all)} of {len(legs_all)} legs, net {'+' if net >= 0 else '-'}${abs(net):,.0f} at $25 a ticket.",
                       "#5a6070")
credits = META.get("credits_remaining")
min_cush = min((t["mincush"] for t in tick), default=0) * 100
positive = [t for t in tick if t["ev"] >= 1.0]
rows = "".join(
    f'<tr><td>{t["name"]} expected value per $1</td><td align="right" style="color:#9a6d00;font-weight:bold;">{t["ev"]:.2f}</td></tr>'
    f'<tr><td>{t["name"]} Kelly stake, fraction of bankroll</td><td align="right" style="font-weight:bold;">'
    f'{max(0.0, m.kelly_fraction(t["joint"], t["ret"] / t["stake"])) * 100:.1f}%</td></tr>'
    for t in tick)
ev_line = ("every ticket is negative expected value at posted prices, as every long parlay at a real book is"
           if not positive else
           f"{' and '.join(t['name'] for t in positive)} shows expected value at or above 1.0 at posted prices; "
           "treat that as a pricing quirk on the book's ladder, not a model edge, and size it by the Kelly line above")
notes = (
    last_week
    + E.note("How the links work",
           "Every leg has a blue <b>Add this leg</b> button and every ticket a green <b>Add all legs in one tap</b> button. "
           "The link format was tap-tested on 2026-09-13 and loaded the FanDuel slip both ways. Today's links were pulled "
           "fresh and are not individually tested. Prices on the slip are live and can differ from this page; the slip "
           "total is the number to read before you place. If a one-tap link opens FanDuel with an empty slip, use the "
           "per-leg buttons.")
    + E.note("Slip total vs page price",
             "The price on each ticket is the straight product of FanDuel's posted prices at build time. FanDuel groups "
             "legs from the same game into a same-game parlay and reprices them, so the slip total will usually be a "
             "little lower. Legs per game are capped to keep that repricing small.")
    + E.note("Card maths, honest version",
             '<table width="100%" cellpadding="0" cellspacing="0" border="0">' + rows +
             '</table><br>'
             "Probabilities are FanDuel's own, read from their alternate ladders, with no credit taken for any model. "
             f"Every leg sits at least {min_cush:.0f} percent below the book's projected mean, the tickets share no players, "
             f"and {ev_line}. "
             "The structure is built for hit rate and independence, not edge. The $ figures assume a flat $25 per ticket.",
             "#9a6d00")
    + E.note("Build notes",
             f"Slate: {len(S['games'])} game{'s' if len(S['games']) != 1 else ''} still ahead at build "
             f"({', '.join(windows)} ET). {S['ladders']} player ladders fitted from {S['rungs']} priced rungs. "
             + (f"Excluded on the injury report: {', '.join(S['excluded'])}. " if S["excluded"] else "No injury exclusions were supplied for this build. ")
             + (f"Usage check on {S.get('usage_rows', 0):,} player-game rows dropped fragile lines for {len(S.get('fragile_dropped', []))} players"
                + (f" ({', '.join(S['fragile_dropped'][:8])}{'...' if len(S['fragile_dropped']) > 8 else ''})" if S.get('fragile_dropped') else "")
                + (f"; no usage history for {', '.join(S['no_usage_history'][:6])}{'...' if len(S['no_usage_history']) > 6 else ''}" if S.get('no_usage_history') else "")
                + ". " if S.get("usage_rows") else "No usage logs were available for this build. ")
             + (f"Bands not filled: {', '.join(missing)}. " if missing else "")
             + (f"Odds feed credits left this month: {credits}." + (" Fewer than 120: upgrade the plan before next Sunday." if credits is not None and credits < 120 else "") if credits is not None else ""))
)
meta = {"title": title, "date": datestr,
        "slate": f"{len(S['games'])} games &middot; {', '.join(windows)} ET",
        "built": f"built {clock(now)} {now.strftime('%p')} ET from live FanDuel prices"}
html = E.render(meta, tick, notes).replace("</tr>", "</tr>\n")
open("email_fd2.html", "w").write(html)
half = html.find("</tr>\n", len(html) // 2) + 6
open("part1.html", "w").write(html[:half])
open("part2.html", "w").write(html[half:])
txt = [f"{title.upper()} - FANDUEL - {today.strftime('%b %-d, %Y')}", ""]
for t in tick:
    txt.append(f"{t['name']} [{t['tier']}] {E.odds(t['american'])} | {t['n']} legs | hit {t['joint']*100:.1f}% | EV {t['ev']:.2f}")
    txt.append(f"  ADD ALL {t['n']} LEGS IN ONE TAP: {E.bulk_link(t['legs'])}")
    for i, l in enumerate(t["legs"], 1):
        txt.append(f"  {i}. {l['player']} - Over {l['line']} {E.LBL.get(l['stat'], l['stat'])} ({E.odds(l['price'])})  {E.GAMEL.get(l['game'], l['game'])}")
        txt.append(f"     {l['link']}")
    txt.append("")
txt.append("Model output, not advice. Prices move; confirm the slip total. Must be 21+. Gambling problem? Call 1-800-GAMBLER.")
open("email_fd2.txt", "w").write("\n".join(txt))
subject = f"{title} - FanDuel - {today.strftime('%b %-d')} - " + " / ".join(f"{t['name'][-1]} {E.odds(t['american'])}" for t in tick)
open("subject.txt", "w").write(subject)
print(f"html {len(html)} bytes ({html.count(chr(10))} lines); parts {half} + {len(html)-half}; subject: {subject}")
for t in tick:
    print(f"   {t['name']} {t['american']:+d} {t['n']} legs EV {t['ev']:.2f}")
