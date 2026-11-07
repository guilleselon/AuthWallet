"""Use case: verify a signed SIWE message and create a session.

The client calls `/auth/verify` with `{message, signature}`. We:
    1. Parse the message to extract nonce, domain, chain_id, issued_at.
    2. Reject if domain or chain_id don't match our expectations.
    3. Consume the nonce atomically (anti-replay).
    4. Verify the signature, recovering the signer's address.
    5. Confirm the recovered address matches the message's address.
    6. Create a session and return it.

Nonce consumption happens BEFORE signature verification. Why:
    If verification failed first and nonce consumption came after, an
    attacker with a captured nonce could try thousands of signatures
    against it. Consuming on the first attempt forces one nonce = one
    try. Failures still burn the nonce (client must request a new one),
    which is acceptable UX.
"""
from __future__ import annotations

from auth_service.domain.errors import (
    NonceNotFound,
    SignatureVerificationFailed,
)
from auth_service.domain.session import Session
from auth_service.domain.siwe import parse_iso8601, parse_message
from auth_service.domain.types import (
    ChainId,
    SessionId,
    make_session_id_fresh,
)
from auth_service.ports import (
    Clock,
    NonceStore,
    SessionStore,
    SiweService,
)


class VerifyLogin:
    """Verifies a signed SIWE message and issues a session."""

    def __init__(
        self,
        *,
        nonce_store: NonceStore,
        session_store: SessionStore,
        siwe: SiweService,
        clock: Clock,
        expected_domain: str,
        expected_chain_id: ChainId,
        session_ttl_seconds: int = 86400,
        max_message_age_seconds: int = 600,
    ) -> None:
        if session_ttl_seconds <= 0:
            raise ValueError("session_ttl_seconds must be positive")
        if max_message_age_seconds <= 0:
            raise ValueError("max_message_age_seconds must be positive")
        self._nonce_store = nonce_store
        self._session_store = session_store
        self._siwe = siwe
        self._clock = clock
        self._expected_domain = expected_domain
        self._expected_chain_id = expected_chain_id
        self._session_ttl = session_ttl_seconds
        self._max_age = max_message_age_seconds

    async def verify(self, *, message: str, signature: str) -> Session:
        parsed = parse_message(message)

        # Domain and chain id checks prevent cross-site phishing and
        # cross-chain replays. A message signed for evil.com, or for
        # Ethereum mainnet, must not authenticate here.
        if parsed.domain != self._expected_domain:
            raise SignatureVerificationFailed("domain mismatch")
        if parsed.chain_id != self._expected_chain_id:
            raise SignatureVerificationFailed("chain id mismatch")

        now = self._clock.now()
        try:
            issued_ts = parse_iso8601(parsed.issued_at)
        except ValueError as exc:
            raise SignatureVerificationFailed(
                "issued_at is not a valid timestamp"
            ) from exc
        if issued_ts > now + 60:
            raise SignatureVerificationFailed("issued_at in the future")
        if now - issued_ts > self._max_age:
            raise SignatureVerificationFailed("message too old")

        # Consume the nonce before verifying. See module docstring.
        if not await self._nonce_store.consume(parsed.nonce):
            raise NonceNotFound("nonce not found or already used")

        recovered = self._siwe.verify(message=message, signature=signature)
        if recovered != parsed.address:
            # The signature is valid but for a different address than
            # the message claims. This is a malformed (or malicious)
            # request, not just a wrong signature.
            raise SignatureVerificationFailed(
                "recovered address does not match message address"
            )

        session = Session(
            id=make_session_id_fresh(),
            address=parsed.address,
            chain_id=parsed.chain_id,
            created_at=now,
            expires_at=now + self._session_ttl,
        )
        await self._session_store.create(session)
        return session
