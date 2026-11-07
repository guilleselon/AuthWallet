"""Tests for the real SIWE adapter.

We generate real secp256k1 keypairs with `eth_account` (already a
transitive dependency of `signinwithethereum`) and sign real EIP-191
messages. No mocks of the crypto: if this adapter works, a real wallet
signature will verify.
"""
from __future__ import annotations

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct

from auth_service.adapters.outbound.eth import SigninWithEthereumSiweService
from auth_service.domain.errors import SignatureVerificationFailed
from auth_service.domain.siwe import format_iso8601
from auth_service.domain.types import make_address, make_chain_id


DOMAIN = "auth.example.com"
URI = "https://auth.example.com"
CHAIN_ID = make_chain_id(56)


def _make_signed_message(*, statement=None, expiration_time=None):
    """Create a fresh account, build+sign a SIWE message, return fields."""
    acct = Account.create()
    address = make_address(acct.address)
    svc = SigninWithEthereumSiweService()
    issued_at = format_iso8601(1_700_000_000.0)
    message = svc.build_message(
        domain=DOMAIN,
        address=address,
        uri=URI,
        chain_id=CHAIN_ID,
        nonce="a" * 32,
        issued_at=issued_at,
        statement=statement,
        expiration_time=expiration_time,
    )
    signed = acct.sign_message(encode_defunct(text=message))
    return svc, address, message, signed.signature.hex()


def test_build_message_contains_expected_fields():
    acct = Account.create()
    svc = SigninWithEthereumSiweService()
    msg = svc.build_message(
        domain=DOMAIN,
        address=make_address(acct.address),
        uri=URI,
        chain_id=CHAIN_ID,
        nonce="a" * 32,
        issued_at=format_iso8601(1_700_000_000.0),
    )
    assert msg.startswith(f"{DOMAIN} wants you to sign in with your Ethereum account:")
    assert acct.address.lower() in msg.lower()
    assert f"Chain ID: {CHAIN_ID}" in msg
    assert "Nonce: " + "a" * 32 in msg


def test_build_message_includes_statement_when_provided():
    acct = Account.create()
    svc = SigninWithEthereumSiweService()
    msg = svc.build_message(
        domain=DOMAIN,
        address=make_address(acct.address),
        uri=URI,
        chain_id=CHAIN_ID,
        nonce="a" * 32,
        issued_at=format_iso8601(1_700_000_000.0),
        statement="Sign in to MyDApp",
    )
    assert "Sign in to MyDApp" in msg


def test_verify_recovers_signer():
    svc, address, message, signature = _make_signed_message()
    recovered = svc.verify(message=message, signature="0x" + signature)
    assert recovered == address


def test_verify_rejects_tampered_message():
    svc, _, message, signature = _make_signed_message()
    tampered = message.replace("Nonce: " + "a" * 32, "Nonce: " + "b" * 32)
    with pytest.raises(SignatureVerificationFailed):
        svc.verify(message=tampered, signature="0x" + signature)


def test_verify_rejects_wrong_signature():
    _, _, message, _ = _make_signed_message()
    _, _, _, other_sig = _make_signed_message()
    svc = SigninWithEthereumSiweService()
    with pytest.raises(SignatureVerificationFailed):
        svc.verify(message=message, signature="0x" + other_sig)


def test_verify_rejects_garbage_message():
    svc = SigninWithEthereumSiweService()
    with pytest.raises(SignatureVerificationFailed):
        svc.verify(message="not a siwe message", signature="0x" + "00" * 65)


def test_verify_rejects_expired_message():
    acct = Account.create()
    svc = SigninWithEthereumSiweService()
    # Expiration in the past relative to real wall clock.
    message = svc.build_message(
        domain=DOMAIN,
        address=make_address(acct.address),
        uri=URI,
        chain_id=CHAIN_ID,
        nonce="a" * 32,
        issued_at=format_iso8601(1_600_000_000.0),
        expiration_time=format_iso8601(1_600_000_060.0),
    )
    signed = acct.sign_message(encode_defunct(text=message))
    with pytest.raises(SignatureVerificationFailed):
        svc.verify(message=message, signature="0x" + signed.signature.hex())
