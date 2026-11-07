"""Service: orchestrates publish, fetch, subscribe, and ack.

The router is the heart of the relay. It coordinates:
    - ID assignment for new messages
    - Persistence via `MessageStore`
    - Distribution via `PubSub`
    - Subscription management via `SubscriptionRegistry`
    - Ack tracking via `AckTracker`

It knows nothing about WebSockets, JSON, or Redis. Those are adapters.
"""
from __future__ import annotations

from typing import Callable

from relay.domain.message import PublishedMessage, PublishRequest
from relay.domain.types import ConnectionId, MessageId, Topic
from relay.ports import MessageStore, PubSub

from .ack_tracker import AckTracker
from .subscription_registry import SubscriptionRegistry

# Assigns the next message ID. Injected so multi-instance deployments
# can plug in a distributed generator (Redis INCR, ULID, etc.) without
# the router knowing. In single-instance, `itertools.count` suffices.
IdGenerator = Callable[[], MessageId]


class MessageRouter:
    """Use cases for publishing, fetching, subscribing, and acknowledging."""

    def __init__(
        self,
        store: MessageStore,
        pubsub: PubSub,
        subscriptions: SubscriptionRegistry,
        acks: AckTracker,
        next_id: IdGenerator,
    ) -> None:
        self._store = store
        self._pubsub = pubsub
        self._subscriptions = subscriptions
        self._acks = acks
        self._next_id = next_id

    async def publish(self, request: PublishRequest) -> PublishedMessage:
        """Persist and distribute a new message.

        Order matters: persist first, then publish. If we published
        first and the store failed, a subscriber could receive a message
        that `irn_batchFetch` can't later retrieve (a reconnecting
        client would see a gap). Persist-then-publish is the invariant.
        """
        message = PublishedMessage(
            id=self._next_id(),
            topic=request.topic,
            payload=request.payload,
            ttl=request.ttl,
            tag=request.tag,
            prompt=request.prompt,
        )
        await self._store.add(message)
        await self._pubsub.publish(message.topic, message)
        return message

    async def fetch(
        self,
        topic: Topic,
        after_id: MessageId,
        limit: int,
    ) -> list[PublishedMessage]:
        """Retrieve messages for `topic` with id > `after_id`.

        Used by `irn_batchFetch`: a reconnecting client passes the
        highest ID it has seen and receives everything after it.

        `limit <= 0` returns an empty list rather than raising. The
        protocol layer (L4) is responsible for rejecting malformed
        `limit` values with a proper JSON-RPC error; the router stays
        forgiving so it can be reused by other callers.
        """
        if limit <= 0:
            return []
        return await self._store.fetch(topic, after_id, limit)

    async def subscribe(self, connection_id: ConnectionId, topic: Topic) -> None:
        """Subscribe a connection to a topic."""
        await self._subscriptions.subscribe(connection_id, topic)

    async def unsubscribe(self, connection_id: ConnectionId, topic: Topic) -> None:
        """Unsubscribe a connection from a topic."""
        await self._subscriptions.unsubscribe(connection_id, topic)

    async def acknowledge(
        self,
        connection_id: ConnectionId,
        topic: Topic,
        message_id: MessageId,
    ) -> None:
        """Record that a connection has received a specific message.

        Fire-and-forget: the protocol layer returns success without
        waiting for any downstream effect. The AckTracker is used for
        observability and future store-cleanup optimization.
        """
        self._acks.record(connection_id, topic, message_id)
