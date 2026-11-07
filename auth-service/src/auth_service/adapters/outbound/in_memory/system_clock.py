"""Real Clock adapter: returns `time.time()`.

Thin by design. The point of the adapter is that it exists as a named
class (so the composition root can inject it) and that swapping it for
a fake in tests is trivial.
"""
from __future__ import annotations

import time


class SystemClock:
    """Clock backed by the system wall clock (Unix epoch seconds)."""

    def now(self) -> float:
        return time.time()
