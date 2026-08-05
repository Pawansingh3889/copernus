# This file saves and loads people in the database.
"""Identity I/O. person is permanent; person_identity is the only deletable table."""

from __future__ import annotations

from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from copernus.common.db import metadata
from copernus.modules.identity.contract import IdentityRecord

person = sa.Table(
    "person",
    metadata,
    sa.Column("person_id", sa.Uuid, primary_key=True, default=uuid4),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

person_identity = sa.Table(
    "person_identity",
    metadata,
    sa.Column(
        "person_id",
        sa.Uuid,
        sa.ForeignKey("person.person_id"),
        primary_key=True,
    ),
    sa.Column("full_name", sa.Text, nullable=False),
    sa.Column("role_title", sa.Text),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)


async def create_person(
    session: AsyncSession, full_name: str, role_title: str | None
) -> IdentityRecord:
    person_id = uuid4()
    await session.execute(sa.insert(person).values(person_id=person_id))
    await session.execute(
        sa.insert(person_identity).values(
            person_id=person_id, full_name=full_name, role_title=role_title
        )
    )
    return IdentityRecord(person_id=person_id, full_name=full_name, role_title=role_title)


async def resolve(session: AsyncSession, person_id: UUID) -> IdentityRecord | None:
    row = (
        await session.execute(
            sa.select(person_identity.c.full_name, person_identity.c.role_title).where(
                person_identity.c.person_id == person_id
            )
        )
    ).first()
    if row is None:
        return None
    return IdentityRecord(person_id=person_id, full_name=row.full_name, role_title=row.role_title)


async def erase(session: AsyncSession, person_id: UUID) -> bool:
    """Sever the identity. The person row and everything referencing it survive."""
    result = await session.execute(
        sa.delete(person_identity).where(person_identity.c.person_id == person_id)
    )
    return bool(result.rowcount)
