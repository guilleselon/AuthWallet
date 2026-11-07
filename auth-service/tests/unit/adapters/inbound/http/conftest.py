"""Fixtures: a fully wired FastAPI app over in-memory adapters + real SIWE.

The test stack is:
    real FastAPI app → real services → real in-memory adapters
                                     → real signinwithethereum adapter

No mocks. If this passes, a real wallet signature will verify in prod.
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from itsdangerous import URLSafeSerializer

from auth_service.adapters.inbound.http import create_app
from auth_service.adapters.outbound.eth import SigninWithEthereumSiweService
from auth_service.adapters.outbound.in_memory import (
    InMemoryNonceStore,
    InMemorySessionStore,
    SystemClock,
)
from auth_service.domain.types import make_chain_id
from auth_service.service import IssueNonce, ManageSession, VerifyLogin


DOMAIN = "auth.test"
URI = "http://auth.test"
CHAIN_ID = make_chain_id(56)
SECRET = "test-secret-do-not-use-in-prod"
COOKIE_NAME = "auth_session"


@pytest.fixture
def app_ctx():
    clock = SystemClock()
    nonces = InMemoryNonceStore()
    sessions = InMemorySessionStore()
    siwe = SigninWithEthereumSiweService()

    issue_nonce = IssueNonce(
        nonce_store=nonces,
        siwe=siwe,
        clock=clock,
        domain=DOMAIN,
        uri=URI,
        chain_id=CHAIN_ID,
        nonce_ttl_seconds=300,
        statement="Sign in to auth.test",
    )
    verify_login = VerifyLogin(
        nonce_store=nonces,
        session_store=sessions,
        siwe=siwe,
        clock=clock,
        expected_domain=DOMAIN,
        expected_chain_id=CHAIN_ID,
        session_ttl_seconds=86400,
        max_message_age_seconds=600,
    )
    manage_session = ManageSession(session_store=sessions)
    serializer = URLSafeSerializer(SECRET)

    app = create_app(
        issue_nonce=issue_nonce,
        verify_login=verify_login,
        manage_session=manage_session,
        cookie_serializer=serializer,
        cookie_name=COOKIE_NAME,
        cookie_secure=False,  # test uses plain http
    )
    return {
        "app": app,
        "clock": clock,
        "sessions": sessions,
        "cookie_name": COOKIE_NAME,
    }


@pytest.fixture
async def client(app_ctx):
    async with AsyncClient(
        transport=ASGITransport(app=app_ctx["app"]),
        base_url="http://test",
    ) as c:
        yield c
