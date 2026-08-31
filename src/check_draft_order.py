#!/usr/bin/env python3
"""Post-merge item 3: has the draft order been drawn?

Mirrors the draft room's own detection semantics (out/draft_room.html
realSlotMap/detectSeat): slot_to_roster_id returns the identity map
{1:1,...,12:12} before the draw and a real permutation after; a genuine
draw landing on identity is 1 in 12!, so identity is treated as "not
drawn yet". ``draft_order`` and a non-identity ``slot_to_roster_id`` are
independent official evidence; either complete field can resolve Anthony and
both must agree when present.

Prints exactly one status line for the alert Routine to act on:
  DRAFT ORDER EXTERNAL - Anthony has slot <N>; Sleeper confirmation pending
  DRAFT ORDER DRAWN - Anthony has slot <N> (matches external report)
  DRAFT ORDER CONFLICT - external slot <N>, Sleeper slot <M>
  DRAFT ORDER DRAWN - Anthony's slot not resolvable (see payload)

The unresolved drawn state exits nonzero after printing its payload. It is an
alert condition, not a successful draw that the Routine may retire on.

It also runs the geometry preflight (src/preflight_draft.py) on every tick,
because this script already polls the draft every two hours and the preflight
needs no extra request budget to be worth having. The preflight is SILENT ON
SUCCESS so the Routine's one-line contract above is unchanged; a FAILURE
prints an extra PREFLIGHT FAIL line BEFORE the status line and sets a nonzero
exit, which is a real alert - it means the draft format or geometry moved out
from under the app.

The room itself already collapses to the detected seat live (the
order-hypothesis card retires, renderPre follows the real slot), so the
only job here is detection for the out-of-app alert.

Run: python3 src/check_draft_order.py
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preflight_draft import check as preflight_check
from draft_order import (DraftOrderResolutionError, load_reported_order,
                         reconcile_owner_slot)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def format_reconcile_error(exc):
    """Stable alert text for every fail-closed reconciliation state."""
    if isinstance(exc, DraftOrderResolutionError):
        if exc.source in ("official_sources_conflict",
                          "external_report_conflict"):
            return "DRAFT ORDER CONFLICT -" + str(exc).split(":", 1)[1]
        return ("DRAFT ORDER DRAWN - Anthony's slot not resolvable: "
                f"{exc.source} (see payload)")
    message = str(exc)
    if message.startswith("draft-order conflict:"):
        return "DRAFT ORDER CONFLICT -" + message.split(":", 1)[1]
    if "order is drawn" in message and "not resolvable" in message:
        return "DRAFT ORDER DRAWN - Anthony's slot not resolvable (see payload)"
    return "DRAFT ORDER ERROR - " + message


def main():
    # geometry preflight first, and loud only when it fails
    pre_ok, pre_msg = preflight_check()
    if not pre_ok:
        print(pre_msg)

    eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
    lg = eng["league"]
    report = load_reported_order(
        os.path.join(ROOT, "data", "draft_order_2026.json"),
        lg["draft_id"], lg["anthony_user_id"], lg["teams"], lg["rounds"])
    url = f"https://api.sleeper.app/v1/draft/{lg['draft_id']}"
    with urllib.request.urlopen(url, timeout=30) as r:
        draft = json.load(r)

    try:
        basis = reconcile_owner_slot(
            draft, report, lg["anthony_user_id"],
            lg["anthony_roster_id"], lg["teams"])
    except RuntimeError as exc:
        print(format_reconcile_error(exc))
        # Preserve malformed falsey values verbatim. Rewriting []/""/0/false
        # as {} would make a correct fail-closed result look inexplicable.
        print(json.dumps({"draft_order": draft.get("draft_order"),
                          "slot_to_roster_id":
                              draft.get("slot_to_roster_id")}))
        sys.exit(1)

    slot = basis["slot"]
    if basis["official_check"] == "pending":
        print(f"DRAFT ORDER EXTERNAL - Anthony has slot {slot}; Sleeper "
              f"confirmation pending (status {draft.get('status')})")
        if not pre_ok:
            sys.exit(1)
        return
    print(f"DRAFT ORDER DRAWN - Anthony has slot {slot} "
          "(matches external report)")
    if not pre_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
