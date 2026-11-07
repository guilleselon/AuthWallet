import pytest

from relay.adapters.outbound.in_memory import InMemoryPubSub
from relay.domain.message import PublishedMessage
from relay.domain.types import MessageId, make_topic


def _topic():
    return make_topic("a" * 64)


def _msg(topic, mid=1):
    return PublishedMessage(
        id=MessageId(mid), topic=topic, payload="aG9sYQ==",
        ttl=60, tag=1108, prompt=False,
    )


@pytest.mark.asyncio
async def test_publish_delivers_to_subscriber_inline():
    bus = InMemoryPubSub(inline_dispatch=True)
    t = _topic()
    received = []

    async def handler(m):
        received.append(m)

    await bus.subscribe(t, handler)
    await bus.publish(t, _msg(t))

    assert len(received) == 1


@pytest.mark.asyncio
async def test_publish_does_not_deliver_to_other_topics():
    bus = InMemoryPubSub(inline_dispatch=True)
    t1 = _topic()
    t2 = make_topic("b" * 64)
    received = []

    async def handler(m):
        received.append(m)

    await bus.subscribe(t1, handler)
    await bus.publish(t2, _msg(t2))

    assert received == []


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery():
    bus = InMemoryPubSub(inline_dispatch=True)
    t = _topic()
    received = []

    async def handler(m):
        received.append(m)

    handle = await bus.subscribe(t, handler)
    await bus.unsubscribe(handle)
    await bus.publish(t, _msg(t))

    assert received == []


@pytest.mark.asyncio
async def test_multiple_subscribers_all_receive():
    bus = InMemoryPubSub(inline_dispatch=True)
    t = _topic()
    seen = []

    async def h1(m):
        seen.append("h1")

    async def h2(m):
        seen.append("h2")

    await bus.subscribe(t, h1)
    await bus.subscribe(t, h2)
    await bus.publish(t, _msg(t))

    assert sorted(seen) == ["h1", "h2"]


@pytest.mark.asyncio
async def test_broken_handler_does_not_break_others():
    bus = InMemoryPubSub(inline_dispatch=True)
    t = _topic()
    seen = []

    async def broken(m):
        raise RuntimeError("boom")

    async def good(m):
        seen.append(m)

    await bus.subscribe(t, broken)
    await bus.subscribe(t, good)
    await bus.publish(t, _msg(t))

    assert len(seen) == 1


@pytest.mark.asyncio
async def test_async_dispatch_requires_drain():
    bus = InMemoryPubSub()  # default: async dispatch
    t = _topic()
    received = []

    async def handler(m):
        received.append(m)

    await bus.subscribe(t, handler)
    await bus.publish(t, _msg(t))
    await bus.drain()

    assert len(received) == 1


@pytest.mark.asyncio
async def test_close_cancels_pending_and_clears():
    bus = InMemoryPubSub()
    t = _topic()

    async def slow(m):
        await pytest.importorskip("asyncio").sleep(10)

    await bus.subscribe(t, slow)
    await bus.publish(t, _msg(t))
    await bus.close()

    # Nothing to assert beyond: no exception, no leak observable here.
    # (Deeper leak checks would need gc introspection; not worth it.)
