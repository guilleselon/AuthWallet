"""Almacén de nonces sobre Redis.

`consume` usa un script Lua en lugar de `GETDEL` porque `GETDEL`
requiere Redis 6.2+ y algunos despliegues/forks no lo soportan.
El script Lua es atómico (Redis ejecuta scripts sin interrupciones)
y funciona en cualquier versión desde 2.6.
"""
from __future__ import annotations

import redis.asyncio as redis

from auth_service.domain.types import Nonce

# KEYS[1] = clave del nonce
# Devuelve 1 si existía (y la borra), 0 si no.
_CONSUME_LUA = """
local v = redis.call('GET', KEYS[1])
if v == false then
    return 0
end
redis.call('DEL', KEYS[1])
return 1
"""


class RedisNonceStore:
    def __init__(self, client: redis.Redis, key_prefix: str = "auth:nonce:") -> None:
        self._client = client
        self._prefix = key_prefix
        self._consume_script = client.register_script(_CONSUME_LUA)

    def _key(self, nonce: Nonce) -> str:
        return f"{self._prefix}{nonce}"

    async def put(self, nonce: Nonce, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        await self._client.set(self._key(nonce), "1", ex=ttl_seconds)

    async def consume(self, nonce: Nonce) -> bool:
        result = await self._consume_script(keys=[self._key(nonce)])
        return int(result) == 1

    async def ttl_remaining(self, nonce: Nonce) -> float | None:
        ttl = await self._client.ttl(self._key(nonce))
        return float(ttl) if ttl >= 0 else None
