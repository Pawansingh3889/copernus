"""Identity contracts. No secrets here — check_no_secrets_in_contracts.py enforces it."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class IdentityRecord:
    """The severable half of a person: who they are, deletable on request.

    Every other table references person_id only. Erasure deletes this row and
    nothing else — the audit chain stays intact (C-12 vs C-03, ARCHITECTURE.md).
    """

    person_id: UUID
    full_name: str
    role_title: str | None = None


@dataclass(frozen=True, slots=True)
class CreatePersonCommand:
    full_name: str
    role_title: str | None = None


@dataclass(frozen=True, slots=True)
class ErasePersonCommand:
    person_id: UUID
