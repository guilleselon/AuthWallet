"""End-to-end tests with real WebSocket sockets.

These tests bind a real server on an ephemeral port, connect a real
client, and verify the full path: auth → JSON-RPC → response.

They are heavier than unit tests but catch integration bugs that the
FakeWebSocket can't: subprotocol handling, close codes, query parsing
through the real WebSocket library.
"""
from __future__ import annotations

import asyncio
import itertools
import json

import pytest
import websockets

from relay.adapters.inbound.websocket import RelayWebSocketServer
from relay.adapters.outbound.in_memory import (
    InMemoryConnectionManager,
    InMemoryMessageStore,
    InMemoryPubSub,
    InMemoryRateLimiter,
    StaticTokenValidator,
)
from relay.domain.types import ProjectId, make_topic
from relay.protocol import Dispatcher, build_subscription_notification
from relay.protocol.handlers import register_all
from relay.service import AckTracker, MessageRouter, SubscriptionRegistry


def _topic():
    return make_topic("a" * 64)


def _build_server() -> RelayWebSocketServer:
    conn = InMemoryConnectionManager()
    store = InMemoryMessageStore()
    bus = InMemoryPubSub()
    rate = InMemoryRateLimiter(capacity=10_000, refill_rate=1_000.0)
    reg = SubscriptionRegistry(
        conn, bus, build_notification=build_subscription_notification
    )
    acks = AckTracker()
    counter = itertools.count(1)
    router = MessageRouter(store, bus, reg, acks, next_id=lambda: next(counter))
    dispatcher = Dispatcher(rate)
    register_all(dispatcher, router)
    return RelayWebSocketServer(
        host="127.0.0.1",
        port=0,
        dispatcher=dispatcher,
        connection_manager=conn,
        token_validator=StaticTokenValidator({"tok-ok": ProjectId("p1")}),
        ack_tracker=acks,
    )


@pytest.mark.asyncio
async def test_publish_roundtrip_over_real_socket():
    server = _build_server()
    async with server.serve() as ws_server:
        port = ws_server.sockets[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}/?token=tok-ok"
        async with websockets.connect(url, open_timeout=5) as client:
            await client.send(json.dumps({
                "jsonrpc": "2.0", "id": 1, "method": "irn_publish",
                "params": {
                    "topic": _topic(), "payload": "aG9sYQ==",
                    "ttl": 60, "tag": 1108,
                },
            }))
            raw = await asyncio.wait_for(client.recv(), timeout=5)
            response = json.loads(raw)
            assert response["id"] == 1
            assert response["result"] == {"id": 1}


@pytest.mark.asyncio
async def test_missing_token_closes_connection():
    server = _build_server()
    async with server.serve() as ws_server:
        port = ws_server.sockets[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}/"
        with pytest.raises(websockets.ConnectionClosed):
            async with websockets.connect(url, open_timeout=5) as client:
                await asyncio.wait_for(client.recv(), timeout=5)


@pytest.mark.asyncio
async def test_invalid_token_closes_connection():
    server = _build_server()
    async with server.serve() as ws_server:
        port = ws_server.sockets[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}/?token=wrong"
        with pytest.raises(websockets.ConnectionClosed) as exc_info:
            async with websockets.connect(url, open_timeout=5) as client:
                await asyncio.wait_for(client.recv(), timeout=5)
        # Application close code for auth failure.
        assert exc_info.value.rcvd is not None
        assert exc_info.value.rcvd.code == 4001


@pytest.mark.asyncio
async def test_two_clients_broadcast():
    """Two real clients; one subscribes, the other publishes; first receives."""
    server = _build_server()
    async with server.serve() as ws_server:
        port = ws_server.sockets[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}/?token=tok-ok"

        async with websockets.connect(url) as sub:
            await sub.send(json.dumps({
                "jsonrpc": "2.0", "id": 1, "method": "irn_subscribe",
                "params": {"topic": _topic()},
            }))
            await asyncio.wait_for(sub.recv(), timeout=5)  # sub response

            async with websockets.connect(url) as pub:
                await pub.send(json.dumps({
                    "jsonrpc": "2.0", "id": 1, "method": "irn_publish",
                    "params": {
                        "topic": _topic(), "payload": "aG9sYQ==",
                        "ttl": 60, "tag": 1108,
                    },
                }))
                await asyncio.wait_for(pub.recv(), timeout=5)  # pub response

            # The subscriber should receive the notification.
            raw = await asyncio.wait_for(sub.recv(), timeout=5)
            notification = json.loads(raw)
            assert notification["method"] == "irn_subscription"
