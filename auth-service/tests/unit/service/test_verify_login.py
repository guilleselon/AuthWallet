import pytest

from auth_service.domain.errors import (
    NonceNotFound,
    SignatureVerificationFailed,
)
from auth_service.domain.siwe import format_iso8601
from auth_service.domain.types import (
    make_address,
    make_chain_id,
    make_nonce_fresh,
)
from auth_service.service import VerifyLogin

from ._fakes import (
    FakeClock,
    FakeNonceStore,
    FakeSessionStore,
    FakeSiweService,
    make_siwe_message,
)


DOMAIN = "auth.example.com"
CHAIN_ID = make_chain_id(56)
URI = "https://auth.example.com"
ADDRESS = make_address("0x" + "a" * 40)


def _make(*, session_ttl=86400, max_age=600):
    clock = FakeClock()
    nonces = FakeNonceStore(clock)
    sessions = FakeSessionStore(clock)
    siwe = FakeSiweService()
    svc = VerifyLogin(
        nonce_store=nonces,
        session_store=sessions,
        siwe=siwe,
        clock=clock,
        expected_domain=DOMAIN,
        expected_chain_id=CHAIN_ID,
        session_ttl_seconds=session_ttl,
        max_message_age_seconds=max_age,
    )
    return svc, nonces, sessions, siwe, clock


async def _issue_nonce(nonces, clock, *, ttl=300):
    nonce = make_nonce_fresh()
    await nonces.put(nonce, ttl)
    message = make_siwe_message(
        domain=DOMAIN, address=ADDRESS, uri=URI, chain_id=CHAIN_ID,
        nonce=nonce, issued_at=format_iso8601(clock.now()),
        expiration_time=format_iso8601(clock.now() + ttl),
    )
    return nonce, message


@pytest.mark.asyncio
async def test_happy_path_creates_session():
    svc, nonces, sessions, siwe, clock = _make()
    nonce, message = await _issue_nonce(nonces, clock)

    session = await svc.verify(message=message, signature="0xfake")

    assert session.address == ADDRESS
    assert session.chain_id == CHAIN_ID
    assert await sessions.get(session.id) == session
    assert siwe.build_calls == []  # verify does not build


@pytest.mark.asyncio
async def test_consumes_nonce_once():
    svc, nonces, _, _, clock = _make()
    _, message = await _issue_nonce(nonces, clock)

    await svc.verify(message=message, signature="0xfake")
    with pytest.raises(NonceNotFound):
        await svc.verify(message=message, signature="0xfake")


@pytest.mark.asyncio
async def test_unknown_nonce_raises():
    svc, _, _, _, clock = _make()
    message = make_siwe_message(
        domain=DOMAIN, address=ADDRESS, uri=URI, chain_id=CHAIN_ID,
        nonce=make_nonce_fresh(),
        issued_at=format_iso8601(clock.now()),
    )
    with pytest.raises(NonceNotFound):
        await svc.verify(message=message, signature="0xfake")


@pytest.mark.asyncio
async def test_wrong_domain_raises():
    svc, nonces, _, _, clock = _make()
    nonce = make_nonce_fresh()
    await nonces.put(nonce, 300)
    message = make_siwe_message(
        domain="evil.example.com", address=ADDRESS, uri=URI,
        chain_id=CHAIN_ID, nonce=nonce,
        issued_at=format_iso8601(clock.now()),
    )
    with pytest.raises(SignatureVerificationFailed, match="domain"):
        await svc.verify(message=message, signature="0xfake")


@pytest.mark.asyncio
async def test_wrong_chain_raises():
    svc, nonces, _, _, clock = _make()
    nonce = make_nonce_fresh()
    await nonces.put(nonce, 300)
    message = make_siwe_message(
        domain=DOMAIN, address=ADDRESS, uri=URI,
        chain_id=make_chain_id(1), nonce=nonce,
        issued_at=format_iso8601(clock.now()),
    )
    with pytest.raises(SignatureVerificationFailed, match="chain"):
        await svc.verify(message=message, signature="0xfake")


@pytest.mark.asyncio
async def test_signature_failure_propagates():
    svc, nonces, _, siwe, clock = _make()
    _, message = await _issue_nonce(nonces, clock)
    siwe.verify_error = SignatureVerificationFailed("bad sig")
    with pytest.raises(SignatureVerificationFailed, match="bad sig"):
        await svc.verify(message=message, signature="0xfake")


@pytest.mark.asyncio
async def test_recovered_address_mismatch_raises():
    svc, nonces, _, siwe, clock = _make()
    _, message = await _issue_nonce(nonces, clock)
    siwe.recovered_address = make_address("0x" + "b" * 40)
    with pytest.raises(SignatureVerificationFailed, match="recovered"):
        await svc.verify(message=message, signature="0xfake")


@pytest.mark.asyncio
async def test_issued_at_in_future_raises():
    svc, nonces, _, _, clock = _make()
    nonce = make_nonce_fresh()
    await nonces.put(nonce, 300)
    future = format_iso8601(clock.now() + 120)
    message = make_siwe_message(
        domain=DOMAIN, address=ADDRESS, uri=URI, chain_id=CHAIN_ID,
        nonce=nonce, issued_at=future,
    )
    with pytest.raises(SignatureVerificationFailed, match="future"):
        await svc.verify(message=message, signature="0xfake")


@pytest.mark.asyncio
async def test_issued_at_too_old_raises():
    svc, nonces, _, _, clock = _make(max_age=60)
    nonce = make_nonce_fresh()
    await nonces.put(nonce, 300)
    old = format_iso8601(clock.now() - 120)
    message = make_siwe_message(
        domain=DOMAIN, address=ADDRESS, uri=URI, chain_id=CHAIN_ID,
        nonce=nonce, issued_at=old,
    )
    with pytest.raises(SignatureVerificationFailed, match="too old"):
        await svc.verify(message=message, signature="0xfake")


def test_rejects_non_positive_session_ttl():
    with pytest.raises(ValueError):
        VerifyLogin(
            nonce_store=FakeNonceStore(FakeClock()),
            session_store=FakeSessionStore(FakeClock()),
            siwe=FakeSiweService(),
            clock=FakeClock(),
            expected_domain=DOMAIN,
            expected_chain_id=CHAIN_ID,
            session_ttl_seconds=0,
        )
