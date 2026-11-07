"""Port: temporary persistence of published messages.

Why this port exists:
    A subscriber may be offline when a message is published. IRN's
    contract is: if the message's TTL hasn't expired, the subscriber
    must be able to retrieve it on reconnect via `irn_batchFetch`.
    That requires storing published messages somewhere, keyed by topic
    and ordered by ID.

The relay never decrypts payloads. Whatever goes in is opaque base64
that comes back out unchanged.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from relay.domain.message import PublishedMessage
from relay.domain.types import MessageId, Topic


@runtime_checkable
class MessageStore(Protocol):
    """Temporary, per-topic storage of published messages."""

    async def add(self, message: PublishedMessage) -> None:
        """Persist a message for later retrieval.

        Implementations must:
            - Assign nothing: the message already has an `id`.
            - Reject duplicate IDs (raise ValueError) if the ID was
              already used. This catches bugs early.
            - Not enforce TTL themselves: expiry is the adapter's
              responsibility (Redis `EXPIRE`, in-memory timer, etc.).
        """
        ...

    async def fetch(
        self,
        topic: Topic,
        after_id: MessageId,
        limit: int,
    ) -> list[PublishedMessage]:
        """Return messages for `topic` with `id > after_id`, in ascending order.

        Used to implement `irn_batchFetch`: a reconnecting subscriber
        passes the highest ID it has seen, and receives everything after.

        `limit` bounds the response size. Implementations must return
        at most `limit` messages; the caller paginates if needed.
        """
        ...

    async def get(self, topic: Topic, message_id: MessageId) -> PublishedMessage | None:
        """Return a single message by ID, or None if it doesn't exist.

        Used to validate acks: a subscriber cannot ack a message it
        never received. If the message is gone (expired or evicted),
        the ack is a no-op or an error, depending on the caller's choice.
        """
        ...

    async def delete(self, topic: Topic, message_id: MessageId) -> bool:
        """Delete a single message. Returns True if it existed.

        Not used in the happy path (TTL handles expiry), but useful for
        admin commands and tests, and potentially for a future
        "delivered and acked by all subscribers" optimization.
        """
        ...

    async def count(self, topic: Topic) -> int:
        """Return the number of stored messages for `topic`.

        Used by tests and by observability (metrics export).
        Implementations may return a lower bound if exact counting
        is expensive on their backend.
        """
        ...
