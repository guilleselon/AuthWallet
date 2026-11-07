"""Composition root.

This is the ONLY module that is allowed to import from
`relay.adapters.*`. Every other layer depends on ports, not adapters.
Changing an adapter (memory → Redis) is a one-line edit in `build_server`.
"""
from __future__ import annotations

import asyncio
import itertools
import logging
import signal

from relay.adapters.inbound.websocket import RelayWebSocketServer
from relay.adapters.outbound.in_memory import (
    InMemoryConnectionManager,
    InMemoryMessageStore,
    InMemoryPubSub,
    InMemoryRateLimiter,
    StaticTokenValidator,
)
from relay.config import Config, load_config
from relay.domain.types import MessageId
from relay.protocol import Dispatcher, build_subscription_notification
from relay.protocol.handlers import register_all
from relay.service import AckTracker, MessageRouter, SubscriptionRegistry

logger = logging.getLogger(__name__)


def build_server(config: Config) -> RelayWebSocketServer:
    """Wire all the pieces together and return a ready-to-serve server.

    Side effects: none (no network, no DB). Pure construction, so tests
    can call this without starting anything.
    """
    # --- Outbound adapters (L3) ---
    # The backend switches are read here; in L7 the "redis" branches
    # will import their adapter. For now, only "memory" is implemented.
    if config.store_backend != "memory":
        raise NotImplementedError(
            f"store backend {config.store_backend!r} lands in L7"
        )
    if config.bus_backend != "memory":
        raise NotImplementedError(
            f"bus backend {config.bus_backend!r} lands in L7"
        )

    store = InMemoryMessageStore()
    bus = InMemoryPubSub()
    conn = InMemoryConnectionManager()
    rate = InMemoryRateLimiter(
        capacity=config.rate_capacity,
        refill_rate=config.rate_refill,
    )
    token_validator = StaticTokenValidator(config.tokens)

    # --- Services (L2) ---
    registry = SubscriptionRegistry(
        conn, bus, build_notification=build_subscription_notification
    )
    acks = AckTracker()
    counter = itertools.count(1)

    def next_id() -> MessageId:
        return MessageId(next(counter))

    router = MessageRouter(store, bus, registry, acks, next_id=next_id)

    # --- Protocol (L4) ---
    dispatcher = Dispatcher(rate)
    register_all(dispatcher, router)

    # --- Inbound adapter (L5) ---
    return RelayWebSocketServer(
        host=config.host,
        port=config.port,
        dispatcher=dispatcher,
        connection_manager=conn,
        token_validator=token_validator,
        ack_tracker=acks,
    )


def configure_logging(level: str) -> None:
    """Idempotent logging setup.

    `force=False` and `if not root.handlers` keep repeated calls (tests,
    reloads) from duplicating handlers, which would double every log line.
    """
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
        )
    else:
        root.setLevel(level)


async def run(config: Config) -> None:
    """Start the server and run until cancelled."""
    configure_logging(config.log_level)
    server = build_server(config)
    logger.info(
        "starting relay on %s:%s (store=%s bus=%s tokens=%d)",
        config.host,
        config.port,
        config.store_backend,
        config.bus_backend,
        len(config.tokens),
    )
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            # Windows: signal handlers in asyncio are not supported.
            # Fall back to the default KeyboardInterrupt behavior.
            pass

    async with server.serve():
        await stop.wait()
    logger.info("relay stopped")


def main() -> None:
    """Synchronous entrypoint for `python -m relay`."""
    config = load_config()
    try:
        asyncio.run(run(config))
    except KeyboardInterrupt:
        # Ctrl+C already handled gracefully by `run` when add_signal_handler
        # worked; this catch covers the Windows fallback.
        pass
