"""Session cookie helpers.

The cookie carries only the session ID, signed with `itsdangerous`.
Signing serves two purposes:
    1. Detects tampering: a flipped bit in the cookie is rejected
       before it hits the session store.
    2. Prevents cross-service confusion: a cookie from another service
       that happens to share the storage backend won't validate here.

We do NOT use `URLSafeTimedSerializer`: the session store already
enforces expiry, so a second clock would be redundant and could drift.
Expiry lives in one place.
"""
from __future__ import annotations

from itsdangerous import BadSignature, URLSafeSerializer

from auth_service.domain.errors import SessionNotFound
from auth_service.domain.types import SessionId, make_session_id


def encode_session_cookie(serializer: URLSafeSerializer, session_id: SessionId) -> str:
    """Sign a session ID into a cookie-safe string."""
    return serializer.dumps(session_id)


def decode_session_cookie(serializer: URLSafeSerializer, cookie: str) -> SessionId:
    """Verify and extract a session ID from a cookie.

    Raises `SessionNotFound` on any failure (bad signature, malformed
    payload). The caller folds this into a 401: from the client's view,
    "tampered cookie" and "expired session" are indistinguishable.
    """
    try:
        raw = serializer.loads(cookie)
    except BadSignature as exc:
        raise SessionNotFound("invalid session cookie") from exc
    try:
        return make_session_id(raw)
    except Exception as exc:
        raise SessionNotFound("malformed session id in cookie") from exc
