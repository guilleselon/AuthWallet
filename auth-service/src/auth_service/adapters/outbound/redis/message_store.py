import json
import redis.asyncio as redis
from relay.domain.message import PublishedMessage
from relay.domain.types import MessageId, Topic
from relay.ports import MessageStore

class RedisMessageStore(MessageStore):
    """Almacén de mensajes respaldado por Redis usando Sorted Sets."""
    def __init__(self, client: redis.Redis, key_prefix: str = "relay:msgs:"):
        self._client = client
        self._prefix = key_prefix

    def _key(self, topic: Topic) -> str:
        return f"{self._prefix}{topic}"

    async def add(self, message: PublishedMessage) -> None:
        payload = json.dumps({
            "id": message.id, "topic": message.topic, "payload": message.payload,
            "ttl": message.ttl, "tag": message.tag, "prompt": message.prompt,
        })
        # ZADD añade al Sorted Set. La puntuación (score) es el ID para mantener el orden.
        await self._client.zadd(self._key(message.topic), {payload: message.id})
        # Establecemos un TTL en el conjunto completo. Es una aproximación;
        # una limpieza fina por mensaje requeriría un proceso aparte.
        await self._client.expire(self._key(message.topic), message.ttl)

    async def fetch(self, topic: Topic, after_id: MessageId, limit: int) -> list[PublishedMessage]:
        # ZRANGEBYSCORE obtiene los elementos con score > after_id, ordenados y limitados.
        items = await self._client.zrangebyscore(
            self._key(topic), min=f"({after_id}", max="+inf", start=0, num=limit
        )
        return [PublishedMessage(**json.loads(item)) for item in items]

    async def get(self, topic: Topic, message_id: MessageId) -> PublishedMessage | None:
        # ZSCORE comprueba si el miembro existe en el set.
        # Esta implementación es simplificada; en producción se usaría un hash por mensaje.
        items = await self._client.zrangebyscore(self._key(topic), min=message_id, max=message_id)
        if not items:
            return None
        return PublishedMessage(**json.loads(items[0]))

    async def delete(self, topic: Topic, message_id: MessageId) -> bool:
        # ZREMRANGEBYSCORE elimina por rango de puntuación.
        removed = await self._client.zremrangebyscore(self._key(topic), min=message_id, max=message_id)
        return removed > 0

    async def count(self, topic: Topic) -> int:
        return await self._client.zcard(self._key(topic))
