"""Canonical owner-seat resolution for a Sleeper draft payload.

``draft_order`` (user id -> slot) is authoritative when present. A non-identity
``slot_to_roster_id`` map is the fallback. Sleeper publishes the identity map
before this league's order is drawn, so roster id must never be treated as a
draft slot merely because both happen to be 7 today.
"""


def _int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _team_count(value):
    """Return a usable league size only when the caller supplied it exactly."""
    return value if type(value) is int and value > 0 else None


def _valid_slot(value, teams):
    team_count = _team_count(teams)
    slot = _int(value)
    if slot is None or team_count is None or slot < 1:
        return None
    if slot > team_count:
        return None
    return slot


def _complete_slot_map(slot_map, teams):
    """Return integer pairs only for a complete roster/slot permutation."""
    team_count = _team_count(teams)
    if team_count is None:
        return None
    if not isinstance(slot_map, dict) or not slot_map:
        return None
    pairs = [(_int(k), _int(v)) for k, v in slot_map.items()]
    if any(k is None or v is None for k, v in pairs):
        return None
    expected = set(range(1, team_count + 1))
    if ({k for k, _v in pairs} != expected or
            {v for _k, v in pairs} != expected or
            len(pairs) != len(expected)):
        return None
    return pairs


def resolve_owner_slot(draft, user_id, roster_id, teams):
    """Return draw state, resolved slot, and the evidence used.

    A drawn-but-unresolvable payload is deliberately distinct from an undrawn
    identity placeholder. Callers producing decision artifacts should fail loud
    on the former; the latter can safely preserve all slot hypotheses.
    """
    draft = draft if isinstance(draft, dict) else {}
    team_count = _team_count(teams)
    if team_count is None:
        # Completeness and slot bounds are unknowable without the league size.
        # Treat this as unsafe evidence even when a map looks permutation-like:
        # a partial unique map is exactly the plausible-wrong-seat failure this
        # resolver exists to prevent.
        return {"drawn": True, "slot": None,
                "source": "team_count_unavailable"}
    order = draft.get("draft_order") or {}
    slot_map = draft.get("slot_to_roster_id") or {}
    status = draft.get("status")

    raw = order.get(str(user_id)) if isinstance(order, dict) else None
    slot = _valid_slot(raw, team_count)
    if slot is not None:
        return {"drawn": True, "slot": slot, "source": "draft_order"}

    pairs = _complete_slot_map(slot_map, team_count)
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
