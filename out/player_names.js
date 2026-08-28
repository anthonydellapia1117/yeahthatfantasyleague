// Browser parity layer for src/player_names.py:comparison_key.
// Keep one JavaScript implementation; tests execute the shared behavioral
// corpus through both languages and require exact output equality.
(function(root){
  "use strict";
  var SUFFIXES = new Set(["jr", "sr", "ii", "iii", "iv", "v"]);

  function playerComparisonKey(name){
    if (typeof name !== "string") throw new TypeError("player name must be a string");
    var parts = name.replace(/['\u2019\u02bc`\u00b4\u2018]/gu, "'").normalize("NFKD")
      .replace(/\p{M}/gu, "")
      .toLowerCase()
      .replace(/\p{Dash_Punctuation}/gu, " ")
      .replace(/\p{Punctuation}/gu, "")
      .trim().split(/\s+/).filter(Boolean);
    while (parts.length && SUFFIXES.has(parts[parts.length - 1])) parts.pop();
    return parts.join("");
  }

  root.playerComparisonKey = playerComparisonKey;
  if (typeof module !== "undefined" && module.exports)
    module.exports = { playerComparisonKey: playerComparisonKey };
})(typeof globalThis !== "undefined" ? globalThis : this);
