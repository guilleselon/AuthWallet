"""Protocol layer: JSON-RPC 2.0 framing and IRN method handlers.

Rules:
    - May import from `relay.domain`, `relay.ports`, `relay.service`.
    - MUST NOT import from `relay.adapters` (except in tests).
    - MUST NOT contain business logic: it delegates to `MessageRouter`.
"""
from .dispatcher import Dispatcher, Handler, HandlerContext
from .jsonrpc import (
    Error,
    Request,
    Response,
    error_response,
    parse_request,
    serialize_response,
)
from .notification import build_subscription_notification

__all__ = [
    "Dispatcher",
    "Handler",
    "HandlerContext",
    "Error",
    "Request",
    "Response",
    "error_response",
    "parse_request",
    "serialize_response",
    "build_subscription_notification",
]
