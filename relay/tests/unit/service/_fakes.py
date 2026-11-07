"""Minimal in-memory fakes for L2 tests.

These implement the ports just enough to test the service layer.
They are NOT the production in-memory adapters (those come in L3);
they exist only to keep L2 tests fast and dependency-free.
"""
from __future__ import annotations

from relay.domain.message import PublishedMessage
from relay.domain.types import ConnectionId, MessageId, Topic
from relay.ports import ConnectionManager, MessageStore, PubSub, SubscriptionHandle


class FakeMessageStore(MessageStore):
    def __init__(self) -> None:
        self._data: dict[Topic, list[PublishedMessage]] = {}

    async def add(self, message: PublishedMessage) -> None:
        self._data.setdefault(message.topic, []).append(message)

    async def fetch(
        self, topic: Topic, after_id: MessageId, limit: int
    ) -> list[PublishedMessage]:
        return [m for m in self._data.get(topic, []) if m.id > after_id][:limit]

    async def get(self, topic: Topic, message_id: MessageId) -> PublishedMessage | None:
        for m in self._data.get(topic, []):
            if m.id == message_id:
                return m
        return None

    async def delete(self, topic: Topic, message_id: MessageId) -> bool:
        bucket = self._data.get(topic, [])
        for i, m in enumerate(bucket):
            if m.id == message_id:
                bucket.pop(i)
                return True
        return False

    async def count(self, topic: Topic) -> int:
        return len(self._data.get(topic, []))


class FakePubSub(PubSub):
    def __init__(self) -> None:
        self.published: list[tuple[Topic, PublishedMessage]] = []
        self._handlers: dict[SubscriptionHandle, tuple[Topic, object]] = {}
        self._next = 0

    async def publish(self, topic: Topic, message: PublishedMessage) -> None:
        self.published.append((topic, message))
        # Fan out to subscribed handlers (single-instance semantics).
        for handle, (t, handler) in list(self._handlers.items()):
            if t == topic:
                await handler(message)  # type: ignore[misc]

    async def subscribe(self, topic: Topic, handler):  # type: ignore[no-untyped-def]
        self._next += 1
        handle = SubscriptionHandle(str(self._next))
        self._handlers[handle] = (topic, handler)
        return handle

    async def unsubscribe(self, handle: SubscriptionHandle) -> None:
        self._handlers.pop(handle, None)

    async def close(self) -> None:
        self._handlers.clear()


class FakeConnectionManager(ConnectionManager):
    def __init__(self) -> None:
        self._senders: dict[ConnectionId, object] = {}
        self._subscriptions: dict[Topic, set[ConnectionId]] = {}
        self.sent: list[tuple[ConnectionId, str]] = []

    async def register(self, connection_id: ConnectionId, sender) -> None:  # type: ignore[no-untyped-def]
        if connection_id in self._senders:
            raise ValueError(f"already registered: {connection_id}")
        self._senders[connection_id] = sender

    async def unregister(self, connection_id: ConnectionId) -> None:
        self._senders.pop(connection_id, None)
        for conns in self._subscriptions.values():
            conns.discard(connection_id)

    async def subscribe(self, connection_id: ConnectionId, topic: Topic) -> None:
        if connection_id not in self._senders:
            raise ValueError(f"unknown connection: {connection_id}")
        self._subscriptions.setdefault(topic, set()).add(connection_id)

    async def unsubscribe(self, connection_id: ConnectionId, topic: Topic) -> None:
        conns = self._subscriptions.get(topic)
        if conns is not None:
            conns.discard(connection_id)
            if not conns:
                del self._subscriptions[topic]

    async def send_to(self, connection_id: ConnectionId, payload: str) -> None:
        if connection_id not in self._senders:
            raise ValueError(f"unknown connection: {connection_id}")
        self.sent.append((connection_id, payload))

    async def broadcast(self, topic: Topic, payload: str) -> int:
        conns = self._subscriptions.get(topic, set())
        for cid in conns:
            self.sent.append((cid, payload))
        return len(conns)

    async def subscribers(self, topic: Topic) -> frozenset[ConnectionId]:
        return frozenset(self._subscriptions.get(topic, set()))

    async def is_registered(self, connection_id: ConnectionId) -> bool:
        return connection_id in self._senders
