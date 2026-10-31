"""Ports of the auth-service's hexagonal architecture.

A port is a `typing.Protocol`: it defines *what* the service layer needs
from the outside world, without saying *how* it's implemented.

Rules for this package:
    - May import from `auth_service.domain` (the domain's language).
    - May import from stdlib (`typing`, `collections.abc`).
    - MUST NOT import from `auth_service.adapters` or `auth_service.service`.
    - MUST NOT import from third-party libraries
      (signinwithethereum, fastapi, redis, itsdangerous).

The adapters in `auth_service.adapters.outbound.*` implement these protocols.
The service layer in `auth_service.service.*` consumes them.
"""
from .clock import Clock
from .nonce_store import NonceStore
from .session_store import SessionStore
from .siwe import SiweService

__all__ = [
    "Clock",
    "NonceStore",
    "SessionStore",
    "SiweService",
]
