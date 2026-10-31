"""Domain errors for the auth service.

Unlike the relay (which speaks JSON-RPC and carries protocol codes),
the auth service speaks HTTP. Each error carries the HTTP status that
the transport layer should return, so the inbound adapter never has to
do a chain of isinstance checks: it just catches `AuthError` and uses
`exc.http_status`.
"""


class AuthError(Exception):
    """Base class for all auth-service domain errors."""

    http_status: int = 500


# --- Parameter errors (client's fault, retriable after fixing input) ---

class InvalidAddress(AuthError):
    """Address is not a valid 0x-prefixed 20-byte hex string."""

    http_status = 400


class InvalidNonce(AuthError):
    """Nonce is not a valid 32-byte hex string."""

    http_status = 400


class InvalidChainId(AuthError):
    """Chain ID is not a positive integer within the supported range."""

    http_status = 400


class InvalidSessionId(AuthError):
    """Session ID is empty or malformed."""

    http_status = 400


# --- Nonce lifecycle errors (client must request a new nonce) ---

class NonceNotFound(AuthError):
    """Nonce was never issued, or has already been consumed.

    We intentionally do NOT distinguish "never existed" from "already
    used" in the message sent to the client: telling an attacker which
    is which provides no value and helps them enumerate.
    """

    http_status = 400


class NonceExpired(AuthError):
    """Nonce was issued but its TTL has passed."""

    http_status = 400


class NonceAlreadyUsed(AuthError):
    """Nonce was already consumed by a previous successful login.

    Kept as a distinct class internally for logging; the public error
    response folds it into `NonceNotFound`.
    """

    http_status = 400


# --- Signature / authentication failures ---

class SignatureVerificationFailed(AuthError):
    """Signature is malformed, doesn't match the message, or the
    recovered address doesn't match the claimed address."""

    http_status = 401


# --- Session errors ---

class SessionNotFound(AuthError):
    """Session ID doesn't exist or was already logged out."""

    http_status = 401


class SessionExpired(AuthError):
    """Session existed but has passed its TTL."""

    http_status = 401
