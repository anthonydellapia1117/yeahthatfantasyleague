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

// Keep explicit fresh and stale fixtures: DRAFT_MORNING.md permits an optional-layer lineage lag, so checkout timing must never choose the smoke oracle.
function freshDisplayLayers(){
  const fs = require("fs");
  const engineDigest = JSON.parse(fs.readFileSync(
    path.resolve("out/engine_2026.json"), "utf8")).content_sha256;
  const layers = {};
  for (const name of ["bullish_2026.json", "ceiling_2026.json"]){
    const data = JSON.parse(fs.readFileSync(
      path.resolve("out/data", name), "utf8"));
    data.provenance.engine_content_sha256 = engineDigest;
    layers["/out/data/" + name] = Buffer.from(JSON.stringify(data));
  }
  return layers;
}

function currentRosterLabels(){
  const fs = require("fs");
  const engine = JSON.parse(fs.readFileSync(
    path.resolve("out/engine_2026.json"), "utf8"));
  return [...new Set(engine.rosters.flatMap(r =>
    [r.handle, r.team_name, r.franchise].filter(Boolean)))];
}

(async () => {
  const browser = await chromium.launch({
    // this image ships the browser at a fixed path; CI overrides it
    executablePath: process.env.PW_CHROMIUM || "/opt/pw-browsers/chromium" });

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
    const ohypTxt = await page.textContent("#ohyp-card");
    const engR = JSON.parse(require("fs").readFileSync(
      path.resolve("out/engine_2026.json"), "utf8")).rosters;
    ok(engR.every(r => ohypTxt.includes(r.handle)),
       "order hypothesis: every option carries its sleeper handle");
    ok(engR.every(r => ohypTxt.includes(r.franchise)),
       "order hypothesis: every option still carries its franchise era");
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
    await page.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" }, body: "[]" }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
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
    ok(/sleeper (FAILED|TIMEOUT) after \d+ms/.test(await page.textContent("#conn")),
       "offline: the connection diagnostic names the failure and its timing");
    ok(await page.locator(".chips button").count() === 12, "offline still renders scenarios");
    await page.close();
  }

  // ---- scenario 3: mocked live draft
  {
    const page = await browser.newPage();
    const order = {}; order["345197760305307648"] = 7;
    const slotToRoster = {}; for (let i = 1; i <= 12; i++) slotToRoster[i] = i;
    await page.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify([
        { metadata: { first_name: "Jahmyr", last_name: "Gibbs", position: "RB" } },
        { metadata: { first_name: "Bijan", last_name: "Robinson", position: "RB" } },
        { metadata: { first_name: "Ja'Marr", last_name: "Chase", position: "WR" } },
      ]),
    }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
      r.fulfill({
        contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", settings: { teams: 12, rounds: 14, pick_timer: 90 }, last_picked: Date.now() - 12000, draft_order: order,
                               slot_to_roster_id: slotToRoster }),
      });
    });
    await page.goto(FILE);
    await page.waitForTimeout(3000);
    const mode = await page.textContent("#mode");
    ok(/LIVE/.test(mode), "mode 2 detected");
    ok(/seat 7/.test(mode), "Anthony's seat auto-detected from the draw");
    ok(/sleeper 200 - \d+ms/.test(await page.textContent("#conn")),
       "live: the connection diagnostic shows status and round-trip");
    ok(/data \d+s old/.test(await page.textContent("#conn")),
       "live: SOURCE age is shown separately from fetch time");
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
    await page.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" },
      body: "[]" }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", settings: { teams: 12, rounds: 14, pick_timer: 90 }, last_picked: Date.now() - 12000, draft_order: null,
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
    await page.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify(picks) }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", settings: { teams: 12, rounds: 14, pick_timer: 90 }, last_picked: Date.now() - 12000, draft_order: { "345197760305307648": 7 },
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
    // f6: position run - 6 RBs in the last 8 picks, round 2. Under the
    // archive's rd1-3 base rates (RB ~45%) that is binomial p ~= 0.09: the
    // derived detector correctly reads it as the league's normal diet and
    // stays silent (the old 4-of-8 constant fired here). NOTE the old body
    // regex was vacuous - page textContent includes the script source, where
    // the banner template itself says "POSITION RUN" - so this asserts the
    // rendered element. The positive case lives in the QB-burst scenario.
    ok((await page.textContent("#f-run")).trim() === "",
       "f6 six early RBs is the archive's normal - derived detector stays silent",
       (await page.textContent("#f-run")).trim().slice(0, 60));
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
    await page.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify([{ metadata: { first_name: "Jonathan", last_name: "Taylor", position: "RB" } }]) }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
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
    await page.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" }, body: "[]" }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", settings: { teams: 12, rounds: 14, pick_timer: 90 }, last_picked: Date.now() - 12000, draft_order: null,
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
    await page.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: "[]" }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", settings: { teams: 12, rounds: 14, pick_timer: 90 }, last_picked: Date.now() - 12000, draft_order: { "345197760305307648": 7 },
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
    await page.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify(picks) }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", settings: { teams: 12, rounds: 14, pick_timer: 90 }, last_picked: Date.now() - 12000, draft_order: { "345197760305307648": 7 },
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
    await page.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify(picks) }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", settings: { teams: 12, rounds: 14, pick_timer: 90 }, last_picked: Date.now() - 12000, draft_order: { "345197760305307648": 7 },
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
      O.state.map = { "unit-bull": { player: "Aaa Bbb", call: "BULL",
                                     move: "+1 tier", reason: "r", source: "s",
                                     date: "2026-08-13", matched: true },
                      "unit-bear": { player: "Ccc Ddd", call: "BEAR",
                                     move: "", reason: "r", source: "s",
                                     date: "2026-08-13", matched: true } };
      const res = {
        chip: O.chip({ name: "Aaa Bbb", sleeper_id: "unit-bull" }),
        chipNone: O.chip({ name: "Zzz Qqq", sleeper_id: "unit-none" }),
        flipBull: O.flip([{ name: "Zzz Qqq", sleeper_id: "unit-none" },
                          { name: "Aaa Bbb", sleeper_id: "unit-bull" }]),
        flipNone: O.flip([{ name: "Zzz Qqq", sleeper_id: "unit-none" },
                          { name: "Yyy Www", sleeper_id: "unit-other" }]),
        resorted: O.resort([
          { name: "P One", sleeper_id: "unit-one", pos: "RB", tier: 2, vor: 90 },
          { name: "Ccc Ddd", sleeper_id: "unit-bear", pos: "RB", tier: 2, vor: 88 },
          { name: "Aaa Bbb", sleeper_id: "unit-bull", pos: "RB", tier: 2, vor: 85 },
          { name: "P Four", sleeper_id: "unit-four", pos: "RB", tier: 3, vor: 80 },
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
               matched: true, sleeper_id: p.sleeper_id, pos: p.pos,
               adp: p.adp, vor: p.vor, tier: p.tier };
    };
    // The bull call has to sit on whoever the model actually ranks second
    // behind its primary once the fixture's six picks are gone - naming a
    // player outright bakes one day's ADP into the suite (Ashton Jeanty was
    // the runner until a refresh moved his VOR 99 -> 74). Derive it.
    const gone9 = new Set(["Ja'Marr Chase", "Bijan Robinson", "Jahmyr Gibbs",
                           "Jonathan Taylor", "Puka Nacua", "Christian McCaffrey"]);
    const alive9 = payload.players
      .filter(x => !gone9.has(x.name) && x.pos !== "K" && x.pos !== "DEF")
      .sort((x, y) => y.vor - x.vor);
    const runnerUp = alive9[1].name;
    payload.my_board = [mkCall(runnerUp, "BULL", "+1 tier"),
                        mkCall(alive9[8].name, "BEAR", "-1 tier")];
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "ytfl-overlay-smoke-"));
    const tmp = path.join(tmpDir, "ytfl_overlay_smoke.html");
    fs.writeFileSync(tmp, raw.slice(0, a) + JSON.stringify(payload) + raw.slice(b));
    fs.copyFileSync(path.resolve("out/player_names.js"), path.join(tmpDir, "player_names.js"));
    const p9 = await browser.newPage();
    const mk9 = (f, l, pos) => ({ metadata: { first_name: f, last_name: l, position: pos } });
    const picks9 = [mk9("Ja'Marr","Chase","WR"), mk9("Bijan","Robinson","RB"),
      mk9("Jahmyr","Gibbs","RB"), mk9("Jonathan","Taylor","RB"),
      mk9("Puka","Nacua","WR"), mk9("Christian","McCaffrey","RB")];
    const idSlots9 = {}; for (let i = 1; i <= 12; i++) idSlots9[i] = i;
    await p9.route("**/v1/players/nfl/trending/**", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: "[]" }));
    await p9.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify(picks9) }));
    await p9.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", settings: { teams: 12, rounds: 14, pick_timer: 90 }, last_picked: Date.now() - 12000, draft_order: { "345197760305307648": 7 },
                               slot_to_roster_id: idSlots9 }) });
    });
    await p9.goto("file://" + tmp);
    await p9.waitForTimeout(3000);
    const big9 = await p9.textContent(".bignm");
    const expectedPrimary = alive9[0].name;
    ok(big9.includes(expectedPrimary),
       "overlay e2e: the model primary is still the subject (" + expectedPrimary + ")",
       big9.trim());
    const body9 = await p9.textContent("body");
    ok(body9.includes("break toward your call - " + runnerUp),
       "overlay e2e: live coin flip breaks toward the bull call (" + runnerUp + ")");
    await p9.click('#nav button[data-scr="board"]');
    await p9.waitForTimeout(400);
    ok(await p9.locator(".yc.bull").count() >= 1 && await p9.locator(".yc.bear").count() >= 1,
       "overlay e2e: YOUR CALL chips render on the value board");
    await p9.close();
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }

  // ---- scenario 10: PHASE C PLAYER PAGES. Served over a local hermetic
  // server (the page fetches its shards); every block renders from real
  // shard fields and the tap-provenance popover names its source.
  {
    const http = require("http");
    const fs = require("fs");
    const root = path.resolve(".");
    const freshLayers = freshDisplayLayers();
    const srv = http.createServer((req, res) => {
      if (req.url === "/favicon.ico"){ res.writeHead(204); return res.end(); }
      const urlPath = decodeURIComponent(req.url.split("?")[0]);
      if (freshLayers[urlPath]){
        res.writeHead(200, { "content-type": "application/json" });
        return res.end(freshLayers[urlPath]);
      }
      const f = path.join(root, urlPath.replace(/^\//, ""));
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

    // players index: 3-across groups, tight rows, database-wide VOR ramp,
    // in-group filtering that REMOVES rows and collapses emptied groups
    await page.goto(base + "/out/players.html");
    await page.waitForTimeout(700);
    const grpOrder = await page.$$eval("#pgrid .pgrp h2",
      els => els.map(e => e.textContent.trim().split(/\s+/)[0]));
    ok(JSON.stringify(grpOrder) === JSON.stringify(["QB","RB","WR","TE","DST","K"]),
       "players: groups run QB RB WR then TE DST K", grpOrder.join(","));
    ok(await page.$eval("#pgrid", el =>
         getComputedStyle(el).gridTemplateColumns.split(" ").length === 3),
       "players: the grid renders three containers across");
    ok(await page.$eval(".idxrow", el =>
         getComputedStyle(el).justifyContent === "flex-start"),
       "players: rows pack name and numbers together, not space-between");
    // the ramp: highest-VOR player greener than the lowest shown, and both
    // colored from the same database-wide scale
    const ramp = await page.evaluate(() => {
      const vs = [...document.querySelectorAll("#pgrid .vorv")];
      const parse = e => getComputedStyle(e).color.match(/\d+/g).map(Number);
      const nums = vs.map(e => ({ v: parseFloat(e.textContent.replace(/\D+/g, "")),
                                  c: parse(e) }));
      nums.sort((a, b) => b.v - a.v);
      return { hi: nums[0].c, lo: nums[nums.length - 1].c, n: nums.length };
    });
    ok(ramp.n > 50 && ramp.hi[1] > ramp.hi[0] && ramp.lo[0] > ramp.lo[1],
       "players: VOR ramp runs green at the top and red at the bottom",
       JSON.stringify(ramp));
    ok(!/color/.test(await page.$eval("#pgrid .nums", el => el.outerHTML)
        .then(h => h.replace(/<span class="vorv"[^>]*>.*?<\/span>/, ""))),
       "players: ADP carries no color conditioning");
    // filter: BULLISH/WATCH only
    const beforeRows = await page.locator("#pgrid .idxrow").count();
    const beforeGrps = await page.locator("#pgrid .pgrp:not([hidden])").count();
    await page.click('#pfilt button[data-pf="bull"]');
    await page.waitForTimeout(300);
    const afterRows = await page.locator("#pgrid .idxrow").count();
    ok(afterRows > 0 && afterRows < beforeRows,
       "players: tagged-only filter removes non-matching rows from the DOM",
       beforeRows + " -> " + afterRows);
    ok(await page.locator("#pgrid .pgrp[hidden]").count() > 0 ||
       await page.locator("#pgrid .pgrp:not([hidden])").count() < beforeGrps,
       "players: a group with no matches collapses out of the grid");
    ok(/FILTERED/.test(await page.textContent("#pactive")),
       "players: active-filter state is visible");
    await page.click("#pf-clear");
    await page.waitForTimeout(300);
    ok(await page.locator("#pgrid .idxrow").count() === beforeRows &&
       await page.locator("#pgrid .pgrp:not([hidden])").count() === beforeGrps,
       "players: CLEAR ALL restores every group and row");
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
    await tpg.goto(base + "/out/teams.html#t=LAR");
    await tpg.waitForTimeout(600);
    const lartxt = await tpg.textContent("#content");
    ok(/LAR/.test(lartxt) && /2025 PROE/.test(lartxt) && /Puka Nacua/.test(lartxt),
       "team page: LAR route joins nflverse LA PROE and depth evidence");
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
      const shellErrors = [];
      pg.on("pageerror", e => shellErrors.push(String(e)));
      pg.on("console", m => { if (m.type() === "error") shellErrors.push(m.text()); });
      await pg.route("**/api.sleeper.app/**", r => r.abort());
      await pg.goto(base + "/out/" + file);
      await pg.waitForTimeout(800);
      ok(await pg.locator(".ynav").count() === 1, `nav renders on ${file}`);
      ok(await pg.locator(".ynav-items a").count() === 7, `nav carries seven items on ${file}`);
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
      if (file === "ff-hub.html"){
        const n1 = JSON.parse(fs.readFileSync(
          path.resolve("out/data/bullish_vs_adp.json"), "utf8"));
        await pg.waitForFunction(() =>
          document.querySelector("#n1State").dataset.state !== "loading");
        await pg.click('.tabs button[data-p="p5"]');
        ok(await pg.locator("#n1State").getAttribute("data-state") === "ready",
           "findings N.1: computed artifact reaches an explicit ready state");
        ok(await pg.locator("#n1Results").isVisible(),
           "findings N.1: reviewed result is visible after artifact load");
        ok((await pg.textContent("#n1Text")).trim() === n1.verdict,
           "findings N.1: verdict is rendered verbatim from the artifact");
        const oneDecimal = v => (Math.round(v * 1000) / 10).toFixed(1);
        const pct = v => oneDecimal(v) + "%";
        const pp = v => (v >= 0 ? "+" : "") + oneDecimal(v);
        const hit = side => side.n
          ? `${side.hit12.k}/${side.n} (${pct(side.hit12.rate)})`
          : "0 - not identifiable";
        const lift = v => v
          ? `${pp(v.diff)}pp [${pp(v.diff_ci95[0])}, ${pp(v.diff_ci95[1])}]`
          : "not identifiable";
        const labels = {"pos1-12":"Positional 1-12", "pos13-24":"Positional 13-24",
                        "pos25-48":"Positional 25-48"};
        const expectedRows = Object.entries(labels).map(([key, label]) => {
          const b = n1.within_band[key];
          return [label, hit(b.tagged), hit(b.untagged), lift(b.lift_hit12),
                  b.lift_hit12 ? b.lift_hit12.p_two_sided.toFixed(3) : "-"];
        });
        const actualRows = await pg.$$eval("#n1Body tr", rows => rows.map(row =>
          [...row.querySelectorAll("td")].map(td => td.textContent.trim())));
        ok(JSON.stringify(actualRows) === JSON.stringify(expectedRows),
           "findings N.1: every rendered band cell comes from the artifact",
           JSON.stringify(actualRows));
        const expectedConcentration =
          `${pct(n1.concentration.share_in_top12_band)} of tags are in positional ADP 1-12. ` +
          n1.concentration.note;
        ok((await pg.textContent("#n1Concentration")).trim() === expectedConcentration,
           "findings N.1: tag concentration and note come from the artifact");
        const verdictLabel = n1.verdict.split(/\s[—-]\s/)[0];
        ok((await pg.locator("#n1Verdict").getAttribute("class")) === "tag" &&
           (await pg.textContent("#n1Verdict")).trim() === verdictLabel,
           "findings N.1: verdict uses the neutral tag scale");
        ok((await pg.textContent("#n1Hero")).includes(verdictLabel),
           "findings N.1: the hero states a verdict only after artifact success");
      }
      // dark lock: these pages load under the default (light) OS preference
      // in this suite, and must render the dark family anyway
      ok(await pg.evaluate(() => getComputedStyle(document.body).backgroundColor)
         === "rgb(11, 17, 32)",
         `${file} renders dark under a light OS preference`);
      if (file === "ff-hub.html")
        ok(shellErrors.length === 0, `${file}: zero console errors`, shellErrors[0] || "");
      await pg.close();
    }
    // TE matrix honesty: the artifact omits per-player rows but every surface
    // states why. This remains separate from stale/missing optional-shard tests.
    const bullArtifact = JSON.parse(fs.readFileSync(
      path.resolve("out/data/bullish_2026.json"), "utf8"));
    const teSusp = bullArtifact.te_gate_suspension;
    const omittedTe = teSusp.omitted_tags[0];
    const nonTe = bullArtifact.tags.find(t => t.status === "BULLISH");
    for (const file of ["big_board.html", "players.html", "draft_room.html"]){
      const pg = await browser.newPage();
      await pg.route("**/api.sleeper.app/**", r => r.abort());
      await pg.goto(base + "/out/" + file);
      await pg.waitForTimeout(file === "draft_room.html" ? 2500 : 1000);
      ok((await pg.textContent("#bull-status")).trim() === teSusp.display_note &&
         await pg.locator("#bull-status").isVisible(),
         `${file}: TE tag suspension is visible and artifact-driven`);
      if (file === "big_board.html"){
        const teRow = pg.locator(`#board a[href*="${omittedTe.sleeper_id}"]`).locator("xpath=ancestor::div[contains(@class,'brow')]");
        const nonTeRow = pg.locator(`#board a[href*="${nonTe.sleeper_id}"]`).locator("xpath=ancestor::div[contains(@class,'brow')]");
        ok(await teRow.count() === 1 &&
           !/BULLISH|WATCH|SUSPENDED/.test(await teRow.textContent()) &&
           /BULLISH/.test(await nonTeRow.textContent()),
           "big board: omitted TE has no tag while a valid non-TE tag remains");
      } else if (file === "players.html"){
        const teRow = pg.locator(`#pgrid a[href*="${omittedTe.sleeper_id}"]`).locator("xpath=ancestor::div[contains(@class,'idxrow')]");
        const nonTeRow = pg.locator(`#pgrid a[href*="${nonTe.sleeper_id}"]`).locator("xpath=ancestor::div[contains(@class,'idxrow')]");
        const bothBeginVisible = await teRow.count() === 1 && await nonTeRow.count() === 1;
        await pg.click('#pfilt button[data-pf="bull"]');
        await pg.waitForTimeout(100);
        ok(bothBeginVisible && await teRow.count() === 0 && await nonTeRow.count() === 1,
           "players: tagged-only filter omits the suspended TE and keeps a valid non-TE");
      } else {
        const chips = await pg.evaluate(({teId, nonTeId}) => {
          const te = E.players.find(p => String(p.sleeper_id || "") === teId);
          const other = E.players.find(p => String(p.sleeper_id || "") === nonTeId);
          return {te: bullChip(te), other: bullChip(other)};
        }, {teId: String(omittedTe.sleeper_id), nonTeId: String(nonTe.sleeper_id)});
        ok(chips.te === "" && /BULLISH/.test(chips.other),
           "draft room: omitted TE has no chip while a valid non-TE chip remains");
      }
      await pg.close();
    }
    // N.1 failure is deliberately loud. A missing or rejected artifact may
    // never leave a stale table visible or infer a replacement verdict.
    const n1err = await browser.newPage();
    const n1Errors = [];
    n1err.on("pageerror", e => n1Errors.push(String(e)));
    n1err.on("console", m => { if (m.type() === "error") n1Errors.push(m.text()); });
    const malformedN1 = JSON.parse(fs.readFileSync(
      path.resolve("out/data/bullish_vs_adp.json"), "utf8"));
    delete malformedN1.within_band["pos1-12"].tagged.hit12;
    await n1err.route("**/data/bullish_vs_adp.json", r => r.fulfill({
      status: 200, contentType: "application/json", body: JSON.stringify(malformedN1) }));
    await n1err.goto(base + "/out/ff-hub.html");
    await n1err.waitForFunction(() =>
      document.querySelector("#n1State").dataset.state === "error");
    await n1err.click('.tabs button[data-p="p5"]');
    const n1Failure = await n1err.textContent("#n1State");
    ok(/N\.1 unavailable \(unusable schema\)/.test(n1Failure) &&
       /No verdict is inferred/.test(n1Failure),
       "findings N.1: unusable artifact produces a visible no-inference error");
    ok(await n1err.locator("#n1Results").isHidden(),
       "findings N.1: rejected artifact cannot expose stale results");
    const rejectedLabel = malformedN1.verdict.split(/\s[—-]\s/)[0];
    ok(!(await n1err.textContent("#n1Hero")).includes(rejectedLabel),
       "findings N.1: rejected artifact cannot leak its verdict through the hero");
    ok(n1Errors.length === 0, "findings N.1 error state: zero console errors",
       n1Errors[0] || "");
    await n1err.close();
    // A non-2xx response is a different failure mechanism from malformed
    // JSON. Chromium may log the expected failed resource, so this assertion
    // watches uncaught page errors and the visible state instead.
    const n1http = await browser.newPage();
    const n1HttpPageErrors = [];
    n1http.on("pageerror", e => n1HttpPageErrors.push(String(e)));
    await n1http.route("**/data/bullish_vs_adp.json", r => r.fulfill({
      status: 503, contentType: "text/plain", body: "temporarily unavailable" }));
    await n1http.goto(base + "/out/ff-hub.html");
    await n1http.waitForFunction(() =>
      document.querySelector("#n1State").dataset.state === "error");
    await n1http.click('.tabs button[data-p="p5"]');
    const n1HttpFailure = await n1http.textContent("#n1State");
    ok(/N\.1 unavailable \(HTTP 503\)/.test(n1HttpFailure) &&
       /No verdict is inferred/.test(n1HttpFailure),
       "findings N.1: HTTP failure produces a visible no-inference error");
    ok(await n1http.locator("#n1Results").isHidden(),
       "findings N.1: HTTP failure cannot expose stale results");
    const committedN1 = JSON.parse(fs.readFileSync(
      path.resolve("out/data/bullish_vs_adp.json"), "utf8"));
    const committedLabel = committedN1.verdict.split(/\s[—-]\s/)[0];
    ok(!(await n1http.textContent("#n1Hero")).includes(committedLabel),
       "findings N.1: HTTP failure cannot leak the committed verdict");
    ok(n1HttpPageErrors.length === 0,
       "findings N.1 HTTP error state: zero uncaught page errors",
       n1HttpPageErrors[0] || "");
    await n1http.close();
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
    await lv.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify([mk13("Ja'Marr","Chase","WR"), mk13("Bijan","Robinson","RB"),
                            mk13("Jahmyr","Gibbs","RB")]) }));
    await lv.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", settings: { teams: 12, rounds: 14, pick_timer: 90 }, last_picked: Date.now() - 12000, draft_order: { "345197760305307648": 7 },
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
    const freshLayers = freshDisplayLayers();
    const srv = http.createServer((req, res) => {
      if (req.url === "/favicon.ico"){ res.writeHead(204); return res.end(); }
      const urlPath = decodeURIComponent(req.url.split("?")[0]);
      if (freshLayers[urlPath]){
        res.writeHead(200, { "content-type": "application/json" });
        return res.end(freshLayers[urlPath]);
      }
      const f = path.join(root, urlPath.replace(/^\//, ""));
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
    // C2 base-rate columns: chips carry the band, the interval, and n; the
    // reference table and its honesty line render under the board
    const brd = await pg.textContent("#board");
    ok(/band pos\d/.test(brd) && /n=\d+/.test(brd),
       "base-rate chips name the band and its sample size");
    ok(await pg.locator("#board .brow .thin").count() >= 5,
       "base-rate intervals render beside the rates");
    ok(/Base rates 2016-2025/.test(brd), "base-rate reference table present");
    ok(/History, not a projection/.test(brd), "base-rate honesty line rendered");
    // C4 ceiling view: enabled, ranked table with boom rates and the zero-IR
    // availability column, limitation stated
    await pg.click('#views button[data-v="ceiling"]');
    await pg.waitForTimeout(300);
    const ceil = await pg.textContent("#v-ceiling");
    ok(/scores every week twice/.test(ceil), "ceiling view states the format basis");
    ok(await pg.locator("#ceil-t tr").count() >= 20, "ceiling table ranks a real pool");
    ok(/\d+\/\d+ \(\d+%\)/.test(ceil), "boom rates render as k/n with percent");
    ok(/No synthetic variance premium/.test(ceil),
       "the lens declares its limitation");
    await pg.click('#views button[data-v="board"]');
    // C5: BULLISH chips render on the board with age, beside the signals
    const bull = await pg.textContent("#board");
    ok(/BULLISH \d+h|WATCH \d+h/.test(bull),
       "BULLISH/WATCH chips render with their age");
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
    // CONFLICTS view: data-driven from the payload - names every live
    // conflict, or shows the explicit empty states; either way, never hides
    await pg.click('#views button[data-v="conflicts"]');
    await pg.waitForTimeout(300);
    const conf = await pg.textContent("#v-conflicts");
    const cvsPayload = JSON.parse(require("fs").readFileSync(
      path.resolve("out/cvs.json"), "utf8"));
    for (const c of cvsPayload.model_conflicts)
      ok(conf.includes(c.name),
         "model conflict queue names the live conflict: " + c.name);
    if (!cvsPayload.model_conflicts.length)
      ok(/queue empty/.test(conf), "model conflict queue states it is empty");
    for (const c of cvsPayload.signal_conflicts)
      ok(conf.includes(c.name) && /disagreement preserved/.test(conf),
         "signal conflicts keep both sides visible: " + c.name);
    if (!cvsPayload.signal_conflicts.length)
      ok(/no opposing signals today/.test(conf),
         "signal conflict list states it is empty");
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
    // BULLISH/WATCH filter: tagged-only, with visible clearable state
    const beforeN = await pg.locator("#board .brow").count();
    await pg.click('#togf button[data-t="bull"]');
    await pg.waitForTimeout(300);
    const afterN = await pg.locator("#board .brow").count();
    ok(afterN > 0 && afterN < beforeN,
       "board: BULLISH/WATCH filter narrows the board to tagged players",
       beforeN + " -> " + afterN);
    const taggedOnly = await pg.$$eval("#board .brow .nm",
      els => els.every(e => /BULLISH|WATCH/.test(e.textContent)));
    ok(taggedOnly, "board: every surviving row carries a tag");
    const af = await pg.textContent("#activef");
    ok(/FILTERED/.test(af) && /BULLISH\/WATCH only/.test(af) &&
       new RegExp(afterN + " of ").test(af),
       "board: active-filter state is visible with the shown-of-total count");
    await pg.click("#af-clear");
    await pg.waitForTimeout(300);
    ok(await pg.locator("#board .brow").count() === beforeN,
       "board: CLEAR ALL restores the unfiltered board");
    ok(await pg.locator("#activef").isHidden(),
       "board: the filter bar hides itself when nothing is filtered");
    ok(errs15.length === 0, "big board: zero console errors", errs15[0] || "");
    await pg.close();

    // Same-day lineage mismatch: optional display layers stay nonfatal, but
    // their old values must read as stale rather than current.
    const staleDisplay = await browser.newPage();
    const staleBull = JSON.parse(fs.readFileSync(
      path.resolve("out/data/bullish_2026.json"), "utf8"));
    staleBull.provenance.engine_content_sha256 = "0".repeat(64);
    const staleCeiling = JSON.parse(fs.readFileSync(
      path.resolve("out/data/ceiling_2026.json"), "utf8"));
    staleCeiling.provenance.engine_content_sha256 = "0".repeat(64);
    await staleDisplay.route("**/data/bullish_2026.json", r => r.fulfill({
      contentType: "application/json", body: JSON.stringify(staleBull) }));
    await staleDisplay.route("**/data/ceiling_2026.json", r => r.fulfill({
      contentType: "application/json", body: JSON.stringify(staleCeiling) }));
    await staleDisplay.goto(base + "/out/big_board.html");
    await staleDisplay.waitForTimeout(1200);
    await staleDisplay.evaluate(() => {
      View.bull = true; persist(); renderFilters(); renderBoard();
    });
    const staleBoardText = await staleDisplay.textContent("#board");
    ok(/BULLISH tags stale versus current board/.test(staleBoardText) &&
       /TAGS STALE \d+h/.test(staleBoardText) &&
       await staleDisplay.locator("#board .brow").count() > 0 &&
       await staleDisplay.locator('button[data-t="bull"]:disabled').count() === 1,
       "big board: stale BULLISH filter is disabled without emptying the board");
    await staleDisplay.click('#views button[data-v="ceiling"]');
    ok(/ceiling data stale versus current board/.test(
         await staleDisplay.textContent("#ceil-t")),
       "big board: mismatched ceiling values are hidden visibly");
    await staleDisplay.goto(base + "/out/players.html");
    await staleDisplay.waitForTimeout(1000);
    await staleDisplay.evaluate(() => {
      PView.bull = true; renderPFilters(); renderGroups();
    });
    ok(/BULLISH tags stale versus current board/.test(
         await staleDisplay.textContent("#content")) &&
       await staleDisplay.locator("#pgrid .idxrow").count() > 0 &&
       await staleDisplay.locator('button[data-pf="bull"]:disabled').count() === 1,
       "players: stale BULLISH filter is disabled without emptying the index");
    await staleDisplay.close();

    // The core CVS board is decision-bearing and fails closed, not merely
    // badged. The date remains unchanged; only the content digest disagrees.
    const badBoard = await browser.newPage();
    const staleCvs = JSON.parse(fs.readFileSync(path.resolve("out/cvs.json"), "utf8"));
    staleCvs.engine_content_sha256 = "0".repeat(64);
    await badBoard.route("**/cvs.json", r => r.fulfill({
      contentType: "application/json", body: JSON.stringify(staleCvs) }));
    await badBoard.goto(base + "/out/big_board.html");
    await badBoard.waitForTimeout(900);
    const mismatchBanner = await badBoard.textContent("#banner");
    ok(/artifacts out of sync/i.test(mismatchBanner) &&
       /board blocked/i.test(mismatchBanner) &&
       !/unreachable/i.test(mismatchBanner) &&
       await badBoard.locator("#board .brow").count() === 0,
       "big board: same-date CVS mismatch names lineage, not the network",
       mismatchBanner.trim());
    await badBoard.close();

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
    await pe.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify([
        { metadata: { first_name: "Jahmyr", last_name: "Gibbs", position: "RB" } },
        { metadata: { first_name: "Bijan", last_name: "Robinson", position: "RB" } },
        { metadata: { first_name: "Ja'Marr", last_name: "Chase", position: "WR" } },
      ]) }));
    await pe.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", settings: { teams: 12, rounds: 14, pick_timer: 90 }, last_picked: Date.now() - 12000, draft_order: order16,
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
      draftBadges: document.querySelectorAll("#scr-draft .sig").length,
      draftContainers: document.querySelectorAll("#scr-draft [data-sig]").length,
      legends: document.querySelectorAll(".siglegend").length,
    }));
    ok(sigOn.badges >= 3, "room signal badges render (icon + label)",
       String(sigOn.badges));
    // scoped to the draft screen so the (hidden) Board tab's rows can never
    // satisfy the assertion on their own
    ok(sigOn.draftBadges >= 3,
       "draft-screen surfaces carry signal badges (not just the Board tab)",
       String(sigOn.draftBadges));
    ok(sigOn.draftContainers >= 2,
       "draft-screen surfaces carry signal containers (not just the Board tab)",
       String(sigOn.draftContainers));
    ok(sigOn.legends >= 1, "room signal legend renders", String(sigOn.legends));
    // the Sleeper link: present, and pointing at the draft the room polls
    const link = await pe.evaluate(() => {
      const a = document.getElementById("sleeper-link");
      return a ? { href: a.href, text: a.textContent.trim(), target: a.target } : null;
    });
    const wantDraft = JSON.parse(require("fs").readFileSync(
      path.resolve("out/engine_2026.json"), "utf8")).league.draft_id;
    ok(link && link.href === "https://sleeper.com/draft/nfl/" + wantDraft,
       "header links to the live Sleeper draft the room polls",
       link ? link.href : "no link");
    ok(link && link.target === "_blank", "the draft link opens in its own tab");
    // the on-the-clock line leads with the Sleeper team name
    const upSoon = await pe.textContent("#lv-upnext");
    ok(/UP IN \d+ PICKS?/.test(upSoon) || /YOU ARE ON THE CLOCK/.test(upSoon),
       "up-next states the distance to your turn", upSoon.trim());
    ok(/before you:/.test(upSoon) || /YOU ARE ON THE CLOCK/.test(upSoon),
       "up-next names who picks before you", upSoon.trim());
    const franch = await pe.textContent("#lv-franch");
    const rosterLabels = currentRosterLabels();
    ok(rosterLabels.some(label => franch.includes(label)),
       "the clock line carries a payload-derived team label", franch.trim());
    // the Board tab (best-available view) carries all three channels too
    const vb = await pe.evaluate(() => ({
      containers: document.querySelectorAll("#scr-board .vrow[data-sig]").length,
      badges: document.querySelectorAll("#scr-board .sig").length,
      legends: document.querySelectorAll("#scr-board .siglegend").length,
    }));
    ok(vb.containers >= 3, "value board rows carry the signal container", String(vb.containers));
    ok(vb.badges >= 3, "value board rows carry signal badges", String(vb.badges));
    ok(vb.legends >= 1, "value board carries the signal legend", String(vb.legends));
    // grey-out mode: gone rows stay listed but never carry a signal
    await pe.evaluate(() => document.getElementById("vb-keep").click());
    const goneSig = await pe.evaluate(() => ({
      gone: document.querySelectorAll("#scr-board .vrow.gone").length,
      badged: document.querySelectorAll("#scr-board .vrow.gone .sig").length
        + document.querySelectorAll("#scr-board .vrow.gone[data-sig]").length,
    }));
    ok(goneSig.gone >= 1, "grey-out mode lists gone rows", String(goneSig.gone));
    ok(goneSig.badged === 0, "gone rows are signal-free (both channels)",
       String(goneSig.badged));
    await pe.evaluate(() => document.getElementById("vb-rm").click());
    // the shared kill-switch: with the layer off, the card says so and
    // scores from the pure-model variant with no walter percentages
    await pe.evaluate(() => localStorage.setItem("ytfl_walter_live", "off"));
    await pe.reload();
    await pe.waitForTimeout(3500);
    const sigOff = await pe.evaluate(() => document.querySelectorAll(".sig").length);
    // off mode must still RENDER the no_walter signals - a dead off-channel
    // (0 badges) would otherwise pass a bare inequality check
    ok(sigOff > 0 && sigOff !== sigOn.badges,
       "walter toggle changes the room's rendered signals (server variants)",
       `${sigOn.badges} -> ${sigOff}`);
    const offtxt = await pe.textContent("#pe-body");
    ok(/WALTER LAYER OFF/.test(offtxt), "pick engine honors the live kill-switch");
    ok(!/walter [+-]/.test(offtxt), "off-mode card carries no walter percentages");
    ok(!/NaN/.test(offtxt), "off-mode card renders no NaN");
    await pe.evaluate(() => localStorage.removeItem("ytfl_walter_live"));
    const staleBullRoom = JSON.parse(fs.readFileSync(
      path.resolve("out/data/bullish_2026.json"), "utf8"));
    staleBullRoom.provenance.engine_content_sha256 = "0".repeat(64);
    staleBullRoom.tags = [];
    await pe.route("**/data/bullish_2026.json", r => r.fulfill({
      contentType: "application/json", body: JSON.stringify(staleBullRoom) }));
    await pe.reload();
    await pe.waitForTimeout(3500);
    ok(/TAGS STALE \d+h/.test(await pe.textContent("#lv-chips")),
       "draft room: stale BULLISH state remains visible for an untagged recommendation");
    const staleCvsRoom = JSON.parse(require("fs").readFileSync(
      path.resolve("out/cvs.json"), "utf8"));
    staleCvsRoom.engine_content_sha256 = "0".repeat(64);
    await pe.route("**/cvs.json", r => r.fulfill({
      contentType: "application/json", body: JSON.stringify(staleCvsRoom) }));
    await pe.reload();
    await pe.waitForTimeout(3500);
    const stalePe = await pe.textContent("#pe-body");
    ok(/different engine payload/.test(stalePe) &&
       await pe.locator("#pe-body .rname").count() === 0,
       "draft room: same-date CVS mismatch suppresses the pick recommendation");
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
    await oc.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify(ocPicks) }));
    await oc.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", settings: { teams: 12, rounds: 14, pick_timer: 90 }, last_picked: Date.now() - 12000, draft_order: order16,
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
    // UPNEXT: seat 7 is up at pick 7, so the strip must say so outright
    const upNow = await oc.textContent("#lv-upnext");
    ok(/YOU ARE ON THE CLOCK/.test(upNow),
       "up-next says you are on the clock when it is your pick", upNow.trim());
    ok(await oc.locator("#lv-upnext.now").count() === 1,
       "the on-the-clock strip takes its clock-state treatment");
    ok(errsOc.length === 0, "on-the-clock: zero console errors", errsOc[0] || "");
    // RUNDETECT negative case: 3 RB + 3 WR in round 1 IS the archive's normal
    // diet (~45%/41% base) - the derived detector must stay silent where the
    // old 4-of-8 constant would soon have fired on noise
    ok((await oc.textContent("#f-run")).trim() === "",
       "no run banner when the mix matches the archive's base rates");
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

    // POSITION RUN positive case: three QBs inside eight round-1 picks is a
    // genuine anomaly for a league that drafts QBs at ~7.7% in rounds 1-3
    // (binomial p ~= 0.02); the banner must fire, name QB, and show the
    // archive's expected count
    const pr2 = await browser.newPage();
    const runPicks = ["Josh Allen QB", "Lamar Jackson QB", "Jayden Daniels QB",
      "Jahmyr Gibbs RB", "Bijan Robinson RB", "Ja'Marr Chase WR", "Puka Nacua WR",
      "Saquon Barkley RB"].map(s => {
        const parts = s.split(" ");
        return { metadata: { first_name: parts[0], last_name: parts.slice(1, -1).join(" "),
                             position: parts[parts.length - 1] } };
      });
    const idSlots2 = {}; for (let i = 1; i <= 12; i++) idSlots2[i] = i;
    await pr2.route("**/v1/players/nfl/trending/**", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: "[]" }));
    await pr2.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json", headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify(runPicks) }));
    await pr2.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting", settings: { teams: 12, rounds: 14, pick_timer: 90 }, last_picked: Date.now() - 12000, draft_order: { "345197760305307648": 7 },
                               slot_to_roster_id: idSlots2 }) });
    });
    await pr2.goto(base + "/out/draft_room.html");
    await pr2.waitForTimeout(3000);
    const runTxt = await pr2.textContent("#f-run");
    ok(/POSITION RUN/.test(runTxt) && /QB/.test(runTxt),
       "run banner fires on a stage-anomalous QB burst", runTxt.trim().slice(0, 80));
    ok(/archive expects/.test(runTxt),
       "run banner cites the archive's expected count", runTxt.trim().slice(0, 80));
    await pr2.close();
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

  // ---- scenario 18: DRAFT MODE - mock loaded, creator unseated, format
  // mismatch labeled (three-state seat law: creator is NOT seat)
  {
    const page = await browser.newPage();
    const MOCK = "1398365807171371008", REAL = "1389378429505241089";
    const ident = n => { const m = {}; for (let i = 1; i <= n; i++) m[i] = i; return m; };
    const mockDraft = { league_id: null, status: "pre_draft",
      creators: ["345197760305307648"], draft_order: null,
      slot_to_roster_id: ident(10),
      settings: { teams: 10, rounds: 15, slots_flex: 2, pick_timer: 120, cpu_autopick: 1 },
      metadata: { scoring_type: "std" } };
    const realDraft = { status: "pre_draft", draft_order: null,
      slot_to_roster_id: ident(12),
      settings: { teams: 12, rounds: 14, slots_flex: 1, pick_timer: 60 },
      metadata: { scoring_type: "ppr" } };
    await page.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" }, body: "[]" }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify(r.request().url().includes(REAL) ? realDraft : mockDraft) });
    });
    await page.goto(FILE + "?draft=" + MOCK);
    await page.waitForTimeout(4000);
    const bar = await page.textContent("#mockbar");
    ok(/DRAFT MODE/.test(bar), "mock: the mockbar announces draft mode");
    ok(/Your mock, no seat claimed yet/.test(bar),
       "mock: creator-but-unseated state named explicitly, no seat guessed");
    ok(/SCORING MISMATCH/.test(bar) && /std/.test(bar),
       "mock: std-vs-ppr flagged loudest");
    ok(/teams.*10.*vs league 12/.test(bar) && /rounds.*15.*vs league 14/.test(bar),
       "mock: each differing format field named");
    ok(/may not transfer/.test(bar),
       "mock: board values labeled as real-league priced, never recomputed");
    ok(/DRAFT MODE/.test(await page.textContent("#mode")),
       "mock: mode pill carries draft mode");
    ok(!/you are seat/.test(await page.textContent("#mode")),
       "mock: no seat auto-selected while unseated");
    await page.close();
  }

  // ---- scenario 19: DRAFT MODE live - seated via draft_order, mock
  // geometry drives the snake, league-keyed features off
  {
    const page = await browser.newPage();
    const MOCK = "1398365807171371008", REAL = "1389378429505241089";
    const ident = n => { const m = {}; for (let i = 1; i <= n; i++) m[i] = i; return m; };
    const mockDraft = { league_id: null, status: "drafting",
      last_picked: Date.now() - 10000,
      creators: ["345197760305307648"],
      draft_order: { "345197760305307648": 3 },
      slot_to_roster_id: ident(10),
      settings: { teams: 10, rounds: 15, slots_flex: 2, pick_timer: 120 },
      metadata: { scoring_type: "ppr" } };
    const realDraft = { status: "pre_draft", draft_order: null,
      slot_to_roster_id: ident(12),
      settings: { teams: 12, rounds: 14, slots_flex: 1, pick_timer: 60 },
      metadata: { scoring_type: "ppr" } };
    await page.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify([
        { metadata: { first_name: "Jahmyr", last_name: "Gibbs", position: "RB" } },
      ]) }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify(r.request().url().includes(REAL) ? realDraft : mockDraft) });
    });
    await page.goto(FILE + "?draft=" + MOCK);
    await page.waitForTimeout(4000);
    const mode = await page.textContent("#mode");
    ok(/DRAFT MODE - MOCK LIVE/.test(mode), "mock live: mode pill goes live");
    ok(/seat 3/.test(mode), "mock live: seat 3 auto-selected from draft_order");
    ok(/Seat.*3.*detected from draft_order/.test(await page.textContent("#mockbar")),
       "mock live: the auto-selection is shown for confirmation");
    ok(await page.locator("#lv-seatpick button").count() === 10,
       "mock live: seat picker follows the mock's 10 teams, not the league's 12");
    ok(/off in draft mode/.test(await page.textContent("#f-opps")),
       "mock live: league-mate dossiers off with the reason stated");
    const mockFranchise = await page.textContent("#lv-franch");
    const leakedRosterLabels = currentRosterLabels().filter(
      label => mockFranchise.includes(label));
    ok(leakedRosterLabels.length === 0,
       "mock live: no real-league roster labels attached to mock seats",
       leakedRosterLabels.join(", "));
    await page.close();
  }

  // ---- scenario 20: forward-pick law at the snake turn - no player may
  // appear twice in any slot's projected sequence (the live bug: the same
  // WR at back-to-back picks 24 and 25 from slot 1)
  {
    const page = await browser.newPage();
    await page.route("**/api.sleeper.app/**", r => r.abort());
    await page.goto(FILE);
    await page.waitForTimeout(2500);
    for (const slot of [1, 12]){   // both wrap seats take back-to-back picks
      await page.click(`.chips button[data-slot="${slot}"]`);
      await page.waitForTimeout(300);
      const names = (await page.$$eval(".rc-name", els =>
        els.map(e => e.textContent.trim())))
        .filter(n => !/best available/.test(n))
        .map(n => n.replace(/projection = floor.*$/, "").trim());
      const dupes = names.filter((n, i) => names.indexOf(n) !== i);
      ok(names.length >= 10 && dupes.length === 0,
         `slot ${slot}: no player repeats across its projected picks`,
         dupes.join(", "));
    }
    // the wrap itself: slot 1 rounds 2 and 3 are consecutive overall picks
    await page.click('.chips button[data-slot="1"]');
    await page.waitForTimeout(300);
    const picks = await page.$$eval(".rowcard", cards => cards.slice(0, 4).map(c => ({
      pick: (c.querySelector(".rc-pick") || {}).textContent || "",
      name: (c.querySelector(".rc-name") || {}).textContent || "" })));
    const r2 = picks.find(p => /pick 24\b/.test(p.pick));
    const r3 = picks.find(p => /pick 25\b/.test(p.pick));
    ok(!!r2 && !!r3 && r2.name.trim() !== r3.name.trim(),
       "back-to-back turn picks 24 and 25 project two different players",
       r2 && r3 ? r2.name + " / " + r3.name : "cards missing");
    await page.close();
  }

  // ---- scenario 21: the PATHS tab (VONA tree)
  {
    const http = require("http");
    const fs = require("fs");
    const srv = http.createServer((req, res) => {
      const url = req.url.split("?")[0];
      // the browser probes /favicon.ico on its own; answering it keeps the
      // zero-console-error assertion about the PAGE, not about Chromium
      if (url === "/favicon.ico"){ res.writeHead(204); res.end(); return; }
      const p = path.join(process.cwd(), decodeURIComponent(url));
      fs.readFile(p, (e, b) => {
        if (e){ res.writeHead(404); res.end("nf"); return; }
        res.writeHead(200, { "content-type": p.endsWith(".json")
          ? "application/json" : p.endsWith(".js")
          ? "text/javascript" : "text/html" });
        res.end(b);
      });
    }).listen(0);
    await new Promise(r => srv.on("listening", r));
    const base = "http://127.0.0.1:" + srv.address().port;
    const pg = await browser.newPage();
    const perr = [];
    pg.on("console", m => { if (m.type() === "error") perr.push(m.text()); });
    await pg.goto(base + "/out/paths.html");
    await pg.waitForTimeout(900);
    const body = await pg.textContent("#content");
    ok(/Slot 1 - picks/.test(body), "paths: renders a slot tree");
    ok(await pg.locator(".tnode").count() > 3, "paths: the tree has nodes");
    ok(!/BULLISH|WATCH/.test(body),
       "paths: no BULLISH marker anywhere on the decision surface");
    ok(/real decision points/.test(body) && /pruned as dominated/.test(body),
       "paths: fork and prune accounting is on screen, never silent");
    ok(/undrawn/.test(await pg.textContent("#hdr")),
       "paths: slot-conditional, states the order is undrawn");
    // switching slots re-renders a different tree
    const t1 = await pg.textContent("#content");
    await pg.click('#slots button[data-slot="8"]');
    await pg.waitForTimeout(300);
    const t8 = await pg.textContent("#content");
    ok(/Slot 8 - picks/.test(t8) && t1 !== t8,
       "paths: the slot picker re-renders the tree");
    ok(/Correlation caveat/.test(t8) && /UNDERSTATES VONA/.test(t8),
       "paths: the independence caveat and its direction are shown");
    ok(/Stated deviation/.test(t8),
       "paths: the spec deviations are disclosed on the page");
    const terminalLookahead = await pg.$$eval(".tpick", els => {
      const r7 = els.map(e => e.textContent.trim()).filter(t => /^R7\b/.test(t));
      return r7.length > 0 && r7.every(t => /^R7 - pick \d+ to \d+$/.test(t));
    });
    ok(terminalLookahead,
       "paths: every rendered round-7 node names its real round-8 lookahead");
    // every rendered node clears the survival floor the page states
    const floorOk = await pg.evaluate(() => {
      const nums = [...document.querySelectorAll(".tnums")]
        .map(e => e.textContent.match(/there (\d+)%/))
        .filter(Boolean).map(m => Number(m[1]));
      return nums.length > 0 && nums.every(n => n >= 40);
    });
    ok(floorOk, "paths: every rendered node is at least 40% likely to be there");
    const stalePaths = await browser.newPage();
    const staleTree = JSON.parse(fs.readFileSync(
      path.resolve("out/data/vona_tree_2026.json"), "utf8"));
    staleTree.provenance.engine_content_sha256 = "0".repeat(64);
    await stalePaths.route("**/data/vona_tree_2026.json", r => r.fulfill({
      contentType: "application/json", body: JSON.stringify(staleTree) }));
    await stalePaths.goto(base + "/out/paths.html");
    await stalePaths.waitForTimeout(700);
    ok(/different engine payload/.test(await stalePaths.textContent("#content")) &&
       await stalePaths.locator(".tnode").count() === 0,
       "paths: same-date content mismatch refuses to render the tree");
    await stalePaths.close();
    ok(perr.length === 0, "paths: zero console errors", perr[0] || "");
    await pg.close();
    srv.close();
  }

  // ---- scenario 22: THE PICK CLOCK IS SERVER-ANCHORED OR ABSENT (P0).
  // The old clock hardcoded 120s and anchored to poll detection - it could
  // show time remaining after the real 60s window had expired and the pick
  // had been autopicked, silently. These asserts make that impossible.
  {
    // 22a: a 60-second draft, last pick 20s ago -> the clock must read the
    // REAL remainder (~40s), never 2:00, never anything over 1:00
    const page = await browser.newPage();
    await page.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" },
      body: JSON.stringify([
        { metadata: { first_name: "Jahmyr", last_name: "Gibbs", position: "RB" } },
      ]) }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting",
          settings: { teams: 12, rounds: 14, pick_timer: 60 },
          last_picked: Date.now() - 20000,
          draft_order: { "345197760305307648": 7 },
          slot_to_roster_id: null }) });
    });
    await page.goto(FILE);
    await page.waitForTimeout(3000);
    const c = (await page.textContent("#clock")).trim();
    const m = c.match(/^(\d+):(\d\d)$/);
    const secs = m ? Number(m[1]) * 60 + Number(m[2]) : -1;
    ok(m && secs <= 45 && secs >= 25,
       "60s draft: the clock reads the real server-anchored remainder", c);
    ok(secs <= 60, "60s draft: the room NEVER renders more than the real timer", c);
    ok(/clock 60s per pick \(draft settings\)/.test(await page.textContent("#lv-rule")),
       "the rule line states the duration came from draft settings");
    await page.close();
  }
  {
    // 22b: last_picked missing -> no plausible wrong number, an honest absence
    const page = await browser.newPage();
    await page.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" }, body: "[]" }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting",
          settings: { teams: 12, rounds: 14, pick_timer: 60 },
          last_picked: null,
          draft_order: { "345197760305307648": 7 },
          slot_to_roster_id: null }) });
    });
    await page.goto(FILE);
    await page.waitForTimeout(3000);
    ok((await page.textContent("#clock")).trim() === "-:--",
       "no last_picked: the clock shows no number at all");
    ok(/waiting for Sleeper|clock unavailable/.test(await page.textContent("#lv-rule")),
       "no last_picked: the rule line says why, and points at Sleeper");
    await page.close();
  }
  {
    // 22c: the clock expired by Sleeper's own timestamps -> says so, holds 0:00
    const page = await browser.newPage();
    await page.route("**/v1/draft/*/picks*", r => r.fulfill({
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" }, body: "[]" }));
    await page.route("**/v1/draft/*", r => {
      if (r.request().url().includes("/picks")) return r.fallback();
      r.fulfill({ contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify({ status: "drafting",
          settings: { teams: 12, rounds: 14, pick_timer: 60 },
          last_picked: Date.now() - 300000,
          draft_order: { "345197760305307648": 7 },
          slot_to_roster_id: null }) });
    });
    await page.goto(FILE);
    await page.waitForTimeout(3000);
    ok((await page.textContent("#clock")).trim() === "0:00",
       "expired by server timestamps: the clock holds 0:00, never a live number");
    ok(/expired.*check Sleeper/.test(await page.textContent("#lv-rule")),
       "expired: the rule line says to check Sleeper");
    await page.close();
  }

  // ---- scenario 23: EVERY LIVE TIME SIGNAL SCALES WITH THE DRAFT TIMER.
  // These are driven through Sleeper-shaped responses and the public DOM. The
  // room's closure state stays private; browser time is fixed only so class
  // boundaries cannot wobble while the assertions run.
  {
    const FIXED_NOW = 1800000000000;
    const ANTHONY = "345197760305307648";
    const draftPayload = (timer, lastPicked, extra = {}) => ({
      status: "drafting",
      settings: { teams: 12, rounds: 14, pick_timer: timer },
      last_picked: lastPicked,
      draft_order: { [ANTHONY]: 7 },
      slot_to_roster_id: null,
      ...extra,
    });
    const pick = (pickNo, playerId, firstName, lastName, position) => ({
      pick_no: pickNo,
      player_id: playerId,
      draft_slot: pickNo,
      roster_id: pickNo,
      round: 1,
      metadata: { first_name: firstName, last_name: lastName, position },
    });
    const parseClock = text => {
      const m = String(text).trim().match(/^(\d+):(\d\d)$/);
      return m ? Number(m[1]) * 60 + Number(m[2]) : -1;
    };
    const clockSnapshot = async (timer, remaining) => {
      const page = await browser.newPage();
      await page.addInitScript(now => { Date.now = () => now; }, FIXED_NOW);
      await page.route("**/v1/draft/*/picks*", r => r.fulfill({
        contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: "[]",
      }));
      await page.route("**/v1/draft/*", r => {
        if (r.request().url().includes("/picks")) return r.fallback();
        r.fulfill({
          contentType: "application/json",
          headers: { "access-control-allow-origin": "*" },
          body: JSON.stringify(draftPayload(
            timer, FIXED_NOW - (1 - remaining) * timer * 1000)),
        });
      });
      await page.goto(FILE);
      await page.waitForFunction(() =>
        document.querySelector("#clock")?.textContent.trim() !== "-:--");
      const state = await page.$eval("#clock", el => ({
        text: el.textContent.trim(),
        amber: el.classList.contains("amber"),
        red: el.classList.contains("red"),
        blink: el.classList.contains("blink"),
        classes: el.className,
      }));
      await page.close();
      return state;
    };
    const triggerVisibleRefresh = async page => {
      await page.bringToFront();
      await Promise.all([
        page.waitForResponse(r => /\/picks\?cb=/.test(r.url())),
        page.evaluate(() => document.dispatchEvent(new Event("visibilitychange"))),
      ]);
      await page.waitForTimeout(250);
    };

    // 23a: the amber phase must be reachable at 40% remaining for both the
    // league's 60-second clock and the 120-second mock used in prior tests.
    const amberResults = [];
    for (const timer of [60, 120]){
      const s = await clockSnapshot(timer, 0.40);
      amberResults.push({ timer, ...s });
    }
    ok(amberResults.every(s => s.amber && !s.red && !s.blink),
       "timer scaling: amber is reachable at 40% remaining for 60s and 120s",
       amberResults.map(s => `${s.timer}s=${s.text} [${s.classes}]`).join("; "));

    // 23b: a newer draft timestamp may not restart the clock unless the
    // picks board reaches the same snapshot. A failed picks fetch must hold
    // the coherent clock or surface the mismatch visibly.
    {
      const page = await browser.newPage();
      await page.addInitScript(now => { Date.now = () => now; }, FIXED_NOW);
      let draftCalls = 0, pickCalls = 0;
      const stablePicks = [pick(1, "p1", "Jahmyr", "Gibbs", "RB")];
      await page.route("**/v1/draft/*/picks*", r => {
        pickCalls++;
        if (pickCalls === 1) return r.fulfill({
          contentType: "application/json",
          headers: { "access-control-allow-origin": "*" },
          body: JSON.stringify(stablePicks),
        });
        return pickCalls === 2 ? r.fulfill({
            status: 500,
            contentType: "application/json",
            headers: { "access-control-allow-origin": "*" },
            body: JSON.stringify({ error: "fixture picks failure" }),
          }) : r.fulfill({
            contentType: "application/json",
            headers: { "access-control-allow-origin": "*" },
            body: JSON.stringify(stablePicks),
          });
      });
      await page.route("**/v1/draft/*", r => {
        if (r.request().url().includes("/picks")) return r.fallback();
        draftCalls++;
        r.fulfill({
          contentType: "application/json",
          headers: { "access-control-allow-origin": "*" },
          body: JSON.stringify(draftPayload(60,
            draftCalls === 1 ? FIXED_NOW - 20000 : FIXED_NOW)),
        });
      });
      await page.goto(FILE);
      await page.waitForFunction(() => /PICK 2/.test(
        document.querySelector("#lv-kick")?.textContent || ""));
      await page.waitForFunction(() =>
        document.querySelector("#clock")?.textContent.trim() !== "-:--");
      const beforePick = (await page.textContent("#lv-kick")).trim();
      const beforeClock = parseClock(await page.textContent("#clock"));
      await triggerVisibleRefresh(page);
      await page.waitForTimeout(1000);
      const failedPick = (await page.textContent("#lv-kick")).trim();
      const failedClock = parseClock(await page.textContent("#clock"));
      const failedVisible = [
        await page.textContent("#conn"),
        await page.textContent("#lv-fresh"),
        await page.locator("#banner").isVisible() ? await page.textContent("#banner") : "",
      ].join(" ");
      const failedWarned = /desync|out of sync|clock.*board|feed mismatch|picks (failed|unavailable)|last coherent state/i
        .test(failedVisible);
      // A 200 carrying the still-old picks array is also incoherent with the
      // newer draft anchor. This catches cache skew, not only loud failure.
      await triggerVisibleRefresh(page);
      await page.waitForTimeout(1000);
      const stalePick = (await page.textContent("#lv-kick")).trim();
      const staleClock = parseClock(await page.textContent("#clock"));
      const staleVisible = [
        await page.textContent("#conn"),
        await page.textContent("#lv-fresh"),
        await page.locator("#banner").isVisible() ? await page.textContent("#banner") : "",
      ].join(" ");
      const staleWarned = /desync|out of sync|clock.*board|feed mismatch|feeds disagree|mismatched.*snapshot/i
        .test(staleVisible);
      ok(failedPick === beforePick && failedClock <= beforeClock && failedWarned &&
         stalePick === beforePick && staleClock <= beforeClock && staleWarned,
         "paired feed: no fresh countdown over a stale picks board",
         `500: ${beforePick}/${beforeClock}s -> ${failedPick}/${failedClock}s warning=${failedWarned}; ` +
         `stale 200: ${stalePick}/${staleClock}s warning=${staleWarned}`);
      await page.close();
    }

    // 23c: N -> N-1 -> N-1 models commissioner undo followed by a confirming
    // poll. The third poll proves a smaller board cannot remain trapped behind
    // the old high-water mark forever.
    {
      const page = await browser.newPage();
      await page.addInitScript(now => { Date.now = () => now; }, FIXED_NOW);
      let draftCalls = 0, pickCalls = 0;
      const three = [
        pick(1, "p1", "Jahmyr", "Gibbs", "RB"),
        pick(2, "p2", "Bijan", "Robinson", "RB"),
        pick(3, "p3", "Ja'Marr", "Chase", "WR"),
      ];
      const two = three.slice(0, 2);
      await page.route("**/v1/draft/*/picks*", r => {
        pickCalls++;
        r.fulfill({
          contentType: "application/json",
          headers: { "access-control-allow-origin": "*" },
          body: JSON.stringify(pickCalls === 1 || pickCalls >= 4 ? three : two),
        });
      });
      await page.route("**/v1/draft/*", r => {
        if (r.request().url().includes("/picks")) return r.fallback();
        draftCalls++;
        r.fulfill({
          contentType: "application/json",
          headers: { "access-control-allow-origin": "*" },
          body: JSON.stringify(draftPayload(60,
            draftCalls === 1 ? FIXED_NOW - 5000 : FIXED_NOW)),
        });
      });
      await page.goto(FILE);
      await page.waitForFunction(() => /PICK 4/.test(
        document.querySelector("#lv-kick")?.textContent || ""));
      await triggerVisibleRefresh(page);
      await triggerVisibleRefresh(page);
      const recoveredKick = (await page.textContent("#lv-kick")).trim();
      // A fourth poll serves the exact pre-undo N snapshot with the confirmed
      // undo anchor. It must not silently resurrect the removed pick.
      await triggerVisibleRefresh(page);
      const replayKick = (await page.textContent("#lv-kick")).trim();
      const replayVisible = [
        await page.textContent("#conn"),
        await page.locator("#banner").isVisible() ? await page.textContent("#banner") : "",
      ].join(" ");
      ok(/PICK 3/.test(recoveredKick) && /PICK 3/.test(replayKick) &&
         /pre-undo|resurfaced|recovered.*board.*held/i.test(replayVisible),
         "commissioner undo: the confirming third poll recovers the N-1 board",
         `third=${recoveredKick}; replay=${replayKick}; ${(await page.textContent("#conn")).trim()}`);
      await page.close();
    }

    // 23d: 24 seconds is a different fraction of a 60s and a 120s window.
    // Advance Date.now only; the public one-second ticker updates the dot.
    const freshResults = [];
    for (const timer of [60, 120]){
      const page = await browser.newPage();
      await page.addInitScript(now => { Date.now = () => now; }, FIXED_NOW);
      await page.route("**/v1/draft/*/picks*", r => r.fulfill({
        contentType: "application/json",
        headers: { "access-control-allow-origin": "*" }, body: "[]",
      }));
      await page.route("**/v1/draft/*", r => {
        if (r.request().url().includes("/picks")) return r.fallback();
        r.fulfill({
          contentType: "application/json",
          headers: { "access-control-allow-origin": "*" },
          body: JSON.stringify(draftPayload(timer, FIXED_NOW - 5000)),
        });
      });
      await page.goto(FILE);
      await page.waitForFunction(() =>
        document.querySelector("#lv-dot")?.classList.contains("ok"));
      await page.evaluate(now => { Date.now = () => now + 24000; }, FIXED_NOW);
      await page.waitForTimeout(1100);
      freshResults.push(await page.$eval("#lv-dot", (dot, timer) => ({
        timer,
        ok: dot.classList.contains("ok"),
        warn: dot.classList.contains("warn"),
        bad: dot.classList.contains("bad"),
        label: document.querySelector("#lv-fresh")?.textContent.trim() || "",
      }), timer));
      await page.close();
    }
    const fresh60 = freshResults.find(x => x.timer === 60);
    const fresh120 = freshResults.find(x => x.timer === 120);
    ok(!fresh60.ok && fresh60.label !== "current" && !fresh120.bad,
       "freshness scaling: a 24s-old poll is not green on 60s, but is not stale on 120s",
       freshResults.map(x => `${x.timer}s=${x.label}`).join("; "));

    // 23e: contract test across timer lengths. The old 120s visual stages
    // scale proportionally: 40% amber, 15% red-only, 5% blinking red.
    const stageFailures = [];
    for (const timer of [30, 60, 90, 120]){
      const amber = await clockSnapshot(timer, 0.40);
      const red = await clockSnapshot(timer, 0.15);
      const blink = await clockSnapshot(timer, 0.05);
      if (!(amber.amber && !amber.red && !amber.blink))
        stageFailures.push(`${timer}s@40%=${amber.classes}`);
      if (!(red.red && !red.amber && !red.blink))
        stageFailures.push(`${timer}s@15%=${red.classes}`);
      if (!(blink.red && blink.blink && !blink.amber))
        stageFailures.push(`${timer}s@5%=${blink.classes}`);
    }
    ok(stageFailures.length === 0,
       "timer contract: 40% amber, 15% red, 5% blinking red at 30/60/90/120s",
       stageFailures.join("; "));

    // 23f: audio and paint must enter the SAME red stage. The AudioContext
    // stub records frequencies without exposing the room's closure state; the
    // scenario is driven through Sleeper responses and the public one-second
    // clock. The 880Hz on-clock beep is valid and intentionally ignored here.
    const urgentFailures = [];
    for (const timer of [30, 60, 90, 120]){
      const page = await browser.newPage();
      await page.addInitScript(now => {
        window.__clockNow = now;
        window.__beeps = [];
        Date.now = () => window.__clockNow;
        class FakeAudioContext {
          constructor(){ this.currentTime = 0; this.destination = {}; }
          createOscillator(){
            const osc = {
              frequency: { value: 0 }, connect(){}, stop(){},
              start(){ window.__beeps.push(osc.frequency.value); },
            };
            return osc;
          }
          createGain(){
            return { gain: { setValueAtTime(){}, exponentialRampToValueAtTime(){} },
                     connect(){} };
          }
        }
        window.AudioContext = FakeAudioContext;
        window.webkitAudioContext = FakeAudioContext;
      }, FIXED_NOW);
      const redBoundarySecond = Math.ceil(timer / 4);
      const sixPicks = [
        pick(1, "p1", "One", "Player", "RB"),
        pick(2, "p2", "Two", "Player", "WR"),
        pick(3, "p3", "Three", "Player", "RB"),
        pick(4, "p4", "Four", "Player", "WR"),
        pick(5, "p5", "Five", "Player", "QB"),
        pick(6, "p6", "Six", "Player", "TE"),
      ];
      await page.route("**/v1/draft/*/picks*", r => r.fulfill({
        contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify(sixPicks),
      }));
      await page.route("**/v1/draft/*", r => {
        if (r.request().url().includes("/picks")) return r.fallback();
        r.fulfill({
          contentType: "application/json",
          headers: { "access-control-allow-origin": "*" },
          body: JSON.stringify(draftPayload(
            timer, FIXED_NOW - (timer - redBoundarySecond) * 1000)),
        });
      });
      await page.goto(FILE);
      await page.waitForFunction(() =>
        document.querySelector("#clock")?.textContent.trim() !== "-:--");
      const atBoundary = await page.evaluate(() => ({
        amber: document.querySelector("#clock").classList.contains("amber"),
        red: document.querySelector("#clock").classList.contains("red"),
        urgent: window.__beeps.filter(freq => freq === 1200).length,
        text: document.querySelector("#clock").textContent.trim(),
      }));
      await page.evaluate(now => { window.__clockNow = now + 1000; }, FIXED_NOW);
      const firstRedText = Math.floor((redBoundarySecond - 1) / 60) + ":" +
        String((redBoundarySecond - 1) % 60).padStart(2, "0");
      await page.waitForFunction(expected =>
        document.querySelector("#clock")?.textContent.trim() === expected,
        firstRedText);
      const inRed = await page.evaluate(() => ({
        amber: document.querySelector("#clock").classList.contains("amber"),
        red: document.querySelector("#clock").classList.contains("red"),
        urgent: window.__beeps.filter(freq => freq === 1200).length,
        text: document.querySelector("#clock").textContent.trim(),
      }));
      await page.evaluate(now => { window.__clockNow = now + 2000; }, FIXED_NOW);
      const secondRedText = Math.floor((redBoundarySecond - 2) / 60) + ":" +
        String((redBoundarySecond - 2) % 60).padStart(2, "0");
      await page.waitForFunction(expected =>
        document.querySelector("#clock")?.textContent.trim() === expected,
        secondRedText);
      const afterTick = await page.evaluate(() => ({
        amber: document.querySelector("#clock").classList.contains("amber"),
        red: document.querySelector("#clock").classList.contains("red"),
        urgent: window.__beeps.filter(freq => freq === 1200).length,
        text: document.querySelector("#clock").textContent.trim(),
      }));
      if (!atBoundary.amber || atBoundary.red || atBoundary.urgent !== 0 ||
          inRed.amber || !inRed.red || inRed.urgent !== 1 ||
          afterTick.amber || !afterTick.red || afterTick.urgent !== 1)
        urgentFailures.push(
          `${timer}s boundary=${JSON.stringify(atBoundary)} ` +
          `red=${JSON.stringify(inRed)} repeat=${JSON.stringify(afterTick)}`);
      await page.close();
    }
    ok(urgentFailures.length === 0,
       "timer audio contract: urgent beep begins with red at 30/60/90/120s and fires once",
       urgentFailures.join("; "));
  }

  await browser.close();
  console.log(failures === 0 ? "\nALL PASS" : `\n${failures} FAILURES`);
  process.exit(failures === 0 ? 0 : 1);
})();
