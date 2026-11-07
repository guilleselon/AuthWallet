"""In-memory fakes for the 4 auth-service ports.

Not the production in-memory adapters (those come in L3). These exist
only to test L2 without touching infrastructure.
"""
from __future__ import annotations

from auth_service.domain.errors import SignatureVerificationFailed
from auth_service.domain.session import Session
from auth_service.domain.siwe import format_iso8601
from auth_service.domain.types import (
    Address,
    ChainId,
    Nonce,
    SessionId,
    make_nonce_fresh,
)


class FakeClock:
    """Advanceable clock. Call `advance(seconds)` to move forward."""

    def __init__(self, start: float = 1_700_000_000.0) -> None:
        self._now = start

    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


class FakeNonceStore:
    """Dict-backed nonce store with TTL."""

    def __init__(self, clock: FakeClock) -> None:
        self._clock = clock
        # nonce -> expires_at
        self._data: dict[Nonce, float] = {}

    async def put(self, nonce: Nonce, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._data[nonce] = self._clock.now() + ttl_seconds

    async def consume(self, nonce: Nonce) -> bool:
        expires = self._data.pop(nonce, None)
        if expires is None:
            return False
        return expires > self._clock.now()

    async def ttl_remaining(self, nonce: Nonce) -> float | None:
        expires = self._data.get(nonce)
        if expires is None:
            return None
        return max(0.0, expires - self._clock.now())


class FakeSessionStore:
    """Dict-backed session store with expiry filtering."""

    def __init__(self, clock: FakeClock) -> None:
        self._clock = clock
        self._data: dict[SessionId, Session] = {}

    async def create(self, session: Session) -> None:
        if session.expires_at <= session.created_at:
            raise ValueError("session already expired")
        if session.id in self._data:
            raise ValueError(f"duplicate session id: {session.id}")
        self._data[session.id] = session

    async def get(self, session_id: SessionId) -> Session | None:
        session = self._data.get(session_id)
        if session is None:
            return None
        if session.is_expired(self._clock.now()):
            return None
        return session

    async def delete(self, session_id: SessionId) -> bool:
        return self._data.pop(session_id, None) is not None


class FakeSiweService:
    """Configurable SiweService fake.

    - `build_message` produces a valid EIP-4361 message so that
      `parse_message` (domain, L0) can parse it in tests.
    - `verify` returns `recovered_address` (configurable) or raises
      `verify_error` (configurable). By default it returns the address
      embedded in the message, which mimics a correct signature.
    """

    def __init__(self) -> None:
        self.build_calls: list[dict] = []
        self.recovered_address: Address | None = None
        self.verify_error: Exception | None = None

    def build_message(
        self,
        *,
        domain: str,
        address: Address,
        uri: str,
        chain_id: ChainId,
        nonce: Nonce,
        issued_at: str,
        statement: str | None = None,
        expiration_time: str | None = None,
    ) -> str:
        self.build_calls.append({
            "domain": domain, "address": address, "uri": uri,
            "chain_id": chain_id, "nonce": nonce, "issued_at": issued_at,
            "statement": statement, "expiration_time": expiration_time,
        })
        return _render_siwe(
            domain=domain, address=address, uri=uri, chain_id=chain_id,
            nonce=nonce, issued_at=issued_at, statement=statement,
            expiration_time=expiration_time,
        )

    def verify(self, *, message: str, signature: str) -> Address:
        if self.verify_error is not None:
            raise self.verify_error
        if self.recovered_address is not None:
            return self.recovered_address
        # Default: recover the address embedded in the message, i.e.
        # behave as if the signature is correct.
        from auth_service.domain.siwe import parse_message
        return parse_message(message).address


def _render_siwe(
    *,
    domain: str,
    address: Address,
    uri: str,
    chain_id: ChainId,
    nonce: Nonce,
    issued_at: str,
    statement: str | None,
    expiration_time: str | None,
) -> str:
    lines = [
        f"{domain} wants you to sign in with your Ethereum account:",
        address,
        "",
    ]
    if statement:
        lines.append(statement)
        lines.append("")
    lines.append(f"URI: {uri}")
    lines.append("Version: 1")
    lines.append(f"Chain ID: {chain_id}")
    lines.append(f"Nonce: {nonce}")
    lines.append(f"Issued At: {issued_at}")
    if expiration_time:
        lines.append(f"Expiration Time: {expiration_time}")
    return "\n".join(lines)


def make_siwe_message(
    *,
    domain: str,
    address: Address,
    uri: str,
    chain_id: ChainId,
    nonce: Nonce,
    issued_at: str,
    statement: str | None = None,
    expiration_time: str | None = None,
) -> str:
    """Public helper for tests that don't use FakeSiweService.build_message."""
    return _render_siwe(
        domain=domain, address=address, uri=uri, chain_id=chain_id,
        nonce=nonce, issued_at=issued_at, statement=statement,
        expiration_time=expiration_time,
    )


def fresh_nonce() -> Nonce:
    return make_nonce_fresh()


def _format(ts: float) -> str:
    return format_iso8601(ts)
