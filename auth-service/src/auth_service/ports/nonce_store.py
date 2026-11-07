"""Port: short-lived storage of issued SIWE nonces.

Why this port exists:
    `/auth/nonce` issues a nonce. `/auth/verify` receives it back and
    must consume it exactly once. Between those two HTTP requests, the
    nonce must survive somewhere the second request can see — usually
    a different worker process, so in a real deployment this can't be
    process memory.

    The store also enforces the TTL: a nonce older than the configured
    window is no longer valid, regardless of whether the client got
    around to using it. Without TTL, a leaked nonce would be a
    long-lived credential.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from auth_service.domain.types import Nonce


@runtime_checkable
class NonceStore(Protocol):
    """Stores issued nonces and consumes them atomically."""

    async def put(self, nonce: Nonce, ttl_seconds: int) -> None:
        """Store `nonce` as valid for the next `ttl_seconds`.

        Implementations must:
            - Reject `ttl_seconds <= 0` (raise ValueError).
            - Be idempotent for identical (nonce, ttl) writes, so a
              retried issuance doesn't error out.

        In Redis, this is `SET key 1 EX ttl`. In memory, a dict with
        `expires_at`.
        """
        ...

    async def consume(self, nonce: Nonce) -> bool:
        """Atomically check-and-delete.

        Returns True if `nonce` existed and had not expired; False
        otherwise. The deletion MUST be atomic with the check so that
        two concurrent `/auth/verify` calls with the same nonce produce
        exactly one True and one False — never two Trues, never zero.

        In Redis, `DEL` is atomic and returns 1/0, which is exactly
        this contract. In memory, dict.pop inside a single coroutine
        is atomic.
        """
        ...

    async def ttl_remaining(self, nonce: Nonce) -> float | None:
        """Seconds until `nonce` expires, or None if it doesn't exist.

        Used for observability: a spike in short remaining TTLs may
        indicate clients that wait too long between nonce and verify.
        Not on the hot path.
        """
        ...
