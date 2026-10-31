"""Real SiweService backed by the `signinwithethereum` package (import `siwe`).

This is the adapter that talks to the SIWE library. Everything above
(the service layer) sees only the `SiweService` port, so swapping
libraries means replacing this one file.

Key mapping between the port and `siwe.SiweMessage`:
    - build_message: constructs `SiweMessage` and calls `prepare_message()`.
    - verify: parses with `SiweMessage.from_message`, then calls
      `message.verify(..., strict=True)`. `strict=True` enforces that
      domain, uri, chain_id and nonce are all supplied, which is what
      EIP-4361 recommends for authentication flows.

Errors from the `siwe` library (`VerificationError`, `ExpiredMessage`,
`ValueError`) are folded into the domain's `SignatureVerificationFailed`
so callers see a single error class.
"""
from __future__ import annotations

from siwe import ExpiredMessage, SiweMessage, VerificationError

from auth_service.domain.errors import SignatureVerificationFailed
from auth_service.domain.types import Address, ChainId, Nonce, make_address

# EIP-4361 defines exactly one version, "1". The `siwe` library has no
# default and requires it explicitly. Hardcoding here is correct: this
# adapter targets EIP-4361 specifically. If a future spec (EIP-XXXX)
# ever adds a version "2", a new adapter is created alongside, not a
# branch inside this one.
_SIWE_VERSION = "1"


class SigninWithEthereumSiweService:
    """SiweService adapter using the `siwe` package."""

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
        # `issued_at` and `expiration_time` arrive as RFC 3339 strings
        # already formatted by the service layer (`format_iso8601`).
        # `SiweMessage` accepts them as strings in its constructor.
        msg = SiweMessage(
            domain=domain,
            address=address,
            uri=uri,
            version=_SIWE_VERSION,
            chain_id=chain_id,
            nonce=nonce,
            issued_at=issued_at,
            statement=statement,
            expiration_time=expiration_time,
        )
        return msg.prepare_message()

    def verify(self, *, message: str, signature: str) -> Address:
        try:
            parsed = SiweMessage.from_message(message=message)
        except (ValueError, VerificationError) as exc:
            raise SignatureVerificationFailed(
                "message is not a valid EIP-4361 message"
            ) from exc

        # `verify` recovers the signer from the signature (EIP-191) and
        # checks it against `parsed.address`. `strict=True` forces the
        # caller to supply domain, nonce, uri and chain_id, which are
        # the fields that prevent phishing and replay. We pass the
        # values embedded in the parsed message: the service layer
        # already validated them against its own configuration, so
        # here we only need the library's format/crypto checks.
        try:
            parsed.verify(
                signature=signature,
                domain=parsed.domain,
                nonce=parsed.nonce,
                uri=parsed.uri,
                chain_id=parsed.chain_id,
                strict=True,
            )
        except ExpiredMessage as exc:
            raise SignatureVerificationFailed("message expired") from exc
        except (VerificationError, ValueError) as exc:
            raise SignatureVerificationFailed(
                "signature verification failed"
            ) from exc

        # On success, the signer is `parsed.address` (the library
        # compared the recovered address against it internally).
        return make_address(parsed.address)
