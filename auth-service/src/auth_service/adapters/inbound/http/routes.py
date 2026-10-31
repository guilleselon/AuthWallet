"""FastAPI app factory for the auth service.

Design notes:
    - The app is a *factory* (`create_app`), not a module-level instance.
      This keeps services injectable and tests isolated.
    - Services are captured by closure, NOT declared as route parameters.
      FastAPI inspects route signatures and would try to interpret a
      service class as a query parameter — which fails loudly at startup.
    - Errors are handled by a single exception handler for `AuthError`.
      The handler uses `exc.http_status`, so the domain keeps control
      of status codes without the adapter having to `isinstance` per error.
    - Session cookie is `HttpOnly`, `SameSite=Lax`, `Secure` configurable.
      `Lax` mitigates CSRF for login/logout/me. Sensitive mutations would
      need `Strict` or a CSRF token.
"""
from __future__ import annotations

from typing import Iterable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from itsdangerous import URLSafeSerializer

from auth_service.domain.errors import AuthError, SessionNotFound
from auth_service.domain.types import make_address
from auth_service.service import IssueNonce, ManageSession, VerifyLogin

from .cookies import decode_session_cookie, encode_session_cookie
from .schemas import (
    ErrorResponse,
    NonceRequest,
    NonceResponse,
    SessionResponse,
    StatusResponse,
    VerifyRequest,
)

_DEFAULT_COOKIE_NAME = "auth_session"


def create_app(
    *,
    issue_nonce: IssueNonce,
    verify_login: VerifyLogin,
    manage_session: ManageSession,
    cookie_serializer: URLSafeSerializer,
    cookie_name: str = _DEFAULT_COOKIE_NAME,
    cookie_secure: bool = True,
    cors_origins: Iterable[str] = (),
) -> FastAPI:
    app = FastAPI(title="auth-service", version="0.1.0")

    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )

    # --- Error handler: every AuthError carries its own status ---
    @app.exception_handler(AuthError)
    async def _auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content=ErrorResponse(error=str(exc)).model_dump(),
        )

    # --- Healthcheck ---
    @app.get("/health", response_model=StatusResponse)
    async def health() -> StatusResponse:
        return StatusResponse(status="ok")

    # --- POST /auth/nonce ---
    @app.post("/auth/nonce", response_model=NonceResponse)
    async def post_nonce(body: NonceRequest) -> NonceResponse:
        address = make_address(body.address)
        result = await issue_nonce.issue(address)
        return NonceResponse(
            nonce=result.nonce,
            message=result.message,
            expires_in=result.expires_in,
        )

    # --- POST /auth/verify ---
    @app.post("/auth/verify", response_model=SessionResponse)
    async def post_verify(body: VerifyRequest, response: Response) -> SessionResponse:
        session = await verify_login.verify(
            message=body.message, signature=body.signature
        )
        # Set the session cookie. `max_age` uses the initial TTL: the
        # session was created at the same instant the cookie is set,
        # so `expires_at - created_at` equals remaining time.
        initial_ttl = int(session.expires_at - session.created_at)
        response.set_cookie(
            key=cookie_name,
            value=encode_session_cookie(cookie_serializer, session.id),
            max_age=initial_ttl,
            httponly=True,
            secure=cookie_secure,
            samesite="none",
            path="/",
        )
        return SessionResponse(
            address=session.address,
            chain_id=session.chain_id,
            expires_at=session.expires_at,
        )

    # --- GET /auth/me ---
    @app.get("/auth/me", response_model=SessionResponse)
    async def get_me(request: Request) -> SessionResponse:
        cookie = request.cookies.get(cookie_name)
        if cookie is None:
            raise SessionNotFound("no session cookie")
        session_id = decode_session_cookie(cookie_serializer, cookie)
        session = await manage_session.get(session_id)
        return SessionResponse(
            address=session.address,
            chain_id=session.chain_id,
            expires_at=session.expires_at,
        )

    # --- POST /auth/logout ---
    @app.post("/auth/logout", response_model=StatusResponse)
    async def post_logout(request: Request, response: Response) -> StatusResponse:
        cookie = request.cookies.get(cookie_name)
        if cookie is not None:
            try:
                session_id = decode_session_cookie(cookie_serializer, cookie)
                await manage_session.logout(session_id)
            except SessionNotFound:
                # Idempotent logout: bad cookie is treated as "no session".
                pass
        # Always clear the cookie, even if the session was already gone.
        response.delete_cookie(key=cookie_name, path="/")
        return StatusResponse(status="logged_out")

    return app
