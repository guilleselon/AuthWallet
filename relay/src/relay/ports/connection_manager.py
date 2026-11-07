"""Port: registry of live connections on this instance.

Why this port exists:
    WebSocket servers manage thousands of open connections. Each
    connection is associated with a `ConnectionId` and is subscribed
    to zero or more topics. The service layer needs to ask:
        - "who is subscribed to topic X on this instance?"
        - "send this serialized message to connection Y"
    This port abstracts those operations without exposing WebSocket
    internals (frames, close codes, backpressure).

    The port is intentionally *transport-agnostic*: it deals in strings
    (`MessageSender` receives a `str`), not in WebSocket frames or JSON-RPC.
    Serialization is the adapter's responsibility.
"""
from __future__ import annotations

from typing import Awaitable, Callable, Protocol, runtime_checkable

from relay.domain.types import ConnectionId, Topic

# Writes a raw string to a specific connection. The adapter decides
# whether that's a WebSocket text frame, an SSE chunk, or anything else.
MessageSender = Callable[[str], Awaitable[None]]


@runtime_checkable
class ConnectionManager(Protocol):
    """Tracks live connections and their topic subscriptions."""

    async def register(
        self,
        connection_id: ConnectionId,
        sender: MessageSender,
    ) -> None:
        """Register a new live connection.

        `sender` is how the manager writes to this connection. It must be
        safe to call concurrently with other sends (the adapter ensures
        serialization if needed, or the caller does).

        Raises ValueError if `connection_id` is already registered.
        """
        ...

    async def unregister(self, connection_id: ConnectionId) -> None:
        """Remove a connection and all its subscriptions.

        Called when the WebSocket closes (gracefully or not).
        Idempotent: unregistering an unknown ID is a no-op.
        """
        ...

    async def subscribe(self, connection_id: ConnectionId, topic: Topic) -> None:
        """Add `topic` to this connection's subscriptions.

        Idempotent: subscribing twice is a no-op.
        Raises ValueError if `connection_id` is not registered.
        """
        ...

    async def unsubscribe(self, connection_id: ConnectionId, topic: Topic) -> None:
        """Remove `topic` from this connection's subscriptions.

        Idempotent: unsubscribing from an unsubscribed topic is a no-op.
        """
        ...

    async def send_to(self, connection_id: ConnectionId, payload: str) -> None:
        """Send a raw string to a single connection.

        Raises ValueError if `connection_id` is not registered.
        Silently drops if the connection is gone (race with close):
        the caller cannot do anything useful about a dead connection.
        """
        ...

    async def broadcast(self, topic: Topic, payload: str) -> int:
        """Send a raw string to every connection subscribed to `topic`.

        Returns the number of connections the message was sent to
        (successes only; failures are logged and counted separately
        by observability).

        Called from the PubSub handler on every instance. Cheap when
        no local subscriber exists for `topic`.
        """
        ...

    async def subscribers(self, topic: Topic) -> frozenset[ConnectionId]:
        """Return the set of connections subscribed to `topic` on this instance.

        Used for diagnostics and for `irn_batchFetch` to know whether
        to even bother querying the MessageStore.
        """
        ...

    async def is_registered(self, connection_id: ConnectionId) -> bool:
        """True if the connection is currently registered.

        Used to short-circuit sends to dead connections without
        raising, and by tests.
        """
        ...
