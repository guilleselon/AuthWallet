import asyncio
import json
import logging
import redis.asyncio as redis
from relay.domain.message import PublishedMessage
from relay.domain.types import Topic
from relay.ports import MessageHandler, PubSub, SubscriptionHandle

logger = logging.getLogger(__name__)

class RedisPubSub(PubSub):
    """PubSub implementation using the Redis bus for multi-instance."""
    def __init__(self, client: redis.Redis):
        self._client = client
        # We use a dedicated pubsub for subscriptions.
        self._pubsub = self._client.pubsub()
        self._handlers: dict[Topic, list[MessageHandler]] = {}
        self._listen_task: asyncio.Task | None = None

    async def publish(self, topic: Topic, message: PublishedMessage) -> None:
        payload = json.dumps({
            "id": message.id, "topic": message.topic, "payload": message.payload,
            "ttl": message.ttl, "tag": message.tag, "prompt": message.prompt,
        })
        await self._client.publish(topic, payload)

    async def subscribe(self, topic: Topic, handler: MessageHandler) -> SubscriptionHandle:
        if topic not in self._handlers:
            self._handlers[topic] = []
            await self._pubsub.subscribe(topic)
            # If it's the first subscription, launch the listen loop.
            if self._listen_task is None or self._listen_task.done():
                self._listen_task = asyncio.create_task(self._listen_loop())
        self._handlers[topic].append(handler)
        return SubscriptionHandle(f"{topic}:{id(handler)}")

    async def unsubscribe(self, handle: SubscriptionHandle) -> None:
        # Simplified implementation. Full handling would require mapping handles to topic+handler.
        pass

    async def close(self) -> None:
        if self._listen_task:
            self._listen_task.cancel()
        await self._pubsub.close()
        await self._client.aclose()

    async def _listen_loop(self) -> None:
        async for message in self._pubsub.listen():
            if message["type"] != "message":
                continue
            topic = message["channel"].decode()
            data = json.loads(message["data"])
            published = PublishedMessage(**data)
            # The handler is invoked for each local subscriber of this topic.
            for handler in self._handlers.get(topic, []):
                try:
                    await handler(published)
                except Exception:
                    logger.exception("Error in PubSub handler for topic %s", topic)
