"""Canonical owner-seat resolution for a Sleeper draft payload.

``draft_order`` (user id -> slot) is authoritative when present. A non-identity
``slot_to_roster_id`` map is the fallback. Sleeper publishes the identity map
before this league's order is drawn, so roster id must never be treated as a
draft slot merely because both happen to be 7 today.
"""


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _valid_slot(value, teams):
    slot = _int(value)
    if slot is None or slot < 1:
        return None
    if teams is not None and slot > int(teams):
        return None
    return slot


def _complete_slot_map(slot_map, teams):
    """Return integer pairs only for a complete roster/slot permutation."""
    if not isinstance(slot_map, dict) or not slot_map:
        return None
    pairs = [(_int(k), _int(v)) for k, v in slot_map.items()]
    if any(k is None or v is None for k, v in pairs):
        return None
    if teams is None:
        keys = [k for k, _v in pairs]
        values = [v for _k, v in pairs]
        return pairs if (len(set(keys)) == len(keys) and
                         len(set(values)) == len(values)) else None
    expected = set(range(1, int(teams) + 1))
    if ({k for k, _v in pairs} != expected or
            {v for _k, v in pairs} != expected or
            len(pairs) != len(expected)):
        return None
    return pairs


def resolve_owner_slot(draft, user_id, roster_id, teams=None):
    """Return draw state, resolved slot, and the evidence used.

    A drawn-but-unresolvable payload is deliberately distinct from an undrawn
    identity placeholder. Callers producing decision artifacts should fail loud
    on the former; the latter can safely preserve all slot hypotheses.
    """
    draft = draft if isinstance(draft, dict) else {}
    order = draft.get("draft_order") or {}
    slot_map = draft.get("slot_to_roster_id") or {}
    status = draft.get("status")

    raw = order.get(str(user_id)) if isinstance(order, dict) else None
    slot = _valid_slot(raw, teams)
    if slot is not None:
        return {"drawn": True, "slot": slot, "source": "draft_order"}

    pairs = _complete_slot_map(slot_map, teams)
    identity = bool(pairs) and all(k == v for k, v in pairs)
    if pairs:
        if not identity:
            wanted = _int(roster_id)
            for key, value in pairs:
                if value == wanted:
                    return {"drawn": True, "slot": key,
                            "source": "slot_to_roster_id"}

    # Only a pre-draft empty payload or the known complete identity placeholder
    # is safe to call undrawn. Once Sleeper says drafting/complete, or when a
    # purported slot map is partial/duplicated, guessing would create a
    # plausible wrong seat; callers must fail loudly instead.
    if status == "pre_draft" and not order and (not slot_map or identity):
        return {"drawn": False, "slot": None,
                "source": ("identity_placeholder" if identity
                           else "pre_draft_empty")}
    return {"drawn": True, "slot": None, "source": "drawn_unresolved"}
