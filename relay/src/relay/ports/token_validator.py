"""Port: authentication of relay clients.

Why this port exists:
    Every WebSocket connection to the relay must present a JWT issued
    by WalletConnect (or by your own auth-service, if you control
    the whole stack). The JWT carries a `projectId` claim that
    identifies the client application. Rate limits, metrics, and
    isolation are all keyed by `projectId`.

    The relay must NEVER accept an unauthenticated connection:
    it's a DoS vector and a protocol correctness issue.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from relay.domain.types import ProjectId


@runtime_checkable
class TokenValidator(Protocol):
    """Validates JWTs and extracts the projectId."""

    def validate(self, token: str) -> ProjectId:
        """Return the projectId encoded in the JWT.

        Raises `relay.domain.errors.Unauthorized` if:
            - the token is malformed,
            - the signature is invalid,
            - the token is expired or not yet valid,
            - the `projectId` claim is missing or malformed.

        Implementations MUST NOT return an empty or placeholder
        `ProjectId`. If in doubt, raise.

        Why sync: JWT validation is CPU-bound (HMAC or RSA verify)
        and takes microseconds to low milliseconds. Making it async
        would force the WebSocket accept handler to await on
        something that never yields, which is strictly worse.
        If a future adapter calls a remote auth server, we'll
        introduce a separate async port (`RemoteTokenValidator`)
        rather than retrofitting this one.
        """
        ...
