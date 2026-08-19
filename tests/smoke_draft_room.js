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
    // visible text, not script source - the pick engine's honest
    // "championship lens" label lives in the live-mode template string
    const vis1 = await page.evaluate(() => document.body.innerText);
    ok(!/champion/i.test(vis1.replace(/no champion mimicry[^.]*/gi, "")), "no champion panel");
    // click another slot tab
    await page.click('.chips button[data-slot="3"]');
    await page.waitForTimeout(300);
    ok(/Slot 3 - your picks/.test(await page.textContent("body")), "slot tab switch");
    // ORDER HYPOTHESIS: card renders with 12 selects x 12 franchises; a
    // change persists, remaps the strips, and jumps to my hypothesized seat
    ok(await page.locator("#ohyp-card [data-ohyp]").count() === 12,
       "order hypothesis: 12 slot selects render");
    ok(await page.locator('[data-ohyp="1"] option').count() === 12,
       "order hypothesis: each select offers the 12 real franchises");
    ok(/Rob & GregBo \(RobFlacc\)/.test(await page.textContent("#ohyp-card")),
       "order hypothesis: options carry franchise and sleeper handle");
    await page.selectOption('[data-ohyp="1"]', "10");
    await page.waitForTimeout(400);
    const t1h = await page.textContent("body");
    ok(/hypothesis active/.test(t1h), "order hypothesis: active note renders");
    ok(/Slot 7 - your picks/.test(t1h),
       "order hypothesis: view follows my seat under the hypothesis");
    ok(/your hypothesis order/.test(t1h),
       "order hypothesis: gap strips relabel to the hypothesis");
    // swap semantics: roster 10 moved to slot 1, so slot 10 got roster 1 -
    // the order stays a permutation and no duplicate warning appears
    ok(await page.locator('[data-ohyp="10"]').inputValue() === "1",
       "order hypothesis: assignment swaps, never duplicates");
    ok(!/duplicates:/.test(await page.textContent("#ohyp-card")),
       "order hypothesis: no duplicate state from the UI");
    await page.reload();
    await page.waitForTimeout(3000);
    ok(await page.locator('[data-ohyp="1"]').inputValue() === "10",
       "order hypothesis: persists across reload");
    await page.evaluate(() => localStorage.removeItem("ytfl_order_hyp"));
    ok(errors.length === 0, "zero console errors" + (errors.length ? ": " + errors[0] : ""));
    await page.close();
  }

  // ---- scenario 1b: order DRAWN but draft not started - the hypothesis
  // retires visibly and Sleeper's order labels the strips
  {
    const page = await browser.newPage();
    await page.evaluate(() => {}).catch(() => {});
    const drawn = {1:5,2:9,3:7,4:1,5:12,6:3,7:2,8:11,9:4,10:8,11:6,12:10};
    await page.route("**/v1/draft/*/picks", r => r.fulfill({
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" }, body: "[]" }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().endsWith("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "pre_draft", draft_order: null,
                               slot_to_roster_id: drawn }) });
    });
    await page.goto(FILE);
    await page.waitForTimeout(4000);
    const t1b = await page.textContent("body");
    ok(/draw is live - the hypothesis is retired/.test(t1b),
       "drawn order: hypothesis card retires itself");
    ok(/Sleeper's drawn order/.test(t1b),
       "drawn order: gap strips credit the real draw");
    ok(/seat 3/.test(await page.textContent("#banner")),
       "drawn order: my real seat detected from the permutation");
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
    // SURVIVAL CALIBRATION: wrapper parity with the payload table, the
    // one-tap toggle, and the frozen fallback
    const calPar = await page.evaluate(() => {
      // cross-language parity: the JS wrapper must reproduce the
      // Python-computed anchors embedded by the engine (never circular)
      const t = E.survival_calibration;
      let okAll = (E.calibration_reference || []).length >= 5, flipBin = false;
      for (const r of E.calibration_reference || []){
        if (Math.abs(window.__calCondSurvival(r.adp, r.to_pick, r.from_pick) - r.cal) > 1e-9)
          okAll = false;
      }
      for (let i = 0; i < t.length; i++)
        if (i / t.length < 0.6 && t[i] >= 0.6) flipBin = true;
      return { okAll, flipBin, len: t.length, enabled: E.survival_calibration_enabled };
    });
    ok(calPar.okAll && calPar.len === 20 && calPar.enabled,
       "JS wrapper reproduces the Python-computed calibration anchors");
    ok(calPar.flipBin,
       "the table contains bins that flip TAKE NOW to WAIT (the correction is real)");
    ok(/CALIBRATED SURVIVAL ON/.test(await page.textContent("#survcal-toggle")),
       "calibration toggle renders ON by default");
    await page.click("#survcal-toggle");
    await page.waitForTimeout(300);
    ok(/CALIBRATED SURVIVAL OFF/.test(await page.textContent("#survcal-toggle")),
       "one tap flips the calibration off");
    const calOff = await page.evaluate(() =>
      window.__calCondSurvival(24, 18, 7) === condSurvival(24, 18, 7));
    ok(calOff, "with the toggle off the wrapper returns the frozen number");
    await page.evaluate(() => localStorage.removeItem("ytfl_survcal_live"));
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

  // ---- scenario 10: PHASE C PLAYER PAGES. Served over a local hermetic
  // server (the page fetches its shards); every block renders from real
  // shard fields and the tap-provenance popover names its source.
  {
    const http = require("http");
    const fs = require("fs");
    const root = path.resolve(".");
    const srv = http.createServer((req, res) => {
      if (req.url === "/favicon.ico"){ res.writeHead(204); return res.end(); }
      const f = path.join(root, decodeURIComponent(req.url.split("?")[0].replace(/^\//, "")));
      try {
        const body = fs.readFileSync(f);
        res.writeHead(200, { "content-type": f.endsWith(".json") ? "application/json"
          : f.endsWith(".html") ? "text/html" : "text/plain" });
        res.end(body);
      } catch { res.writeHead(404); res.end("nope"); }
    });
    await new Promise(r => srv.listen(0, "127.0.0.1", r));
    const base = "http://127.0.0.1:" + srv.address().port;
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", e => errors.push(String(e)));
    page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
    await page.goto(base + "/out/players.html");
    await page.waitForTimeout(1500);
    ok(await page.locator("input[type=search]").count() === 1, "players index renders with search");
    ok(await page.locator(".idxrow").count() > 100, "players index lists the positional boards");
    ok((await page.textContent("#foot")).includes("Provenance"), "players provenance footer renders");
    ok((await page.textContent("#foot")).includes("FantasyFootballCalculator"),
       "players FFC attribution rendered");
    ok(await page.locator(".yc").count() === 0, "players: empty board, zero YOUR CALL chips");
    // a skill player with usage + band
    await page.goto(base + "/out/players.html#p=" + encodeURIComponent("Jahmyr Gibbs"));
    await page.waitForTimeout(800);
    const ptxt = await page.textContent("#content");
    ok(/Jahmyr Gibbs/.test(ptxt), "player page renders the header");
    ok(/Value vs the market/.test(ptxt), "value block renders");
    ok(/market's range on him/.test(ptxt) && /mocks/.test(ptxt), "FFC market band renders with mock count");
    ok(/2025 usage - literal nflverse columns/.test(ptxt), "usage block renders literal columns");
    ok(/Prospect profile/.test(ptxt), "prospect block renders");
    ok(/Not wired, on purpose/.test(ptxt), "absent blocks declared absent");
    // tap-any-number provenance - pattern 1
    await page.click('#content .pv[data-shard="usage_2025.json"]');
    await page.waitForTimeout(300);
    const pop = await page.textContent("#pvpop");
    ok(/usage_2025\.json/.test(pop) && /nflverse/.test(pop) && /fetched/.test(pop),
       "tap a number: popover names shard, source, fetch time");
    const popFit = await page.evaluate(() => {
      const p = document.getElementById("pvpop");
      return { inner: p.scrollWidth - p.clientWidth,
               inView: p.getBoundingClientRect().right <= document.documentElement.clientWidth + 1 };
    });
    ok(popFit.inner <= 1 && popFit.inView,
       "popover content wraps inside its box (long shard URLs included)",
       JSON.stringify(popFit));
    // K/DST carries the floor
    await page.goto(base + "/out/players.html");
    await page.waitForTimeout(500);
    const kName = await page.evaluate(() => {
      const E = null; // page has no engine sentinel; read from the app state
      return fetch("engine_2026.json").then(r => r.json())
        .then(e => e.players.filter(p => p.pos === "K").sort((a, b) => b.vor - a.vor)[0].name);
    });
    await page.goto(base + "/out/players.html#p=" + encodeURIComponent(kName));
    await page.waitForTimeout(800);
    ok((await page.textContent("#content")).includes("projection = floor"),
       "K page carries the floor label");
    ok(errors.length === 0, "players page: zero console errors",
       errors[0] || "");
    await page.close();

    // ---- scenario 11: PHASE D TEAM PAGES on the same hermetic server
    const tpg = await browser.newPage();
    const terr = [];
    tpg.on("pageerror", e => terr.push(String(e)));
    tpg.on("console", m => { if (m.type() === "error") terr.push(m.text()); });
    await tpg.goto(base + "/out/teams.html");
    await tpg.waitForTimeout(1200);
    ok(await tpg.locator(".tgrid a").count() === 32, "teams index lists all 32 teams");
    await tpg.goto(base + "/out/teams.html#t=BUF");
    await tpg.waitForTimeout(800);
    const ttxt = await tpg.textContent("#content");
    ok(/Joe Brady/.test(ttxt) && /REPORTED/.test(ttxt),
       "team page: curated play-caller card with its tag");
    ok(/2025 PROE/.test(ttxt) && /neutral-situation snaps/.test(ttxt),
       "team page: PROE card with its measurement basis");
    ok(/Vacated opportunity/.test(ttxt), "team page: vacated block renders");
    ok(/Depth chart - ranked by value/.test(ttxt) && /slot /.test(ttxt),
       "team page: value-ordered depth grid keeps official slot as metadata");
    ok((ttxt.match(/computation:/g) || []).length >= 4,
       "team page: every instrument carries its computation note");
    // a team OUTSIDE the curated 19 must say so, not assert continuity
    await tpg.goto(base + "/out/teams.html#t=KC");
    await tpg.waitForTimeout(600);
    ok(/not among the 19 confirmed changes/.test(await tpg.textContent("#content")),
       "team page: uncurated team declares absence instead of asserting continuity");
    ok(terr.length === 0, "team page: zero console errors", terr[0] || "");
    await tpg.close();

    // ---- scenario 12: PHASE E HOME. Countdown from the payload, staleness
    // board, overlay completeness on the empty board, mocked trending with
    // names resolved through the payload, all surfaces linked.
    const hpg = await browser.newPage();
    const herr = [];
    hpg.on("pageerror", e => herr.push(String(e)));
    hpg.on("console", m => { if (m.type() === "error") herr.push(m.text()); });
    await hpg.route("**/v1/players/nfl/trending/**", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify([{ player_id: "9221", count: 12345 },
                            { player_id: "0000-nobody", count: 999 }]) }));
    await hpg.goto(base + "/out/home.html");
    await hpg.waitForTimeout(1500);
    const htxt = await hpg.textContent("body");
    ok(/\d+ days/.test(await hpg.textContent("#countdown")) || /DRAFT DAY/.test(htxt),
       "home: countdown renders from the payload date");
    ok(await hpg.locator("#stale table tr").count() >= 7,
       "home: staleness board lists the engine plus every shard");
    ok(/0 calls recorded/.test(htxt), "home: overlay completeness on the empty board");
    ok(/Jahmyr Gibbs/.test(await hpg.textContent("#trend")),
       "home: trending resolves names through the engine payload");
    ok(/counted, not invented/.test(await hpg.textContent("#trend")),
       "home: unknown trending players counted, not invented");
    ok(/0 times in 13 seasons/.test(htxt) && /p=0\.323/.test(htxt),
       "home: history fact carries its caveat");
    for (const s of ["draft_room.html", "players.html", "teams.html", "ff-hub.html"])
      ok(await hpg.locator(`.surfaces a[href="${s}"]`).count() === 1, "home links " + s);
    ok(herr.length === 0, "home: zero console errors", herr[0] || "");
    await hpg.close();
    srv.close();
  }

  // ---- scenario 13: APP SHELL. The shared nav renders on all five pages
  // with exactly one active item; the drawer works at 390px; the draft room
  // collapses to the slim bar in live mode and the answer stack stays above
  // the fold; the pill counts down pre-draft and goes LIVE with the dot.
  {
    const http = require("http");
    const fs = require("fs");
    const root = path.resolve(".");
    const srv = http.createServer((req, res) => {
      if (req.url === "/favicon.ico"){ res.writeHead(204); return res.end(); }
      const f = path.join(root, decodeURIComponent(req.url.split("?")[0].replace(/^\//, "")));
      try {
        const body = fs.readFileSync(f);
        res.writeHead(200, { "content-type": f.endsWith(".json") ? "application/json"
          : f.endsWith(".html") ? "text/html"
          : f.endsWith(".js") ? "text/javascript" : "text/plain" });
        res.end(body);
      } catch { res.writeHead(404); res.end("nope"); }
    });
    await new Promise(r => srv.listen(0, "127.0.0.1", r));
    const base = "http://127.0.0.1:" + srv.address().port;
    const ACTIVE = { "big_board.html": "BIG BOARD", "players.html": "PLAYERS",
                     "teams.html": "TEAMS", "home.html": "HUB",
                     "ff-hub.html": "FINDINGS" };
    for (const [file, label] of Object.entries(ACTIVE)){
      const pg = await browser.newPage();
      await pg.route("**/api.sleeper.app/**", r => r.abort());
      await pg.goto(base + "/out/" + file);
      await pg.waitForTimeout(800);
      ok(await pg.locator(".ynav").count() === 1, `nav renders on ${file}`);
      ok(await pg.locator(".ynav-items a").count() === 6, `nav carries six items on ${file}`);
      const on = pg.locator(".ynav-items a.on");
      ok(await on.count() === 1 && (await on.textContent()).trim() === label
         && await on.getAttribute("aria-current") === "page",
         `exactly one active item on ${file}: ${label}`);
      if (file === "home.html"){
        // phase 3: reveal arms on opted-in pages and completes in-viewport
        const rv = await pg.evaluate(() => ({
          armed: document.querySelectorAll(".card.yrv").length,
          shown: document.querySelectorAll(".card.yrv.in").length }));
        ok(rv.armed > 0 && rv.shown > 0,
           "reveals arm and complete on the home page", JSON.stringify(rv));
      }
      // dark lock: these pages load under the default (light) OS preference
      // in this suite, and must render the dark family anyway
      ok(await pg.evaluate(() => getComputedStyle(document.body).backgroundColor)
         === "rgb(11, 17, 32)",
         `${file} renders dark under a light OS preference`);
      await pg.close();
    }
    // drawer behavior at 390px
    const dw = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await dw.route("**/api.sleeper.app/**", r => r.abort());
    await dw.goto(base + "/out/players.html");
    await dw.waitForTimeout(800);
    ok(await dw.locator(".ynav-burger").isVisible(), "hamburger shows at 390px");
    ok(!(await dw.locator(".ynav-items").isVisible()), "inline items hide at 390px");
    await dw.click(".ynav-burger");
    ok(await dw.locator(".ynav-drawer").isVisible(), "drawer opens over the scrim");
    await dw.keyboard.press("Escape");
    ok(!(await dw.locator(".ynav-drawer").isVisible()), "Escape closes the drawer");
    await dw.close();
    // draft room pre-draft: full bar with the countdown pill
    const pd = await browser.newPage({ viewport: { width: 390, height: 844 } });
    const idSlots13 = {}; for (let i = 1; i <= 12; i++) idSlots13[i] = i;
    await pd.route("**/v1/draft/*", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify({ status: "pre_draft", draft_order: null,
                             slot_to_roster_id: idSlots13 }) }));
    await pd.goto(base + "/out/draft_room.html");
    await pd.waitForTimeout(3000);
    ok(/\d+ DAYS|DRAFT DAY/.test(await pd.textContent("#ynav-pill")),
       "pre-draft pill counts down from the payload date");
    ok(!(await pd.evaluate(() => document.documentElement.classList.contains("ynav-slim"))),
       "pre-draft keeps the full 52px bar");
    await pd.close();
    // draft room LIVE at 390px: slim bar, answer stack above the fold
    const lv = await browser.newPage({ viewport: { width: 390, height: 844 } });
    const mk13 = (f, l, pos) => ({ metadata: { first_name: f, last_name: l, position: pos } });
    await lv.route("**/v1/players/nfl/trending/**", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: "[]" }));
    await lv.route("**/v1/draft/*/picks", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify([mk13("Ja'Marr","Chase","WR"), mk13("Bijan","Robinson","RB"),
                            mk13("Jahmyr","Gibbs","RB")]) }));
    await lv.route("**/v1/draft/*", r => {
      if (r.request().url().endsWith("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", draft_order: { "345197760305307648": 7 },
                               slot_to_roster_id: idSlots13 }) });
    });
    await lv.goto(base + "/out/draft_room.html");
    await lv.waitForTimeout(3500);
    ok(await lv.evaluate(() => document.documentElement.classList.contains("ynav-slim")),
       "live mode collapses the bar to the slim strip");
    const navH = await lv.evaluate(() => document.querySelector(".ynav").offsetHeight);
    ok(navH === 36, "slim bar is 36px", String(navH));
    ok(/LIVE/.test(await lv.textContent("#ynav-pill"))
       && await lv.locator("#ynav-pill .dot").count() === 1,
       "live pill carries the label and the freshness dot");
    for (const [sel, name13] of [[".bignm", "answer name"], ["#lv-gear", "gear"], ["#lv-why", "verdict line"]]){
      const box = await lv.locator(sel).boundingBox();
      ok(box && box.y >= 0 && box.y + box.height <= 844,
         `live first paint keeps the ${name13} above the fold at 390px`,
         box ? `bottom ${Math.round(box.y + box.height)}` : "missing");
    }
    ok(await lv.evaluate(() => document.querySelectorAll(".yrv").length) === 0,
       "the draft room receives zero entrance animations");
    await lv.close();
    srv.close();
  }

  // ---- scenario 15: BIG BOARD (CVS). The on-screen order is the payload's
  // CVS rank; all signal channels render with the legend; Explain opens with
  // the full factor decomposition and walter quotes; the delta and conflicts
  // views render from the payload; filters persist across a reload.
  {
    const http = require("http");
    const fs = require("fs");
    const root = path.resolve(".");
    const srv = http.createServer((req, res) => {
      if (req.url === "/favicon.ico"){ res.writeHead(204); return res.end(); }
      const f = path.join(root, decodeURIComponent(req.url.split("?")[0].replace(/^\//, "")));
      try {
        res.writeHead(200, { "content-type": f.endsWith(".json") ? "application/json"
          : f.endsWith(".html") ? "text/html"
          : f.endsWith(".js") ? "text/javascript" : "text/plain" });
        res.end(fs.readFileSync(f));
      } catch { res.writeHead(404); res.end(); }
    });
    await new Promise(r => srv.listen(0, "127.0.0.1", r));
    const base = "http://127.0.0.1:" + srv.address().port;
    const pg = await browser.newPage();
    const errs15 = [];
    pg.on("pageerror", e => errs15.push(String(e)));
    pg.on("console", m => { if (m.type() === "error") errs15.push(m.text()); });
    await pg.goto(base + "/out/big_board.html");
    await pg.waitForTimeout(1500);
    ok(await pg.locator("#board .brow").count() >= 150, "big board renders the CVS pool");
    // the order on screen must be the payload's CVS order - fetch and compare
    const orderOk = await pg.evaluate(async () => {
      const C = await fetch("cvs.json").then(r => r.json());
      const want = C.players.slice(0, 10).map(p => p.name);
      const got = [...document.querySelectorAll("#board .brow .nm a")].slice(0, 10).map(a => a.textContent.trim());
      return JSON.stringify(want) === JSON.stringify(got);
    });
    ok(orderOk, "on-screen order IS the payload CVS order, top 10 exact");
    // signal encoding: legend always visible with every label + conflict marker
    const leg = await pg.textContent("#legend");
    for (const lbl of ["MY DND", "DND x2", "TARGET x2", "SLEEPER x2", "CONFLICT"])
      ok(leg.includes(lbl), "legend carries " + lbl);
    ok(await pg.locator('#board .brow[data-sig]:not([data-sig=""])').count() >= 5,
       "signal container treatments render on the board");
    ok(await pg.locator("#board .brow .sig svg").count() >= 5,
       "signal icons render (third channel)");
    // Explain: full factor decomposition + walter layer
    const explOk = await pg.evaluate(() => {
      const row = [...document.querySelectorAll("#board .brow")]
        .find(r => r.querySelector(".wq"));
      const d = (row || document.querySelector("#board .brow")).querySelector("details");
      d.open = true;
      return { rows: d.querySelectorAll(".xtable tr").length,
               walter: /Walter layer:/.test(d.textContent),
               quote: !!d.querySelector(".wq") };
    });
    ok(explOk.rows === 8, "Explain opens with all 7 factor rows", String(explOk.rows));
    ok(explOk.walter && explOk.quote, "Explain shows the walter layer with its quote");
    const ftxt = await pg.textContent(".factors");
    ok(/CVS = VOR \+ z_point_scale x weighted-z/.test(ftxt),
       "the ledger states the anchor law");
    ok(/NOT WIRED, ON PURPOSE/.test(ftxt) && /p=0\.99/.test(ftxt),
       "the factor ledger keeps the rejected folds and the missing sources");
    // CVS vs WALTER view: delta table + regression cross-map
    await pg.click('#views button[data-v="delta"]');
    await pg.waitForTimeout(300);
    ok(await pg.locator("#delta-t tr").count() >= 5, "walter delta table renders");
    const cross = await pg.textContent("#cross-t");
    ok(/agree/.test(cross) && /disagree/.test(cross),
       "regression cross-map renders both agreement kinds");
    const tmv = await pg.textContent("#tiermoves");
    ok(tmv.length > 10 && (/tier \d to \d/.test(tmv) || /none at the current cap/.test(tmv)),
       "tier-move list renders names or says none, never hides");
    // CONFLICTS view: the Jayden Daniels queue entry
    await pg.click('#views button[data-v="conflicts"]');
    await pg.waitForTimeout(300);
    const conf = await pg.textContent("#v-conflicts");
    ok(/Jayden Daniels/.test(conf), "model conflict queue names the live conflict");
    ok(/disagreement preserved/.test(conf), "signal conflicts keep both sides visible");
    // filter persistence: set RB + a signal filter, reload, both survive
    await pg.click('#views button[data-v="board"]');
    await pg.click('#posf button[data-pos="RB"]');
    await pg.waitForTimeout(300);
    ok((await pg.textContent("#board")).indexOf("QB - ") === -1,
       "position filter actually filters");
    await pg.reload();
    await pg.waitForTimeout(1200);
    ok(await pg.locator('#posf button[data-pos="RB"].on').count() === 1,
       "position filter persists across reload");
    ok((await pg.textContent("#board")).indexOf("QB - ") === -1,
       "reloaded board still filtered");
    // the live kill-switch: order becomes the server-ranked pure-model
    // board, the note renders, and the state survives a reload
    await pg.click('#posf button[data-pos="ALL"]');
    await pg.click("#wl-toggle");
    await pg.waitForTimeout(300);
    ok(/WALTER LAYER OFF/.test(await pg.textContent("#togf")),
       "kill-switch toggle flips to OFF");
    ok(/pure model board/.test(await pg.textContent("#board")),
       "off-mode note renders on the board");
    const nwOrderOk = await pg.evaluate(async () => {
      const C = await fetch("cvs.json").then(r => r.json());
      const want = C.players.slice().sort((a, b) => a.no_walter.cvs_rank - b.no_walter.cvs_rank)
        .slice(0, 10).map(p => p.name);
      const got = [...document.querySelectorAll("#board .brow .nm a")].slice(0, 10).map(a => a.textContent.trim());
      return JSON.stringify(want) === JSON.stringify(got);
    });
    ok(nwOrderOk, "off-mode order IS the server-ranked no-walter order, top 10 exact");
    await pg.reload();
    await pg.waitForTimeout(1200);
    ok(/WALTER LAYER OFF/.test(await pg.textContent("#togf")),
       "kill-switch state survives a reload");
    await pg.click("#wl-toggle");
    await pg.waitForTimeout(300);
    ok(!/pure model board/.test(await pg.textContent("#board")),
       "toggling back restores the walter board");
    ok(/floors/.test(await pg.textContent("#kdef-card")),
       "K/DST floor card renders off the CVS board");
    ok(/walter cap 10%/.test(await pg.textContent("#foot")),
       "provenance footer echoes the cap from config");
    ok(errs15.length === 0, "big board: zero console errors", errs15[0] || "");
    await pg.close();

    // phone-width net: no horizontal overflow at 375, and injury badges
    // never paint over the conf/vol column (the polish-pass regression)
    const p375 = await browser.newPage({ viewport: { width: 375, height: 667 } });
    await p375.goto(base + "/out/big_board.html");
    await p375.waitForTimeout(1500);
    const m375 = await p375.evaluate(() => {
      const doc = document.documentElement;
      let collisions = 0;
      for (const row of document.querySelectorAll("#board .brow")){
        const inj = row.querySelector(".inj"), trio = row.querySelector(".trio");
        if (!inj || !trio) continue;
        const a = inj.getBoundingClientRect(), b = trio.getBoundingClientRect();
        if (a.right > b.left + 1 && a.left < b.right && a.bottom > b.top && a.top < b.bottom)
          collisions++;
      }
      return { overflow: doc.scrollWidth - doc.clientWidth, collisions };
    });
    ok(m375.overflow <= 1, "big board 375: no horizontal page overflow",
       String(m375.overflow));
    ok(m375.collisions === 0, "big board 375: injury badges never overlap the score column",
       String(m375.collisions));
    await p375.close();

    // ---- scenario 16: PICK ENGINE. Served over the same hermetic server so
    // cvs.json resolves; a mocked live draft with Anthony's seat. The card is
    // additive: it names an available player, states its proxy honestly, and
    // the audited verdict card above it never mentions the lens.
    const pe = await browser.newPage();
    const errs16 = [];
    pe.on("pageerror", e => errs16.push(String(e)));
    pe.on("console", m => { if (m.type() === "error") errs16.push(m.text()); });
    const order16 = {}; order16["345197760305307648"] = 7;
    const s2r16 = {}; for (let i = 1; i <= 12; i++) s2r16[i] = i;
    await pe.route("**/v1/draft/*/picks", r => r.fulfill({
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify([
        { metadata: { first_name: "Jahmyr", last_name: "Gibbs", position: "RB" } },
        { metadata: { first_name: "Bijan", last_name: "Robinson", position: "RB" } },
        { metadata: { first_name: "Ja'Marr", last_name: "Chase", position: "WR" } },
      ]) }));
    await pe.route("**/v1/draft/*", r => {
      if (r.request().url().endsWith("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", draft_order: order16,
                               slot_to_roster_id: s2r16 }) });
    });
    await pe.goto(base + "/out/draft_room.html");
    await pe.waitForTimeout(3500);
    ok(await pe.locator("#pe-card:visible").count() === 1, "pick engine card renders live");
    const petxt = await pe.textContent("#pe-body");
    ok(/CVS/.test(petxt) && !/unreachable/.test(petxt), "pick engine loaded cvs.json");
    const peName = await pe.textContent("#pe-body .rname");
    ok(!/Gibbs|Bijan|Chase/.test(peName), "the pick is an available player: " + peName.trim().split("\n")[0]);
    ok((petxt.match(/alt \d:/g) || []).length === 2, "two alternates with conditions");
    ok(/take him if|take him /.test(petxt), "each alternate carries its condition");
    ok(/Cost of waiting/.test(petxt), "cost of waiting from the survival model");
    ok(/confidence (HIGH|MEDIUM|LOW)/.test(await pe.textContent("#pe-card")),
       "confidence band stated");
    ok(/not a title-odds simulation/.test(petxt), "the proxy is labelled honestly");
    ok(/wk15-17/.test(petxt), "weeks 15-17 lens on the card");
    // isolation: the audited verdict card never mentions the lens
    const lvtxt = await pe.textContent("#lv");
    ok(!/CVS|championship/.test(lvtxt), "verdict card untouched by the pick engine");
    ok(/Survival to your pick/.test(await pe.textContent("body")),
       "audited survival table still renders");
    ok(!/NaN/.test(petxt), "pick engine renders no NaN");
    // SIGNAL ENCODING in the room: badges, containers, and legends render
    // from the loaded cvs.json with the board's exact states
    const sigOn = await pe.evaluate(() => ({
      badges: document.querySelectorAll(".sig").length,
      containers: document.querySelectorAll("[data-sig]").length,
      legends: document.querySelectorAll(".siglegend").length,
    }));
    ok(sigOn.badges >= 3, "room signal badges render (icon + label)",
       String(sigOn.badges));
    ok(sigOn.containers >= 3, "room signal containers render (third channel)",
       String(sigOn.containers));
    ok(sigOn.legends >= 1, "room signal legend renders", String(sigOn.legends));
    // the Board tab (best-available view) carries all three channels too
    const vb = await pe.evaluate(() => ({
      containers: document.querySelectorAll("#scr-board .vrow[data-sig]").length,
      badges: document.querySelectorAll("#scr-board .sig").length,
      legends: document.querySelectorAll("#scr-board .siglegend").length,
    }));
    ok(vb.containers >= 3, "value board rows carry the signal container", String(vb.containers));
    ok(vb.badges >= 3, "value board rows carry signal badges", String(vb.badges));
    ok(vb.legends >= 1, "value board carries the signal legend", String(vb.legends));
    // the shared kill-switch: with the layer off, the card says so and
    // scores from the pure-model variant with no walter percentages
    await pe.evaluate(() => localStorage.setItem("ytfl_walter_live", "off"));
    await pe.reload();
    await pe.waitForTimeout(3500);
    const sigOff = await pe.evaluate(() => document.querySelectorAll(".sig").length);
    ok(sigOff !== sigOn.badges,
       "walter toggle changes the room's rendered signals (server variants)",
       `${sigOn.badges} -> ${sigOff}`);
    const offtxt = await pe.textContent("#pe-body");
    ok(/WALTER LAYER OFF/.test(offtxt), "pick engine honors the live kill-switch");
    ok(!/walter [+-]/.test(offtxt), "off-mode card carries no walter percentages");
    ok(!/NaN/.test(offtxt), "off-mode card renders no NaN");
    await pe.evaluate(() => localStorage.removeItem("ytfl_walter_live"));
    ok(errs16.length === 0, "pick engine: zero console errors", errs16[0] || "");
    await pe.close();

    // on the clock (6 picks gone, seat 7 up at pick 7): the card must look
    // to my NEXT turn (pick 18) - never the degenerate survival-to-now
    const oc = await browser.newPage();
    const errsOc = [];
    oc.on("pageerror", e => errsOc.push(String(e)));
    const ocPicks = ["Jahmyr Gibbs RB", "Bijan Robinson RB", "Ja'Marr Chase WR",
      "Saquon Barkley RB", "Justin Jefferson WR", "CeeDee Lamb WR"].map(s => {
        const parts = s.split(" ");
        return { metadata: { first_name: parts[0], last_name: parts.slice(1, -1).join(" "),
                             position: parts[parts.length - 1] } };
      });
    await oc.route("**/v1/draft/*/picks", r => r.fulfill({
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify(ocPicks) }));
    await oc.route("**/v1/draft/*", r => {
      if (r.request().url().endsWith("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", draft_order: order16,
                               slot_to_roster_id: s2r16 }) });
    });
    await oc.goto(base + "/out/draft_room.html");
    await oc.waitForTimeout(3500);
    ok(/ON THE CLOCK - PICK 7/.test(await oc.textContent("body")),
       "on-the-clock fixture: seat 7 is up at pick 7");
    const octxt = await oc.textContent("#pe-body");
    ok(/your pick 18/.test(octxt),
       "on my clock the card targets my NEXT turn, not the current pick");
    ok(!/: 0% gone by your pick/.test(octxt),
       "survival on my clock is not the degenerate 100%-safe");
    ok(!/NaN/.test(octxt), "on-the-clock card renders no NaN");
    ok(errsOc.length === 0, "on-the-clock: zero console errors", errsOc[0] || "");
    // phone-width net: the survival table's verdict tags fire here (target
    // pick 18 makes most top rows sub-40%), so this state is exactly where
    // the table used to widen the page at 375
    await oc.setViewportSize({ width: 375, height: 667 });
    await oc.waitForTimeout(400);
    const ocOver = await oc.evaluate(() => {
      const d = document.documentElement;
      return d.scrollWidth - d.clientWidth;
    });
    ok(ocOver <= 1, "draft room live 375: no horizontal page overflow",
       String(ocOver));
    await oc.close();
    srv.close();
  }

  // ---- scenario 14: TEASER. The shared build renders its countdown and
  // locked cards, fetches NOTHING beyond its own page, and every link stays
  // inside out/teaser/.
  {
    const http = require("http");
    const fs = require("fs");
    const root = path.resolve(".");
    const srv = http.createServer((req, res) => {
      if (req.url === "/favicon.ico"){ res.writeHead(204); return res.end(); }
      const f = path.join(root, decodeURIComponent(req.url.split("?")[0].replace(/^\//, "")));
      try {
        res.writeHead(200, { "content-type": f.endsWith(".html") ? "text/html" : "text/plain" });
        res.end(fs.readFileSync(f));
      } catch { res.writeHead(404); res.end(); }
    });
    await new Promise(r => srv.listen(0, "127.0.0.1", r));
    const base = "http://127.0.0.1:" + srv.address().port;
    const pg = await browser.newPage({ viewport: { width: 390, height: 844 } });
    const fetched = [];
    pg.on("request", r => fetched.push(r.url()));
    const errs14 = [];
    pg.on("pageerror", e => errs14.push(String(e)));
    await pg.goto(base + "/out/teaser/index.html");
    await pg.waitForTimeout(800);
    ok(/\d+ days|DRAFT DAY/.test(await pg.textContent("#cd")),
       "teaser hub: countdown renders");
    ok(await pg.locator(".card.lock").count() >= 4,
       "teaser hub: every other card locked");
    const external = fetched.filter(u => !u.includes("/out/teaser/") && !u.endsWith("/favicon.ico"));
    ok(external.length === 0, "teaser fetches nothing beyond its own pages",
       external[0] || "");
    for (const f of ["players.html", "draft_room.html", "teams.html", "ff-hub.html"]){
      await pg.goto(base + "/out/teaser/" + f);
      await pg.waitForTimeout(400);
      const hrefs = await pg.evaluate(() =>
        [...document.querySelectorAll("a[href]")].map(a => a.getAttribute("href")));
      ok(hrefs.every(h => !h.includes("..") && !h.includes("://")),
         `teaser ${f}: every link stays inside the teaser`);
      ok(await pg.locator(".card.lock").count() >= 1
         && (await pg.textContent("body")).length > 0,
         `teaser ${f}: locked cards render`);
    }
    await pg.goto(base + "/out/teaser/players.html");
    await pg.waitForTimeout(400);
    ok(await pg.locator(".row .nm").count() === 12,
       "teaser players: exactly 12 named rows");
    ok(await pg.locator("input").count() === 0, "teaser players: no search, no routing");
    ok(errs14.length === 0, "teaser: zero console errors", errs14[0] || "");
    await pg.close();
    srv.close();
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
