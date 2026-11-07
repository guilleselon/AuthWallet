"""Development token validator: a fixed token → projectId mapping.

NOT for production. In production, use the JWT validator (L7), which
verifies signatures issued by WalletConnect (or your own auth service).

This one exists because:
    - Tests need to authenticate without generating JWTs.
    - Local development needs a way to connect with `?token=dev-token`
      without spinning up an auth server.

Usage:
    validator = StaticTokenValidator({"dev-token": ProjectId("proj-1")})
    project = validator.validate("dev-token")  # → "proj-1"
    validator.validate("wrong")                # → raises Unauthorized
"""
from __future__ import annotations

from relay.domain.errors import Unauthorized
from relay.domain.types import ProjectId


class StaticTokenValidator:
    """Maps opaque tokens to projectIds. For dev and tests only."""

    def __init__(self, tokens: dict[str, ProjectId]) -> None:
        # Defensive copy: the caller must not be able to mutate the
        # mapping after construction (the validator is effectively
        # read-only).
        self._tokens = dict(tokens)

    def validate(self, token: str) -> ProjectId:
        project_id = self._tokens.get(token)
        if project_id is None:
            raise Unauthorized("unknown token")
        return project_id
