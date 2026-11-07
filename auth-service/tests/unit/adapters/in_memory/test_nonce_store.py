import pytest

from auth_service.adapters.outbound.in_memory import InMemoryNonceStore
from auth_service.domain.types import make_nonce_fresh


def _store():
    state = {"t": 1000.0}
    def clock():
        return state["t"]
    def advance(n):
        state["t"] += n
    return InMemoryNonceStore(clock=clock), advance


@pytest.mark.asyncio
async def test_put_and_consume():
    store, _ = _store()
    n = make_nonce_fresh()
    await store.put(n, 60)
    assert await store.consume(n) is True
    assert await store.consume(n) is False


@pytest.mark.asyncio
async def test_consume_unknown_returns_false():
    store, _ = _store()
    assert await store.consume(make_nonce_fresh()) is False


@pytest.mark.asyncio
async def test_expired_nonce_cannot_be_consumed():
    store, advance = _store()
    n = make_nonce_fresh()
    await store.put(n, 10)
    advance(11)
    assert await store.consume(n) is False


@pytest.mark.asyncio
async def test_ttl_remaining_decreases():
    store, advance = _store()
    n = make_nonce_fresh()
    await store.put(n, 60)
    assert await store.ttl_remaining(n) == 60
    advance(20)
    assert await store.ttl_remaining(n) == 40


@pytest.mark.asyncio
async def test_ttl_remaining_none_for_unknown():
    store, _ = _store()
    assert await store.ttl_remaining(make_nonce_fresh()) is None


@pytest.mark.asyncio
async def test_put_rejects_non_positive_ttl():
    store, _ = _store()
    with pytest.raises(ValueError):
        await store.put(make_nonce_fresh(), 0)
