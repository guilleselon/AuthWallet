"""Port: cross-instance message distribution.

Why this port exists:
    In a single-instance deployment, the ConnectionManager alone is enough:
    it knows every connection on the box and can fan out a message
    directly. But the moment you run two relay replicas, a message
    published on instance A must reach a subscriber connected to
    instance B. That's what PubSub is for.

    In single-instance mode, use an in-memory PubSub that fan-outs
    to local handlers. In multi-instance mode, use Redis Pub/Sub
    (or NATS, or Kafka). The service layer doesn't know which.
"""
from __future__ import annotations

from typing import Awaitable, Callable, NewType, Protocol, runtime_checkable

from relay.domain.message import PublishedMessage
from relay.domain.types import Topic

# Opaque handle returned by `subscribe`. Used to `unsubscribe` later.
# A string is enough: UUID, hash, whatever the adapter chooses.
SubscriptionHandle = NewType("SubscriptionHandle", str)

# Called once per received message on a subscribed topic.
# Awaitable because delivery is async (writes to a WebSocket, etc.).
MessageHandler = Callable[[PublishedMessage], Awaitable[None]]


@runtime_checkable
class PubSub(Protocol):
    """Fan-out of messages across all relay instances."""

    async def publish(self, topic: Topic, message: PublishedMessage) -> None:
        """Distribute a message to every instance subscribed to `topic`.

        Returns once the message has been handed off to the underlying
        transport (Redis, etc.), NOT once every subscriber has received
        it. Delivery guarantees are the transport's concern.
        """
        ...

    async def subscribe(self, topic: Topic, handler: MessageHandler) -> SubscriptionHandle:
        """Register `handler` to be called for every message on `topic`.

        The handler runs asynchronously. Implementations must NOT
        block the caller waiting for the handler to finish (fire-and-forget
        or queued, but not inline-blocking).

        Returns a handle usable with `unsubscribe`.
        """
        ...

    async def unsubscribe(self, handle: SubscriptionHandle) -> None:
        """Cancel a subscription. After this returns, the handler
        will not be called again for future messages.

        Calling `unsubscribe` on an unknown handle is a no-op.
        """
        ...

    async def close(self) -> None:
        """Release all subscriptions and connections.

        Called on application shutdown. Implementations must be idempotent.
        """
        ...
