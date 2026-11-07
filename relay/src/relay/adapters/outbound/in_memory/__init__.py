"""In-memory implementations of the relay's outbound ports.

Used for:
    - Local development (no Redis needed).
    - Unit tests of the service layer (fast, deterministic).
    - Single-instance deployments with modest load.

These are NOT toys: they are correct, complete implementations of the
ports. They only differ from the Redis adapters in scalability and
persistence, not in behavior.

If you need multi-instance routing, swap InMemoryPubSub for RedisPubSub.
If you need persistence across restarts, swap InMemoryMessageStore for
RedisMessageStore. The service layer will not notice the difference.
"""
from .connection_manager import InMemoryConnectionManager
from .message_store import InMemoryMessageStore
from .pubsub import InMemoryPubSub
from .rate_limiter import InMemoryRateLimiter
from .static_token_validator import StaticTokenValidator

__all__ = [
    "InMemoryConnectionManager",
    "InMemoryMessageStore",
    "InMemoryPubSub",
    "InMemoryRateLimiter",
    "StaticTokenValidator",
]
