"""Inbound HTTP adapter (FastAPI).

The composition root (L5) imports `create_app` and wires the concrete
services into it. This package MUST NOT import from
`auth_service.adapters.outbound.*` — services are injected.
"""
from .routes import create_app
from .schemas import (
    ErrorResponse,
    NonceRequest,
    NonceResponse,
    SessionResponse,
    StatusResponse,
    VerifyRequest,
)

__all__ = [
    "create_app",
    "ErrorResponse",
    "NonceRequest",
    "NonceResponse",
    "SessionResponse",
    "StatusResponse",
    "VerifyRequest",
]
