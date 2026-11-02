"""Pydantic DTOs para la API HTTP."""
from __future__ import annotations

from pydantic import BaseModel, Field


class NonceRequest(BaseModel):
    address: str = Field(..., description="Dirección Ethereum con 0x")


class NonceResponse(BaseModel):
    nonce: str
    message: str
    expires_in: int = Field(..., description="Segundos hasta que expira el nonce")


class VerifyRequest(BaseModel):
    message: str = Field(..., description="El mensaje EIP-4361 firmado")
    signature: str = Field(..., description="Firma ECDSA en hexadecimal (0x...)")


class SessionResponse(BaseModel):
    address: str
    chain_id: int
    expires_at: float = Field(..., description="Unix epoch en segundos")
    token: str = Field(..., description="Token de sesión para clientes que no aceptan cookies")


class StatusResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    error: str
