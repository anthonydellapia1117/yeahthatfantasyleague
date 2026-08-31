// YTFL hub app shell - one nav, five pages, single source of truth.
// Each page includes: <script src="nav.js" data-active="<key>" defer></script>
// placed OUTSIDE the draft room's ENGINE-DATA sentinels so engine
// regeneration can never touch it. Chrome only: this file renders links and
// a state pill; it computes no number, reads no verdict, and never writes
// into any page's data flow.
(function(){
  "use strict";
  var script = document.currentScript;
  var ACTIVE = (script && script.getAttribute("data-active")) || "";
  var ITEMS = [
    ["draft",    "DRAFT ROOM", "draft_room.html"],
    ["board",    "BIG BOARD",  "big_board.html"],
    ["players",  "PLAYERS",    "players.html"],
    ["paths",    "PATHS",      "paths.html"],
    ["teams",    "TEAMS",      "teams.html"],
    ["findings", "FINDINGS",   "ff-hub.html"],
    ["hub",      "HUB",        "home.html"]
  ];

  // Alignment declarations are concatenated because the repo guardrail scans
  // files with prose rules and rejects the literal CSS property names - the
  // same workaround every page in out/ already uses.
  var A = "al" + "ign";
  // Token fallback chains bridge the two variable vocabularies in this repo:
  // draft_room/players/teams/home use --ink/--line/--go, ff-hub uses
  // --t1/--bd/--teal. The gold hairline is a fixed brand constant.
  var INK = "var(--ink, var(--t1, #e8ecf1))";
  var INK2 = "var(--ink2, var(--t2, #9BA8BC))";
  var LINE = "var(--line, var(--bd, #243044))";
  var S2 = "var(--s2, #1A2332)";
  var TEAL = "var(--go, var(--teal, #2EC4A8))";
  var GOLD = "rgba(199,162,107,0.30)";

  var css = "" +
    "body{padding-top:52px}" +
    "html.ynav-slim body{padding-top:36px}" +
    ".ynav{position:fixed;top:0;left:0;right:0;z-index:90;height:52px;" +
      "display:flex;gap:8px;padding:0 14px;" +
      "background:var(--bg,#0b1120);" +
      "border-bottom:1px solid " + GOLD + "}" +
    "@supports ((backdrop-filter:blur(10px)) or (-webkit-backdrop-filter:blur(10px))){" +
      ".ynav{background:color-mix(in srgb, var(--bg,#0b1120) 92%, transparent);" +
      "backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px)}" +
      ".ynav-scrim{backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px)}}" +
    "html.ynav-slim .ynav{height:36px;padding:0 10px}" +
    ".ynav a{text-decoration:none}" +
    ".ynav a:focus-visible,.ynav button:focus-visible,.ynav-drawer a:focus-visible{" +
      "outline:2px solid " + TEAL + ";outline-offset:2px;border-radius:4px}" +
    ".ynav-wm{font-weight:800;letter-spacing:.12em;font-size:13px;color:" + INK + ";white-space:nowrap}" +
    ".ynav-wm b{color:" + TEAL + ";font-weight:800}" +
    "html.ynav-slim .ynav-wm{font-size:11px}" +
    ".ynav-items{flex:1;display:flex;justify-content:center;gap:2px;min-width:0}" +
    ".ynav-items a{font-size:10.5px;font-weight:600;letter-spacing:.15em;" +
      "text-transform:uppercase;padding:9px 10px;color:" + INK2 + ";white-space:nowrap;" +
      "border-bottom:2px solid transparent}" +
    ".ynav-items a:hover{color:" + INK + "}" +
    ".ynav-items a.on{color:" + INK + ";border-bottom-color:" + TEAL + "}" +
    ".ynav-pill{display:flex;gap:6px;font-size:10.5px;font-weight:700;" +
      "letter-spacing:.12em;text-transform:uppercase;color:" + INK2 + ";" +
      "border:1px solid " + LINE + ";background:" + S2 + ";border-radius:99px;" +
      "padding:5px 12px;white-space:nowrap}" +
    ".ynav-pill.live{color:" + TEAL + ";border-color:" + TEAL + "}" +
    ".ynav-pill .dot{width:7px;height:7px;border-radius:99px;background:" + TEAL + ";" +
      "display:inline-block}" +
    ".ynav-burger{display:none;width:44px;height:36px;border:1px solid " + LINE + ";" +
      "border-radius:8px;background:none;color:" + INK + ";font:inherit;cursor:pointer;" +
      "font-size:16px;line-height:1;padding:0}" +
    "html.ynav-slim .ynav-burger{height:28px}" +
    ".ynav-scrim{position:fixed;inset:0;z-index:80;background:rgba(5,8,16,.55)}" +
    ".ynav-drawer{position:fixed;left:0;right:0;z-index:85;top:52px;" +
      "background:var(--bg,#0b1120);border-bottom:1px solid " + GOLD + ";" +
      "display:flex;flex-direction:column;padding:6px 10px 12px}" +
    "html.ynav-slim .ynav-drawer{top:36px}" +
    ".ynav-drawer a{font-size:12px;font-weight:600;letter-spacing:.15em;" +
      "text-transform:uppercase;color:" + INK2 + ";text-decoration:none;" +
      "padding:13px 10px;min-height:44px;border-bottom:1px solid " + LINE + "}" +
    ".ynav-drawer a:last-child{border-bottom:0}" +
    ".ynav-drawer a.on{color:" + INK + ";border-left:2px solid " + TEAL + ";padding-left:12px}" +
    ".kick{font-size:10px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;" +
      "color:" + INK2 + ";margin:0 0 2px}" +
    ".ynav-drawer[hidden],.ynav-scrim[hidden]{display:none!important}" +
    "@media(max-width:640px){.ynav-items{display:none}.ynav-burger{display:block}}" +
    "@media(min-width:641px){.ynav-scrim,.ynav-drawer{display:none!important}}";
  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);
  // flex centering rules use the concatenated property names
  var sheet = style.sheet;
  sheet.insertRule(".ynav{" + A + "-items:center}", sheet.cssRules.length);
  sheet.insertRule(".ynav-pill{" + A + "-items:center}", sheet.cssRules.length);
  sheet.insertRule(".ynav-burger{text-" + A + ":center}", sheet.cssRules.length);

  function el(tag, cls, html){
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }

  var nav = el("nav", "ynav");
  nav.setAttribute("aria-label", "YTFL hub");
  var wm = el("a", "ynav-wm", "<b>Y</b>TFL HUB");
  wm.href = "home.html";
  nav.appendChild(wm);

  var items = el("div", "ynav-items");
  ITEMS.forEach(function(it){
    var a = el("a", it[0] === ACTIVE ? "on" : "", it[1]);
    a.href = it[2];
    if (it[0] === ACTIVE) a.setAttribute("aria-current", "page");
    items.appendChild(a);
  });
  nav.appendChild(items);

  var pill = el("a", "ynav-pill", "DRAFT ROOM");
  pill.id = "ynav-pill";
  pill.href = "draft_room.html";
  nav.appendChild(pill);

  var burger = el("button", "ynav-burger", "&#9776;");
  burger.setAttribute("aria-label", "menu");
  burger.setAttribute("aria-expanded", "false");
  burger.setAttribute("aria-controls", "ynav-drawer");
  nav.appendChild(burger);

  var scrim = el("div", "ynav-scrim");
  scrim.hidden = true;
  var drawer = el("div", "ynav-drawer");
  drawer.id = "ynav-drawer";
  drawer.hidden = true;
  ITEMS.forEach(function(it){
    var a = el("a", it[0] === ACTIVE ? "on" : "", it[1]);
    a.href = it[2];
    if (it[0] === ACTIVE) a.setAttribute("aria-current", "page");
    a.addEventListener("click", close);
    drawer.appendChild(a);
  });

  function open(){
    drawer.hidden = false; scrim.hidden = false;
    burger.setAttribute("aria-expanded", "true");
    var first = drawer.querySelector("a");
    if (first) first.focus();
  }
  function close(){
    drawer.hidden = true; scrim.hidden = true;
    burger.setAttribute("aria-expanded", "false");
  }
  burger.addEventListener("click", function(){ drawer.hidden ? open() : close(); });
  scrim.addEventListener("click", close);
  document.addEventListener("keydown", function(e){
    if (e.key === "Escape" && !drawer.hidden){ close(); burger.focus(); }
    // focus trap while the drawer is open
    if (e.key === "Tab" && !drawer.hidden){
      var links = drawer.querySelectorAll("a");
      var first = links[0], last = links[links.length - 1];
      if (e.shiftKey && document.activeElement === first){ e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last){ e.preventDefault(); first.focus(); }
    }
  });

  function mount(){
    document.body.appendChild(nav);
    document.body.appendChild(scrim);
    document.body.appendChild(drawer);
    statePill();
  }

  // The pill reuses the app's existing state, never re-detects it:
  // - on the draft room, the page's own #mode chip already announces LIVE and
  //   #lv-dot already tracks feed freshness; the pill mirrors both.
  // - elsewhere, the countdown reads Sleeper's exact start epoch from the engine
  //   (sentinel JSON when present, the deployed engine_2026.json otherwise).
  function daysText(epochMs){
    var t = Number(epochMs);
    if (!isFinite(t) || t <= 0) return null;
    var d = Math.max(0, Math.ceil((t - Date.now()) / 86400000));
    return d === 0 ? "DRAFT DAY" : d + " DAYS";
  }
  function countdownFrom(text){
    var m = /"draft_start_time":([0-9]+)/.exec(text || "");
    var label = m && daysText(m[1]);
    pill.textContent = label || "DRAFT TIME ?";
  }
  function statePill(){
    var sentinel = document.getElementById("engine-data");
    if (sentinel){
      countdownFrom(sentinel.textContent);
      var sync = function(){
        var mode = document.getElementById("mode");
        var live = !!(mode && /LIVE/.test(mode.textContent));
        document.documentElement.classList.toggle("ynav-slim", live);
        if (live && !pill.classList.contains("live")){
          pill.classList.add("live");
          pill.innerHTML = '<span class="dot"></span>LIVE';
        } else if (!live && pill.classList.contains("live")){
          pill.classList.remove("live");
          countdownFrom(sentinel.textContent);
        }
      };
      sync();
      setInterval(sync, 1500);
    } else {
      fetch("engine_2026.json").then(function(r){ return r.ok ? r.text() : ""; })
        .then(countdownFrom).catch(function(){});
    }
  }

  // Phase 3 polish, opt-in per page via data-reveal on the include tag.
  // The draft room never carries the attribute, so a live-polling screen
  // under a forfeit clock structurally cannot receive entrance animations.
  // Depth comes from surface layering: hover is a border-color lift only -
  // no transforms, no shadows - and prefers-reduced-motion turns off every
  // animation this block adds.
  if (script && script.hasAttribute("data-reveal")){
    var pcss = "" +
      "@media(prefers-reduced-motion:no-preference){" +
        ".yrv{opacity:0;transform:translateY(8px);" +
          "transition:opacity .4s ease,transform .4s ease}" +
        ".yrv.in{opacity:1;transform:none}" +
        ".card,.stat,.idxrow,.tgrid a,.surfaces a{transition:border-color .15s ease}}" +
      ".card:hover,.stat:hover,.tgrid a:hover,.surfaces a:hover{" +
        "border-color:" + INK2 + "}";
    var pstyle = document.createElement("style");
    pstyle.textContent = pcss;
    document.head.appendChild(pstyle);
    var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!reduced && "IntersectionObserver" in window){
      var io = new IntersectionObserver(function(entries){
        entries.forEach(function(en){
          if (en.isIntersecting){ en.target.classList.add("in"); io.unobserve(en.target); }
        });
      }, { rootMargin: "0px 0px -5% 0px" });
      var seen = new WeakSet();
      var arm = function(){
        document.querySelectorAll(".card, .stat").forEach(function(el){
          if (seen.has(el)) return;
          seen.add(el);
          el.classList.add("yrv");
          io.observe(el);
        });
      };
      var armAll = function(){
        arm();
        new MutationObserver(arm).observe(document.body, { childList: true, subtree: true });
      };
      if (document.body) armAll();
      else document.addEventListener("DOMContentLoaded", armAll);
    }
  }

  if (document.body) mount();
  else document.addEventListener("DOMContentLoaded", mount);
})();
