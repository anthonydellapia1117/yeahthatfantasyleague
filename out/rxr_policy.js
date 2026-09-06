// RxR browser mirror of src/forward_policy.py. Python is canonical.
// This module computes one-step Marginal Policy scores only; it does not
// model availability, opponents, uncertainty, or a multi-round path.
(function(root){
  "use strict";

  var FLEX_OK = ["RB", "WR", "TE"];
  var BASE_SLOTS = { QB:1, RB:2, WR:2, TE:1, K:1, DEF:1 };
  var POLICY_POSITIONS = ["QB", "RB", "WR", "TE"];

  function playerId(player){
    var value = player && (player.player_id || player.sleeper_id);
    if (value === undefined || value === null || String(value).trim() === ""){
      throw new Error("policy player lacks canonical id");
    }
    return String(value);
  }

  function requireKeys(obj, keys, label){
    var missing = keys.filter(function(k){ return !Object.prototype.hasOwnProperty.call(obj || {}, k); });
    if (missing.length) throw new Error(label + " incomplete: " + missing.join(","));
  }

  function requireFiniteMap(obj, keys, label, nonnegative){
    requireKeys(obj, keys, label);
    var bad = keys.filter(function(k){
      var n = obj[k];
      return typeof n !== "number" || !Number.isFinite(n) || (nonnegative && n < 0);
    });
    if (bad.length) throw new Error(label + " invalid: " + bad.join(","));
  }

  // Python round(x, 4) rounds the exact IEEE-754 value with ties-to-even.
  // Math.round and toFixed do not implement that contract. Convert the double
  // to its exact binary rational, scale by 10,000, and round the integer ratio.
  function pythonRound4(value){
    value = Number(value);
    if (!Number.isFinite(value) || value === 0) return value;
    var negative = value < 0;
    var x = Math.abs(value);
    var bytes = new ArrayBuffer(8);
    var view = new DataView(bytes);
    view.setFloat64(0, x, false);
    var hi = view.getUint32(0, false);
    var lo = view.getUint32(4, false);
    var expBits = (hi >>> 20) & 0x7ff;
    var frac = (BigInt(hi & 0xfffff) << 32n) | BigInt(lo);
    var mantissa, exponent;
    if (expBits === 0){
      mantissa = frac;
      exponent = -1074;
    } else {
      mantissa = (1n << 52n) | frac;
      exponent = expBits - 1023 - 52;
    }
    var scaled = mantissa * 10000n;
    var rounded;
    if (exponent >= 0){
      rounded = scaled << BigInt(exponent);
    } else {
      var denominator = 1n << BigInt(-exponent);
      rounded = scaled / denominator;
      var remainder = scaled % denominator;
      var twice = remainder * 2n;
      if (twice > denominator || (twice === denominator && rounded % 2n === 1n)){
        rounded += 1n;
      }
    }
    var answer = Number(rounded) / 10000;
    return negative ? -answer : answer;
  }

  function phantomLineupPts(players, baselines){
    requireFiniteMap(baselines, Object.keys(BASE_SLOTS), "policy baselines", false);
    var byPos = {};
    Object.keys(BASE_SLOTS).forEach(function(pos){ byPos[pos] = []; });
    players.slice().sort(function(a,b){ return Number(b.pts) - Number(a.pts); })
      .forEach(function(p){
        if (!Object.prototype.hasOwnProperty.call(BASE_SLOTS, p.pos)){
          throw new Error("unknown policy position: " + p.pos);
        }
        if (!Number.isFinite(Number(p.pts))) throw new Error("policy player has non-finite pts: " + playerId(p));
        byPos[p.pos].push(p);
      });
    var total = 0;
    var used = new Set();
    function take(pos, n){
      var got = 0;
      byPos[pos].forEach(function(p){
        if (got === n) return;
        var id = playerId(p);
        if (!used.has(id)){
          used.add(id);
          total += Math.max(Number(p.pts), Number(baselines[pos]));
          got += 1;
        }
      });
      while (got < n){ total += Number(baselines[pos]); got += 1; }
    }
    take("QB", 1); take("RB", 2); take("WR", 2); take("TE", 1);
    var flex = [];
    FLEX_OK.forEach(function(pos){
      byPos[pos].forEach(function(p){ if (!used.has(playerId(p))) flex.push(p); });
    });
    var flexBest = Math.max.apply(null,
      flex.map(function(p){ return Number(p.pts); })
        .concat([Math.max.apply(null, FLEX_OK.map(function(pos){ return Number(baselines[pos]); }))]));
    total += flexBest;
    take("K", 1); take("DEF", 1);
    return total;
  }

  function rosterCaps(flexAllocation){
    var caps = {};
    Object.keys(BASE_SLOTS).forEach(function(pos){
      var flexes = FLEX_OK.indexOf(pos) >= 0 && Number((flexAllocation || {})[pos] || 0) > 0 ? 1 : 0;
      caps[pos] = BASE_SLOTS[pos] + flexes + (pos === "K" || pos === "DEF" ? 0 : 1);
    });
    return caps;
  }

  function scoreCandidates(pool, roster, baselines, caps){
    requireFiniteMap(baselines, Object.keys(BASE_SLOTS), "policy baselines", false);
    requireFiniteMap(caps, POLICY_POSITIONS, "policy caps", true);
    var rosterIds = roster.map(playerId);
    var poolIds = pool.map(playerId);
    if (new Set(rosterIds).size !== rosterIds.length) throw new Error("policy roster contains a duplicate player id");
    if (new Set(poolIds).size !== poolIds.length) throw new Error("policy pool contains a duplicate player id");
    var rosterSet = new Set(rosterIds);
    var overlap = poolIds.filter(function(id){ return rosterSet.has(id); });
    if (overlap.length) throw new Error("policy pool overlaps roster: " + overlap.join(","));

    var counts = {};
    Object.keys(BASE_SLOTS).forEach(function(pos){ counts[pos] = 0; });
    roster.forEach(function(p){
      if (!Object.prototype.hasOwnProperty.call(BASE_SLOTS, p.pos)) throw new Error("unknown policy position: " + p.pos);
      if (typeof p.pts !== "number" || !Number.isFinite(p.pts)) throw new Error("policy player has non-finite pts: " + playerId(p));
      counts[p.pos] += 1;
    });
    var base = phantomLineupPts(roster, baselines);
    var eligible = [];
    var records = pool.map(function(p, index){
      if (!Object.prototype.hasOwnProperty.call(BASE_SLOTS, p.pos)) throw new Error("unknown policy position: " + p.pos);
      if (typeof p.pts !== "number" || !Number.isFinite(p.pts)) throw new Error("policy player has non-finite pts: " + playerId(p));
      if (typeof p.vor !== "number" || !Number.isFinite(p.vor)) throw new Error("policy player has non-finite VOR: " + playerId(p));
      var rec = {
        player_id: playerId(p), name:p.name, pos:p.pos,
        marginal_lineup_gain_raw:null, marginal_lineup_gain_key:null,
        vor_tiebreak:Number(p.vor), input_index:index, eligible:false,
        cap_reason:null, policy_rank:null, raw_gap_from_leader:null,
        policy_key_gap:null
      };
      if (p.pos === "K" || p.pos === "DEF"){
        rec.cap_reason = "projection_floor";
      } else if (counts[p.pos] >= Number(caps[p.pos])){
        rec.cap_reason = p.pos.toLowerCase() + "_cap";
      } else {
        var raw = phantomLineupPts(roster.concat([p]), baselines) - base;
        rec.marginal_lineup_gain_raw = raw;
        rec.marginal_lineup_gain_key = pythonRound4(raw);
        rec.eligible = true;
        eligible.push(index);
      }
      return rec;
    });
    eligible.sort(function(a,b){
      var ka = records[a], kb = records[b];
      return (kb.marginal_lineup_gain_key - ka.marginal_lineup_gain_key) ||
        (kb.vor_tiebreak - ka.vor_tiebreak) || (ka.input_index - kb.input_index);
    });
    eligible.forEach(function(index, rank){ records[index].policy_rank = rank + 1; });
    if (eligible.length){
      var leader = records[eligible[0]];
      eligible.forEach(function(index){
        records[index].raw_gap_from_leader = leader.marginal_lineup_gain_raw - records[index].marginal_lineup_gain_raw;
        records[index].policy_key_gap = leader.marginal_lineup_gain_key - records[index].marginal_lineup_gain_key;
      });
    }
    return records;
  }

  root.RxRPolicy = {
    playerId:playerId,
    pythonRound4:pythonRound4,
    phantomLineupPts:phantomLineupPts,
    rosterCaps:rosterCaps,
    scoreCandidates:scoreCandidates
  };
})(typeof window !== "undefined" ? window : globalThis);
