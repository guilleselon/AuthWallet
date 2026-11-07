"""JSON-RPC dispatcher.

Routes a Request to its handler, applying rate limiting and translating
domain errors into wire-ready error responses.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from relay.domain.errors import RelayError
from relay.domain.types import ConnectionId, ProjectId
from relay.ports import RateLimiter

from .jsonrpc import Error, Request, Response, error_response

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HandlerContext:
    """Per-request information available to every handler."""
    connection_id: ConnectionId
    project_id: ProjectId


Handler = Callable[[dict[str, Any], HandlerContext], Awaitable[Any]]


class Dispatcher:
    """Maps JSON-RPC method names to handlers, with rate limiting."""

    def __init__(self, rate_limiter: RateLimiter) -> None:
        self._handlers: dict[str, Handler] = {}
        self._rate_limiter = rate_limiter

    def register(self, method: str, handler: Handler) -> None:
        if method in self._handlers:
            raise ValueError(f"method already registered: {method}")
        self._handlers[method] = handler

    async def dispatch(self, request: Request, ctx: HandlerContext) -> Response:
        handler = self._handlers.get(request.method)
        if handler is None:
            return Response(
                id=request.id,
                error=Error(
                    code=-32601,
                    message=f"method not found: {request.method}",
                ),
            )
        try:
            await self._rate_limiter.check(ctx.project_id, request.method)
            result = await handler(request.params, ctx)
            return Response(id=request.id, result=result)
        except RelayError as exc:
            return error_response(request.id, exc)
        except Exception:
            logger.exception("unhandled error in %s", request.method)
            return Response(
                id=request.id,
                error=Error(code=-32603, message="internal error"),
            )
