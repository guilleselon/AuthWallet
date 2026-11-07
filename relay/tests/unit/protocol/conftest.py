"""Shared fixtures for protocol tests.

Uses the real in-memory adapters from L3 (not fakes): the protocol layer
deserves to be tested against the same behavior the service layer sees.
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
from relay.domain.types import ConnectionId, ProjectId
from relay.protocol import Dispatcher, HandlerContext
from relay.protocol.handlers import register_all
from relay.service import AckTracker, MessageRouter, SubscriptionRegistry


@pytest.fixture
def services():
    conn = InMemoryConnectionManager()
    store = InMemoryMessageStore()
    bus = InMemoryPubSub(inline_dispatch=True)  # deterministic in tests
    rate = InMemoryRateLimiter(capacity=10_000, refill_rate=1_000.0)
    reg = SubscriptionRegistry(conn, bus, build_notification=lambda m: m.payload)
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
def ctx() -> HandlerContext:
    return HandlerContext(
        connection_id=ConnectionId("c1"),
        project_id=ProjectId("p1"),
    )
