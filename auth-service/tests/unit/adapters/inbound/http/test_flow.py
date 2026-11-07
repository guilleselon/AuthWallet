"""End-to-end HTTP flow with a real Ethereum keypair and real signature."""
from __future__ import annotations

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct


async def _sign_message(acct, message: str) -> str:
    signed = acct.sign_message(encode_defunct(text=message))
    return "0x" + signed.signature.hex()


@pytest.mark.asyncio
async def test_full_login_flow(client, app_ctx):
    acct = Account.create()
    address = acct.address.lower()

    # 1. Request a nonce + message
    r = await client.post("/auth/nonce", json={"address": address})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "nonce" in body
    assert "message" in body
    assert body["expires_in"] == 300

    # 2. Sign the message
    signature = await _sign_message(acct, body["message"])

    # 3. Verify
    r = await client.post(
        "/auth/verify", json={"message": body["message"], "signature": signature}
    )
    assert r.status_code == 200, r.text
    session_body = r.json()
    assert session_body["address"] == address
    assert session_body["chain_id"] == 56
    assert app_ctx["cookie_name"] in client.cookies

    # 4. /auth/me returns the session
    r = await client.get("/auth/me")
    assert r.status_code == 200, r.text
    me = r.json()
    assert me["address"] == address
    assert me["chain_id"] == 56

    # 5. Logout clears cookie and session
    r = await client.post("/auth/logout")
    assert r.status_code == 200
    # After logout, /auth/me must fail (cookie was cleared by the server)
    r = await client.get("/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_replay_is_rejected(client):
    """A captured (message, signature) pair cannot be used twice."""
    acct = Account.create()
    address = acct.address.lower()

    r = await client.post("/auth/nonce", json={"address": address})
    body = r.json()
    signature = await _sign_message(acct, body["message"])

    # First verify: succeeds.
    r1 = await client.post(
        "/auth/verify", json={"message": body["message"], "signature": signature}
    )
    assert r1.status_code == 200

    # Second verify with the SAME message+signature: nonce already consumed.
    r2 = await client.post(
        "/auth/verify", json={"message": body["message"], "signature": signature}
    )
    assert r2.status_code == 400
    assert "nonce" in r2.json()["error"].lower()


@pytest.mark.asyncio
async def test_wrong_signature_rejected(client):
    """Signature from a different account must not authenticate."""
    attacker = Account.create()
    victim = Account.create()

    r = await client.post(
        "/auth/nonce", json={"address": victim.address.lower()}
    )
    body = r.json()
    # Sign with the attacker's key.
    signature = await _sign_message(attacker, body["message"])

    r = await client.post(
        "/auth/verify", json={"message": body["message"], "signature": signature}
    )
    assert r.status_code == 401
