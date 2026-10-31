"""Pydantic DTOs for the HTTP API.

These are the wire format. They are intentionally separate from the
domain objects: renaming a domain field should not change the public
API, and vice versa.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class NonceRequest(BaseModel):
    address: str = Field(..., description="0x-prefixed Ethereum address")


class NonceResponse(BaseModel):
    nonce: str
    message: str
    expires_in: int = Field(..., description="Seconds until nonce expires")


class VerifyRequest(BaseModel):
    message: str = Field(..., description="The EIP-4361 message that was signed")
    signature: str = Field(..., description="Hex-encoded ECDSA signature (0x...)")


class SessionResponse(BaseModel):
    address: str
    chain_id: int
    expires_at: float = Field(..., description="Unix epoch seconds")


class StatusResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    error: str
