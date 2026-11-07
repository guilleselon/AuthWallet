"""End-to-end smoke test: build the server via the composition root,
connect a real WebSocket client, publish, and verify the response.

This is the closest thing to "run the relay and poke it" that we can
do inside pytest. If this passes, `python -m relay` will work too.
"""
from __future__ import annotations

import asyncio
import itertools
import json

import pytest
import websockets

from relay.config import Config
from relay.domain.types import ProjectId, make_topic
from relay.main import build_server


def _config() -> Config:
    return Config(
        host="127.0.0.1",
        port=0,  # ephemeral: let the OS pick a free port
        tokens={"smoke-token": ProjectId("smoke-project")},
        store_backend="memory",
        bus_backend="memory",
        redis_url="redis://localhost:6379/0",
        log_level="WARNING",
        rate_capacity=10_000,
        rate_refill=1_000.0,
    )


def _topic():
    return make_topic("a" * 64)


@pytest.mark.asyncio
async def test_smoke_publish_over_real_socket():
    server = build_server(_config())
    async with server.serve() as ws_server:
        port = ws_server.sockets[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}/?token=smoke-token"
        async with websockets.connect(url, open_timeout=5) as client:
            await client.send(json.dumps({
                "jsonrpc": "2.0", "id": 1, "method": "irn_publish",
                "params": {
                    "topic": _topic(),
                    "payload": "aG9sYQ==",
                    "ttl": 60,
                    "tag": 1108,
                },
            }))
            raw = await asyncio.wait_for(client.recv(), timeout=5)
            response = json.loads(raw)
            assert response["id"] == 1
            assert response["result"] == {"id": 1}


@pytest.mark.asyncio
async def test_smoke_batch_publish_roundtrip():
    server = build_server(_config())
    async with server.serve() as ws_server:
        port = ws_server.sockets[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}/?token=smoke-token"
        async with websockets.connect(url, open_timeout=5) as client:
            await client.send(json.dumps({
                "jsonrpc": "2.0", "id": 2, "method": "irn_batchPublish",
                "params": {
                    "messages": [
                        {
                            "topic": _topic(),
                            "payload": "aG9sYQ==",
                            "ttl": 60,
                            "tag": 1108,
                        },
                        {
                            "topic": _topic(),
                            "payload": "aG9sYQ==",
                            "ttl": 60,
                            "tag": 1108,
                        },
                    ],
                },
            }))
            raw = await asyncio.wait_for(client.recv(), timeout=5)
            response = json.loads(raw)
            assert response["result"] == {"ids": [1, 2]}
