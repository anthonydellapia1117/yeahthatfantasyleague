"""Canonical owner-seat resolution and reported-order reconciliation.

``draft_order`` (user id -> slot) and a non-identity
``slot_to_roster_id`` map are independent official evidence. Either complete
field may resolve the seat, but two complete fields must agree. Sleeper
publishes the identity map before this league's order is drawn, so roster id
must never be treated as a draft slot merely because both happen to be 7 today.

The league can also draw its order outside Sleeper. That fact lives in a
separate reported-order snapshot: it may choose the primary planning slot while
Sleeper is still on its identity placeholder, but it may never silently defeat a
later official conflict. Agreement promotes the source; disagreement is fatal.
"""
import json


class DraftOrderResolutionError(RuntimeError):
    """A fail-closed seat-resolution error with machine-readable cause."""

    def __init__(self, source, message, evidence=None):
        super().__init__(message)
        self.source = source
        self.evidence = dict(evidence or {})


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


def _complete_draft_order(order, teams):
    """Return user/slot pairs only for a complete slot permutation."""
    team_count = _team_count(teams)
    if team_count is None or not isinstance(order, dict) or not order:
        return None
    pairs = [(str(user_id), _int(slot)) for user_id, slot in order.items()]
    expected = set(range(1, team_count + 1))
    if (len(pairs) != team_count or
            any(not user_id or slot is None for user_id, slot in pairs) or
            {slot for _user_id, slot in pairs} != expected):
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
    raw_order = draft.get("draft_order")
    raw_slot_map = draft.get("slot_to_roster_id")
    order = raw_order if isinstance(raw_order, dict) else {}
    slot_map = raw_slot_map if isinstance(raw_slot_map, dict) else {}
    status = draft.get("status")

    # Null and an empty object are the only absent forms Sleeper publishes.
    # A list/string/number is malformed evidence, not permission to ignore one
    # official source and trust the other.
    order_present = raw_order is not None and raw_order != {}
    order_pairs = _complete_draft_order(order, team_count)
    if order_present and (not isinstance(raw_order, dict) or not order_pairs):
        return {"drawn": True, "slot": None,
                "source": "incomplete_draft_order"}
    by_user = next((slot for uid, slot in (order_pairs or [])
                    if uid == str(user_id)), None)

    slot_map_present = raw_slot_map is not None and raw_slot_map != {}
    pairs = _complete_slot_map(slot_map, team_count)
    if slot_map_present and (not isinstance(raw_slot_map, dict) or not pairs):
        return {"drawn": True, "slot": None,
                "source": "incomplete_slot_to_roster_id"}
    identity = bool(pairs) and all(k == v for k, v in pairs)
    wanted = _int(roster_id)
    by_roster = (next((key for key, value in (pairs or [])
                       if value == wanted), None) if not identity else None)

    # Both official payload fields are independent evidence once complete.
    # Precedence is safe only when the fallback is absent/identity; accepting
    # two contradictory complete maps would make a stale cache look coherent.
    if by_user is not None and by_roster is not None and by_user != by_roster:
        return {"drawn": True, "slot": None,
                "source": "official_sources_conflict",
                "draft_order_slot": by_user,
                "slot_map_slot": by_roster}
    if by_user is not None:
        return {"drawn": True, "slot": by_user,
                "source": ("draft_order+slot_to_roster_id"
                           if by_roster is not None else "draft_order")}
    if order_pairs:
        return {"drawn": True, "slot": None,
                "source": "draft_order_owner_missing"}
    if by_roster is not None:
        return {"drawn": True, "slot": by_roster,
                "source": "slot_to_roster_id"}
    if pairs and not identity:
        return {"drawn": True, "slot": None,
                "source": "slot_map_owner_missing"}

    # Only a pre-draft empty payload or the known complete identity placeholder
    # is safe to call undrawn. Once Sleeper says drafting/complete, or when a
    # purported slot map is partial/duplicated, guessing would create a
    # plausible wrong seat; callers must fail loudly instead.
    if (status == "pre_draft" and not order_present and
            (not slot_map_present or identity)):
        return {"drawn": False, "slot": None,
                "source": ("identity_placeholder" if identity
                           else "pre_draft_empty")}
    return {"drawn": True, "slot": None, "source": "drawn_unresolved"}


def snake_picks(slot, teams, rounds):
    """The reported-order geometry contract, independent of the engine."""
    return [(rnd - 1) * teams +
            (slot if rnd % 2 else teams + 1 - slot)
            for rnd in range(1, rounds + 1)]


