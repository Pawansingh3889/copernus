"""Alembic environment — async engine, URL from settings, metadata from the modules."""

from __future__ import annotations

import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from copernus.common.db import metadata
from copernus.config import load_settings

# Importing the repositories registers their tables on the shared metadata.
import copernus.modules.audit.repository  # noqa: F401
import copernus.modules.auth.repository  # noqa: F401
import copernus.modules.identity.repository  # noqa: F401

target_metadata = metadata


def run_migrations_offline() -> None:
    context.configure(
        url=load_settings().migration_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(load_settings().migration_database_url)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
