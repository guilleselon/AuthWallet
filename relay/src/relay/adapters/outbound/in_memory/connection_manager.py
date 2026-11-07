"""In-memory implementation of ConnectionManager.

Data model:
    _senders[connection_id] = sender (async callable)
    _subscriptions[topic] = set[connection_id]

Concurrency: single event loop. No method awaits during mutation of
the internal dicts, so operations are atomic with respect to other
coroutines. `broadcast` awaits each sender *after* snapshotting the
subscribers set, so a sender that triggers subscribe/unsubscribe
cannot corrupt the iteration.
"""
from __future__ import annotations

import logging

from relay.domain.types import ConnectionId, Topic
from relay.ports import MessageSender

logger = logging.getLogger(__name__)


class InMemoryConnectionManager:
    """In-memory ConnectionManager. Not thread-safe: single event loop only."""

    def __init__(self) -> None:
        self._senders: dict[ConnectionId, MessageSender] = {}
        self._subscriptions: dict[Topic, set[ConnectionId]] = {}

    async def register(
        self, connection_id: ConnectionId, sender: MessageSender
    ) -> None:
        if connection_id in self._senders:
            raise ValueError(f"already registered: {connection_id}")
        self._senders[connection_id] = sender

    async def unregister(self, connection_id: ConnectionId) -> None:
        self._senders.pop(connection_id, None)
        empty_topics: list[Topic] = []
        for topic, conns in self._subscriptions.items():
            conns.discard(connection_id)
            if not conns:
                empty_topics.append(topic)
        for topic in empty_topics:
            del self._subscriptions[topic]

    async def subscribe(self, connection_id: ConnectionId, topic: Topic) -> None:
        if connection_id not in self._senders:
            raise ValueError(f"unknown connection: {connection_id}")
        self._subscriptions.setdefault(topic, set()).add(connection_id)

    async def unsubscribe(self, connection_id: ConnectionId, topic: Topic) -> None:
        conns = self._subscriptions.get(topic)
        if conns is None:
            return
        conns.discard(connection_id)
        if not conns:
            del self._subscriptions[topic]

    async def send_to(self, connection_id: ConnectionId, payload: str) -> None:
        sender = self._senders.get(connection_id)
        if sender is None:
            raise ValueError(f"unknown connection: {connection_id}")
        try:
            await sender(payload)
        except Exception:
            logger.exception("send_to failed for connection %s", connection_id)

    async def broadcast(self, topic: Topic, payload: str) -> int:
        # Snapshot to make iteration safe against mutations by senders.
        snapshot = list(self._subscriptions.get(topic, ()))
        delivered = 0
        for cid in snapshot:
            sender = self._senders.get(cid)
            if sender is None:
                continue
            try:
                await sender(payload)
                delivered += 1
            except Exception:
                logger.exception("broadcast failed for connection %s", cid)
        return delivered

    async def subscribers(self, topic: Topic) -> frozenset[ConnectionId]:
        return frozenset(self._subscriptions.get(topic, ()))

    async def is_registered(self, connection_id: ConnectionId) -> bool:
        return connection_id in self._senders
