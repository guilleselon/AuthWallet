from __future__ import annotations

from typing import Any

from relay.domain.errors import InvalidParams
from relay.domain.types import make_topic
from relay.service import MessageRouter

from ..dispatcher import Handler, HandlerContext


def make_subscribe_handler(router: MessageRouter) -> Handler:
    async def handle(params: dict[str, Any], ctx: HandlerContext) -> dict[str, Any]:
        topic_raw = params.get("topic")
        if not isinstance(topic_raw, str):
            raise InvalidParams("topic must be a string")
        topic = make_topic(topic_raw)
        await router.subscribe(ctx.connection_id, topic)
        return {"id": topic}

    return handle
