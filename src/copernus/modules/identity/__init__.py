"""Identity module: handle(event, state) -> Result. The engine wires everything."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from copernus.common.types import Event, Result
from copernus.modules.identity import repository, service

PERMISSIONS = {
    "identity.create": "identity.manage",
    "identity.erase": "identity.manage",
    "identity.resolve": "identity.view",
}


async def handle(event: Event, state: dict[str, Any]) -> Result[Any]:
    factory = state["session_factory"]
    async with factory() as session, session.begin():
        if event.type == "identity.create":
            name = service.validate_name(event.payload["full_name"])
            record = await repository.create_person(session, name, event.payload.get("role_title"))
            return Result.success(record)

        if event.type == "identity.erase":
            erased = await repository.erase(session, UUID(str(event.payload["person_id"])))
            if not erased:
                return Result.err("No identity to erase for that person", "not_found")
            return Result.success(True)

        if event.type == "identity.resolve":
            person_id = UUID(str(event.payload["person_id"]))
            record = await repository.resolve(session, person_id)
            return Result.success(service.display_name(person_id, record))

    return Result.err(f"identity does not handle {event.type!r}", "module_not_found")
