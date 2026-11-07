import pytest

from relay.adapters.outbound.in_memory import InMemoryConnectionManager
from relay.domain.types import ConnectionId, make_topic


def _topic():
    return make_topic("a" * 64)


def _cid(name):
    return ConnectionId(name)


def _recorder():
    """Returns (sender_callable, list_of_strings)."""
    received: list[str] = []
    async def sender(payload: str) -> None:
        received.append(payload)
    return sender, received


@pytest.mark.asyncio
async def test_register_and_is_registered():
    cm = InMemoryConnectionManager()
    sender, _ = _recorder()
    await cm.register(_cid("c1"), sender)
    assert await cm.is_registered(_cid("c1"))
    assert not await cm.is_registered(_cid("c2"))


@pytest.mark.asyncio
async def test_register_duplicate_raises():
    cm = InMemoryConnectionManager()
    sender, _ = _recorder()
    await cm.register(_cid("c1"), sender)
    with pytest.raises(ValueError):
        await cm.register(_cid("c1"), sender)


@pytest.mark.asyncio
async def test_send_to_unknown_raises():
    cm = InMemoryConnectionManager()
    with pytest.raises(ValueError):
        await cm.send_to(_cid("ghost"), "x")


@pytest.mark.asyncio
async def test_send_to_delivers_payload():
    cm = InMemoryConnectionManager()
    sender, received = _recorder()
    await cm.register(_cid("c1"), sender)
    await cm.send_to(_cid("c1"), "hello")
    assert received == ["hello"]


@pytest.mark.asyncio
async def test_subscribe_unknown_raises():
    cm = InMemoryConnectionManager()
    with pytest.raises(ValueError):
        await cm.subscribe(_cid("ghost"), _topic())


@pytest.mark.asyncio
async def test_broadcast_only_to_subscribers():
    cm = InMemoryConnectionManager()
    s1, r1 = _recorder()
    s2, r2 = _recorder()
    t = _topic()
    await cm.register(_cid("c1"), s1)
    await cm.register(_cid("c2"), s2)
    await cm.subscribe(_cid("c1"), t)

    count = await cm.broadcast(t, "x")

    assert count == 1
    assert r1 == ["x"]
    assert r2 == []


@pytest.mark.asyncio
async def test_broadcast_counts_only_successes():
    cm = InMemoryConnectionManager()
    good, _ = _recorder()
    async def bad(payload): raise RuntimeError("boom")
    t = _topic()
    await cm.register(_cid("good"), good)
    await cm.register(_cid("bad"), bad)
    await cm.subscribe(_cid("good"), t)
    await cm.subscribe(_cid("bad"), t)

    count = await cm.broadcast(t, "x")

    assert count == 1  # only the good one counted


@pytest.mark.asyncio
async def test_unregister_clears_subscriptions():
    cm = InMemoryConnectionManager()
    sender, _ = _recorder()
    t = _topic()
    await cm.register(_cid("c1"), sender)
    await cm.subscribe(_cid("c1"), t)

    await cm.unregister(_cid("c1"))

    assert await cm.subscribers(t) == frozenset()
    assert not await cm.is_registered(_cid("c1"))


@pytest.mark.asyncio
async def test_subscribers_returns_frozenset():
    cm = InMemoryConnectionManager()
    sender, _ = _recorder()
    t = _topic()
    await cm.register(_cid("c1"), sender)
    await cm.subscribe(_cid("c1"), t)
    subs = await cm.subscribers(t)
    assert subs == frozenset({_cid("c1")})
    assert isinstance(subs, frozenset)
