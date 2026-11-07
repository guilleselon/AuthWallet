"""In-memory token-bucket rate limiter.

Per `(project_id, operation)` bucket. Each bucket holds `capacity`
tokens, refilled at `refill_rate` tokens per second.

Why token bucket over a fixed window:
    Fixed windows allow a client to burst 2x the limit at the boundary
    (once at the end of one window, once at the start of the next).
    Token buckets smooth traffic and are the de facto standard in
    API rate limiting.

The clock is injectable so tests can advance time without sleeping.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from relay.domain.errors import RateLimited
from relay.domain.types import ProjectId

# Sensible defaults for a relay. Tune per deployment; the composition
# root can pass stricter values. Numbers are conservative: they allow
# bursts but cap sustained throughput per project.
_DEFAULT_CAPACITY = 100
_DEFAULT_REFILL_RATE = 10.0  # tokens / second


@dataclass
class _Bucket:
    tokens: float
    last_refill: float = field(default_factory=time.monotonic)


class InMemoryRateLimiter:
    """In-memory token-bucket limiter. Not thread-safe: single event loop only."""

    def __init__(
        self,
        *,
        capacity: int = _DEFAULT_CAPACITY,
        refill_rate: float = _DEFAULT_REFILL_RATE,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if refill_rate <= 0:
            raise ValueError("refill_rate must be positive")
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._clock = clock
        self._buckets: dict[tuple[ProjectId, str], _Bucket] = {}

    async def check(
        self,
        project_id: ProjectId,
        operation: str,
        cost: int = 1,
    ) -> None:
        if cost <= 0:
            raise ValueError("cost must be positive")

        now = self._clock()
        key = (project_id, operation)
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _Bucket(tokens=float(self._capacity), last_refill=now)
            self._buckets[key] = bucket

        # Refill since last check.
        elapsed = now - bucket.last_refill
        if elapsed > 0:
            bucket.tokens = min(
                float(self._capacity),
                bucket.tokens + elapsed * self._refill_rate,
            )
            bucket.last_refill = now

        if bucket.tokens < cost:
            raise RateLimited(
                f"rate limit exceeded for project {project_id} on {operation}"
            )
        bucket.tokens -= cost

    async def reset(self, project_id: ProjectId) -> None:
        for key in [k for k in self._buckets if k[0] == project_id]:
            del self._buckets[key]
