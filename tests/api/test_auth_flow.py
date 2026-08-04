"""The auth flow over HTTP, both adapters, one wired app on SQLite."""

from __future__ import annotations

import httpx
import pytest

from copernus.app import build_engine, create_app


@pytest.fixture
async def client(session_factory, settings):
    app = create_app(settings)
    # Same wiring as production, database swapped for the test factory.
    app.state.engine = build_engine(session_factory, settings)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


CREDS = {"email": "worker@example.com", "password": "Str0ng!pass"}


async def test_json_adapter_full_flow(client):
    r = await client.post("/api/v1/auth/register", json={**CREDS, "full_name": "A Worker"})
    assert r.status_code == 201, r.text

    r = await client.post("/api/v1/auth/login", json=CREDS)
    assert r.status_code == 200
    cookie = r.cookies.get("copernus_session")
    assert cookie
    assert "httponly" in r.headers["set-cookie"].lower()

    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == CREDS["email"]

    r = await client.post("/api/v1/auth/logout")
    assert r.status_code == 200
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_json_adapter_maps_error_codes_to_statuses(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "x@elsewhere.com", "password": "Str0ng!pass", "full_name": "X"},
    )
    assert r.status_code == 400

    await client.post("/api/v1/auth/register", json={**CREDS, "full_name": "A"})
    r = await client.post("/api/v1/auth/register", json={**CREDS, "full_name": "A"})
    assert r.status_code == 409

    r = await client.post("/api/v1/auth/login", json={**CREDS, "password": "wrong"})
    assert r.status_code == 401


async def test_html_adapter_login_and_home(client):
    await client.post("/api/v1/auth/register", json={**CREDS, "full_name": "A Worker"})

    # Anonymous / redirects to the login page.
    r = await client.get("/")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"
    assert "<form" in (await client.get("/login")).text

    # Wrong password comes back as an inline fragment, not a redirect.
    r = await client.post("/login", data={**CREDS, "password": "wrong"})
    assert 'class="error"' in r.text

    r = await client.post("/login", data=CREDS)
    assert r.headers.get("HX-Redirect") == "/"
    assert r.cookies.get("copernus_session")

    r = await client.get("/")
    assert r.status_code == 200
    assert CREDS["email"] in r.text

    r = await client.post("/logout")
    assert r.headers.get("HX-Redirect") == "/login"
