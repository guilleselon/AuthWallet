"""Pure SIWE (EIP-4361) message formatting and parsing.

This module knows the *format* of EIP-4361 messages. It does NOT verify
signatures — that's the SiweService port's adapter. Here we only format
and parse strings, so the service layer can extract fields (nonce,
domain, chain_id, issued_at) from a message without depending on the
crypto library.

Why a regex and not a full parser:
    EIP-4361 has a fixed structure. A regex is sufficient for the fields
    we care about, and it's auditable. We are not trying to accept every
    possible valid message: we're trying to accept exactly the messages
    our own `build_message` produces. Strictness is a feature.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from .errors import SignatureVerificationFailed
from .types import Address, ChainId, Nonce, make_address, make_chain_id, make_nonce


@dataclass(frozen=True)
class ParsedSiweMessage:
    """The fields of an EIP-4361 message that the auth service cares about."""

    domain: str
    address: Address
    uri: str
    chain_id: ChainId
    nonce: Nonce
    issued_at: str
    statement: str | None = None
    expiration_time: str | None = None


# The EIP-4361 canonical layout. Non-capturing groups avoid surprises.
_SIWE_RE = re.compile(
    r"^(?P<domain>[^\n]+) wants you to sign in with your Ethereum account:\n"
    r"(?P<address>0x[0-9a-fA-F]{40})\n"
    r"\n"
    r"(?:(?P<statement>[^\n]+)\n\n)?"
    r"URI: (?P<uri>[^\n]+)\n"
    r"Version: (?P<version>1)\n"
    r"Chain ID: (?P<chain_id>\d+)\n"
    r"Nonce: (?P<nonce>[0-9a-f]{32})\n"
    r"Issued At: (?P<issued_at>[^\n]+)"
    r"(?:\nExpiration Time: (?P<expiration_time>[^\n]+))?$",
    re.DOTALL,
)


def parse_message(message: str) -> ParsedSiweMessage:
    """Parse an EIP-4361 message. Raises `SignatureVerificationFailed`
    if the message is not a valid EIP-4361 string.

    The choice of error class is intentional: from the caller's point
    of view, an unparseable message is indistinguishable from a forged
    one. We don't leak "your message was malformed" vs "your signature
    was wrong" to the client.
    """
    match = _SIWE_RE.match(message)
    if match is None:
        raise SignatureVerificationFailed("not a valid EIP-4361 message")
    groups = match.groupdict()
    try:
        chain_id = make_chain_id(int(groups["chain_id"]))
        nonce = make_nonce(groups["nonce"])
        address = make_address(groups["address"])
    except Exception as exc:
        # If field validation fails (e.g. chain id out of range), the
        # message is well-structured but semantically invalid. Fold
        # into the same error class for the same reason as above.
        raise SignatureVerificationFailed(
            "EIP-4361 message has invalid field"
        ) from exc

    return ParsedSiweMessage(
        domain=groups["domain"],
        address=address,
        uri=groups["uri"],
        chain_id=chain_id,
        nonce=nonce,
        issued_at=groups["issued_at"],
        statement=groups.get("statement"),
        expiration_time=groups.get("expiration_time"),
    )


def format_iso8601(ts: float) -> str:
    """Format a Unix timestamp as RFC 3339 with millisecond precision.

    EIP-4361 requires this exact form: `YYYY-MM-DDTHH:MM:SS.sssZ`.
    `datetime.isoformat()` produces `+00:00` instead of `Z`, which some
    wallets reject or display oddly, so we build the string explicitly.
    """
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def parse_iso8601(value: str) -> float:
    """Parse an RFC 3339 timestamp into Unix epoch seconds.

    Python 3.11+ `datetime.fromisoformat` handles the trailing 'Z'.
    """
    dt = datetime.fromisoformat(value)
    return dt.timestamp()
