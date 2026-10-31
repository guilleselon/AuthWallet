"""Composition root del auth-service. Único módulo que importa adapters."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from itsdangerous import URLSafeSerializer

from auth_service.adapters.inbound.http import create_app
from auth_service.adapters.outbound.eth import SigninWithEthereumSiweService
from auth_service.adapters.outbound.in_memory import (
    InMemoryNonceStore,
    InMemorySessionStore,
    SystemClock,
)
from auth_service.adapters.outbound.redis import RedisNonceStore, RedisSessionStore
from auth_service.config import Config, load_config
from auth_service.service import IssueNonce, ManageSession, VerifyLogin

logger = logging.getLogger(__name__)


def build_app(config: Config) -> FastAPI:
    """Construye la app. Ningún efecto de red aquí; el cliente Redis se conecta lazy."""

    clock = SystemClock()
    siwe = SigninWithEthereumSiweService()
    serializer = URLSafeSerializer(config.cookie_secret)

    # Backends según config
    redis_client = None
    if config.store_backend == "redis":
        import redis.asyncio as redis
        redis_client = redis.Redis.from_url(config.redis_url, decode_responses=True)
        nonces = RedisNonceStore(redis_client)
        sessions = RedisSessionStore(redis_client)
        logger.info("auth-service using Redis store at %s", config.redis_url)
    else:
        nonces = InMemoryNonceStore()
        sessions = InMemorySessionStore()
        logger.info("auth-service using in-memory store")

    issue_nonce = IssueNonce(
        nonce_store=nonces, siwe=siwe, clock=clock,
        domain=config.domain, uri=config.uri, chain_id=config.chain_id,
        nonce_ttl_seconds=config.nonce_ttl_seconds, statement=config.statement,
    )
    verify_login = VerifyLogin(
        nonce_store=nonces, session_store=sessions, siwe=siwe, clock=clock,
        expected_domain=config.domain, expected_chain_id=config.chain_id,
        session_ttl_seconds=config.session_ttl_seconds,
        max_message_age_seconds=config.max_message_age_seconds,
    )
    manage_session = ManageSession(session_store=sessions)

    app = create_app(
        issue_nonce=issue_nonce,
        verify_login=verify_login,
        manage_session=manage_session,
        cookie_serializer=serializer,
        cookie_name=config.cookie_name,
        cookie_secure=config.cookie_secure,
        cors_origins=config.cors_origins,
    )

    # Cierre limpio del cliente Redis al apagar.
    if redis_client is not None:
        _original_shutdown = app.router.on_shutdown
        async def _shutdown_with_redis() -> None:
            if _original_shutdown:
                await _original_shutdown()
            await redis_client.aclose()
        app.router.on_shutdown = [_shutdown_with_redis]

    return app


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
        )
    else:
        root.setLevel(level)


def main() -> None:
    import uvicorn
    uvicorn.run("auth_service.main:app", host="0.0.0.0", port=8000, reload=False)

app = build_app(load_config())
