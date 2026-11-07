from __future__ import annotations

from typing import Any

from relay.domain.errors import InvalidParams
from relay.domain.types import make_topic
from relay.service import MessageRouter

from ..dispatcher import Handler, HandlerContext


def make_unsubscribe_handler(router: MessageRouter) -> Handler:
    async def handle(params: dict[str, Any], ctx: HandlerContext) -> bool:
        topic_raw = params.get("topic")
        if not isinstance(topic_raw, str):
            raise InvalidParams("topic must be a string")
        await router.unsubscribe(ctx.connection_id, make_topic(topic_raw))
        return True

    return handle
