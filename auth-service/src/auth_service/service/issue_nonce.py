"""Use case: issue a nonce and the SIWE message to sign.

The client calls `/auth/nonce` with its address. We return a fresh
nonce (stored with TTL) and a fully formatted EIP-4361 message the
wallet can display and sign. The message already embeds the nonce,
domain, uri, chain_id and timestamps; the client signs it verbatim.
"""
from __future__ import annotations

from dataclasses import dataclass

from auth_service.domain.siwe import format_iso8601
from auth_service.domain.types import (
    Address,
    ChainId,
    Nonce,
    make_nonce_fresh,
)
from auth_service.ports import Clock, NonceStore, SiweService


@dataclass(frozen=True)
class NonceResult:
    """Result of issuing a nonce. Returned to the HTTP adapter."""

    nonce: Nonce
    message: str
    expires_in: int


class IssueNonce:
    """Issues nonces and builds the corresponding SIWE message."""

    def __init__(
        self,
        *,
        nonce_store: NonceStore,
        siwe: SiweService,
        clock: Clock,
        domain: str,
        uri: str,
        chain_id: ChainId,
        nonce_ttl_seconds: int = 300,
        statement: str | None = None,
    ) -> None:
        if nonce_ttl_seconds <= 0:
            raise ValueError("nonce_ttl_seconds must be positive")
        self._nonce_store = nonce_store
        self._siwe = siwe
        self._clock = clock
        self._domain = domain
        self._uri = uri
        self._chain_id = chain_id
        self._ttl = nonce_ttl_seconds
        self._statement = statement

    async def issue(self, address: Address) -> NonceResult:
        """Issue a nonce for `address` and return the signed-message-to-be.

        Order matters: persist the nonce BEFORE returning the message.
        If we returned the message first and the store failed, a client
        could sign and call verify with a nonce we never recorded. By
        persisting first, "returned message" implies "nonce is valid".
        """
        nonce = make_nonce_fresh()
        await self._nonce_store.put(nonce, self._ttl)

        now = self._clock.now()
        issued_at = format_iso8601(now)
        expiration_time = format_iso8601(now + self._ttl)

        message = self._siwe.build_message(
            domain=self._domain,
            address=address,
            uri=self._uri,
            chain_id=self._chain_id,
            nonce=nonce,
            issued_at=issued_at,
            statement=self._statement,
            expiration_time=expiration_time,
        )
        return NonceResult(nonce=nonce, message=message, expires_in=self._ttl)
