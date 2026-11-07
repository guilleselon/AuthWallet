import itertools

import pytest

from relay.domain.message import PublishRequest
from relay.domain.types import make_payload, make_tag, make_topic, make_ttl
from relay.service import AckTracker, MessageRouter, SubscriptionRegistry

from ._fakes import FakeConnectionManager, FakeMessageStore, FakePubSub


def _topic():
    return make_topic("a" * 64)


def _router():
    store = FakeMessageStore()
    bus = FakePubSub()
    conn = FakeConnectionManager()
    reg = SubscriptionRegistry(conn, bus, build_notification=lambda m: m.payload)
    acks = AckTracker()
    counter = itertools.count(1)
    router = MessageRouter(store, bus, reg, acks, next_id=lambda: next(counter))
    return router, store, bus, conn, acks


def _request(topic, payload="aG9sYQ==", ttl=60, tag=1108):
    return PublishRequest(
        topic=topic,
        payload=make_payload(payload),
        ttl=make_ttl(ttl),
        tag=make_tag(tag),
        prompt=False,
    )


@pytest.mark.asyncio
async def test_publish_persists_then_distributes():
    router, store, bus, _, _ = _router()
    topic = _topic()

    msg = await router.publish(_request(topic))

    assert msg.id == 1
    assert await store.count(topic) == 1
    assert len(bus.published) == 1
    assert bus.published[0][1].id == 1


@pytest.mark.asyncio
async def test_publish_ids_are_monotonic():
    router, _, _, _, _ = _router()
    topic = _topic()

    m1 = await router.publish(_request(topic))
    m2 = await router.publish(_request(topic))
    m3 = await router.publish(_request(topic))

    assert (m1.id, m2.id, m3.id) == (1, 2, 3)


@pytest.mark.asyncio
async def test_fetch_returns_messages_after_id():
    router, _, _, _, _ = _router()
    topic = _topic()
    await router.publish(_request(topic))
    await router.publish(_request(topic))
    await router.publish(_request(topic))

    results = await router.fetch(topic, after_id=1, limit=10)

    assert [m.id for m in results] == [2, 3]


@pytest.mark.asyncio
async def test_fetch_with_non_positive_limit_returns_empty():
    router, _, _, _, _ = _router()
    topic = _topic()
    await router.publish(_request(topic))

    assert await router.fetch(topic, after_id=0, limit=0) == []
    assert await router.fetch(topic, after_id=0, limit=-1) == []


@pytest.mark.asyncio
async def test_subscribe_and_unsubscribe_delegate_to_registry():
    router, _, _, conn, _ = _router()
    await conn.register("c1", sender=lambda s: None)
    topic = _topic()

    await router.subscribe("c1", topic)
    assert await conn.subscribers(topic) == frozenset({"c1"})

    await router.unsubscribe("c1", topic)
    assert await conn.subscribers(topic) == frozenset()


@pytest.mark.asyncio
async def test_acknowledge_records_in_tracker():
    router, _, _, _, acks = _router()
    topic = _topic()

    await router.acknowledge("c1", topic, 1)

    assert acks.has_acked("c1", topic, 1)
    assert not acks.has_acked("c2", topic, 1)
