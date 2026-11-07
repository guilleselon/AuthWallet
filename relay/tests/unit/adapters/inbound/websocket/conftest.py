"""Fixtures for WebSocket adapter tests.

`FakeWebSocket` mimics the parts of `websockets.ServerConnection` that
`ConnectionHandler` uses: `send()`, async iteration over incoming
messages, and `close()`. No real sockets involved.

The `services` fixture wires the real in-memory adapters (L3) through
the real service layer (L2) and the real protocol layer (L4), so
WebSocket tests exercise the full stack minus the actual socket.

Note: `build_notification` is the **real** one from L4
(`relay.protocol.build_subscription_notification`), not a trivial
lambda. L5 tests verify the wire format, so the builder must produce
valid JSON-RPC, not the raw payload.
"""
from __future__ import annotations

import itertools

import pytest

from relay.adapters.outbound.in_memory import (
    InMemoryConnectionManager,
    InMemoryMessageStore,
    InMemoryPubSub,
    InMemoryRateLimiter,
)
from relay.domain.types import ProjectId
from relay.protocol import Dispatcher, build_subscription_notification
from relay.protocol.handlers import register_all
from relay.service import AckTracker, MessageRouter, SubscriptionRegistry


class FakeWebSocket:
    """Minimal fake. Behaves like an async-iterable with a send method."""

    def __init__(self, incoming: list[str] | None = None) -> None:
        self._incoming = list(incoming or [])
        self._index = 0
        self.sent: list[str] = []
        self.closed_with: tuple[int, str] | None = None

    async def send(self, payload: str) -> None:
        self.sent.append(payload)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed_with = (code, reason)

    def __aiter__(self) -> "FakeWebSocket":
        return self

    async def __anext__(self) -> str:
        if self._index >= len(self._incoming):
            raise StopAsyncIteration
        msg = self._incoming[self._index]
        self._index += 1
        return msg


@pytest.fixture
def services():
    conn = InMemoryConnectionManager()
    store = InMemoryMessageStore()
    bus = InMemoryPubSub(inline_dispatch=True)
    rate = InMemoryRateLimiter(capacity=10_000, refill_rate=1_000.0)
    reg = SubscriptionRegistry(
        conn, bus, build_notification=build_subscription_notification
    )
    acks = AckTracker()
    counter = itertools.count(1)
    router = MessageRouter(store, bus, reg, acks, next_id=lambda: next(counter))
    dispatcher = Dispatcher(rate)
    register_all(dispatcher, router)
    return {
        "conn": conn,
        "store": store,
        "bus": bus,
        "rate": rate,
        "router": router,
        "acks": acks,
        "dispatcher": dispatcher,
    }


@pytest.fixture
def project_id() -> ProjectId:
    return ProjectId("p1")
