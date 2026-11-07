from __future__ import annotations

from typing import Any

from relay.domain.errors import InvalidParams
from relay.domain.types import make_topic
from relay.service import MessageRouter

from ..dispatcher import Handler, HandlerContext


def make_batch_subscribe_handler(router: MessageRouter) -> Handler:
    async def handle(params: dict[str, Any], ctx: HandlerContext) -> dict[str, Any]:
        raw = params.get("topics")
        if not isinstance(raw, list):
            raise InvalidParams("topics must be a list")
        topics = []
        for i, t in enumerate(raw):
            if not isinstance(t, str):
                raise InvalidParams(f"topics[{i}] must be a string")
            topics.append(make_topic(t))

        ids: list[str] = []
        for topic in topics:
            await router.subscribe(ctx.connection_id, topic)
            ids.append(topic)
        return {"ids": ids}

    return handle
