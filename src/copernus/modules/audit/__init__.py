# The audit module: it writes down who did what and when, so nothing is forgotten.
"""Audit module: handle(event, state) -> Result."""

from __future__ import annotations

from typing import Any

from copernus.common.types import Event, Result
from copernus.modules.audit import repository

PERMISSIONS = {"audit.recent": "audit.view"}


async def handle(event: Event, state: dict[str, Any]) -> Result[Any]:
    factory = state["session_factory"]
    async with factory() as session:
        if event.type == "audit.recent":
            limit = int(event.payload.get("limit", 50))
            return Result.success(await repository.recent(session, limit))

    return Result.err(f"audit does not handle {event.type!r}", "module_not_found")
