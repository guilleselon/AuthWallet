"""Domain errors with JSON-RPC 2.0 compatible codes.

JSON-RPC 2.0 reserved ranges:
    -32700 .. -32600   transport / parse errors
    -32000 .. -32099   implementation-defined server errors

WalletConnect IRN uses the server-error range for auth and rate limits.
Reference: https://www.jsonrpc.org/specification#error_object
"""


class RelayError(Exception):
    """Base class for all domain errors. Maps to a JSON-RPC error code."""

    code: int = -32603  # generic internal error


# --- Parameter errors (client's fault) ---

class InvalidParams(RelayError):
    """Client sent parameters that don't satisfy the protocol."""

    code = -32602


class InvalidTopic(InvalidParams):
    pass


class InvalidPayload(InvalidParams):
    pass


class PayloadTooLarge(InvalidParams):
    """Payload exceeds the maximum encoded size.

    Inherits -32602: it's a client-parameter problem, not a server fault.
    """


class InvalidTTL(InvalidParams):
    pass


class InvalidTag(InvalidParams):
    pass


class SubscriptionNotFound(InvalidParams):
    pass


# --- Server-side errors (implementation range) ---

class Unauthorized(RelayError):
    """JWT missing, expired, or invalid for this project."""

    code = -32001


class RateLimited(RelayError):
    """Client exceeded its rate budget for this method."""

    code = -32005
