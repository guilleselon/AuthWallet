"""Port: Sign-In with Ethereum (EIP-4361).

Two responsibilities wrapped in one port:
    1. Build the canonical SIWE message for a given (address, nonce,
       chain_id, domain, uri, issued_at, ...). The message format is
       standardized (EIP-4361); getting it wrong means wallets refuse
       to sign, or worse, sign something different from what the
       server expects.
    2. Verify a signed message and recover the signer's address.

Why both live in one port:
    Both operations must agree on the exact message format. Splitting
    them would create the possibility of building with one library
    and verifying with another, silently breaking. Keeping them
    together makes the format a single concern with a single source
    of truth.

    A future adapter backed by a different library (e.g. a custom
    implementation) replaces both at once. That's the point.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from auth_service.domain.errors import SignatureVerificationFailed
from auth_service.domain.types import Address, ChainId, Nonce


@runtime_checkable
class SiweService(Protocol):
    """Builds and verifies EIP-4361 messages."""

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
        """Return the EIP-4361 message string the wallet should sign.

        The exact format is defined by EIP-4361. Do not hand-roll it:
        any deviation causes the wallet to display a warning, or to
        sign a string the server's verifier won't match.

        `issued_at` and `expiration_time` are ISO-8601 timestamps in
        the format EIP-4361 specifies (RFC 3339, typically
        `YYYY-MM-DDTHH:MM:SS.sssZ`). The service layer produces them
        from `Clock`; this port just embeds them.

        Why sync: SIWE message construction is pure string formatting,
        microseconds. Making it async would force the caller to await
        on CPU work, which is strictly worse.
        """
        ...

    def verify(self, *, message: str, signature: str) -> Address:
        """Recover the signer's address from a signed SIWE message.

        Raises `SignatureVerificationFailed` if:
            - the signature is malformed,
            - the message doesn't parse as EIP-4361,
            - the recovered address doesn't match the message's address,
            - the message's domain / chain_id don't match the
              verifier's configured expectation (implementations must
              enforce this: a message from another domain is a replay
              attempt, not a valid login).

        Returns the recovered address in lowercase. The caller must
        still check `nonce` and `issued_at` against the nonce store
        and clock — those are policy decisions, not format checks.
        """
        ...
