# Tests the identity module: creating and finding people.
"""Identity: creation, resolution, and the C-12 severance guarantee."""

from __future__ import annotations

import sqlalchemy as sa

from copernus.common.types import Event
from copernus.modules.identity import repository, service
from copernus.modules.identity.contract import IdentityRecord


async def test_create_and_resolve(wired_engine):
    created = await wired_engine.dispatch(
        Event(
            type="identity.create", payload={"full_name": "Sam Lee", "role_title": "Team Leader"}
        ),
        granted={"identity.manage"},
    )
    assert created.ok

    resolved = await wired_engine.dispatch(
        Event(type="identity.resolve", payload={"person_id": str(created.value.person_id)}),
        granted={"identity.view"},
    )
    assert resolved.value == "Sam Lee (Team Leader)"


async def test_erase_severs_identity_but_keeps_the_person(wired_engine, session_factory):
    """C-12: erasure deletes the mapping row and nothing else."""
    created = await wired_engine.dispatch(
        Event(type="identity.create", payload={"full_name": "Sam Lee"}),
        granted={"identity.manage"},
    )
    person_id = created.value.person_id

    erased = await wired_engine.dispatch(
        Event(type="identity.erase", payload={"person_id": str(person_id)}),
        granted={"identity.manage"},
    )
    assert erased.ok

    # The person row survives; only the identity is gone.
    async with session_factory() as session:
        remaining = (
            await session.execute(
                sa.select(repository.person).where(repository.person.c.person_id == person_id)
            )
        ).first()
    assert remaining is not None

    resolved = await wired_engine.dispatch(
        Event(type="identity.resolve", payload={"person_id": str(person_id)}),
        granted={"identity.view"},
    )
    assert resolved.value.startswith("person ")  # pseudonym, not a name


async def test_erase_after_audit_leaves_the_trail_intact(wired_engine, session_factory):
    """The C-12/C-03 interlock: severing identity must not break the audit chain."""
    from copernus.modules.audit import repository as audit_repository

    created = await wired_engine.dispatch(
        Event(
            type="identity.create",
            payload={"full_name": "Sam Lee"},
            user_id="u-sam",
            correlation_id="c1",
        ),
        granted={"identity.manage"},
    )
    await wired_engine.dispatch(
        Event(
            type="identity.erase",
            payload={"person_id": str(created.value.person_id)},
            user_id="u-admin",
        ),
        granted={"identity.manage"},
    )

    async with session_factory() as session:
        entries = await audit_repository.recent(session)
    events = [e.event for e in entries]
    assert "identity.create" in events
    assert "identity.erase" in events  # the erasure itself is audited


def test_display_name_falls_back_to_pseudonym():
    from uuid import uuid4

    person_id = uuid4()
    assert service.display_name(person_id, None) == f"person {str(person_id)[:8]}"
    assert service.display_name(person_id, IdentityRecord(person_id, "Sam Lee", None)) == "Sam Lee"


def test_validate_name_rejects_blank():
    import pytest

    with pytest.raises(ValueError, match="non-empty"):
        service.validate_name("   ")
