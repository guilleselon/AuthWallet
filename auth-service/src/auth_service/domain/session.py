"""Session value object.

A Session is what a successful login produces: an opaque identifier
plus the facts about *who* logged in and *until when*. It is immutable;
renewing produces a new Session.

Timestamps are Unix epoch seconds (float). Reasons:
    - Portable across in-memory and Redis (no dependency on monotonic
      clocks that Redis wouldn't share).
    - Comparable across processes without relying on wall-clock skew
      being zero.
    - Easy to serialize to JSON / Redis strings without a datetime codec.
"""
from __future__ import annotations

from dataclasses import dataclass

from .types import Address, ChainId, SessionId


@dataclass(frozen=True, slots=True)
class Session:
    """An authenticated session.

    `expires_at` is inclusive: the session is valid while
    `now <= expires_at`. The boundary is checked in the domain, not in
    adapters, so every adapter sees the same expiry semantics.
    """

    id: SessionId
    address: Address
    chain_id: ChainId
    created_at: float
    expires_at: float

    def is_expired(self, now: float) -> bool:
        """True if the session has passed its expiry at `now`."""
        return now > self.expires_at

    def remaining_seconds(self, now: float) -> float:
        """Seconds until expiry (0.0 if already expired).

        Used to compute `Max-Age` on the session cookie. Never negative:
        an expired session should produce `Max-Age=0`, not a negative
        value, because some browsers behave inconsistently with
        negative Max-Age.
        """
        return max(0.0, self.expires_at - now)
