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
    ok(await page.locator(".tabs button").count() === 12, "12 slot tabs");
    ok(await page.locator(".wr").count() > 5, "wait-or-reach centrepiece rows");
    const body = await page.textContent("body");
    ok(/WAIT|TAKE NOW/.test(body), "verdicts rendered");
    ok(/to last to your next pick/.test(body), "explicit wait comparison text");
    ok(/COIN FLIP/.test(body), "coin flips surfaced");
    ok(/FLOOR/.test(body), "K/DEF floor label");
    ok(/n_eff/.test(body), "opponent priors table");
    ok(!/champion/i.test(body.replace(/no champion mimicry[^.]*/gi, "")), "no champion panel");
    // click another slot tab
    await page.click('.tabs button[data-slot="3"]');
    await page.waitForTimeout(300);
    ok(/Slot 3 - picks/.test(await page.textContent("body")), "slot tab switch");
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
    ok(await page.locator(".tabs button").count() === 12, "offline still renders scenarios");
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
    ok(/Pick 4/.test(body), "current pick derived from picks gone (3+1)");
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
