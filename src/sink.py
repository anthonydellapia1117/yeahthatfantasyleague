#!/usr/bin/env python3
"""Local-only sink for the browser harvester.

The browser holds the authenticated Yahoo session but cannot write files, and
piping tens of thousands of rows back through tool output is not viable. This
listens on 127.0.0.1 and appends whatever the page POSTs to raw/yahoo/.

Binds to loopback only. No auth, no TLS, and none is needed: nothing outside
this machine can reach it. Stop it when the harvest finishes.

Run:  python3 src/sink.py            (default port 8899)
"""
import http.server, json, os, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "raw", "yahoo")
os.makedirs(OUT, exist_ok=True)
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8899

HDR = "season,wk,team_name,slot,bench,player,pts,proj\n"


class Handler(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(n))
            season = str(payload.get("season", "unknown"))
            rows = payload.get("rows", [])
            path = os.path.join(OUT, f"players_{season}.csv")
            new = not os.path.exists(path)
            with open(path, "a", newline="") as f:
                if new:
                    f.write(HDR)
                for r in rows:
                    f.write(",".join(
                        '"' + str(v).replace('"', '""') + '"'
                        if any(c in str(v) for c in ',"\n') else str(v if v is not None else "")
                        for v in r) + "\n")
            total = sum(1 for _ in open(path)) - 1
            print(f"  [{datetime.datetime.now():%H:%M:%S}] {season} +{len(rows)} rows "
                  f"-> {os.path.basename(path)} ({total} total)", flush=True)
            body = json.dumps({"ok": True, "written": len(rows), "total": total}).encode()
        except Exception as e:
            print(f"  ERROR {e}", flush=True)
            body = json.dumps({"ok": False, "error": str(e)}).encode()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass          # quiet; we print our own lines


if __name__ == "__main__":
    print(f"sink listening on http://127.0.0.1:{PORT}  ->  {OUT}", flush=True)
    http.server.HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
