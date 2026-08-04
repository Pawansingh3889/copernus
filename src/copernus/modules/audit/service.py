"""Audit rules. Pure functions — no I/O, enforced by lint-imports."""

from __future__ import annotations

from typing import Any

from copernus.modules.audit.contract import AuditEntry


def entry_from_dispatch(raw: dict[str, Any]) -> AuditEntry:
    """Shape the engine's dispatch record into an entry worth persisting.

    Fails loudly on a missing event name — an unnamed audit row is the
    "Something went wrong" of audit trails (§7.7).
    """
    event = raw.get("event")
    if not event:
        raise ValueError("An audit entry must name its event")
    return AuditEntry(
        event=str(event),
        user_id=raw.get("user_id"),
        correlation_id=raw.get("correlation_id"),
    )
