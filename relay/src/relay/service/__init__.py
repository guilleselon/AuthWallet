"""Service layer: the relay's business logic.

This package orchestrates the ports (`relay.ports`) to implement the
relay's use cases:
    - SubscriptionRegistry: keep PubSub subscriptions in sync with local interest.
    - MessageRouter:        publish, fetch, and route messages.
    - AckTracker:           record client acknowledgments.

Rules for this package:
    - May import from `relay.domain` and `relay.ports`.
    - MUST NOT import from `relay.adapters`, `relay.protocol`, or `relay.main`.
    - MUST NOT import from third-party libraries (redis, websockets, jwt).
"""
from .ack_tracker import AckTracker
from .message_router import MessageRouter
from .subscription_registry import NotificationBuilder, SubscriptionRegistry

__all__ = [
    "AckTracker",
    "MessageRouter",
    "NotificationBuilder",
    "SubscriptionRegistry",
]
