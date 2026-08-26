#!/usr/bin/env python3
"""Assert the live draft still matches the geometry the app was built for.

WHY THIS EXISTS. The P0 defect was a pick clock hardcoded to 120 seconds
against a draft whose `settings.pick_timer` is 60: a server-knowable value
that was assumed by an author instead of read from the server, and that
failed silently because a wrong clock still counts down. The self-audit
predicted the same shape elsewhere and found it - nothing in this codebase
reads `draft.type` or `settings.reversal_round`, and `TEAMS`/`ROUNDS` are
module constants in src/engine_2026.py that are never cross-checked against
the server. All four are correct today only because the current settings
happen to match the assumption.

The blast radius if any of them changes is total and silent: enable
third-round reversal or switch the draft to linear, and every pick number
the engine and the room compute is wrong by a snake turn, while the board
still renders, the up-next strip still names teams, and nothing looks
broken. This script converts that into a loud stop.

It compares the LIVE draft against the shipped payload (out/engine_2026.json),
not against a second hardcoded copy - the payload is what the app actually
serves, so that is the thing that must agree with reality.

Prints one PREFLIGHT line per run:
  PREFLIGHT OK - snake, 12 teams, 14 rounds, 60s timer, no reversal
  PREFLIGHT FAIL - <field>: payload says X, Sleeper says Y[; ...]

Exit 0 on match, 1 on any mismatch or on an unusable response.
Run: python3 src/preflight_draft.py
"""
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check():
    """Returns (ok, message). Never raises - an unusable response is a FAIL."""
    eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
    lg = eng["league"]
    url = f"https://api.sleeper.app/v1/draft/{lg['draft_id']}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            if r.status != 200:
                return False, f"PREFLIGHT FAIL - Sleeper returned HTTP {r.status}"
            draft = json.load(r)
    except Exception as e:                                    # noqa: BLE001
        return False, f"PREFLIGHT FAIL - draft unreachable: {type(e).__name__}: {e}"
    if not isinstance(draft, dict) or not isinstance(draft.get("settings"), dict):
        return False, "PREFLIGHT FAIL - draft payload has no settings object"

    s = draft["settings"]
    bad = []

    # the draft FORMAT: the whole engine assumes a plain snake. Neither of
    # these fields is read anywhere else in the codebase - that is the point.
    if draft.get("type") != "snake":
        bad.append(f"type: engine assumes snake, Sleeper says {draft.get('type')!r}")
    rev = s.get("reversal_round")
    if rev not in (0, None):
        bad.append(f"reversal_round: engine assumes none, Sleeper says {rev!r} "
                   "(third-round reversal breaks every computed pick number)")

    # the draft GEOMETRY: the payload's league block drives the room's snake
    # math and the engine's per-slot cards.
    for field, payload_val in (("teams", lg.get("teams")),
                               ("rounds", lg.get("rounds"))):
        live = s.get(field)
        if live is not None and payload_val is not None and int(live) != int(payload_val):
            bad.append(f"{field}: payload says {payload_val}, Sleeper says {live}")

    # the CLOCK: not fatal (the room reads pick_timer live and hides the clock
    # when it cannot), but a change is worth seeing before draft morning.
    timer = s.get("pick_timer")

    if bad:
        return False, "PREFLIGHT FAIL - " + "; ".join(bad)
    return True, (f"PREFLIGHT OK - {draft.get('type')}, {s.get('teams')} teams, "
                  f"{s.get('rounds')} rounds, {timer}s timer, no reversal")


def main():
    ok, msg = check()
    print(msg)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
