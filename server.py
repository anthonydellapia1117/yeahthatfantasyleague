#!/usr/bin/env python3
"""ff-hub MCP: draft board, positional tiers, and wait/reach math for a Sleeper league.

Wraps draft_board.py so any Claude chat, cowork, or code session can call it.
Sleeper public API only. No credentials.
"""
import asyncio, json, os, sys
from collections import defaultdict

# Desktop launches MCP servers from an arbitrary cwd; make the sibling import work anyway
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mcp.server.stdio
from mcp.server import Server
from mcp.types import Tool, TextContent

import draft_board as db

app = Server("ff-hub")

LEAGUE_ARG = {"league_id": {"type": "string", "description": "Sleeper league id"}}


@app.list_tools()
async def list_tools():
    return [
        Tool(name="draft_board",
             description="Top players by value over replacement for a league, with ADP and the gap between ADP and value rank. Use to find who falls past their worth.",
             inputSchema={"type": "object", "required": ["league_id"],
                          "properties": {**LEAGUE_ARG,
                                         "top": {"type": "integer", "description": "how many players, default 30"}}}),
        Tool(name="position_tiers",
             description="Tier breaks for one position, computed from value-over-replacement gaps. Use to see where a position cliffs.",
             inputSchema={"type": "object", "required": ["league_id", "position"],
                          "properties": {**LEAGUE_ARG,
                                         "position": {"type": "string", "enum": db.POSITIONS}}}),
        Tool(name="wait_or_reach",
             description="For each position, the projected points lost by skipping a full draft turn from a given pick. Low cost means the curve is flat and you can wait; high cost means it cliffs and you take it now.",
             inputSchema={"type": "object", "required": ["league_id", "pick"],
                          "properties": {**LEAGUE_ARG,
                                         "pick": {"type": "integer", "description": "your next overall pick number"}}}),
    ]


def _by_pos(rows):
    d = defaultdict(list)
    for r in rows:
        d[r["pos"]].append(r)
    return d


@app.call_tool()
async def call_tool(name, arguments):
    lid = arguments["league_id"]
    lg, rows, baseline, repl = db.build(lid)
    bp = _by_pos(rows)

    if name == "draft_board":
        n = arguments.get("top", 30)
        out = {"league": lg["name"], "teams": lg["teams"], "scoring": lg["key"],
               "players": [{"rank": r["vor_rank"], "name": r["name"], "pos": r["pos"],
                            "team": r["team"], "proj": r["pts"], "vor": r["vor"],
                            "adp": r["adp"], "injury": r["injury"],
                            "adp_minus_value_rank": round(r["adp"] - r["vor_rank"], 1)}
                           for r in rows[:n]]}

    elif name == "position_tiers":
        pos = arguments["position"].upper()
        out = {"league": lg["name"], "position": pos,
               "replacement_rank": repl.get(pos), "replacement_points": baseline.get(pos),
               "tiers": [[{"name": p["name"], "team": p["team"], "proj": p["pts"],
                           "vor": p["vor"], "adp": p["adp"], "injury": p["injury"]} for p in t]
                         for t in db.tiers(bp[pos])[:8]]}

    elif name == "wait_or_reach":
        pick = arguments["pick"]
        rec = []
        for pos in db.POSITIONS:
            c = db.wait_cost(bp[pos], pick, lg["teams"])
            if c is None:
                continue
            nxt = [p for p in bp[pos] if p["adp"] >= pick]
            rec.append({"pos": pos, "best_available": nxt[0]["name"] if nxt else None,
                        "points_lost_if_you_wait": c,
                        "read": "wait" if c < 15 else ("reach" if c > 35 else "soft")})
        out = {"league": lg["name"], "from_pick": pick, "teams": lg["teams"], "positions": rec}

    else:
        out = {"error": f"unknown tool {name}"}

    return [TextContent(type="text", text=json.dumps(out, indent=1))]


async def main():
    async with mcp.server.stdio.stdio_server() as (r, w):
        await app.run(r, w, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