def validate_reported_order(report, draft_id, user_id, teams, rounds):
    """Validate and return an externally reported draw snapshot.

    The snapshot is complete as a list of *reported labels*, not as a Sleeper
    roster-id permutation. History may honestly be unresolved for a seat; those
    rows must remain null rather than inheriting the pre-draw identity occupant.
    Only the owner slot is seat-resolution evidence.
    """
    if not isinstance(report, dict):
        raise ValueError("reported draft order must be an object")
    if report.get("schema_version") != 1:
        raise ValueError("unsupported reported draft-order schema")
    if str(report.get("draft_id")) != str(draft_id):
        raise ValueError("reported draft order names a different draft")
    if report.get("teams") != teams or report.get("rounds") != rounds:
        raise ValueError("reported draft-order geometry disagrees with engine")
    if report.get("draft_type") != "snake":
        raise ValueError("reported draft order is not snake")

    start = report.get("draft_start") or {}
    if (type(start.get("epoch_ms")) is not int or
            start["epoch_ms"] <= 0 or
            start.get("source_kind") != "sleeper_draft_endpoint" or
            not start.get("observed_at")):
        raise ValueError("reported draft order lacks a verified draft start")

    owner = report.get("owner") or {}
    if str(owner.get("user_id")) != str(user_id):
        raise ValueError("reported draft order names a different owner")
    owner_slot = _valid_slot(owner.get("slot"), teams)
    if owner_slot is None:
        raise ValueError("reported owner slot is missing or out of range")
    expected_picks = snake_picks(owner_slot, teams, rounds)
    if owner.get("picks") != expected_picks:
        raise ValueError("reported owner picks do not match snake geometry")

    rows = report.get("slots")
    if not isinstance(rows, list) or len(rows) != teams:
        raise ValueError("reported draft order must name every slot exactly once")
    found = []
    labels = []
    franchises = []
    owner_rows = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("reported slot row must be an object")
        slot = _valid_slot(row.get("slot"), teams)
        label = row.get("reported_label")
        status = row.get("history_status")
        franchise = row.get("history_franchise")
        if slot is None or not isinstance(label, str) or not label.strip():
            raise ValueError("reported slot row has invalid slot or label")
        if status in ("known", "owner"):
            if not isinstance(franchise, str) or not franchise.strip():
                raise ValueError("known reported seat lacks a history franchise")
        elif status in ("unresolved_merge", "unresolved_new_manager"):
            if franchise is not None:
                raise ValueError("unresolved reported seat must keep history null")
        else:
            raise ValueError("reported seat has unknown history status")
        found.append(slot)
        labels.append(label.strip().casefold())
        if franchise is not None:
            franchises.append(franchise.strip())
        if status == "owner":
            owner_rows.append(slot)
    if set(found) != set(range(1, teams + 1)) or len(set(found)) != teams:
        raise ValueError("reported draft order is not a complete slot listing")
    if owner_rows != [owner_slot]:
        raise ValueError("reported owner row disagrees with owner slot")
    if len(set(labels)) != teams:
        raise ValueError("reported draft order repeats a seat label")
    if len(set(franchises)) != len(franchises):
        raise ValueError("reported draft order assigns one history twice")

    source = report.get("source") or {}
    if source.get("kind") != "owner_reported_external_draw":
        raise ValueError("reported draft order lacks its external source")
    if not source.get("reported_date"):
        raise ValueError("reported draft order lacks its report date")
    return report


def load_reported_order(path, draft_id, user_id, teams, rounds):
    """Read one committed reported-order snapshot and enforce its contract."""
    with open(path) as fh:
        report = json.load(fh)
    return validate_reported_order(
        report, draft_id, user_id, teams, rounds)


def reported_order_basis(report, official_check, sleeper_source=None):
    """Planning basis when the external draw is known and Sleeper is pending."""
    return {
        "status": ("drawn_confirmed" if official_check == "agrees"
                   else "reported_pending_sleeper"),
        "slot": report["owner"]["slot"],
        "source": (sleeper_source if official_check == "agrees"
                   else report["source"]["kind"]),
        "reported_source": report["source"]["kind"],
        "reported_date": report["source"]["reported_date"],
        "official_check": official_check,
        "sleeper_source": sleeper_source,
        "coverage": "all_slots",
    }


def reconcile_owner_slot(draft, report, user_id, roster_id, teams):
    """Reconcile Sleeper with a validated externally reported owner slot.

    A safely undrawn Sleeper payload leaves the report primary but pending.
    A resolvable official draw must agree. Drawn-but-unresolvable evidence and
    disagreement both fail before a plausible wrong-seat artifact can publish.
    """
    official = resolve_owner_slot(draft, user_id, roster_id, teams)
    if not official["drawn"]:
        return reported_order_basis(
            report, "pending", sleeper_source=official["source"])
    if official["slot"] is None:
        if official["source"] == "official_sources_conflict":
            evidence = {
                "reported_slot": report["owner"]["slot"],
                "draft_order_slot": official["draft_order_slot"],
                "slot_map_slot": official["slot_map_slot"],
            }
            raise DraftOrderResolutionError(
                "official_sources_conflict",
                f"draft-order conflict: externally reported slot "
                f"{report['owner']['slot']}, Sleeper draft_order slot "
                f"{official['draft_order_slot']}, Sleeper slot map slot "
                f"{official['slot_map_slot']}", evidence)
        raise DraftOrderResolutionError(
            official["source"],
            "Sleeper order is drawn but the owner slot is not resolvable: "
            f"{official['source']}", {"reported_slot": report["owner"]["slot"]})
    reported_slot = report["owner"]["slot"]
    if official["slot"] != reported_slot:
        evidence = {"reported_slot": reported_slot,
                    "official_slot": official["slot"],
                    "official_source": official["source"]}
        raise DraftOrderResolutionError(
            "external_report_conflict",
            f"draft-order conflict: externally reported slot {reported_slot}, "
            f"Sleeper resolved slot {official['slot']}", evidence)
    return reported_order_basis(
        report, "agrees", sleeper_source=official["source"])
