"""Builds `irn_subscription` notifications sent to subscribed clients.

Real IRN includes a `publishedAt` timestamp in the payload. We don't
track timestamps in the domain (they're adapter-side metadata), so this
implementation omits that field. Clients that require it can be served
by a future ProtocolVersion-2 adapter without touching the service layer.
"""
from __future__ import annotations

import json

from relay.domain.message import PublishedMessage


def build_subscription_notification(message: PublishedMessage) -> str:
    """Serialize a PublishedMessage into an `irn_subscription` notification.

    Subscription ID = topic. Our ConnectionManager tracks subscriptions
    per (connection, topic), so the topic IS the natural identifier.
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "irn_subscription",
        "params": {
            "id": message.topic,
            "data": {
                "topic": message.topic,
                "message": message.payload,
                "tag": message.tag,
            },
        },
    }
    return json.dumps(payload, separators=(",", ":"))
