import json

import pytest

from relay.adapters.inbound.websocket import (
    ConnectionHandler,
    parse_token_from_path,
)
from relay.domain.types import ConnectionId, MessageId, make_topic
from relay.protocol import Dispatcher, Request
from relay.adapters.outbound.in_memory import InMemoryRateLimiter


def _topic():
    return make_topic("a" * 64)


def _handler(services, project_id, incoming):
    conn_id = ConnectionId("conn-1")
    handler = ConnectionHandler(
        connection_id=conn_id,
        project_id=project_id,
        dispatcher=services["dispatcher"],
        connection_manager=services["conn"],
        ack_tracker=services["acks"],
    )
    ws = __import__("tests.unit.adapters.inbound.websocket.conftest",
                    fromlist=["FakeWebSocket"]).FakeWebSocket(incoming)
    return handler, ws, conn_id


# --- parse_token_from_path (pure function) ---

@pytest.mark.parametrize("path,expected", [
    ("/?token=abc", "abc"),
    ("/?token=abc&foo=bar", "abc"),
    ("/?foo=bar&token=xyz", "xyz"),
    ("/?token=", ""),
    ("/", None),
    ("/?foo=bar", None),
    ("/?token=a&token=b", "a"),  # first wins
])
def test_parse_token_from_path(path, expected):
    assert parse_token_from_path(path) == expected


# --- ConnectionHandler ---

@pytest.mark.asyncio
async def test_publish_roundtrip(services, project_id):
    handler, ws, conn_id = _handler(services, project_id, [
        json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "irn_publish",
            "params": {
                "topic": _topic(), "payload": "aG9sYQ==",
                "ttl": 60, "tag": 1108,
            },
        }),
    ])
    await handler.run(ws)

    assert len(ws.sent) == 1
    response = json.loads(ws.sent[0])
    assert response["id"] == 1
    assert response["result"] == {"id": 1}


@pytest.mark.asyncio
async def test_notification_gets_no_response(services, project_id):
    # No "id" → notification → no response, but side-effect happens.
    handler, ws, _ = _handler(services, project_id, [
        json.dumps({
            "jsonrpc": "2.0", "method": "irn_publish",
            "params": {
                "topic": _topic(), "payload": "aG9sYQ==",
                "ttl": 60, "tag": 1108,
            },
        }),
    ])
    await handler.run(ws)

    assert ws.sent == []
    assert await services["store"].count(_topic()) == 1


@pytest.mark.asyncio
async def test_invalid_json_yields_parse_error(services, project_id):
    handler, ws, _ = _handler(services, project_id, ["not json"])
    await handler.run(ws)

    response = json.loads(ws.sent[0])
    assert response["error"]["code"] == -32700


@pytest.mark.asyncio
async def test_invalid_request_structure_yields_invalid_request(
    services, project_id
):
    handler, ws, _ = _handler(services, project_id, [
        json.dumps({"jsonrpc": "1.0", "id": 1, "method": "x"}),
    ])
    await handler.run(ws)

    response = json.loads(ws.sent[0])
    assert response["error"]["code"] == -32600


@pytest.mark.asyncio
async def test_unknown_method_yields_method_not_found(services, project_id):
    handler, ws, _ = _handler(services, project_id, [
        json.dumps({"jsonrpc": "2.0", "id": 5, "method": "nope", "params": {}}),
    ])
    await handler.run(ws)

    response = json.loads(ws.sent[0])
    assert response["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_domain_error_propagates_as_error_response(
    services, project_id
):
    handler, ws, _ = _handler(services, project_id, [
        json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "irn_publish",
            "params": {  # missing fields
                "topic": _topic(), "payload": "not-base64!!!",
                "ttl": 60, "tag": 1108,
            },
        }),
    ])
    await handler.run(ws)

    response = json.loads(ws.sent[0])
    assert response["error"]["code"] == -32602


@pytest.mark.asyncio
async def test_multiple_requests_in_sequence(services, project_id):
    handler, ws, _ = _handler(services, project_id, [
        json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "irn_publish",
            "params": {"topic": _topic(), "payload": "aG9sYQ==",
                       "ttl": 60, "tag": 1108},
        }),
        json.dumps({
            "jsonrpc": "2.0", "id": 2, "method": "irn_publish",
            "params": {"topic": _topic(), "payload": "aG9sYQ==",
                       "ttl": 60, "tag": 1108},
        }),
    ])
    await handler.run(ws)

    ids = [json.loads(s)["id"] for s in ws.sent]
    assert ids == [1, 2]


@pytest.mark.asyncio
async def test_connection_unregistered_on_exit(services, project_id):
    handler, ws, conn_id = _handler(services, project_id, [])
    await handler.run(ws)

    assert not await services["conn"].is_registered(conn_id)


@pytest.mark.asyncio
async def test_broadcast_uses_handler_send(services, project_id):
    """A message published on the bus reaches a subscriber over the WS."""
    handler, ws, _ = _handler(services, project_id, [
        # Subscribe first
        json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "irn_subscribe",
            "params": {"topic": _topic()},
        }),
        # Then another client publishes to the same topic (via service)
        json.dumps({
            "jsonrpc": "2.0", "id": 2, "method": "irn_publish",
            "params": {"topic": _topic(), "payload": "aG9sYQ==",
                       "ttl": 60, "tag": 1108},
        }),
    ])
    await handler.run(ws)
    # Drain the inline pubsub to make sure notifications went out
    await services["bus"].drain()

    # ws.sent should contain: subscribe response, publish response,
    # AND a subscription notification.
    payloads = [json.loads(s) for s in ws.sent]
    methods = [p.get("method") for p in payloads if "method" in p]
    assert "irn_subscription" in methods
