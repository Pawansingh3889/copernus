"""Auth flow through the engine — UC-01 acceptance criteria."""

from __future__ import annotations

import pytest

from copernus.common.errors import PermissionDeniedError
from copernus.common.types import Event
from copernus.modules.auth.contract import Role


async def _register(engine, email="worker@example.com", password="Str0ng!pass"):
    return await engine.dispatch(
        Event(
            type="auth.register",
            payload={"email": email, "password": password, "full_name": "A Worker"},
        )
    )


async def test_register_then_login(wired_engine):
    assert (await _register(wired_engine)).ok

    result = await wired_engine.dispatch(
        Event(type="auth.login", payload={"email": "worker@example.com", "password": "Str0ng!pass"})
    )
    assert result.ok
    assert result.value["token"]
    assert result.value["user"].role is Role.PARTICIPANT


async def test_register_rejects_foreign_domain(wired_engine):
    result = await _register(wired_engine, email="worker@elsewhere.com")
    assert not result.ok
    assert result.error_code == "email_domain"


async def test_register_rejects_weak_password_with_reasons(wired_engine):
    result = await _register(wired_engine, password="weak")
    assert not result.ok
    assert result.error_code == "weak_password"
    assert "digit" in result.error  # the message says what to fix (§7.7)


async def test_duplicate_email_is_refused(wired_engine):
    await _register(wired_engine)
    result = await _register(wired_engine)
    assert result.error_code == "email_exists"


async def test_login_error_does_not_reveal_which_half_failed(wired_engine):
    await _register(wired_engine)
    wrong_pw = await wired_engine.dispatch(
        Event(type="auth.login", payload={"email": "worker@example.com", "password": "bad"})
    )
    no_user = await wired_engine.dispatch(
        Event(type="auth.login", payload={"email": "ghost@example.com", "password": "bad"})
    )
    assert wrong_pw.error == no_user.error


async def test_whoami_and_logout(wired_engine):
    await _register(wired_engine)
    login = await wired_engine.dispatch(
        Event(type="auth.login", payload={"email": "worker@example.com", "password": "Str0ng!pass"})
    )
    token = login.value["token"]

    whoami = await wired_engine.dispatch(Event(type="auth.whoami", payload={"token": token}))
    assert whoami.value.email == "worker@example.com"

    await wired_engine.dispatch(Event(type="auth.logout", payload={"token": token}))
    assert (
        await wired_engine.dispatch(Event(type="auth.whoami", payload={"token": token}))
    ).value is None


async def test_promote_requires_the_admin_permission(wired_engine):
    """No self-promotion: the promote event demands auth.promote, which only ADMIN holds."""
    register = await _register(wired_engine)
    user = register.value

    with pytest.raises(PermissionDeniedError):
        await wired_engine.dispatch(
            Event(type="auth.promote", payload={"user_id": str(user.id), "role": "admin"}),
            granted=user.permissions,  # a participant's own permissions
        )

    result = await wired_engine.dispatch(
        Event(type="auth.promote", payload={"user_id": str(user.id), "role": "analyst"}),
        granted={"auth.promote"},
    )
    assert result.ok
