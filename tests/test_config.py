"""Settings come from COP_-prefixed environment, with safe defaults."""

from __future__ import annotations

from copernus.config import load_settings


def test_env_overrides_defaults(monkeypatch):
    monkeypatch.setenv("COP_AUTH_EMAIL_DOMAIN", "plant.example")
    monkeypatch.setenv("COP_SESSION_TTL_HOURS", "8")

    settings = load_settings()

    assert settings.auth_email_domain == "plant.example"
    assert settings.session_ttl_hours == 8
    assert settings.env == "development"  # untouched default


def test_secure_cookie_defaults_off_for_dev(monkeypatch):
    monkeypatch.delenv("COP_SESSION_COOKIE_SECURE", raising=False)
    assert load_settings().session_cookie_secure is False
