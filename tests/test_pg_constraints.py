# Tests the rules only a real Postgres database can enforce.
"""The rules only Postgres can enforce, proven against a real Postgres.

Skipped unless COP_TEST_PG_DSN is set (e.g. postgresql://copernus:copernus@localhost:5433/copernus
after `make db-up && make migrate`). CI provides it via a service container.
"""

from __future__ import annotations

import os
import uuid

import pytest

DSN = os.environ.get("COP_TEST_PG_DSN")
APP_DSN = os.environ.get("COP_TEST_PG_APP_DSN")

pytestmark = pytest.mark.skipif(not DSN, reason="COP_TEST_PG_DSN not set")


@pytest.fixture
async def owner():
    import asyncpg

    conn = await asyncpg.connect(DSN)
    yield conn
    await conn.close()


@pytest.fixture
async def app_role():
    import asyncpg

    dsn = APP_DSN or DSN.replace("copernus:copernus", "copernus_app:copernus_app")
    conn = await asyncpg.connect(dsn)
    yield conn
    await conn.close()


async def test_c03_trigger_blocks_even_the_owner(owner):
    await owner.execute("INSERT INTO audit_log (event) VALUES ('probe')")
    with pytest.raises(Exception, match="append-only"):
        await owner.execute("DELETE FROM audit_log WHERE event = 'probe'")
    with pytest.raises(Exception, match="append-only"):
        await owner.execute("UPDATE audit_log SET event = 'tampered' WHERE event = 'probe'")


async def test_c03_grants_block_the_app_role(app_role):
    await app_role.execute("INSERT INTO audit_log (event) VALUES ('app-probe')")
    with pytest.raises(Exception, match="permission denied"):
        await app_role.execute("DELETE FROM audit_log WHERE event = 'app-probe'")


async def test_c12_erasure_severs_identity_only(owner):
    person_id = uuid.uuid4()
    await owner.execute("INSERT INTO person (person_id) VALUES ($1)", person_id)
    await owner.execute(
        "INSERT INTO person_identity (person_id, full_name) VALUES ($1, 'Probe Person')",
        person_id,
    )
    await owner.execute(
        "INSERT INTO audit_log (event, user_id) VALUES ('probe.event', $1)", str(person_id)
    )

    await owner.execute("DELETE FROM person_identity WHERE person_id = $1", person_id)

    # Identity gone; person and audit intact.
    assert await owner.fetchval("SELECT count(*) FROM person WHERE person_id = $1", person_id) == 1
    assert (
        await owner.fetchval("SELECT count(*) FROM audit_log WHERE user_id = $1", str(person_id))
        == 1
    )
