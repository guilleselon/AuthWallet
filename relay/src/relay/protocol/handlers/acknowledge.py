from __future__ import annotations

from typing import Any

from relay.domain.errors import InvalidParams
from relay.domain.types import MessageId, make_topic
from relay.service import MessageRouter

from ..dispatcher import Handler, HandlerContext


def make_acknowledge_handler(router: MessageRouter) -> Handler:
    async def handle(params: dict[str, Any], ctx: HandlerContext) -> bool:
        topic_raw = params.get("topic")
        if not isinstance(topic_raw, str):
            raise InvalidParams("topic must be a string")
        id_raw = params.get("id")
        if not isinstance(id_raw, int) or isinstance(id_raw, bool):
            raise InvalidParams("id must be an integer")
        await router.acknowledge(
            ctx.connection_id,
            make_topic(topic_raw),
            MessageId(id_raw),
        )
        return True

    return handle
