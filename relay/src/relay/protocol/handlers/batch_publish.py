from __future__ import annotations

from typing import Any

from relay.domain.errors import InvalidParams
from relay.domain.message import PublishRequest
from relay.domain.types import make_payload, make_tag, make_topic, make_ttl
from relay.service import MessageRouter

from ..dispatcher import Handler, HandlerContext


def make_batch_publish_handler(router: MessageRouter) -> Handler:
    async def handle(params: dict[str, Any], ctx: HandlerContext) -> dict[str, Any]:
        raw = params.get("messages")
        if not isinstance(raw, list):
            raise InvalidParams("messages must be a list")

        # Validate all first so a bad entry aborts the whole batch
        # before any message is persisted.
        requests: list[PublishRequest] = []
        for i, entry in enumerate(raw):
            if not isinstance(entry, dict):
                raise InvalidParams(f"messages[{i}] must be an object")
            try:
                requests.append(PublishRequest(
                    topic=make_topic(entry["topic"]),
                    payload=make_payload(entry["payload"]),
                    ttl=make_ttl(entry["ttl"]),
                    tag=make_tag(entry["tag"]),
                    prompt=bool(entry.get("prompt", False)),
                ))
            except KeyError as exc:
                raise InvalidParams(f"messages[{i}] missing {exc.args[0]}") from exc

        ids: list[int] = []
        for request in requests:
            message = await router.publish(request)
            ids.append(message.id)
        return {"ids": ids}

    return handle
