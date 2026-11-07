import pytest

from auth_service.domain.errors import SessionNotFound
from auth_service.domain.session import Session
from auth_service.domain.types import (
    make_address,
    make_chain_id,
    make_session_id,
    make_session_id_fresh,
)
from auth_service.service import ManageSession

from ._fakes import FakeClock, FakeSessionStore


def _session(*, created=1000.0, expires=2000.0) -> Session:
    return Session(
        id=make_session_id_fresh(),
        address=make_address("0x" + "a" * 40),
        chain_id=make_chain_id(56),
        created_at=created,
        expires_at=expires,
    )


@pytest.mark.asyncio
async def test_get_returns_existing_session():
    clock = FakeClock(start=1500.0)
    store = FakeSessionStore(clock)
    svc = ManageSession(session_store=store)
    s = _session(created=1000.0, expires=2000.0)
    await store.create(s)

    assert await svc.get(s.id) == s


@pytest.mark.asyncio
async def test_get_missing_raises():
    store = FakeSessionStore(FakeClock())
    svc = ManageSession(session_store=store)
    with pytest.raises(SessionNotFound):
        await svc.get(make_session_id("0" * 32))


@pytest.mark.asyncio
async def test_get_expired_raises():
    clock = FakeClock(start=2500.0)  # after expiry
    store = FakeSessionStore(clock)
    svc = ManageSession(session_store=store)
    s = _session(created=1000.0, expires=2000.0)
    await store.create(s)

    with pytest.raises(SessionNotFound):
        await svc.get(s.id)


@pytest.mark.asyncio
async def test_logout_returns_true_when_existed():
    clock = FakeClock(start=1500.0)
    store = FakeSessionStore(clock)
    svc = ManageSession(session_store=store)
    s = _session()
    await store.create(s)

    assert await svc.logout(s.id) is True
    assert await store.get(s.id) is None


@pytest.mark.asyncio
async def test_logout_is_idempotent():
    clock = FakeClock(start=1500.0)
    store = FakeSessionStore(clock)
    svc = ManageSession(session_store=store)
    s = _session()
    await store.create(s)

    assert await svc.logout(s.id) is True
    assert await svc.logout(s.id) is False
