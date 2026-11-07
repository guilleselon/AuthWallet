from __future__ import annotations

from typing import Any

from relay.domain.errors import InvalidParams
from relay.domain.types import MessageId, make_topic
from relay.service import MessageRouter

from ..dispatcher import Handler, HandlerContext


def make_batch_fetch_handler(router: MessageRouter) -> Handler:
    async def handle(params: dict[str, Any], ctx: HandlerContext) -> dict[str, Any]:
        topic_raw = params.get("topic")
        if not isinstance(topic_raw, str):
            raise InvalidParams("topic must be a string")
        after_raw = params.get("after", 0)
        if not isinstance(after_raw, int) or isinstance(after_raw, bool):
            raise InvalidParams("after must be an integer")
        limit_raw = params.get("limit")
        if not isinstance(limit_raw, int) or isinstance(limit_raw, bool):
            raise InvalidParams("limit must be an integer")

        messages = await router.fetch(
            make_topic(topic_raw),
            MessageId(after_raw),
            limit_raw,
        )
        return {
            "messages": [
                {"id": m.id, "message": m.payload, "tag": m.tag}
                for m in messages
            ]
        }

    return handle
