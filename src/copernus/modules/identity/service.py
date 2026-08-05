# This file holds the rules about people. It never touches the database.
"""Identity rules. Pure functions — no I/O, enforced by lint-imports."""

from __future__ import annotations

from uuid import UUID

from copernus.modules.identity.contract import IdentityRecord


def validate_name(full_name: str) -> str:
    name = full_name.strip()
    if not name:
        raise ValueError("A person needs a non-empty name")
    return name


def display_name(person_id: UUID, record: IdentityRecord | None) -> str:
    """What a screen shows for a person — including one whose identity is erased.

    An erased person still appears in audit trails and incident records; the
    pseudonym keeps those rows readable without resurrecting the identity.
    """
    if record is None:
        return f"person {str(person_id)[:8]}"
    if record.role_title:
        return f"{record.full_name} ({record.role_title})"
    return record.full_name
