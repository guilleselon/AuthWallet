"""Port: persistent storage of authenticated sessions.

Why this port exists:
    After a successful `/auth/verify`, the user has a session. That
    session must be readable on every subsequent request (`/auth/me`,
    protected endpoints), which may land on any worker process. This
    is the session store.

    The store is intentionally session-opaque: it stores `Session`
    objects and returns them. Expiry filtering is the store's job
    (return None for expired), so the service layer doesn't need to
    re-implement time logic on every read.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from auth_service.domain.session import Session
from auth_service.domain.types import SessionId


@runtime_checkable
class SessionStore(Protocol):
    """Stores active sessions, filtered by expiry on read."""

    async def create(self, session: Session) -> None:
        """Store `session` as active.

        Implementations must:
            - Reject sessions whose `expires_at <= created_at` (raise
              ValueError): a pre-expired session is a bug upstream.
            - Configure their own TTL from `session.expires_at` when
              the backend supports it (Redis EXPIREAT), so expired
              sessions are reclaimed even if no one reads them.
            - Raise ValueError on duplicate `session.id`.
        """
        ...

    async def get(self, session_id: SessionId) -> Session | None:
        """Return the session, or None if it doesn't exist or expired.

        "Expired" is judged by the store using its own clock (or the
        backend's TTL). Implementations that can't reliably filter
        (e.g. Redis whose TTL hasn't fired yet) must still filter
        lazily by comparing `expires_at` to `time.time()` on read.

        This keeps the contract honest: a caller can trust that a
        non-None return is a live session.
        """
        ...

    async def delete(self, session_id: SessionId) -> bool:
        """Remove the session. Returns True if it existed.

        Used by `/auth/logout`. Idempotent in behavior: deleting an
        unknown ID returns False and does not raise.
        """
        ...
