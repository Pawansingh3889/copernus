"""Pure auth rules — no database, no mocks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from copernus.modules.auth import service


def test_email_domain_gate():
    assert service.email_allowed("a@example.com", "example.com")
    assert service.email_allowed("A@EXAMPLE.COM", "example.com")
    assert not service.email_allowed("a@other.com", "example.com")
    assert not service.email_allowed("a@notexample.com", "example.com")


def test_password_problems_lists_every_failure_at_once():
    assert service.password_problems("Str0ng!pass") == []
    problems = service.password_problems("short")
    assert len(problems) == 3  # length, digit, special — all reported (§7.7)


def test_password_hash_roundtrip():
    hashed = service.hash_password("Str0ng!pass")
    assert service.verify_password("Str0ng!pass", hashed)
    assert not service.verify_password("wrong", hashed)


def test_token_is_stored_as_hash_only():
    token = "not-a-secret-in-tests"
    assert service.hash_token(token) != token
    assert len(service.hash_token(token)) == 64  # sha256 hex


def test_session_expiry_uses_configured_ttl():
    now = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)
    assert service.session_expiry(now, 12) == now + timedelta(hours=12)
