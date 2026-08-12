#!/bin/bash
# Adds the sleeper and ff-hub MCP servers to claude_desktop_config.json.
#
# MUST be run while Claude Desktop is QUIT. The running app owns that file and
# rewrites it, discarding any mcpServers key added underneath it.
#
#   1. Quit Claude Desktop completely (Cmd-Q, not just close the window)
#   2. bash ~/ff-hub/install-mcp.sh
#   3. Launch Claude Desktop
set -euo pipefail

CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
PY="$HOME/ff-hub/sleeper-mcp-server/.venv/bin/python"

# pgrep -x "Claude" does not match on macOS; the bundle path is the reliable signal
if pgrep -f 'Claude\.app' >/dev/null 2>&1; then
  echo "Claude Desktop is RUNNING. Quit it first (Cmd-Q), then run this again."
  echo "Writing now would be discarded when the app next saves."
  exit 1
fi

[ -x "$PY" ] || { echo "venv python missing at $PY"; exit 1; }
[ -f "$CFG" ] || { echo "config missing at $CFG"; exit 1; }

cp "$CFG" "$CFG.bak.$(date +%Y%m%d-%H%M%S)"

python3 - "$CFG" "$PY" <<'PY'
import json, sys
cfg, py = sys.argv[1], sys.argv[2]
d = json.load(open(cfg))
d.setdefault("mcpServers", {})
d["mcpServers"]["sleeper"] = {
    "command": py,
    "args": ["-m", "sleeper_mcp_server"],
}
d["mcpServers"]["ff-hub"] = {
    "command": py,
    "args": [f"{__import__('os').path.expanduser('~')}/ff-hub/server.py"],
}
json.dump(d, open(cfg, "w"), indent=2)
print("mcpServers now:", list(d["mcpServers"]))
PY

echo "Done. Launch Claude Desktop; both servers appear under the connectors button."
