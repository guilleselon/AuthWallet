"""Edge-case tests per endpoint."""
from __future__ import annotations

import pytest

from auth_service.adapters.inbound.http.routes import _DEFAULT_COOKIE_NAME


ADDR = "0x" + "a" * 40


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# --- /auth/nonce ---

@pytest.mark.asyncio
async def test_nonce_without_address_422(client):
    r = await client.post("/auth/nonce", json={})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_nonce_with_invalid_address_400(client):
    r = await client.post("/auth/nonce", json={"address": "not-an-address"})
    assert r.status_code == 400
    assert "address" in r.json()["error"].lower()


@pytest.mark.asyncio
async def test_nonce_valid_address_returns_fields(client):
    r = await client.post("/auth/nonce", json={"address": ADDR})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"nonce", "message", "expires_in"}


# --- /auth/me ---

@pytest.mark.asyncio
async def test_me_without_cookie_401(client):
    r = await client.get("/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_with_garbage_cookie_401(client, app_ctx):
    client.cookies.set(app_ctx["cookie_name"], "garbage-not-signed")
    r = await client.get("/auth/me")
    assert r.status_code == 401


# --- /auth/logout ---

@pytest.mark.asyncio
async def test_logout_without_session_succeeds(client):
    """Logout is idempotent; no cookie is still a 200."""
    r = await client.post("/auth/logout")
    assert r.status_code == 200
    assert r.json() == {"status": "logged_out"}


@pytest.mark.asyncio
async def test_logout_with_garbage_cookie_succeeds(client, app_ctx):
    client.cookies.set(app_ctx["cookie_name"], "garbage")
    r = await client.post("/auth/logout")
    assert r.status_code == 200


# --- /auth/verify ---

@pytest.mark.asyncio
async def test_verify_with_invalid_message_401(client):
    r = await client.post(
        "/auth/verify", json={"message": "not a siwe message", "signature": "0x00"}
    )
    assert r.status_code == 401
