import pytest

from relay.domain.message import PublishedMessage
from relay.domain.types import make_topic
from relay.service import SubscriptionRegistry

from ._fakes import FakeConnectionManager, FakePubSub


def _topic():
    return make_topic("a" * 64)


def _registry():
    conn = FakeConnectionManager()
    bus = FakePubSub()
    reg = SubscriptionRegistry(conn, bus, build_notification=lambda m: m.payload)
    return reg, conn, bus


@pytest.mark.asyncio
async def test_first_subscriber_triggers_bus_subscription():
    reg, conn, bus = _registry()
    await conn.register("c1", sender=lambda s: None)
    topic = _topic()

    await reg.subscribe("c1", topic)

    assert await reg.local_subscriber_count(topic) == 1
    assert len(bus._handlers) == 1


@pytest.mark.asyncio
async def test_second_subscriber_does_not_duplicate_bus_subscription():
    reg, conn, bus = _registry()
    await conn.register("c1", sender=lambda s: None)
    await conn.register("c2", sender=lambda s: None)
    topic = _topic()

    await reg.subscribe("c1", topic)
    await reg.subscribe("c2", topic)

    assert await reg.local_subscriber_count(topic) == 2
    assert len(bus._handlers) == 1


@pytest.mark.asyncio
async def test_last_unsubscribe_drops_bus_subscription():
    reg, conn, bus = _registry()
    await conn.register("c1", sender=lambda s: None)
    topic = _topic()

    await reg.subscribe("c1", topic)
    await reg.unsubscribe("c1", topic)

    assert await reg.local_subscriber_count(topic) == 0
    assert len(bus._handlers) == 0


@pytest.mark.asyncio
async def test_message_from_bus_is_broadcast_to_local_subscribers():
    reg, conn, bus = _registry()
    await conn.register("c1", sender=lambda s: None)
    await conn.register("c2", sender=lambda s: None)
    topic = _topic()
    await reg.subscribe("c1", topic)

    msg = PublishedMessage(id=1, topic=topic, payload="aG9sYQ==", ttl=60, tag=1108, prompt=False)
    await bus.publish(topic, msg)

    assert ("c1", "aG9sYQ==") in conn.sent
    assert ("c2", "aG9sYQ==") not in conn.sent  # c2 not subscribed


@pytest.mark.asyncio
async def test_unknown_connection_raises_before_touching_bus():
    reg, conn, bus = _registry()
    topic = _topic()
    with pytest.raises(ValueError):
        await reg.subscribe("ghost", topic)
    assert len(bus._handlers) == 0
