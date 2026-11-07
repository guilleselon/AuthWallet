"""Service: keep PubSub subscriptions in sync with local interest.

Why this exists:
    `ConnectionManager` knows which connections on *this instance* are
    subscribed to which topics. `PubSub` knows how to receive messages
    published by *any instance*. Neither should know about the other:
    the ConnectionManager shouldn't care about the bus, and the PubSub
    shouldn't care about connections.

    This registry bridges them with a single responsibility: subscribe
    to a topic on the bus only when the first local connection wants
    it, and unsubscribe when the last one leaves. Without this, every
    instance would stay subscribed to every topic forever — a memory
    leak and a wasted fan-out.

Why the notification builder is injected:
    When a message arrives from the bus, it must be serialized to the
    wire format (JSON-RPC `irn_subscription`) before being sent to a
    connection. That format belongs to the protocol layer (L4), which
    this layer must not import. So the builder is a `Callable` injected
    from the composition root (L6).
"""
from __future__ import annotations

from typing import Callable

from relay.domain.message import PublishedMessage
from relay.domain.types import ConnectionId, Topic
from relay.ports import ConnectionManager, PubSub, SubscriptionHandle

# Builds the wire-ready string for a published message.
# Injected from L6; in tests, a trivial `lambda m: m.payload` suffices.
NotificationBuilder = Callable[[PublishedMessage], str]


class SubscriptionRegistry:
    """Coordinates local subscriptions with the cross-instance bus."""

    def __init__(
        self,
        connection_manager: ConnectionManager,
        pubsub: PubSub,
        build_notification: NotificationBuilder,
    ) -> None:
        self._connections = connection_manager
        self._pubsub = pubsub
        self._build_notification = build_notification
        # Per-topic state. `counts` tracks local subscribers; `handles`
        # tracks the bus subscription (present only when count > 0).
        self._counts: dict[Topic, int] = {}
        self._handles: dict[Topic, SubscriptionHandle] = {}

    async def subscribe(self, connection_id: ConnectionId, topic: Topic) -> None:
        """Subscribe a local connection to `topic`.

        Local subscription is delegated to the ConnectionManager first
        (it validates that the connection exists). Then, if this is the
        first local subscriber, we subscribe to the bus so that messages
        from other instances start flowing in.
        """
        await self._connections.subscribe(connection_id, topic)

        count = self._counts.get(topic, 0)
        if count == 0:
            handle = await self._pubsub.subscribe(topic, self._on_message)
            self._handles[topic] = handle
        self._counts[topic] = count + 1

    async def unsubscribe(self, connection_id: ConnectionId, topic: Topic) -> None:
        """Unsubscribe a local connection from `topic`.

        When the last local subscriber leaves, we also unsubscribe from
        the bus so this instance stops receiving messages it has nowhere
        to deliver.
        """
        await self._connections.unsubscribe(connection_id, topic)

        count = self._counts.get(topic, 0)
        if count <= 1:
            self._counts.pop(topic, None)
            handle = self._handles.pop(topic, None)
            if handle is not None:
                await self._pubsub.unsubscribe(handle)
        else:
            self._counts[topic] = count - 1

    async def local_subscriber_count(self, topic: Topic) -> int:
        """Number of local connections subscribed to `topic`.

        Used by tests and by observability. Not part of the hot path.
        """
        return self._counts.get(topic, 0)

    async def _on_message(self, message: PublishedMessage) -> None:
        """Handler invoked by the bus for every message on a subscribed topic."""
        payload = self._build_notification(message)
        await self._connections.broadcast(message.topic, payload)
