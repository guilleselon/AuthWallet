import pytest

from auth_service.adapters.outbound.in_memory import InMemorySessionStore
from auth_service.domain.session import Session
from auth_service.domain.types import (
    make_address,
    make_chain_id,
    make_session_id_fresh,
)


def _session(*, created=1000.0, expires=2000.0) -> Session:
    return Session(
        id=make_session_id_fresh(),
        address=make_address("0x" + "a" * 40),
        chain_id=make_chain_id(56),
        created_at=created,
        expires_at=expires,
    )


def _store():
    state = {"t": 1500.0}
    def clock():
        return state["t"]
    def advance(n):
        state["t"] += n
    return InMemorySessionStore(clock=clock), advance


@pytest.mark.asyncio
async def test_create_and_get():
    store, _ = _store()
    s = _session()
    await store.create(s)
    assert await store.get(s.id) == s


@pytest.mark.asyncio
async def test_get_returns_none_after_expiry():
    store, advance = _store()
    s = _session(created=1000.0, expires=2000.0)
    await store.create(s)
    advance(1001.0)  # now = 2501.0
    assert await store.get(s.id) is None


@pytest.mark.asyncio
async def test_get_returns_none_for_unknown():
    store, _ = _store()
    assert await store.get(make_session_id_fresh()) is None


@pytest.mark.asyncio
async def test_delete_returns_bool():
    store, _ = _store()
    s = _session()
    await store.create(s)
    assert await store.delete(s.id) is True
    assert await store.delete(s.id) is False


@pytest.mark.asyncio
async def test_create_rejects_pre_expired_session():
    store, _ = _store()
    s = _session(created=2000.0, expires=1000.0)
    with pytest.raises(ValueError):
        await store.create(s)


@pytest.mark.asyncio
async def test_create_rejects_duplicate_id():
    store, _ = _store()
    s = _session()
    await store.create(s)
    with pytest.raises(ValueError):
        await store.create(s)


@pytest.mark.asyncio
async def test_sweep_removes_expired():
    store, advance = _store()
    live = _session(created=1000.0, expires=5000.0)
    dead = _session(created=1000.0, expires=1200.0)
    await store.create(live)
    await store.create(dead)
    advance(600.0)  # now = 2100.0, dead is expired, live is not
    removed = await store.sweep()
    assert removed == 1
    assert await store.get(live.id) == live
    assert await store.get(dead.id) is None
