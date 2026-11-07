"""In-memory SessionStore with lazy expiry filtering.

`get` returns None for expired sessions even if `sweep()` hasn't run,
so callers can trust the contract "non-None means live".
"""
from __future__ import annotations

import time
from typing import Callable

from auth_service.domain.session import Session
from auth_service.domain.types import SessionId


class InMemorySessionStore:
    """Dict-backed session store. Not thread-safe: one event loop."""

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self._data: dict[SessionId, Session] = {}

    async def create(self, session: Session) -> None:
        if session.expires_at <= session.created_at:
            raise ValueError("session already expired")
        if session.id in self._data:
            raise ValueError(f"duplicate session id: {session.id}")
        self._data[session.id] = session

    async def get(self, session_id: SessionId) -> Session | None:
        session = self._data.get(session_id)
        if session is None:
            return None
        if session.is_expired(self._clock()):
            return None
        return session

    async def delete(self, session_id: SessionId) -> bool:
        return self._data.pop(session_id, None) is not None

    async def sweep(self) -> int:
        """Remove expired sessions. Returns count removed.

        Not part of the SessionStore port: in-memory maintenance hook.
        L6 can call it periodically to bound memory.
        """
        now = self._clock()
        expired = [sid for sid, s in self._data.items() if s.is_expired(now)]
        for sid in expired:
            del self._data[sid]
        return len(expired)
