from __future__ import annotations

from typing import Any

from relay.domain.errors import InvalidParams
from relay.domain.message import PublishRequest
from relay.domain.types import make_payload, make_tag, make_topic, make_ttl
from relay.service import MessageRouter

from ..dispatcher import Handler, HandlerContext


def make_publish_handler(router: MessageRouter) -> Handler:
    async def handle(params: dict[str, Any], ctx: HandlerContext) -> dict[str, Any]:
        topic_raw = params.get("topic")
        if not isinstance(topic_raw, str):
            raise InvalidParams("topic must be a string")
        payload_raw = params.get("payload")
        if not isinstance(payload_raw, str):
            raise InvalidParams("payload must be a string")
        ttl_raw = params.get("ttl")
        if not isinstance(ttl_raw, int) or isinstance(ttl_raw, bool):
            raise InvalidParams("ttl must be an integer")
        tag_raw = params.get("tag")
        if not isinstance(tag_raw, int) or isinstance(tag_raw, bool):
            raise InvalidParams("tag must be an integer")
        prompt = bool(params.get("prompt", False))

        request = PublishRequest(
            topic=make_topic(topic_raw),
            payload=make_payload(payload_raw),
            ttl=make_ttl(ttl_raw),
            tag=make_tag(tag_raw),
            prompt=prompt,
        )
        message = await router.publish(request)
        return {"id": message.id}

    return handle
