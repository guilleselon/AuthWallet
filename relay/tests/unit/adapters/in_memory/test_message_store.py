import pytest

from relay.adapters.outbound.in_memory import InMemoryMessageStore
from relay.domain.message import PublishedMessage
from relay.domain.types import MessageId, make_topic


def _topic():
    return make_topic("a" * 64)


def _msg(topic, mid, ttl=60):
    return PublishedMessage(
        id=MessageId(mid), topic=topic, payload="aG9sYQ==",
        ttl=ttl, tag=1108, prompt=False,
    )


def _clock(start=0.0):
    """Fake clock: returns start and advances by .advance(n)."""
    state = {"t": start}
    def now():
        return state["t"]
    def advance(n):
        state["t"] += n
    return now, advance


@pytest.mark.asyncio
async def test_add_and_get():
    store = InMemoryMessageStore()
    t = _topic()
    await store.add(_msg(t, 1))
    assert (await store.get(t, 1)).id == 1


@pytest.mark.asyncio
async def test_add_rejects_duplicate_id():
    store = InMemoryMessageStore()
    t = _topic()
    await store.add(_msg(t, 1))
    with pytest.raises(ValueError, match="duplicate"):
        await store.add(_msg(t, 1))


@pytest.mark.asyncio
async def test_fetch_returns_only_after_id_in_order():
    store = InMemoryMessageStore()
    t = _topic()
    for i in (3, 1, 2):
        await store.add(_msg(t, i))
    result = await store.fetch(t, after_id=1, limit=10)
    assert [m.id for m in result] == [2, 3]


@pytest.mark.asyncio
async def test_fetch_respects_limit():
    store = InMemoryMessageStore()
    t = _topic()
    for i in range(1, 11):
        await store.add(_msg(t, i))
    result = await store.fetch(t, after_id=0, limit=3)
    assert [m.id for m in result] == [1, 2, 3]


@pytest.mark.asyncio
async def test_delete_returns_bool():
    store = InMemoryMessageStore()
    t = _topic()
    await store.add(_msg(t, 1))
    assert await store.delete(t, 1) is True
    assert await store.delete(t, 1) is False


@pytest.mark.asyncio
async def test_count_excludes_expired():
    now, advance = _clock()
    store = InMemoryMessageStore(clock=now)
    t = _topic()
    await store.add(_msg(t, 1, ttl=10))
    await store.add(_msg(t, 2, ttl=100))
    advance(20)  # msg 1 expires, msg 2 still valid
    assert await store.count(t) == 1


@pytest.mark.asyncio
async def test_get_returns_none_for_expired():
    now, advance = _clock()
    store = InMemoryMessageStore(clock=now)
    t = _topic()
    await store.add(_msg(t, 1, ttl=10))
    advance(11)
    assert await store.get(t, 1) is None


@pytest.mark.asyncio
async def test_fetch_skips_expired():
    now, advance = _clock()
    store = InMemoryMessageStore(clock=now)
    t = _topic()
    await store.add(_msg(t, 1, ttl=5))
    await store.add(_msg(t, 2, ttl=100))
    advance(10)
    result = await store.fetch(t, after_id=0, limit=10)
    assert [m.id for m in result] == [2]


@pytest.mark.asyncio
async def test_sweep_removes_expired_and_returns_count():
    now, advance = _clock()
    store = InMemoryMessageStore(clock=now)
    t = _topic()
    await store.add(_msg(t, 1, ttl=5))
    await store.add(_msg(t, 2, ttl=100))
    advance(10)
    removed = await store.sweep()
    assert removed == 1
    # Only msg 2 remains, even without filtering.
    assert await store.count(t) == 1
