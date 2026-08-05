# The auth module: signing up, logging in, logging out.
"""Auth module: handle(event, state) -> Result.

An account is credentials, not a person: registration stores person_id=None,
and linking an account to a person is an identity.manage action composed at
the adapter layer — auth importing identity would break §7.1.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from copernus.common.types import Event, Result
from copernus.modules.auth import repository, service
from copernus.modules.auth.contract import Role

PERMISSIONS = {"auth.promote": "auth.promote"}


async def handle(event: Event, state: dict[str, Any]) -> Result[Any]:
    factory = state["session_factory"]
    settings = state["settings"]
    now = datetime.now(UTC)

    async with factory() as session, session.begin():
        if event.type == "auth.register":
            email = str(event.payload["email"]).strip().lower()
            password = str(event.payload["password"])
            if not service.email_allowed(email, settings.auth_email_domain):
                return Result.err(
                    f"Registration requires an @{settings.auth_email_domain} address",
                    "email_domain",
                )
            problems = service.password_problems(password)
            if problems:
                return Result.err("Password needs: " + ", ".join(problems), "weak_password")
            if await repository.get_by_email(session, email):
                return Result.err("That email is already registered", "email_exists")
            user = await repository.create_user(
                session, email, service.hash_password(password), person_id=None
            )
            return Result.success(user)

        if event.type == "auth.login":
            email = str(event.payload["email"]).strip().lower()
            found = await repository.get_by_email(session, email)
            # Same error either way — an attacker learns nothing about which half failed.
            if not found or not service.verify_password(str(event.payload["password"]), found[1]):
                return Result.err("Email or password is incorrect", "invalid_credentials")
            user, _ = found
            if not user.active:
                return Result.err("This account is deactivated", "account_inactive")
            token = secrets.token_urlsafe(32)
            await repository.create_session(
                session,
                service.hash_token(token),
                user.id,
                service.session_expiry(now, settings.session_ttl_hours),
            )
            return Result.success({"user": user, "token": token})

        if event.type == "auth.logout":
            await repository.delete_session(
                session, service.hash_token(str(event.payload["token"]))
            )
            return Result.success(True)

        if event.type == "auth.whoami":
            current = await repository.user_for_session(
                session, service.hash_token(str(event.payload["token"])), now
            )
            return Result.success(current)  # None means "not logged in", not an error

        if event.type == "auth.promote":
            ok = await repository.set_role(
                session, UUID(str(event.payload["user_id"])), Role(event.payload["role"])
            )
            if not ok:
                return Result.err("No such user", "not_found")
            return Result.success(True)

    return Result.err(f"auth does not handle {event.type!r}", "module_not_found")
