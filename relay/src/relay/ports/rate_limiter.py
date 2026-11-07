"""Port: per-project rate limiting.

Why this port exists:
    The relay is a trivially abusable endpoint: a single client can
    open thousands of WebSockets and publish millions of messages.
    Rate limiting is not optional; it's part of the security model.

    Limits are scoped by `(projectId, operation)` so that a noisy
    client doesn't penalize other projects, and a chatty method
    (publish) doesn't starve a quiet one (subscribe).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from relay.domain.types import ProjectId


@runtime_checkable
class RateLimiter(Protocol):
    """Token-bucket style rate limiting per project and operation."""

    async def check(
        self,
        project_id: ProjectId,
        operation: str,
        cost: int = 1,
    ) -> None:
        """Consume `cost` tokens for `(project_id, operation)`.

        Raises `relay.domain.errors.RateLimited` if the budget would
        be exceeded. The caller must catch it and translate it into a
        JSON-RPC error response; the connection stays open.

        `operation` is a short, canonical string: "publish", "subscribe",
        "batchFetch", etc. Implementations must treat unknown operations
        by falling back to a conservative default bucket.

        `cost` lets expensive operations consume more: batch_publish
        with 100 messages costs 100, single publish costs 1.
        """
        ...

    async def reset(self, project_id: ProjectId) -> None:
        """Clear all buckets for a project.

        Used by tests and admin tooling. Idempotent.
        Not exposed via any API endpoint: calling it remotely would
        defeat rate limiting entirely.
        """
        ...
