import pytest

from relay.domain.message import PublishedMessage
from relay.domain.types import ConnectionId, MessageId, make_topic
from relay.protocol import Request


def _topic():
    return make_topic("a" * 64)


async def _call(services, ctx, method, params, req_id=1):
    return await services["dispatcher"].dispatch(
        Request(method=method, params=params, id=req_id),
        ctx,
    )


@pytest.mark.asyncio
async def test_publish_persists_and_returns_id(services, ctx):
    t = _topic()
    resp = await _call(services, ctx, "irn_publish", {
        "topic": t, "payload": "aG9sYQ==", "ttl": 60, "tag": 1108,
    })
    assert resp.error is None
    assert resp.result == {"id": 1}
    assert await services["store"].count(t) == 1


@pytest.mark.asyncio
async def test_publish_invalid_payload_raises_invalid_params(services, ctx):
    t = _topic()
    resp = await _call(services, ctx, "irn_publish", {
        "topic": t, "payload": "not-base64!!!", "ttl": 60, "tag": 1108,
    })
    assert resp.error.code == -32602


@pytest.mark.asyncio
async def test_subscribe_registers_connection(services, ctx):
    t = _topic()
    await services["conn"].register(ctx.connection_id, sender=lambda s: _done())
    resp = await _call(services, ctx, "irn_subscribe", {"topic": t})
    assert resp.error is None
    assert await services["conn"].subscribers(t) == frozenset({ctx.connection_id})


async def _done():
    return None


@pytest.mark.asyncio
async def test_unsubscribe_removes_connection(services, ctx):
    t = _topic()
    await services["conn"].register(ctx.connection_id, sender=lambda s: _done())
    await _call(services, ctx, "irn_subscribe", {"topic": t})
    resp = await _call(services, ctx, "irn_unsubscribe", {"topic": t})
    assert resp.error is None
    assert await services["conn"].subscribers(t) == frozenset()


@pytest.mark.asyncio
async def test_batch_publish_returns_ids(services, ctx):
    t1 = _topic()
    t2 = make_topic("b" * 64)
    resp = await _call(services, ctx, "irn_batchPublish", {
        "messages": [
            {"topic": t1, "payload": "aG9sYQ==", "ttl": 60, "tag": 1108},
            {"topic": t2, "payload": "aG9sYQ==", "ttl": 60, "tag": 1108},
        ],
    })
    assert resp.result == {"ids": [1, 2]}


@pytest.mark.asyncio
async def test_batch_publish_aborts_on_bad_entry(services, ctx):
    t = _topic()
    resp = await _call(services, ctx, "irn_batchPublish", {
        "messages": [
            {"topic": t, "payload": "aG9sYQ==", "ttl": 60, "tag": 1108},
            {"topic": t, "payload": "BAD", "ttl": 60, "tag": 1108},
        ],
    })
    assert resp.error.code == -32602
    # Nothing was published: first message rolled back.
    assert await services["store"].count(t) == 0


@pytest.mark.asyncio
async def test_batch_subscribe(services, ctx):
    t1 = _topic()
    t2 = make_topic("b" * 64)
    await services["conn"].register(ctx.connection_id, sender=lambda s: _done())
    resp = await _call(services, ctx, "irn_batchSubscribe", {"topics": [t1, t2]})
    assert resp.result == {"ids": [t1, t2]}
    assert await services["conn"].subscribers(t1) == frozenset({ctx.connection_id})
    assert await services["conn"].subscribers(t2) == frozenset({ctx.connection_id})


@pytest.mark.asyncio
async def test_batch_fetch_returns_messages_after_id(services, ctx):
    t = _topic()
    for _ in range(3):
        await _call(services, ctx, "irn_publish", {
            "topic": t, "payload": "aG9sYQ==", "ttl": 60, "tag": 1108,
        })
    resp = await _call(services, ctx, "irn_batchFetch", {
        "topic": t, "after": 1, "limit": 10,
    })
    assert [m["id"] for m in resp.result["messages"]] == [2, 3]


@pytest.mark.asyncio
async def test_acknowledge_records(services, ctx):
    t = _topic()
    await _call(services, ctx, "irn_publish", {
        "topic": t, "payload": "aG9sYQ==", "ttl": 60, "tag": 1108,
    })
    resp = await _call(services, ctx, "irn_acknowledge", {"topic": t, "id": 1})
    assert resp.result is True
    assert services["acks"].has_acked(ctx.connection_id, t, MessageId(1))
