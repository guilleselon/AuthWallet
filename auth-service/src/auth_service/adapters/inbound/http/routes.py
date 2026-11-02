"""FastAPI app factory para el auth service."""
from __future__ import annotations

from typing import Iterable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from itsdangerous import URLSafeSerializer

from auth_service.domain.errors import AuthError, SessionNotFound
from auth_service.domain.types import SessionId, make_address
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


def _get_session_id(request: Request, cookie_name: str, serializer: URLSafeSerializer) -> SessionId:
    """Extrae el ID de sesión desde el Header Bearer o desde la Cookie."""
    # 1. Intentar por Header (Trust Wallet, dapps móviles)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
        return decode_session_cookie(serializer, token)
    
    # 2. Intentar por Cookie (MetaMask, escritorio)
    cookie = request.cookies.get(cookie_name)
    if cookie:
        return decode_session_cookie(serializer, cookie)
    
    raise SessionNotFound("no session provided")


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
            allow_headers=["Content-Type", "Authorization"], # Permitir cabecera Authorization
        )

    @app.exception_handler(AuthError)
    async def _auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content=ErrorResponse(error=str(exc)).model_dump(),
        )

    @app.get("/health", response_model=StatusResponse)
    async def health() -> StatusResponse:
        return StatusResponse(status="ok")

    @app.post("/auth/nonce", response_model=NonceResponse)
    async def post_nonce(body: NonceRequest) -> NonceResponse:
        address = make_address(body.address)
        result = await issue_nonce.issue(address)
        return NonceResponse(
            nonce=result.nonce,
            message=result.message,
            expires_in=result.expires_in,
        )

    @app.post("/auth/verify", response_model=SessionResponse)
    async def post_verify(body: VerifyRequest, response: Response) -> SessionResponse:
        session = await verify_login.verify(
            message=body.message, signature=body.signature
        )
        initial_ttl = int(session.expires_at - session.created_at)
        
        # Generamos el token firmado
        token = encode_session_cookie(cookie_serializer, session.id)

        # Seteamos la cookie para navegadores que la soporten
        response.set_cookie(
            key=cookie_name,
            value=token,
            max_age=initial_ttl,
            httponly=True,
            secure=cookie_secure,
            samesite="none",
            path="/",
        )
        
        # Devolvemos el token en el JSON
        return SessionResponse(
            address=session.address,
            chain_id=session.chain_id,
            expires_at=session.expires_at,
            token=token,
        )

    @app.get("/auth/me", response_model=SessionResponse)
    async def get_me(request: Request) -> SessionResponse:
        session_id = _get_session_id(request, cookie_name, cookie_serializer)
        session = await manage_session.get(session_id)
        return SessionResponse(
            address=session.address,
            chain_id=session.chain_id,
            expires_at=session.expires_at,
            token=encode_session_cookie(cookie_serializer, session.id), # Devolvemos el token por consistencia
        )

    @app.post("/auth/logout", response_model=StatusResponse)
    async def post_logout(request: Request, response: Response) -> StatusResponse:
        try:
            session_id = _get_session_id(request, cookie_name, cookie_serializer)
            await manage_session.logout(session_id)
        except SessionNotFound:
            pass # Idempotente
            
        response.delete_cookie(key=cookie_name, path="/")
        return StatusResponse(status="logged_out")

    return app
