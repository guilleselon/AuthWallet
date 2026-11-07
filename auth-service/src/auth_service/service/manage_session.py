"""Use case: read and revoke sessions.

Used by `/auth/me` and `/auth/logout`. Thin wrappers around
SessionStore, but they centralize the "None → raise SessionNotFound"
policy so every caller sees the same errors.
"""
from __future__ import annotations

from auth_service.domain.errors import SessionNotFound
from auth_service.domain.session import Session
from auth_service.domain.types import SessionId
from auth_service.ports import SessionStore


class ManageSession:
    """Read and revoke sessions."""

    def __init__(self, *, session_store: SessionStore) -> None:
        self._session_store = session_store

    async def get(self, session_id: SessionId) -> Session:
        session = await self._session_store.get(session_id)
        if session is None:
            raise SessionNotFound("session not found or expired")
        return session

    async def logout(self, session_id: SessionId) -> bool:
        """Delete the session. Idempotent: returns True if it existed.

        We do NOT raise when the session was already gone. Logout must
        always succeed from the client's perspective: double logout
        (double click, retry) is common and shouldn't error.
        """
        return await self._session_store.delete(session_id)
