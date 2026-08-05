# This file saves and loads user accounts and login sessions in the database.
"""Auth I/O: user accounts and server-side sessions."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from copernus.common.db import metadata
from copernus.modules.auth.contract import Role, User

user_account = sa.Table(
    "user_account",
    metadata,
    sa.Column("id", sa.Uuid, primary_key=True, default=uuid4),
    sa.Column("email", sa.Text, nullable=False, unique=True),
    sa.Column("password_hash", sa.Text, nullable=False),
    sa.Column("role", sa.Text, nullable=False, server_default=Role.PARTICIPANT.value),
    sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
    # Nullable on purpose: an account is credentials, a person is identity.
    # Severing the identity (C-12) must not touch the account row.
    sa.Column("person_id", sa.Uuid, sa.ForeignKey("person.person_id")),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

session_token = sa.Table(
    "session",
    metadata,
    sa.Column("token_hash", sa.Text, primary_key=True),
    sa.Column("user_id", sa.Uuid, sa.ForeignKey("user_account.id"), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
)


def _user(row: sa.Row) -> User:
    return User(
        id=row.id, email=row.email, role=Role(row.role), active=row.active, person_id=row.person_id
    )


async def create_user(
    session: AsyncSession, email: str, password_hash: str, person_id: UUID | None
) -> User:
    user_id = uuid4()
    await session.execute(
        sa.insert(user_account).values(
            id=user_id, email=email.lower(), password_hash=password_hash, person_id=person_id
        )
    )
    return User(
        id=user_id, email=email.lower(), role=Role.PARTICIPANT, active=True, person_id=person_id
    )


async def get_by_email(session: AsyncSession, email: str) -> tuple[User, str] | None:
    """Returns the user and their password hash, or None."""
    row = (
        await session.execute(sa.select(user_account).where(user_account.c.email == email.lower()))
    ).first()
    return (_user(row), row.password_hash) if row else None


async def set_role(session: AsyncSession, user_id: UUID, role: Role) -> bool:
    result = await session.execute(
        sa.update(user_account).where(user_account.c.id == user_id).values(role=role.value)
    )
    return bool(result.rowcount)


async def create_session(
    session: AsyncSession, token_hash: str, user_id: UUID, expires_at: datetime
) -> None:
    await session.execute(
        sa.insert(session_token).values(
            token_hash=token_hash, user_id=user_id, expires_at=expires_at
        )
    )


async def user_for_session(session: AsyncSession, token_hash: str, now: datetime) -> User | None:
    row = (
        await session.execute(
            sa.select(user_account)
            .join(session_token, session_token.c.user_id == user_account.c.id)
            .where(
                session_token.c.token_hash == token_hash,
                session_token.c.expires_at > now,
                user_account.c.active,
            )
        )
    ).first()
    return _user(row) if row else None


async def delete_session(session: AsyncSession, token_hash: str) -> None:
    await session.execute(sa.delete(session_token).where(session_token.c.token_hash == token_hash))
