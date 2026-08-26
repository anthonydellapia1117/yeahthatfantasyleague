#!/usr/bin/env python3
"""Post-merge item 3: has the draft order been drawn?

Mirrors the draft room's own detection semantics (out/draft_room.html
realSlotMap/detectSeat): slot_to_roster_id returns the identity map
{1:1,...,12:12} before the draw and a real permutation after; a genuine
draw landing on identity is 1 in 12!, so identity is treated as "not
drawn yet". draft_order (keyed by user id) is the primary signal when
present; slot_to_roster_id is the fallback via Anthony's stable
roster_id 7.

Prints exactly one status line for the alert Routine to act on:
  DRAFT ORDER UNDRAWN (status <status>)
  DRAFT ORDER DRAWN - Anthony has slot <N>
  DRAFT ORDER DRAWN - Anthony's slot not resolvable (see payload)

The room itself already collapses to the detected seat live (the
order-hypothesis card retires, renderPre follows the real slot), so the
only job here is detection for the out-of-app alert.

Run: python3 src/check_draft_order.py
"""
import json
import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    eng = json.load(open(os.path.join(ROOT, "out", "engine_2026.json")))
    lg = eng["league"]
    url = f"https://api.sleeper.app/v1/draft/{lg['draft_id']}"
    with urllib.request.urlopen(url, timeout=30) as r:
        draft = json.load(r)

    # draft_order going non-null is the primary signal (review note: the
    # cleaner test); the non-identity slot map stays as the cheap secondary
    # in case Sleeper publishes the draw without the per-user mapping
    order = draft.get("draft_order") or {}
    slot_map = draft.get("slot_to_roster_id") or {}
    identity = bool(slot_map) and all(
        int(v) == int(k) for k, v in slot_map.items())
    real_map = slot_map if slot_map and not identity else None
    drawn = bool(order) or real_map is not None

    if not drawn:
        print(f"DRAFT ORDER UNDRAWN (status {draft.get('status')})")
        return

    slot = order.get(str(lg["anthony_user_id"]))
    if slot is None and real_map:
        for s, rid in real_map.items():
            if int(rid) == int(lg["anthony_roster_id"]):
                slot = int(s)
                break
    if slot is not None:
        print(f"DRAFT ORDER DRAWN - Anthony has slot {slot}")
    else:
        print("DRAFT ORDER DRAWN - Anthony's slot not resolvable "
              "(see payload)")
        print(json.dumps({"draft_order": order,
                          "slot_to_roster_id": slot_map}))


if __name__ == "__main__":
    main()
