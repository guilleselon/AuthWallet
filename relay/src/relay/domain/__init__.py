"""Public API of the relay domain layer.

Consumers (service/, adapters/, tests/) import from here, not from
internal modules. This keeps the domain's surface area explicit and
lets us refactor internal file layout without breaking callers.
"""
from .errors import (
    InvalidParams,
    InvalidPayload,
    InvalidTag,
    InvalidTopic,
    InvalidTTL,
    PayloadTooLarge,
    RateLimited,
    RelayError,
    SubscriptionNotFound,
    Unauthorized,
)
from .message import PublishedMessage, PublishRequest
from .types import (
    ConnectionId,
    MessageId,
    ProjectId,
    Tag,
    Topic,
    TTL,
    make_payload,
    make_tag,
    make_topic,
    make_ttl,
)

__all__ = [
    # errors
    "RelayError",
    "InvalidParams",
    "InvalidTopic",
    "InvalidPayload",
    "PayloadTooLarge",
    "InvalidTTL",
    "InvalidTag",
    "SubscriptionNotFound",
    "Unauthorized",
    "RateLimited",
    # types
    "Topic",
    "ProjectId",
    "ConnectionId",
    "MessageId",
    "Tag",
    "TTL",
    "make_topic",
    "make_payload",
    "make_ttl",
    "make_tag",
    # messages
    "PublishRequest",
    "PublishedMessage",
]
