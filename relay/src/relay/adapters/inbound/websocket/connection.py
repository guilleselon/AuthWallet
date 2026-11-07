"""Per-connection message loop.

Responsibilities:
    1. Register with the ConnectionManager on start, unregister on end.
    2. Read raw strings from the WebSocket and dispatch them as JSON-RPC.
    3. Serialize responses and send them back, honoring the "no id = no
       response" rule of JSON-RPC 2.0 notifications.
    4. Serialize sends per connection (concurrent sends are not safe on
       a WebSocket).

What this file does NOT do:
    - Auth (that's the server's job before creating the handler).
    - Business logic (that's `MessageRouter`).
    - JSON-RPC framing beyond delegating to L4 (parse/dispatch/serialize).
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import websockets

from relay.domain.errors import InvalidParams
from relay.domain.types import ConnectionId, ProjectId
from relay.ports import ConnectionManager
from relay.protocol import (
    Dispatcher,
    Error,
    HandlerContext,
    Response,
    parse_request,
    serialize_response,
)
from relay.service import AckTracker

logger = logging.getLogger(__name__)


class ConnectionHandler:
    """Runs the message loop for a single WebSocket connection."""

    def __init__(
        self,
        *,
        connection_id: ConnectionId,
        project_id: ProjectId,
        dispatcher: Dispatcher,
        connection_manager: ConnectionManager,
        ack_tracker: AckTracker,
    ) -> None:
        self._connection_id = connection_id
        self._project_id = project_id
        self._dispatcher = dispatcher
        self._connections = connection_manager
        self._acks = ack_tracker
        self._ctx = HandlerContext(
            connection_id=connection_id,
            project_id=project_id,
        )
        self._websocket: Any = None
        self._send_lock = asyncio.Lock()

    async def run(self, websocket: Any) -> None:
        """Main entry point. Registers, loops, cleans up."""
        self._websocket = websocket
        try:
            await self._connections.register(self._connection_id, self._send)
        except Exception:
            self._websocket = None
            raise

        try:
            await self._loop()
        finally:
            # Drop the websocket reference BEFORE unregistering so any
            # in-flight `_send` from a background task becomes a no-op.
            self._websocket = None
            await self._connections.unregister(self._connection_id)
            self._acks.forget_connection(self._connection_id)
            logger.info("connection %s closed", self._connection_id)

    async def _loop(self) -> None:
        try:
            async for raw in self._websocket:
                await self._process(raw)
        except websockets.ConnectionClosed:
            pass  # normal client disconnect

    async def _process(self, raw: Any) -> None:
        if isinstance(raw, bytes):
            try:
                raw = raw.decode("utf-8")
            except UnicodeDecodeError:
                await self._send_parse_error("payload is not valid utf-8")
                return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            await self._send_parse_error(f"invalid json: {exc.msg}")
            return

        try:
            request = parse_request(data)
        except InvalidParams as exc:
            await self._send_invalid_request(str(exc))
            return

        response = await self._dispatcher.dispatch(request, self._ctx)

        # JSON-RPC 2.0: a notification (no id) never gets a response.
        if request.id is not None:
            await self._send(json.dumps(serialize_response(response)))

    async def _send(self, payload: str) -> None:
        """Serialize writes to the underlying WebSocket.

        Called both by the message loop (responses) and by the
        ConnectionManager (broadcast notifications from PubSub). The
        lock ensures no two coroutines write concurrently.
        """
        async with self._send_lock:
            if self._websocket is None:
                return
            try:
                await self._websocket.send(payload)
            except websockets.ConnectionClosed:
                # Race with client disconnect; the loop will exit on
                # its own. Nothing useful to do here.
                pass

    async def _send_parse_error(self, message: str) -> None:
        await self._send(json.dumps(serialize_response(Response(
            id=None,
            error=Error(code=-32700, message=message),
        ))))

    async def _send_invalid_request(self, message: str) -> None:
        await self._send(json.dumps(serialize_response(Response(
            id=None,
            error=Error(code=-32600, message=message),
        ))))
