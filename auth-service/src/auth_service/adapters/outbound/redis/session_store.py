"""Session store on Redis.

`create` uses `SET ... EX <ttl>` instead of `EXAT <timestamp>` because
`EXAT` requires Redis 6.2+. We compute the TTL in seconds from
`expires_at` and the current clock.
"""
from __future__ import annotations

import json
import time

import redis.asyncio as redis

from auth_service.domain.session import Session
from auth_service.domain.types import SessionId


class RedisSessionStore:
    def __init__(self, client: redis.Redis, key_prefix: str = "auth:session:") -> None:
        self._client = client
        self._prefix = key_prefix

    def _key(self, session_id: SessionId) -> str:
        return f"{self._prefix}{session_id}"

    async def create(self, session: Session) -> None:
        if session.expires_at <= session.created_at:
            raise ValueError("session already expired")
        ttl_seconds = int(session.expires_at - time.time())
        if ttl_seconds <= 0:
            # The session expired while it was being created (shouldn't happen, but
            # as a safety measure we don't persist it).
            raise ValueError("session expired before persistence")
        payload = json.dumps({
            "id": session.id,
            "address": session.address,
            "chain_id": session.chain_id,
            "created_at": session.created_at,
            "expires_at": session.expires_at,
        })
        await self._client.set(self._key(session.id), payload, ex=ttl_seconds)

    async def get(self, session_id: SessionId) -> Session | None:
        raw = await self._client.get(self._key(session_id))
        if raw is None:
            return None
        data = json.loads(raw)
        session = Session(**data)
        if session.is_expired(time.time()):
            return None
        return session

    async def delete(self, session_id: SessionId) -> bool:
        return (await self._client.delete(self._key(session_id))) > 0
