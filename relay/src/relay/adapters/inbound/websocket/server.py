"""WebSocket server: binds connections to ConnectionHandlers.

Responsibilities:
    1. Authenticate the token in the query string.
    2. Allocate a ConnectionId.
    3. Create a ConnectionHandler and hand it the WebSocket.

What this file does NOT do:
    - JSON parsing (handler).
    - Dispatch (handler + dispatcher).
    - Business logic (services).
"""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from urllib.parse import parse_qs, urlparse

import websockets

from relay.domain.errors import Unauthorized
from relay.domain.types import ConnectionId
from relay.ports import ConnectionManager, TokenValidator
from relay.protocol import Dispatcher
from relay.service import AckTracker

from .connection import ConnectionHandler

logger = logging.getLogger(__name__)

# WC-convention close code for authentication failures.
# Codes 4000-4999 are reserved for application use.
_CLOSE_UNAUTHORIZED = 4001


def parse_token_from_path(path: str) -> str | None:
    """Extract `token` from a request path like `/?token=abc`.

    Returns `None` if the query is absent or `token` is missing.
    Returns `""` if the parameter is present but empty (`/?token=`).
    The distinction matters: the server rejects both, but with
    different close reasons, which aids debugging.

    `keep_blank_values=True` is required because `parse_qs` drops
    empty parameters by default.
    """
    parsed = urlparse(path)
    query = parse_qs(parsed.query, keep_blank_values=True)
    tokens = query.get("token", [])
    return tokens[0] if tokens else None


class RelayWebSocketServer:
    """WebSocket server. Owns lifecycle, delegates work to handlers."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        dispatcher: Dispatcher,
        connection_manager: ConnectionManager,
        token_validator: TokenValidator,
        ack_tracker: AckTracker,
    ) -> None:
        self._host = host
        self._port = port
        self._dispatcher = dispatcher
        self._connections = connection_manager
        self._token_validator = token_validator
        self._acks = ack_tracker

    @asynccontextmanager
    async def serve(self) -> AsyncIterator[Any]:
        """Bind and yield the underlying websockets server.

        Use as `async with server.serve() as ws_server: ...`.
        Tests use this to start on port 0 and stop cleanly.
        """
        async with websockets.serve(
            self._accept, self._host, self._port,
            # Subprotocol negotiation: WC uses "wcn" or "wc" depending on
            # version. We accept any subprotocol to stay future-proof.
            subprotocols=None,
        ) as server:
            logger.info(
                "relay ws server listening on %s:%s",
                self._host,
                server.sockets[0].getsockname()[1],
            )
            yield server

    async def serve_forever(self) -> None:
        """Run forever. Use from main()."""
        import asyncio
        async with self.serve():
            await asyncio.Future()

    async def _accept(self, websocket: Any) -> None:
        path = self._extract_path(websocket)
        token = parse_token_from_path(path) if path else None

        if token is None:
            await websocket.close(_CLOSE_UNAUTHORIZED, "missing token")
            return

        try:
            project_id = self._token_validator.validate(token)
        except Unauthorized:
            await websocket.close(_CLOSE_UNAUTHORIZED, "invalid token")
            return
        except Exception:
            logger.exception("unexpected error in token validation")
            await websocket.close(_CLOSE_UNAUTHORIZED, "auth error")
            return

        connection_id = ConnectionId(uuid.uuid4().hex)
        logger.info(
            "connection %s opened (project=%s)",
            connection_id,
            project_id,
        )
        handler = ConnectionHandler(
            connection_id=connection_id,
            project_id=project_id,
            dispatcher=self._dispatcher,
            connection_manager=self._connections,
            ack_tracker=self._acks,
        )
        await handler.run(websocket)

    @staticmethod
    def _extract_path(websocket: Any) -> str | None:
        # `websockets` v12+: `websocket.request.path`.
        # Older versions: `websocket.path`.
        request = getattr(websocket, "request", None)
        if request is not None:
            path = getattr(request, "path", None)
            if path is not None:
                return path
        return getattr(websocket, "path", None)
