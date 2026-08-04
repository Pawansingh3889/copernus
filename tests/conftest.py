"""Shared fixtures. Factories over literals (§7.6).

Module tests run against in-memory SQLite — fast, no daemon. The rules that
only Postgres can enforce (C-03 trigger and grants) have their own pg-marked
tests that read COP_TEST_DATABASE_URL and skip when it is absent.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

# Importing the repositories registers their tables on the shared metadata.
import copernus.modules.audit.repository as audit_repository
import copernus.modules.auth.repository as auth_repository  # noqa: F401
import copernus.modules.identity.repository as identity_repository  # noqa: F401
from copernus.common.db import make_session_factory, metadata
from copernus.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(auth_email_domain="example.com", session_ttl_hours=1)


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    yield make_session_factory(engine)
    await engine.dispose()


@pytest.fixture
async def wired_engine(session_factory, settings):
    """The engine as the app wires it: all modules registered, audit sink attached."""
    from copernus.engine import Engine
    from copernus.modules import audit, auth, identity

    engine = Engine(
        state={"session_factory": session_factory, "settings": settings},
        audit_sink=audit_repository.make_sink(session_factory),
    )
    for module in (auth, identity, audit):
        for event_type, permission in module.PERMISSIONS.items():
            engine.register(event_type, module.handle, permission=permission)
    # Event types without an entry in PERMISSIONS are open (register, login…).
    for event_type in ("auth.register", "auth.login", "auth.logout", "auth.whoami"):
        engine.register(event_type, auth.handle)
    return engine
