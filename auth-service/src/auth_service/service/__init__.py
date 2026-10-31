"""Service layer: the auth-service's use cases.

Orchestrates ports to implement:
    - IssueNonce:    generate nonce + SIWE message, persist with TTL.
    - VerifyLogin:   consume nonce, verify signature, create session.
    - ManageSession: read and revoke sessions.

Rules for this package:
    - May import from `auth_service.domain` and `auth_service.ports`.
    - MUST NOT import from `auth_service.adapters` or `auth_service.main`.
    - MUST NOT import from third-party libraries.
"""
from .issue_nonce import IssueNonce, NonceResult
from .manage_session import ManageSession
from .verify_login import VerifyLogin

__all__ = [
    "IssueNonce",
    "ManageSession",
    "NonceResult",
    "VerifyLogin",
]
