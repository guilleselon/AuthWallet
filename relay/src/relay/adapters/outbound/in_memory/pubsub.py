"""In-memory implementation of PubSub.

Single-instance semantics: publishing a message calls every handler
subscribed to that topic in *this process*. In a real deployment with
multiple relay replicas, you'd replace this with RedisPubSub; the
service layer sees the same contract.

Dispatch mode:
    - `inline_dispatch=False` (default, production-like): handlers run
      in background tasks. `publish` returns immediately. Tests must
      call `drain()` to wait for handlers.
    - `inline_dispatch=True` (test/dev): handlers run inline. `publish`
      returns only after all handlers have completed. Deterministic.

Why both modes:
    The port says "must not block the caller waiting for the handler".
    True fire-and-forget is what Redis will do; we honor that by default.
    But testing fire-and-forget is awkward, so we expose an opt-in inline
    mode for tests that prefer determinism over realism.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Awaitable, Callable

from relay.domain.message import PublishedMessage
from relay.domain.types import Topic
from relay.ports import MessageHandler, SubscriptionHandle

logger = logging.getLogger(__name__)


class InMemoryPubSub:
    """In-memory PubSub. Not thread-safe: single event loop only."""

    def __init__(self, *, inline_dispatch: bool = False) -> None:
        self._inline = inline_dispatch
        # handle -> (topic, handler)
        self._handlers: dict[SubscriptionHandle, tuple[Topic, MessageHandler]] = {}
        # Background tasks spawned by non-inline publish; tracked so
        # `drain()` can await them and `close()` can cancel them.
        self._pending: set[asyncio.Task[None]] = set()

    async def publish(self, topic: Topic, message: PublishedMessage) -> None:
        # Snapshot so handler mutation during iteration is safe.
        snapshot = [
            handler for t, handler in self._handlers.values() if t == topic
        ]
        for handler in snapshot:
            if self._inline:
                await self._safe_call(handler, message)
            else:
                task = asyncio.create_task(self._safe_call(handler, message))
                self._pending.add(task)
                task.add_done_callback(self._pending.discard)

    async def subscribe(
        self, topic: Topic, handler: MessageHandler
    ) -> SubscriptionHandle:
        handle = SubscriptionHandle(uuid.uuid4().hex)
        self._handlers[handle] = (topic, handler)
        return handle

    async def unsubscribe(self, handle: SubscriptionHandle) -> None:
        self._handlers.pop(handle, None)

    async def close(self) -> None:
        for task in list(self._pending):
            task.cancel()
        self._pending.clear()
        self._handlers.clear()

    async def drain(self) -> None:
        """Wait for all background handler tasks to finish.

        In-memory-specific helper. Tests call it after `publish` to
        assert on handler effects. Not part of the PubSub port.
        """
        while self._pending:
            await asyncio.gather(*self._pending, return_exceptions=True)

    @staticmethod
    async def _safe_call(
        handler: MessageHandler, message: PublishedMessage
    ) -> None:
        # A broken handler must not prevent other subscribers from
        # receiving the message. Log and swallow.
        try:
            await handler(message)
        except Exception:
            logger.exception(
                "pubsub handler failed for topic %s message %s",
                message.topic,
                message.id,
            )
