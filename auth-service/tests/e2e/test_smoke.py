"""End-to-end smoke test: build the app via the composition root,
connect an HTTP client, complete the full SIWE flow with a real key.

If this passes, `python -m auth_service` will work too.
"""
from __future__ import annotations

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from httpx import ASGITransport, AsyncClient

from auth_service.config import Config
from auth_service.domain.types import make_chain_id
from auth_service.main import build_app


DOMAIN = "smoke.test"
URI = "http://smoke.test"
CHAIN_ID = make_chain_id(56)
COOKIE_NAME = "smoke_session"


def _config() -> Config:
    return Config(
        host="127.0.0.1",
        port=0,
        log_level="WARNING",
        domain=DOMAIN,
        uri=URI,
        chain_id=CHAIN_ID,
        statement="Sign in to smoke.test",
        cookie_secret="x" * 64,
        cookie_name=COOKIE_NAME,
        cookie_secure=False,
        session_ttl_seconds=3600,
        nonce_ttl_seconds=300,
        max_message_age_seconds=600,
        cors_origins=(),
        store_backend="memory",
    )


@pytest.mark.asyncio
async def test_smoke_full_flow():
    app = build_app(_config())
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        acct = Account.create()
        address = acct.address.lower()

        # Health
        r = await client.get("/health")
        assert r.status_code == 200

        # Nonce
        r = await client.post("/auth/nonce", json={"address": address})
        assert r.status_code == 200
        body = r.json()
        assert "nonce" in body and "message" in body

        # Sign with a real keypair
        signed = acct.sign_message(encode_defunct(text=body["message"]))
        signature = "0x" + signed.signature.hex()

        # Verify → session cookie set
        r = await client.post(
            "/auth/verify",
            json={"message": body["message"], "signature": signature},
        )
        assert r.status_code == 200
        assert COOKIE_NAME in client.cookies

        # Me
        r = await client.get("/auth/me")
        assert r.status_code == 200
        assert r.json()["address"] == address

        # Logout
        r = await client.post("/auth/logout")
        assert r.status_code == 200
        # Cookie cleared; next /auth/me must be 401
        client.cookies.clear()
        r = await client.get("/auth/me")
        assert r.status_code == 401
