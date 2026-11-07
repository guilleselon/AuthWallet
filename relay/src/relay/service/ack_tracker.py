"""Service: records acknowledgments of delivered messages.

IRN's `irn_acknowledge` is fire-and-forget: the client tells the relay
"got it, id N on topic T". The relay uses this for:
    - Observability: how many messages are delivered but unacked?
    - Debugging: which connection is slow to ack?
    - Future: deleting from the store once all subscribers have acked.

In single-instance deployments, the tracker is an in-memory dict. In
multi-instance, each instance tracks its own connections; cross-instance
coordination is out of scope, and TTL handles store cleanup regardless.
"""
from __future__ import annotations

from relay.domain.types import ConnectionId, MessageId, Topic


class AckTracker:
    """In-memory record of `(connection, topic, message)` acknowledgments."""

    def __init__(self) -> None:
        # topic → message_id → set of connections that have acked.
        self._acks: dict[Topic, dict[MessageId, set[ConnectionId]]] = {}

    def record(
        self,
        connection_id: ConnectionId,
        topic: Topic,
        message_id: MessageId,
    ) -> None:
        """Record that `connection_id` has acked `message_id` on `topic`.

        Idempotent: recording the same ack twice is a no-op.
        """
        by_message = self._acks.setdefault(topic, {})
        by_message.setdefault(message_id, set()).add(connection_id)

    def has_acked(
        self,
        connection_id: ConnectionId,
        topic: Topic,
        message_id: MessageId,
    ) -> bool:
        """True if `connection_id` has already acked that message."""
        return connection_id in self._acks.get(topic, {}).get(message_id, set())

    def ack_count(self, topic: Topic, message_id: MessageId) -> int:
        """Number of distinct connections that have acked this message."""
        return len(self._acks.get(topic, {}).get(message_id, set()))

    def forget_connection(self, connection_id: ConnectionId) -> int:
        """Remove every ack recorded for `connection_id`.

        Called on disconnect. Returns the number of ack entries removed,
        for observability. Idempotent.
        """
        removed = 0
        empty_topics: list[Topic] = []
        for topic, by_message in self._acks.items():
            empty_messages: list[MessageId] = []
            for message_id, conns in by_message.items():
                if connection_id in conns:
                    conns.discard(connection_id)
                    removed += 1
                if not conns:
                    empty_messages.append(message_id)
            for message_id in empty_messages:
                del by_message[message_id]
            if not by_message:
                empty_topics.append(topic)
        for topic in empty_topics:
            del self._acks[topic]
        return removed

    def forget_message(self, topic: Topic, message_id: MessageId) -> None:
        """Drop all acks for a specific message.

        Called when the message expires from the store; keeping its acks
        would leak memory. Idempotent.
        """
        by_message = self._acks.get(topic)
        if by_message is None:
            return
        by_message.pop(message_id, None)
        if not by_message:
            del self._acks[topic]

    def stats(self) -> dict[str, int]:
        """Aggregate counters for observability."""
        topics = len(self._acks)
        messages = sum(len(by_message) for by_message in self._acks.values())
        acks = sum(
            len(conns)
            for by_message in self._acks.values()
            for conns in by_message.values()
        )
        return {"topics": topics, "messages": messages, "acks": acks}
