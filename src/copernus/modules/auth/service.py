"""Auth rules. Pure/deterministic where it matters; no I/O, enforced by lint-imports.

bcrypt and hashlib are CPU, not I/O — the tests need no database and no mocks.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

import bcrypt

# UC-01: min 8 chars, at least one digit, at least one special character.
_SPECIALS = set("!@#$%^&*()-_=+[]{};:'\",.<>/?\\|`~")


def email_allowed(email: str, domain: str) -> bool:
    """The company-domain gate. An access-code path can join it later (UC-01)."""
    return email.strip().lower().endswith(f"@{domain.lower()}")


def password_problems(password: str) -> list[str]:
    """Every problem, not just the first — the user fixes them in one pass (§7.7)."""
    problems = []
    if len(password) < 8:
        problems.append("at least 8 characters")
    if not any(c.isdigit() for c in password):
        problems.append("at least one digit")
    if not any(c in _SPECIALS for c in password):
        problems.append("at least one special character")
    return problems


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def hash_token(token: str) -> str:
    """Sessions store the hash, never the token — a leaked table logs nobody in."""
    return hashlib.sha256(token.encode()).hexdigest()


def session_expiry(now: datetime, ttl_hours: int) -> datetime:
    return now + timedelta(hours=ttl_hours)
