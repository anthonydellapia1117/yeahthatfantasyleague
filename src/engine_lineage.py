"""Canonical content lineage for the 2026 engine payload.

The engine's human-readable ``generated`` field has day resolution. It cannot
distinguish two builds on the same day, so downstream artifacts must carry a
digest of the payload they actually consumed. The digest excludes only its own
field to avoid a circular hash; every other part of canonical JSON, including
the generation date, participates.
"""
import hashlib
import json
import re


FIELD = "content_sha256"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def json_content_sha256(payload):
    """Return SHA-256 over the canonical JSON data model of ``payload``."""
    # Hash the JSON data model that is actually written. The in-memory engine
    # carries a few integer-keyed dictionaries and tuples; a JSON round-trip
    # normalizes those to string keys and arrays before canonical ordering.
    canonical = json.loads(json.dumps(
        payload, ensure_ascii=False, allow_nan=False,
    ))
    raw = json.dumps(
        canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def content_sha256(payload):
    """Return the SHA-256 of canonical engine JSON excluding ``FIELD``."""
    if not isinstance(payload, dict):
        raise TypeError("engine payload must be a JSON object")
    canonical = dict(payload)
    canonical.pop(FIELD, None)
    return json_content_sha256(canonical)


def stamp(payload):
    """Set and return the canonical content digest on an engine payload."""
    payload[FIELD] = content_sha256(payload)
    return payload


def is_valid(payload):
    """True only when the declared digest is well formed and matches content."""
    declared = payload.get(FIELD) if isinstance(payload, dict) else None
    return bool(isinstance(declared, str) and _SHA256.fullmatch(declared)
                and declared == content_sha256(payload))


def require(payload):
    """Return a valid declared digest or raise before deriving an artifact."""
    if not is_valid(payload):
        raise ValueError("engine content_sha256 is missing or does not match payload")
    return payload[FIELD]
