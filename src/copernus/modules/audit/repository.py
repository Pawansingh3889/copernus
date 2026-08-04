"""Audit I/O. Append-only: the migration revokes UPDATE/DELETE and adds a
trigger that raises on both — C-03 is enforced by the database, not convention."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from copernus.common.db import metadata
from copernus.modules.audit.contract import AuditEntry

audit_log = sa.Table(
    "audit_log",
    metadata,
    sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
    sa.Column("event", sa.Text, nullable=False),
    sa.Column("user_id", sa.Text),
    sa.Column("correlation_id", sa.Text),
    sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)


async def append(session: AsyncSession, entry: AuditEntry) -> None:
    await session.execute(
        sa.insert(audit_log).values(
            event=entry.event, user_id=entry.user_id, correlation_id=entry.correlation_id
        )
    )


async def recent(session: AsyncSession, limit: int = 50) -> list[AuditEntry]:
    rows = await session.execute(
        sa.select(audit_log).order_by(audit_log.c.id.desc()).limit(limit)
    )
    return [
        AuditEntry(
            event=r.event,
            user_id=r.user_id,
            correlation_id=r.correlation_id,
            recorded_at=r.recorded_at,
        )
        for r in rows
    ]


def make_sink(factory: async_sessionmaker):
    """The engine's audit_sink: persists every dispatch in its own transaction.

    Separate from the handler's transaction on purpose — a rolled-back request
    still happened, and the audit row must survive the rollback (§7.3).
    """
    from copernus.modules.audit.service import entry_from_dispatch

    async def sink(raw: dict) -> None:
        async with factory() as session, session.begin():
            await append(session, entry_from_dispatch(raw))

    return sink
