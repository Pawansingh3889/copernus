"""Auth contracts. No secrets here — check_no_secrets_in_contracts.py enforces it."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class Role(StrEnum):
    PARTICIPANT = "participant"
    ANALYST = "analyst"
    MANAGER = "manager"
    ADMIN = "admin"


# What each role may do. Roles accumulate — every role includes the ones below
# it. The engine checks these strings on dispatch; nothing else grants access.
ROLE_PERMISSIONS: dict[Role, frozenset[str]] = {
    Role.PARTICIPANT: frozenset({"identity.view", "despatch.view"}),
    Role.ANALYST: frozenset({"identity.view", "despatch.view", "audit.view"}),
    Role.MANAGER: frozenset({"identity.view", "despatch.view", "audit.view", "identity.manage"}),
    Role.ADMIN: frozenset(
        {"identity.view", "despatch.view", "audit.view", "identity.manage", "auth.promote"}
    ),
}


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    email: str
    role: Role
    active: bool
    person_id: UUID | None = None

    @property
    def permissions(self) -> frozenset[str]:
        return ROLE_PERMISSIONS[self.role]


@dataclass(frozen=True, slots=True)
class RegisterCommand:
    email: str
    password: str
    full_name: str


@dataclass(frozen=True, slots=True)
class LoginCommand:
    email: str
    password: str
