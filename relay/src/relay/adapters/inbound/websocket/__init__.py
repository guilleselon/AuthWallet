"""Inbound WebSocket adapter.

This is the only place in the relay that knows about the `websockets`
library. Every other layer speaks JSON-RPC or domain objects.

Design:
    - `ConnectionHandler` runs the per-connection message loop. It is
      testable with a `FakeWebSocket` (no real sockets needed).
    - `RelayWebSocketServer` binds `websockets.serve()` and creates a
      `ConnectionHandler` per incoming connection. It is thin enough
      that most of its logic is tested via `ConnectionHandler`.
"""
from .connection import ConnectionHandler
from .server import RelayWebSocketServer, parse_token_from_path

__all__ = [
    "ConnectionHandler",
    "RelayWebSocketServer",
    "parse_token_from_path",
]
