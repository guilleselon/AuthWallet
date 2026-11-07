"""Ports of the relay's hexagonal architecture.

A port is a `typing.Protocol`: it defines *what* the service layer needs
from the outside world, without saying *how* it's implemented.

Rules for this package:
    - May import from `relay.domain` (the domain's language).
    - May import from stdlib (`typing`, `collections.abc`).
    - MUST NOT import from `relay.adapters` or `relay.service`.
    - MUST NOT import from third-party libraries (redis, websockets, jwt).

The adapters in `relay.adapters.outbound.*` implement these protocols.
The service layer in `relay.service.*` consumes them.
"""
from .connection_manager import ConnectionManager, MessageSender
from .message_store import MessageStore
from .pubsub import MessageHandler, PubSub, SubscriptionHandle
from .rate_limiter import RateLimiter
from .token_validator import TokenValidator

__all__ = [
    "ConnectionManager",
    "MessageHandler",
    "MessageSender",
    "MessageStore",
    "PubSub",
    "SubscriptionHandle",
    "RateLimiter",
    "TokenValidator",
]
