"""Port: source of time.

Why this port exists:
    Every piece of logic that reasons about expiry needs `now`. If we
    call `time.time()` directly from services, those services become
    untestable without sleeping or monkeypatching `time`. A tiny
    abstraction (one method) makes tests deterministic and documents
    the time source at every call site.

Why sync and not async:
    `time.time()` is a microsecond operation. Making it async would
    force the service layer to await on something that never yields,
    which is strictly worse (allocation, scheduling, no benefit).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """Returns the current Unix epoch time in seconds."""

    def now(self) -> float:
        """Current Unix timestamp as a float (seconds since epoch).

        Implementations MUST be monotonic *within a single process*
        as far as expiry decisions are concerned: a session that
        expires at T must not become un-expired because the system
        clock went backwards. Production adapters use `time.time()`
        and accept the risk (NTP skew is small); tests use a fake
        clock whose `now()` is deterministic and advanceable.
        """
        ...
