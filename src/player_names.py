#!/usr/bin/env python3
"""Canonical player-name comparison and identity resolution.

``comparison_key`` is deliberately lossy.  It exists for cross-source joins
whose source spellings differ, and therefore folds presentation differences
that do not identify a player: case, diacritics, punctuation, apostrophes,
dashes, whitespace, and a terminal generational suffix.

Lossy comparison is not identity.  ``PlayerIdentityResolver`` retains every
record in a comparison bucket and returns a record only when the bucket is
unique or supplied metadata separates it. Primary source names outrank a
colliding alias; aliases never become comparison-key rules. Its latest-draft-
year rule is the existing Sleeper-to-nflverse crosswalk policy: use it only for
a current-player lookup, only when every same-position candidate has a year,
and only when the newest year is unique. Position mismatches fail closed unless
the crosswalk's legacy compatibility rule is explicitly requested. Otherwise
the collision stays unresolved.
"""
from dataclasses import dataclass
import unicodedata


GENERATIONAL_SUFFIXES = frozenset(("jr", "sr", "ii", "iii", "iv", "v"))

# Source feeds have used, or can export, several visually apostrophe-like
# characters in player names.  Two are Unicode punctuation and were already
# removed by the category fold below; U+02BC is a letter and U+0060/U+00B4 are
# symbols, so relying on category alone leaves a source-dependent join key.
# Translate the whole contract before NFKD (U+00B4 otherwise decomposes into a
# space plus combining mark, which changes search_key tokenization).
APOSTROPHE_VARIANTS = ("'", "\u2019", "\u02bc", "`", "\u00b4", "\u2018")
_APOSTROPHE_TRANSLATION = str.maketrans(
    {variant: "'" for variant in APOSTROPHE_VARIANTS})


def _comparison_parts(name):
    if not isinstance(name, str):
        raise TypeError("player name must be a string")

    chars = []
    for char in unicodedata.normalize(
            "NFKD", name.translate(_APOSTROPHE_TRANSLATION)):
        category = unicodedata.category(char)
        if category.startswith("M"):
            continue
        if category == "Pd":
            chars.append(" ")
        elif not category.startswith("P"):
            chars.append(char.lower())

    parts = "".join(chars).split()
    while parts and parts[-1] in GENERATIONAL_SUFFIXES:
        parts.pop()
    return parts


def comparison_key(name):
    """Return a maximally blind, comparison-only key for a player name."""
    return "".join(_comparison_parts(name))


def search_key(name):
    """Token-preserving form for Walter's explicit nickname/fuzzy search layer."""
    return " ".join(_comparison_parts(name))


@dataclass(frozen=True)
class IdentityResolution:
    """Result of a fail-closed identity lookup."""

    record: object | None
    candidates: tuple
    rule: str | None = None
    reason: str | None = None


class PlayerIdentityResolver:
    """Retain comparison-key collisions and resolve only with unique evidence."""

    def __init__(self, records, *, name_field="name", position_field="pos",
                 draft_year_field="draft_year", aliases_field="aliases"):
        self.name_field = name_field
        self.position_field = position_field
        self.draft_year_field = draft_year_field
        self._by_key = {}
        self._exact_by_name = {}
        self._primary_exact_by_name = {}
        for record in records:
            names = [record[name_field]] + list(record.get(aliases_field) or ())
            for index, name in enumerate(names):
                key = comparison_key(name)
                bucket = self._by_key.setdefault(key, [])
                if not any(candidate is record for candidate in bucket):
                    bucket.append(record)
                # Exact spelling is identity evidence, but it must preserve
                # the punctuation, accents and suffixes that comparison_key
                # deliberately discards.  Case and repeated whitespace are
                # presentation only; everything else remains significant.
                exact = " ".join(unicodedata.normalize("NFC", name).casefold().split())
                exact_bucket = self._exact_by_name.setdefault(exact, [])
                if not any(candidate is record for candidate in exact_bucket):
                    exact_bucket.append(record)
                if index == 0:
                    self._primary_exact_by_name.setdefault(exact, []).append(record)

    def candidates(self, name):
        return tuple(self._by_key.get(comparison_key(name), ()))

    def resolve(self, name, *, position=None, prefer_latest_draft_year=False,
                allow_unique_position_mismatch=False):
        key = comparison_key(name)
        candidates = tuple(self._by_key.get(key, ()))
        exact_key = " ".join(
            unicodedata.normalize("NFC", name).casefold().split())
        exact = tuple(self._exact_by_name.get(exact_key, ()))
        primary_exact = tuple(self._primary_exact_by_name.get(exact_key, ()))
        if not candidates:
            return IdentityResolution(None, (), reason="no comparison-key match")

        if position is None:
            if len(candidates) == 1:
                return IdentityResolution(candidates[0], candidates,
                                          rule="unique comparison key")
            if len(primary_exact) == 1 and len(exact) > 1:
                return IdentityResolution(primary_exact[0], candidates,
                                          rule="exact primary name")
            if not primary_exact and len(exact) == 1:
                return IdentityResolution(exact[0], candidates,
                                          rule="exact alias name")
            return IdentityResolution(None, candidates,
                                      reason="comparison-key collision")

        positioned = tuple(
            record for record in candidates
            if record.get(self.position_field) == position)
        primary_exact_positioned = tuple(
            record for record in primary_exact
            if record.get(self.position_field) == position)
        exact_positioned = tuple(
            record for record in exact
            if record.get(self.position_field) == position)
        if len(positioned) == 1:
            return IdentityResolution(positioned[0], candidates, rule="position")

        if len(positioned) > 1:
            if prefer_latest_draft_year:
                years = [record.get(self.draft_year_field) for record in positioned]
                if all(year is not None for year in years):
                    newest = max(years)
                    latest = tuple(record for record in positioned
                                   if record.get(self.draft_year_field) == newest)
                    if len(latest) == 1:
                        return IdentityResolution(
                            latest[0], candidates, rule="most recent draft_year")
            # Exact spelling may separate an explicit alias collision, but it
            # does not by itself separate two primary identities which the
            # blind key collapsed (the Harrison/Gore father-son case).  That
            # case still needs the audited draft-year rule above.
            if len(primary_exact_positioned) == 1 and \
               len(exact_positioned) > 1:
                return IdentityResolution(primary_exact_positioned[0], candidates,
                                          rule="position + exact primary name")
            if not primary_exact_positioned and len(exact_positioned) == 1:
                return IdentityResolution(exact_positioned[0], candidates,
                                          rule="position + exact alias name")
            return IdentityResolution(
                None, candidates,
                reason="same name and position, entry year cannot separate")

        # One existing boundary deliberately accepts a unique-name match when
        # Sleeper and nflverse disagree on position: the published crosswalk.
        # That compatibility rule is opt-in.  Statistical callers must not,
        # for example, count a TE finish inside a WR cohort merely because the
        # name bucket is unique.
        if len(candidates) == 1 and allow_unique_position_mismatch:
            return IdentityResolution(candidates[0], candidates,
                                      rule="unique comparison key; position mismatch")

        if len(candidates) == 1:
            return IdentityResolution(None, candidates,
                                      reason="position mismatch")

        return IdentityResolution(None, candidates,
                                  reason="comparison-key collision")


