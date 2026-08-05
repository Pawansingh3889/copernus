# This file says what messages the audit module accepts and gives back.
"""Audit contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AuditEntry:
    event: str
    user_id: str | None = None
    correlation_id: str | None = None
    recorded_at: datetime | None = None
