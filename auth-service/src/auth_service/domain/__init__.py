"""Public API of the auth-service domain layer.

Consumers (service/, adapters/, tests/) import from here, not from
internal modules. This keeps the domain's surface area explicit and
lets us refactor internal file layout without breaking callers.

Rules for this package:
    - May import only stdlib (no third-party libraries).
    - MUST NOT import from `relay.*`, `auth_service.adapters.*`,
      `auth_service.service.*`, or `auth_service.ports.*`.
"""
from .errors import (
    AuthError,
    InvalidAddress,
    InvalidChainId,
    InvalidNonce,
    InvalidSessionId,
    NonceAlreadyUsed,
    NonceExpired,
    NonceNotFound,
    SessionExpired,
    SessionNotFound,
    SignatureVerificationFailed,
)
from .session import Session
from .types import (
    Address,
    ChainId,
    Nonce,
    SessionId,
    make_address,
    make_chain_id,
    make_nonce,
    make_session_id,
)

from .siwe import (
    ParsedSiweMessage,
    format_iso8601,
    parse_iso8601,
    parse_message,
)

__all__ = [
    # errors
    "AuthError",
    "InvalidAddress",
    "InvalidChainId",
    "InvalidNonce",
    "InvalidSessionId",
    "NonceAlreadyUsed",
    "NonceExpired",
    "NonceNotFound",
    "SessionExpired",
    "SessionNotFound",
    "SignatureVerificationFailed",
    # types
    "Address",
    "ChainId",
    "Nonce",
    "SessionId",
    "make_address",
    "make_chain_id",
    "make_nonce",
    "make_session_id",
    # values
    "Session",
    "ParsedSiweMessage",
    "format_iso8601",
    "parse_iso8601",
    "parse_message",
]
