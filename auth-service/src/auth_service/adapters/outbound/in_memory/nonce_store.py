"""In-memory NonceStore.

Data model: `nonce -> expires_at` (monotonic seconds).
`consume` is `dict.pop`, atomic within a single event loop iteration.
"""
from __future__ import annotations

import time
from typing import Callable

from auth_service.domain.types import Nonce


class InMemoryNonceStore:
    """Dict-backed nonce store with TTL. Not thread-safe: one event loop."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._data: dict[Nonce, float] = {}

    async def put(self, nonce: Nonce, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._data[nonce] = self._clock() + ttl_seconds

    async def consume(self, nonce: Nonce) -> bool:
        expires = self._data.pop(nonce, None)
        if expires is None:
            return False
        return expires > self._clock()

    async def ttl_remaining(self, nonce: Nonce) -> float | None:
        expires = self._data.get(nonce)
        if expires is None:
            return None
        return max(0.0, expires - self._clock())
