"""In-memory implementations of the auth-service's outbound ports.

Used for local development, unit tests, and single-process deployments.
They are correct, complete implementations of the ports; they only
differ from the Redis adapters in scalability and persistence.
"""
from .nonce_store import InMemoryNonceStore
from .session_store import InMemorySessionStore
from .system_clock import SystemClock

__all__ = [
    "InMemoryNonceStore",
    "InMemorySessionStore",
    "SystemClock",
]