def nflverse_roster_identity(rows, *, positions=None, stat_rows=(),
                             alias_rows=()):
    """Build the canonical resolver from nflverse roster snapshot rows.

    A season's roster is the identity universe for historical market joins:
    unlike weekly stats it retains players who logged zero games, so injury
    and holdout seasons remain honest busts instead of disappearing.  Weekly
    roster snapshots repeat identities; GSIS id deduplicates them before the
    resolver retains name collisions. Stats display names and league-pick
    names are explicit aliases only when their row carries that same GSIS id.
    Those stable-id evidence rows also retain a player omitted from the roster
    snapshot; foreign provider ids never enter this namespace.
    """
    stat_aliases = {}
    evidence_records = {}
    for row in stat_rows:
        gsis_id = row.get("player_id") or row.get("gsis_id")
        name = row.get("player_display_name") or row.get("full_name")
        if gsis_id and name:
            stat_aliases.setdefault(gsis_id, set()).add(name)
            evidence_records.setdefault(
                gsis_id, {"name": name,
                          "pos": row.get("position") or
                                 row.get("position_group")})
    for row in alias_rows:
        gsis_id = row.get("gsis_id") or row.get("player_id")
        name = (row.get("player_name") or row.get("player_display_name") or
                row.get("full_name") or row.get("name"))
        if gsis_id and name:
            stat_aliases.setdefault(gsis_id, set()).add(name)
            evidence_records.setdefault(
                gsis_id, {"name": name,
                          "pos": row.get("pos") or row.get("position")})

    records = {}
    aliases = {}
    for row in rows:
        gsis_id = row.get("gsis_id")
        position = row.get("position")
        if not gsis_id or (positions is not None and position not in positions):
            continue
        try:
            draft_year = int(row["entry_year"]) if row.get("entry_year") else None
        except (TypeError, ValueError):
            draft_year = None
        records[gsis_id] = {
            "name": row["full_name"], "pos": position,
            "gsis_id": gsis_id, "draft_year": draft_year}
        names = aliases.setdefault(gsis_id, set())
        names.add(row["full_name"])
        last = (row.get("last_name") or "").strip()
        for first_field in ("first_name", "football_name"):
            first = (row.get(first_field) or "").strip()
            if first and last:
                names.add(f"{first} {last}")
    # A league pick or a stats row already carries the stable GSIS id. Keep
    # that identity even when a roster snapshot omits the player (suspension,
    # reserve list, or source gap); the evidence row supplies name + position
    # directly and aliases can still collide/fail closed below.
    for gsis_id, evidence in evidence_records.items():
        position = evidence.get("pos")
        if gsis_id in records or not gsis_id.startswith("00-") or \
           (positions is not None and position not in positions):
            continue
        records[gsis_id] = {
            "name": evidence["name"], "pos": position,
            "gsis_id": gsis_id, "draft_year": None}
        aliases.setdefault(gsis_id, set()).add(evidence["name"])
    for gsis_id, record in records.items():
        record["aliases"] = sorted(
            (aliases.get(gsis_id, set()) | stat_aliases.get(gsis_id, set()))
            - {record["name"]})
    return PlayerIdentityResolver(records.values())
