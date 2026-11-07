"""In-memory implementation of MessageStore.

Data model:
    _data[topic][message_id] = (message, expires_at_monotonic)

Why a per-topic dict keyed by ID:
    - `add` checks duplicates in O(1).
    - `get` / `delete` are O(1).
    - `fetch` filters by `id > after_id`, O(n) per topic — fine for
      in-memory where topics have hundreds, not millions, of messages.

TTL: two complementary strategies.
    - Lazy: reads filter out expired messages, so a client never gets
      a message past its TTL even if `sweep()` hasn't run.
    - Periodic: `sweep()` removes expired entries to bound memory.
      L6 (composition root) schedules `sweep()` on a timer; tests call
      it explicitly.

The clock is injectable so TTL tests don't need real `sleep()`.
"""
from __future__ import annotations

import time
from typing import Callable

from relay.domain.message import PublishedMessage
from relay.domain.types import MessageId, Topic


class InMemoryMessageStore:
    """In-memory MessageStore. Not thread-safe: single event loop only."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        # topic -> {message_id: (message, expires_at)}
        self._data: dict[Topic, dict[MessageId, tuple[PublishedMessage, float]]] = {}

    async def add(self, message: PublishedMessage) -> None:
        bucket = self._data.setdefault(message.topic, {})
        if message.id in bucket:
            raise ValueError(
                f"duplicate message id {message.id} on topic {message.topic}"
            )
        expires_at = self._clock() + message.ttl
        bucket[message.id] = (message, expires_at)

    async def fetch(
        self,
        topic: Topic,
        after_id: MessageId,
        limit: int,
    ) -> list[PublishedMessage]:
        now = self._clock()
        bucket = self._data.get(topic, {})
        results: list[PublishedMessage] = []
        # Sorted by ID: in single-instance with monotonic IDs, this
        # matches insertion order. For multi-instance (L7), the Redis
        # adapter uses a ZSET for the same ordering guarantee.
        for mid in sorted(bucket):
            if mid <= after_id:
                continue
            message, expires_at = bucket[mid]
            if expires_at <= now:
                continue  # lazy expiry
            results.append(message)
            if len(results) >= limit:
                break
        return results

    async def get(self, topic: Topic, message_id: MessageId) -> PublishedMessage | None:
        entry = self._data.get(topic, {}).get(message_id)
        if entry is None:
            return None
        message, expires_at = entry
        if expires_at <= self._clock():
            return None
        return message

    async def delete(self, topic: Topic, message_id: MessageId) -> bool:
        bucket = self._data.get(topic)
        if bucket is None:
            return False
        return bucket.pop(message_id, None) is not None

    async def count(self, topic: Topic) -> int:
        now = self._clock()
        bucket = self._data.get(topic, {})
        return sum(1 for _, exp in bucket.values() if exp > now)

    async def sweep(self) -> int:
        """Remove expired messages. Returns the number of entries removed.

        Not part of the MessageStore port: it's an in-memory-specific
        maintenance hook. L6 calls it on a periodic timer (e.g. every
        60 seconds). Tests can call it to simulate time passage without
        waiting for real TTLs.
        """
        now = self._clock()
        removed = 0
        empty_topics: list[Topic] = []
        for topic, bucket in self._data.items():
            expired = [mid for mid, (_, exp) in bucket.items() if exp <= now]
            for mid in expired:
                del bucket[mid]
                removed += 1
            if not bucket:
                empty_topics.append(topic)
        for topic in empty_topics:
            del self._data[topic]
        return removed
