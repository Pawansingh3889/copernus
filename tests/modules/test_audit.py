"""Audit: shaping, persistence, and survival across handler failure."""

from __future__ import annotations

import pytest

from copernus.common.types import Event
from copernus.modules.audit import repository, service


def test_entry_from_dispatch_requires_an_event_name():
    with pytest.raises(ValueError, match="must name its event"):
        service.entry_from_dispatch({"user_id": "u1"})


async def test_every_dispatch_lands_in_the_database(wired_engine, session_factory):
    await wired_engine.dispatch(Event(type="nobody.home", user_id="u1"))

    async with session_factory() as session:
        entries = await repository.recent(session)
    assert entries[0].event == "nobody.home"
    assert entries[0].user_id == "u1"


async def test_audit_survives_a_crashing_handler(wired_engine, session_factory):
    """§7.3 — the audit row is written in its own transaction, before the handler."""

    async def exploding(event, state):
        raise RuntimeError("boom")

    wired_engine.register("bad.query", exploding)
    result = await wired_engine.dispatch(Event(type="bad.query", user_id="u1"))
    assert not result.ok

    async with session_factory() as session:
        entries = await repository.recent(session)
    assert entries[0].event == "bad.query"


async def test_recent_requires_the_audit_permission(wired_engine):
    from copernus.common.errors import PermissionDeniedError

    with pytest.raises(PermissionDeniedError):
        await wired_engine.dispatch(Event(type="audit.recent"), granted=set())

    result = await wired_engine.dispatch(Event(type="audit.recent"), granted={"audit.view"})
    assert result.ok
