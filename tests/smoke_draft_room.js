// CI-equivalent smoke test for out/draft_room.html.
// Run: npm i playwright-core && node tests/smoke_draft_room.js out/draft_room.html
// Set the chromium path for your machine if not using the default install;
// all Sleeper endpoints are mocked, so the test needs no network.
// 1. Loads the standalone file, asserts Mode 1 renders with all 12 slot tabs,
//    the wait-or-reach centrepiece, opponent priors, and zero console errors.
// 2. Blocks Sleeper to assert the honest-offline fallback.
// 3. Mocks a live draft (real order + picks) to assert Mode 2: seat detection,
//    big-name answer, clock, conditional survival table.
const { chromium } = require("playwright-core");
const path = require("path");

const FILE = "file://" + path.resolve(process.argv[2] || "out/draft_room.html");
let failures = 0;
const ok = (cond, name, detail) => {
  console.log((cond ? "PASS" : "FAIL") + "  " + name + (cond || !detail ? "" : "  -> " + detail));
  if (!cond) failures++;
};

(async () => {
  const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });

  // ---- scenario 1: pre_draft, order not drawn (mocked - hermetic, no network)
  {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", e => errors.push(String(e)));
    page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
    const idSlots = {}; for (let i = 1; i <= 12; i++) idSlots[i] = i;
    await page.route("**/v1/draft/*", r => r.fulfill({
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify({ status: "pre_draft", draft_order: null,
                             slot_to_roster_id: idSlots }),
    }));
    await page.goto(FILE);
    await page.waitForTimeout(4000);
    const mode = await page.textContent("#mode");
    ok(/PRE-DRAFT/.test(mode), "mode 1 detected: " + mode.trim());
    ok(await page.locator(".chips button").count() === 12, "12 seat chips in the thumb bar");
    ok(await page.locator(".rowcard").count() > 8, "verdict-first round cards");
    const body = await page.textContent("body");
    ok(/WAIT|TAKE NOW/.test(body), "verdicts rendered");
    ok(/to last to your next pick/.test(body), "explicit wait comparison text");
    ok(/COIN FLIP/.test(body), "coin flips surfaced");
    ok(/FLOOR/.test(body), "K/DEF floor label");
    ok(/n_eff/.test(body), "opponent priors table");
    ok(!/champion/i.test(body.replace(/no champion mimicry[^.]*/gi, "")), "no champion panel");
    // click another slot tab
    await page.click('.chips button[data-slot="3"]');
    await page.waitForTimeout(300);
    ok(/Slot 3 - your picks/.test(await page.textContent("body")), "slot tab switch");
    ok(errors.length === 0, "zero console errors" + (errors.length ? ": " + errors[0] : ""));
    await page.close();
  }

  // ---- scenario 2: Sleeper unreachable - honest fallback
  {
    const page = await browser.newPage();
    await page.route("**/api.sleeper.app/**", r => r.abort());
    await page.goto(FILE);
    await page.waitForTimeout(2500);
    const banner = await page.textContent("#banner");
    ok(/unreachable/.test(banner), "offline banner with staleness warning");
    ok(await page.locator(".chips button").count() === 12, "offline still renders scenarios");
    await page.close();
  }

  // ---- scenario 3: mocked live draft
  {
    const page = await browser.newPage();
    const order = {}; order["345197760305307648"] = 7;
    const slotToRoster = {}; for (let i = 1; i <= 12; i++) slotToRoster[i] = i;
    await page.route("**/v1/draft/*/picks", r => r.fulfill({
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify([
        { metadata: { first_name: "Jahmyr", last_name: "Gibbs", position: "RB" } },
        { metadata: { first_name: "Bijan", last_name: "Robinson", position: "RB" } },
        { metadata: { first_name: "Ja'Marr", last_name: "Chase", position: "WR" } },
      ]),
    }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().endsWith("/picks")) return r.fallback();
      r.fulfill({
        contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", draft_order: order,
                               slot_to_roster_id: slotToRoster }),
      });
    });
    await page.goto(FILE);
    await page.waitForTimeout(3000);
    const mode = await page.textContent("#mode");
    ok(/LIVE/.test(mode), "mode 2 detected");
    ok(/seat 7/.test(mode), "Anthony's seat auto-detected from the draw");
    const body = await page.textContent("body");
    ok(await page.locator(".bignm").count() === 1, "one huge answer name");
    const big = await page.textContent(".bignm");
    ok(!/Gibbs|Bijan|Chase/.test(big), "drafted players removed from the answer: " + big.trim());
    ok(/\d:\d\d/.test(await page.textContent("#clock")), "pick clock running");
    ok(/Survival to your pick/.test(body), "conditional survival table");
    ok(/actually gone/.test(body), "live recompute labelled");
    ok(/PICK 4/i.test(body), "current pick derived from picks gone (3+1)");
    ok(await page.locator("#lv-dot").count() === 1, "freshness dot present");
    ok(/ON THE CLOCK/.test(body), "on-the-clock lower third");
    await page.close();
  }

  // ---- scenario 4: order drawn but draft_order null - seat must still resolve
  {
    const page = await browser.newPage();
    const drawn = {1:5,2:9,3:7,4:1,5:12,6:3,7:2,8:11,9:4,10:8,11:6,12:10};
    await page.route("**/v1/draft/*/picks", r => r.fulfill({
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" },
      body: "[]" }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().endsWith("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", draft_order: null,
                               slot_to_roster_id: drawn }) });
    });
    await page.goto(FILE);
    await page.waitForTimeout(3000);
    const mode = await page.textContent("#mode");
    // roster 7 sits at slot 3 in this permutation
    ok(/seat 3/.test(mode), "seat resolved from slot_to_roster_id when draft_order is null: " + mode.trim());
    await page.close();
  }

  // ---- scenario 3c: PHASE 3 FEATURES - every feature demonstrated live
  {
    const fs = require("fs");
    const engine = JSON.parse(fs.readFileSync(
      require("path").resolve("out/engine_2026.json"), "utf8"));
    const topId = engine.players.find(p => p.sleeper_id && p.vor > 50).sleeper_id;
    const page = await browser.newPage({ acceptDownloads: true });
    await page.addInitScript(() => {
      localStorage.setItem("ytfl_queue", JSON.stringify(["Breece Hall"]));
      localStorage.setItem("ytfl_overrides", "[]");
    });
    const mk = (f, l, pos) => ({ metadata: { first_name: f, last_name: l, position: pos } });
    const picks = [
      mk("Ja'Marr", "Chase", "WR"), mk("Bijan", "Robinson", "RB"), mk("Justin", "Jefferson", "WR"),
      mk("Jahmyr", "Gibbs", "RB"), mk("Saquon", "Barkley", "RB"), mk("CeeDee", "Lamb", "WR"),
      mk("Jonathan", "Taylor", "RB"), mk("Puka", "Nacua", "WR"), mk("Amon-Ra", "St. Brown", "WR"),
      mk("Christian", "McCaffrey", "RB"), mk("Malik", "Nabers", "WR"), mk("Brock", "Bowers", "TE"),
      mk("Bucky", "Irving", "RB"), mk("Kyren", "Williams", "RB"), mk("Ashton", "Jeanty", "RB"),
      mk("James", "Cook", "RB"), mk("De'Von", "Achane", "RB"), mk("Chase", "Brown", "RB"),
      mk("Trey", "McBride", "TE"), mk("Tyreek", "Hill", "WR"),
    ];
    const idSlots = {}; for (let i = 1; i <= 12; i++) idSlots[i] = i;
    await page.route("**/v1/players/nfl/trending/**", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify([{ player_id: topId, count: 9876 }]) }));
    await page.route("**/v1/draft/*/picks", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify(picks) }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().endsWith("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", draft_order: { "345197760305307648": 7 },
                               slot_to_roster_id: idSlots }) });
    });
    await page.goto(FILE);
    await page.waitForTimeout(3000);
    await page.evaluate(() => document.querySelectorAll("details").forEach(d => d.open = true));
    await page.waitForTimeout(200);
    const body = await page.textContent("body");
    // f1: roster tracker - seat 7 owns picks 7 and 18
    const roster = await page.textContent("#f-myroster");
    ok(/pick 7.*Taylor/s.test(roster) && /pick 18.*Brown/s.test(roster), "f1 roster tracker lists my picks");
    ok(/needs:/.test(roster), "f1 roster needs surfaced");
    // f2: best available by position - 4 minis
    ok(await page.locator("#f-bypos .mini").count() === 4, "f2 best-by-position strip");
    // f3: tier cliffs with honest approximation label
    ok(await page.locator("#f-cliff .mini").count() === 4, "f3 tier cliff minis");
    ok(/independence approximation/.test(body), "f3 approximation labelled");
    // f4: board wall filled from the feed
    ok(await page.locator("#f-wall .cell").count() >= 24, "f4 board wall cells");
    ok(await page.locator("#f-wall .cell.pRB").count() >= 8, "f4 wall position-coded");
    // f5: opponent panels with dossier drilldown (f14)
    ok(await page.locator("#f-opps .opp").count() === 12, "f5 twelve opponent panels");
    await page.click('#f-opps .who[data-doss="1"]');
    ok(!(await page.locator("#doss-1").isHidden()), "f14 dossier expands on tap");
    ok(/tendency \(display only\)/.test(await page.textContent("#doss-1")), "f14 lifts labelled display only");
    // f6: position run - 6 RBs in the last 8 picks
    ok(/POSITION RUN/.test(body), "f6 run banner fires");
    // f7: ticker with value tags
    ok(/vs ADP|VALUE \+|REACH -/.test(await page.textContent("#lv-ticker")), "f7 ticker value tags");
    // f8: survival horizon toggle
    const cap1 = await page.textContent("#lv-surv");
    await page.click('#f-horizon button[data-h="1"]');
    await page.waitForTimeout(400);
    const cap2 = await page.textContent("#lv-surv");
    ok(/your pick 31/.test(cap1) && /your pick 42/.test(cap2), "f8 horizon toggle moves the target pick");
    // f9: queue preloaded with a target, shows survival
    ok(/Breece Hall/.test(await page.textContent("#f-queue")), "f9 queue shows target");
    // f10: manual override marks a player drafted
    await page.fill("#f-ovr-in", "Breece Hall");
    await page.click("#f-ovr-go");
    await page.waitForTimeout(400);
    ok(await page.locator("#f-queue .queue-gone").count() >= 1, "f10 override crosses off the queued target");
    // f13: trending badge from the mocked feed (board re-rendered post-interaction)
    ok(/market heat \+9,?876/.test(await page.textContent("#f-board")), "f13 trending badge labelled market heat");
    // f11: sortable board with search
    await page.fill("#f-q", "kelce");
    await page.waitForTimeout(300);
    ok(/Kelce/.test(await page.textContent("#f-board")), "f11 board search filters");
    // f12: sleepers list
    ok(/market is/.test(await page.textContent("#f-sleepers")), "f12 value-vs-ADP sleepers");
    // f15: pick-slot history flavor
    ok(/historically/.test(await page.textContent("#f-hist")), "f15 league-history flavor line");
    await page.close();
  }

  // ---- scenario 3d: RECAP EXPORT on a complete draft (f16)
  {
    const page = await browser.newPage({ acceptDownloads: true });
    const idSlots = {}; for (let i = 1; i <= 12; i++) idSlots[i] = i;
    await page.route("**/v1/players/nfl/trending/**", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: "[]" }));
    await page.route("**/v1/draft/*/picks", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify([{ metadata: { first_name: "Jonathan", last_name: "Taylor", position: "RB" } }]) }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().endsWith("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "complete", draft_order: { "345197760305307648": 7 },
                               slot_to_roster_id: idSlots }) });
    });
    await page.goto(FILE);
    await page.waitForTimeout(2500);
    ok(!(await page.locator("#f-recap").isHidden()), "f16 recap card visible on complete draft");
    const [dl] = await Promise.all([
      page.waitForEvent("download", { timeout: 5000 }).catch(() => null),
      page.click("#f-recap-go"),
    ]);
    ok(dl !== null && /recap/.test(dl.suggestedFilename()), "f16 recap downloads as a file");
    await page.close();
  }

  // ---- scenario 4b: SPECTATOR fallback - live draft, seat unknown, never blank
  {
    const page = await browser.newPage();
    const idSlots = {}; for (let i = 1; i <= 12; i++) idSlots[i] = i;
    await page.route("**/v1/draft/*/picks", r => r.fulfill({
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" }, body: "[]" }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().endsWith("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", draft_order: null,
                               slot_to_roster_id: idSlots }) });
    });
    await page.goto(FILE);
    await page.waitForTimeout(2500);
    ok(!(await page.locator("#lv-spectator").isHidden()), "spectator seat picker shown when seat unknown");
    ok(await page.locator("#lv-seatpick button").count() === 12, "12 manual seat buttons");
    await page.click('#lv-seatpick button[data-slot="5"]');
    await page.waitForTimeout(1200);
    ok(/seat 5/.test(await page.textContent("#mode")), "manual seat selection takes effect");
    await page.close();
  }

  // ---- scenario 6: SIMULATOR (Phase 4) - quarantine + speed gate
  {
    const page = await browser.newPage();
    const idSlots = {}; for (let i = 1; i <= 12; i++) idSlots[i] = i;
    await page.route("**/v1/players/nfl/trending/**", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: "[]" }));
    await page.route("**/v1/draft/*/picks", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: "[]" }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().endsWith("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", draft_order: { "345197760305307648": 7 },
                               slot_to_roster_id: idSlots }) });
    });
    await page.goto(FILE);
    await page.waitForTimeout(2500);
    // quarantine styling before anything runs
    const simCard = page.locator("#f-sim");
    ok(await simCard.count() === 1, "sim card exists");
    ok(/scenario, not a forecast/.test(await simCard.textContent()), "sim caption present");
    ok(await page.locator("#f-sim .simbadge").count() === 1, "amber SIM badge");
    const border = await simCard.evaluate(el => getComputedStyle(el).borderTopStyle);
    ok(border === "dashed", "dashed quarantine border: " + border);
    // capture the verdict surfaces BEFORE the sim runs
    const before = await page.evaluate(() =>
      document.getElementById("lv-why").innerHTML + "|" + document.getElementById("lv-name").textContent);
    // run 500 in-page and time it - the gate says under 2s
    await page.evaluate(() => document.querySelectorAll("details").forEach(d => d.open = true));
    const t0 = Date.now();
    await page.click("#f-sim-500");
    await page.waitForFunction(() =>
      /simulated drafts/.test(document.getElementById("f-sim-out").textContent), { timeout: 15000 });
    const elapsed = Date.now() - t0;
    ok(elapsed < 2000, "500 sims complete in under 2s: " + elapsed + "ms");
    ok(/targets surviving to my picks/.test(await page.textContent("#f-sim-out")),
       "sim outputs target survival distribution");
    ok(/typical roster shape/.test(await page.textContent("#f-sim-out")), "sim outputs roster shape");
    // the verdict surfaces must be BYTE-IDENTICAL after the sim - quarantine proof
    const after = await page.evaluate(() =>
      document.getElementById("lv-why").innerHTML + "|" + document.getElementById("lv-name").textContent);
    ok(before === after, "verdict surfaces byte-identical after sim run (quarantine holds)");
    await page.close();
  }

  // ---- scenario 7: PICK GRADE - frozen anchors + isolation.
  // These integers are PINNED. Any change to the formula or weights breaks
  // them loudly - what 80 means can never drift silently.
  {
    const page = await browser.newPage();
    await page.route("**/api.sleeper.app/**", r => r.abort());
    await page.goto(FILE);
    await page.waitForTimeout(1500);
    const r = await page.evaluate(() => {
      const G = window.__pickGrade;
      const dak = { vor: 18, adp: 90.3, pos: "QB", tier: 2 };
      const dakCtx = [
        [7,   { curPick: 7,   myNext: 18,  bestVor: 130, tierLeft: 5, fillsNeed: false, isSurplus: false }],
        [55,  { curPick: 55,  myNext: 66,  bestVor: 45,  tierLeft: 4, fillsNeed: true,  isSurplus: false }],
        [79,  { curPick: 79,  myNext: 90,  bestVor: 30,  tierLeft: 3, fillsNeed: true,  isSurplus: false }],
        [90,  { curPick: 90,  myNext: 103, bestVor: 22,  tierLeft: 2, fillsNeed: true,  isSurplus: false }],
        [103, { curPick: 103, myNext: 114, bestVor: 18,  tierLeft: 2, fillsNeed: true,  isSurplus: false }],
        [115, { curPick: 115, myNext: 127, bestVor: 18,  tierLeft: 1, fillsNeed: true,  isSurplus: false }],
      ];
      return {
        curve: dakCtx.map(([k, c]) => G(dak, c)),
        amber: G({ vor: 40, adp: 50, pos: "RB" },
                 { curPick: 48, myNext: 60, bestVor: 55, tierLeft: 4, fillsNeed: false, isSurplus: false }),
        needPair: [
          G({ vor: 44, adp: 65, pos: "RB" },
            { curPick: 62, myNext: 74, bestVor: 46, tierLeft: 2, fillsNeed: true, isSurplus: false }),
          G({ vor: 44, adp: 65, pos: "RB" },
            { curPick: 62, myNext: 74, bestVor: 46, tierLeft: 2, fillsNeed: false, isSurplus: true }),
        ],
      };
    });
    ok(JSON.stringify(r.curve) === "[10,33,51,65,75,83]",
       "grade anchors: the Dak curve is pinned at [10,33,51,65,75,83]", JSON.stringify(r.curve));
    ok(r.curve.every((g, i) => i === 0 || g > r.curve[i - 1]),
       "grade: monotonically improves as the pick passes his ADP");
    ok(r.curve[0] <= 39 && r.amber === 55 && r.curve[4] >= 70,
       "one pinned anchor per band: red 10, amber 55, green 75");
    ok(r.needPair[0] === 69 && r.needPair[1] === 57,
       "roster need moves the grade: fills-need 69 vs surplus 57, pinned");
    await page.close();
  }

  // ---- scenario 8: DRAFT-DAY FEATURES 1-4 (gear on answer, recs panel,
  // grid screen, value board)
  {
    const page = await browser.newPage();
    const mk = (f, l, pos) => ({ metadata: { first_name: f, last_name: l, position: pos } });
    const picks = [
      mk("Ja'Marr", "Chase", "WR"), mk("Bijan", "Robinson", "RB"), mk("Justin", "Jefferson", "WR"),
      mk("Jahmyr", "Gibbs", "RB"), mk("Saquon", "Barkley", "RB"), mk("CeeDee", "Lamb", "WR"),
      mk("Jonathan", "Taylor", "RB"), mk("Puka", "Nacua", "WR"), mk("Amon-Ra", "St. Brown", "WR"),
      mk("Christian", "McCaffrey", "RB"), mk("Malik", "Nabers", "WR"), mk("Brock", "Bowers", "TE"),
      mk("Bucky", "Irving", "RB"), mk("Kyren", "Williams", "RB"), mk("Ashton", "Jeanty", "RB"),
      mk("James", "Cook", "RB"), mk("De'Von", "Achane", "RB"), mk("Chase", "Brown", "RB"),
      mk("Trey", "McBride", "TE"), mk("Tyreek", "Hill", "WR")];
    const idSlots = {}; for (let i = 1; i <= 12; i++) idSlots[i] = i;
    await page.route("**/v1/players/nfl/trending/**", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: "[]" }));
    await page.route("**/v1/draft/*/picks", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify(picks) }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().endsWith("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", draft_order: { "345197760305307648": 7 },
                               slot_to_roster_id: idSlots }) });
    });
    await page.goto(FILE);
    await page.waitForTimeout(3000);
    // F1: gear on the answer - band + integer number, no decimals
    ok(await page.locator("#lv-gear .gear svg").count() === 1, "F1 gear dial on the answer");
    const gnum = (await page.textContent("#lv-gear .gnum")).trim();
    ok(/^\d{1,3}$/.test(gnum), "F1 grade is an integer, no false precision: " + gnum);
    ok(/not at this price|defensible|take him/.test(await page.textContent("#lv-gear")),
       "F1 band word carries the meaning beside the color");
    // F2 correctness in the OTHER direction: at this board state the verdict
    // is TAKE NOW with no coin flip, so the panel must stay hidden
    ok(await page.locator("#f-recs").isHidden(), "F2 panel hidden on a clean TAKE NOW");
    // F3: grid screen - 12 team columns x rounds, position-coded
    await page.click('#nav button[data-scr="grid"]');
    await page.waitForTimeout(400);
    ok(!(await page.locator("#scr-grid").isHidden()), "F3 grid is a first-class screen");
    ok(await page.locator("#g-grid .dg-h").count() === 12, "F3 twelve team columns");
    ok(await page.locator("#g-grid .cell.pRB").count() >= 8, "F3 cells position-coded from the feed");
    // F4: value board - two panels, toggles, drafted behavior
    await page.click('#nav button[data-scr="board"]');
    await page.waitForTimeout(400);
    ok(await page.locator("#vb-left .vrow").count() === 50, "F4 overall top 50 default");
    await page.click('#vb-topn button[data-n="100"]');
    await page.waitForTimeout(400);
    ok(await page.locator("#vb-left .vrow").count() === 100, "F4 toggle to top 100");
    ok(await page.locator("#vb-left .vrow.gone").count() === 0, "F4 auto-remove ON: no drafted rows");
    await page.click("#vb-keep");
    await page.waitForTimeout(400);
    ok(await page.locator("#vb-left .vrow.gone").count() > 0, "F4 grey-out OFF-mode shows drafted struck through");
    ok(/FLEX \(RB\+WR\+TE\)/.test(await page.textContent("#vb-right")), "F4 FLEX group present");
    ok(/DST/.test(await page.textContent("#vb-right")), "F4 DST group present");
    ok((await page.textContent("#vb-right")).includes("floor"), "F4 K/DST rows carry the floor label");
    await page.close();
  }

  // ---- scenario 8b: F2 RECS PANEL on a coin-flip board state
  {
    const page = await browser.newPage();
    const mk = (f, l, pos) => ({ metadata: { first_name: f, last_name: l, position: pos } });
    const picks = [mk("Ja'Marr","Chase","WR"), mk("Bijan","Robinson","RB"), mk("Jahmyr","Gibbs","RB"),
      mk("Jonathan","Taylor","RB"), mk("Puka","Nacua","WR"), mk("Christian","McCaffrey","RB")];
    const idSlots = {}; for (let i = 1; i <= 12; i++) idSlots[i] = i;
    await page.route("**/v1/players/nfl/trending/**", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: "[]" }));
    await page.route("**/v1/draft/*/picks", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify(picks) }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().endsWith("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", draft_order: { "345197760305307648": 7 },
                               slot_to_roster_id: idSlots }) });
    });
    await page.goto(FILE);
    await page.waitForTimeout(3000);
    // this board state provably carries a COIN FLIP runner (Jeanty within 8 VOR)
    ok(!(await page.locator("#f-recs").isHidden()), "F2 recs panel shows on WAIT/COIN FLIP");
    ok(await page.locator("#recs-cards .rec").count() === 2, "F2 default is 2 alternatives");
    await page.click('#recs-n button[data-n="5"]');
    await page.waitForTimeout(400);
    ok(await page.locator("#recs-cards .rec").count() === 5, "F2 toggle to 5");
    await page.fill("#recs-q", "Travis Kelce");
    await page.waitForTimeout(500);
    ok(await page.locator("#recs-cards .rec").count() === 6, "F2 search appends a sixth card");
    ok(/Kelce/.test(await page.textContent("#recs-cards")), "F2 searched player rendered");
    ok(await page.locator("#recs-cards .gear").count() === 6, "F2 every card carries its own gear");
    await page.click("#recs-clear");
    await page.waitForTimeout(400);
    ok(await page.locator("#recs-cards .rec").count() === 5, "F2 clear removes only the appended card");
    await page.close();
  }

  // ---- scenario 9: PHASE B OVERLAY. Empty board renders nothing; the
  // helpers behave; a patched payload proves chips, the bull tie-break,
  // and the verdict-subject rule end to end.
  {
    const fs = require("fs");
    const os = require("os");
    // 9a: the shipped (empty-board) file shows zero overlay surfaces
    const page = await browser.newPage();
    await page.route("**/api.sleeper.app/**", r => r.abort());
    await page.goto(FILE);
    await page.waitForTimeout(1500);
    ok(await page.evaluate(() => {
      const E = JSON.parse(document.getElementById("engine-data").textContent);
      return E.my_board === undefined;
    }), "overlay: shipped payload carries no my_board key");
    ok(await page.locator(".yc").count() === 0,
       "overlay: empty board renders zero YOUR CALL chips");
    // 9b: helper contracts, on synthetic state, restored afterwards
    const unit = await page.evaluate(() => {
      const O = window.__overlay;
      const saved = O.state.map;
      O.state.map = { "aaa bbb": { player: "Aaa Bbb", call: "BULL",
                                   move: "+1 tier", reason: "r", source: "s",
                                   date: "2026-08-13", matched: true },
                      "ccc ddd": { player: "Ccc Ddd", call: "BEAR",
                                   move: "", reason: "r", source: "s",
                                   date: "2026-08-13", matched: true } };
      const res = {
        chip: O.chip({ name: "Aaa Bbb" }),
        chipNone: O.chip({ name: "Zzz Qqq" }),
        flipBull: O.flip([{ name: "Zzz Qqq" }, { name: "Aaa Bbb" }]),
        flipNone: O.flip([{ name: "Zzz Qqq" }, { name: "Yyy Www" }]),
        resorted: O.resort([
          { name: "P One", pos: "RB", tier: 2, vor: 90 },
          { name: "Ccc Ddd", pos: "RB", tier: 2, vor: 88 },
          { name: "Aaa Bbb", pos: "RB", tier: 2, vor: 85 },
          { name: "P Four", pos: "RB", tier: 3, vor: 80 },
        ]).map(p => p.name).join(","),
      };
      O.state.map = saved;
      return res;
    });
    ok(/YOUR CALL - BULL \+1 tier/.test(unit.chip), "overlay: bull chip carries call and move");
    ok(unit.chipNone === "", "overlay: no call, no chip");
    ok(unit.flipBull.includes("break toward your call - Aaa Bbb"),
       "overlay: tie-break points at the bull in the flip");
    ok(unit.flipNone === "break toward ceiling",
       "overlay: no bull in the flip, advice unchanged");
    ok(unit.resorted === "Aaa Bbb,P One,Ccc Ddd,P Four",
       "overlay: within-tier resort - bull up, bear down, next tier untouched",
       unit.resorted);
    await page.close();
    // 9c: end to end on a patched payload - bull on the known coin-flip
    // runner. The subject must stay the model's; only the advice text moves.
    const raw = fs.readFileSync(path.resolve(process.argv[2] || "out/draft_room.html"), "utf8");
    const OPEN = '<script id="engine-data" type="application/json">';
    const CLOSE = "</scr" + "ipt><!--engine-data-end-->";
    const a = raw.indexOf(OPEN) + OPEN.length, b = raw.indexOf(CLOSE);
    const payload = JSON.parse(raw.slice(a, b));
    const mkCall = (name, call, move) => {
      const p = payload.players.find(x => x.name === name);
      return { player: p.name, call, move, reason: "smoke fixture",
               source: "test", confidence: "", date: "2026-08-13",
               matched: true, pos: p.pos, adp: p.adp, vor: p.vor, tier: p.tier };
    };
    payload.my_board = [mkCall("Ashton Jeanty", "BULL", "+1 tier"),
                        mkCall("Nico Collins", "BEAR", "-1 tier")];
    const tmp = path.join(os.tmpdir(), "ytfl_overlay_smoke.html");
    fs.writeFileSync(tmp, raw.slice(0, a) + JSON.stringify(payload) + raw.slice(b));
    const p9 = await browser.newPage();
    const mk9 = (f, l, pos) => ({ metadata: { first_name: f, last_name: l, position: pos } });
    const picks9 = [mk9("Ja'Marr","Chase","WR"), mk9("Bijan","Robinson","RB"),
      mk9("Jahmyr","Gibbs","RB"), mk9("Jonathan","Taylor","RB"),
      mk9("Puka","Nacua","WR"), mk9("Christian","McCaffrey","RB")];
    const idSlots9 = {}; for (let i = 1; i <= 12; i++) idSlots9[i] = i;
    await p9.route("**/v1/players/nfl/trending/**", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: "[]" }));
    await p9.route("**/v1/draft/*/picks", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify(picks9) }));
    await p9.route("**/v1/draft/*", r => {
      if (r.request().url().endsWith("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", draft_order: { "345197760305307648": 7 },
                               slot_to_roster_id: idSlots9 }) });
    });
    await p9.goto("file://" + tmp);
    await p9.waitForTimeout(3000);
    const big9 = await p9.textContent(".bignm");
    ok(/James Cook/.test(big9),
       "overlay e2e: the model primary is still the subject: " + big9.trim());
    const body9 = await p9.textContent("body");
    ok(body9.includes("break toward your call - Ashton Jeanty"),
       "overlay e2e: live coin flip breaks toward the bull call");
    await p9.click('#nav button[data-scr="board"]');
    await p9.waitForTimeout(400);
    ok(await p9.locator(".yc.bull").count() >= 1 && await p9.locator(".yc.bear").count() >= 1,
       "overlay e2e: YOUR CALL chips render on the value board");
    await p9.close();
    fs.unlinkSync(tmp);
  }

  // ---- scenario 5: PARITY. The JS mirror must reproduce Python's survival
  // numbers exactly (within float tolerance). This is the test whose absence
  // let the 1-erf tail bug ship: the two surfaces disagreed past z~6 and
  // nothing compared them.
  {
    const page = await browser.newPage();
    await page.route("**/api.sleeper.app/**", r => r.abort());
    await page.goto(FILE);
    await page.waitForTimeout(1500);
    const res = await page.evaluate(() => {
      const E = JSON.parse(document.getElementById("engine-data").textContent);
      let worst = { d: 0 }, deepTailZero = false;
      for (const r of (E.survival_reference || [])) {
        const js = window.__survival(r.adp, r.pick);
        const d = r.s > 1e-12 ? Math.abs(js - r.s) / r.s : Math.abs(js - r.s);
        if (d > worst.d) worst = { d, adp: r.adp, pick: r.pick, py: r.s, js };
        if (r.s > 0 && js === 0) deepTailZero = true;
      }
      return { n: (E.survival_reference || []).length, worst, deepTailZero };
    });
    ok(res.n >= 30, "survival_reference anchors embedded: " + res.n);
    // A-S erfc approximation differs from Python's exact erfc by up to ~1e-7
    // absolute, which is large RELATIVE error deep in the tail. What matters
    // decisionally: near-agreement where probabilities are readable, and no
    // hard zero anywhere Python keeps mass.
    ok(res.worst.d < 0.02 || res.worst.py < 1e-4,
       "JS matches Python within tolerance",
       "worst rel diff " + res.worst.d + " at adp " + res.worst.adp + " pick " + res.worst.pick);
    ok(!res.deepTailZero, "JS deep tail never collapses to 0 where Python keeps mass");
    await page.close();
  }

  await browser.close();
  console.log(failures === 0 ? "\nALL PASS" : `\n${failures} FAILURES`);
  process.exit(failures === 0 ? 0 : 1);
})();
