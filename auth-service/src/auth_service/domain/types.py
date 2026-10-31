"""Value objects with validation. No external dependencies."""
from __future__ import annotations

import re
import secrets
from typing import NewType

from .errors import (
    InvalidAddress,
    InvalidChainId,
    InvalidNonce,
    InvalidSessionId,
)

# --- Type aliases (for mypy; not runtime-validated) ---
Address = NewType("Address", str)      # always 0x-prefixed, lowercase
Nonce = NewType("Nonce", str)          # 32 lowercase hex chars
ChainId = NewType("ChainId", int)      # positive integer
SessionId = NewType("SessionId", str)  # 32 lowercase hex chars

# --- Validation patterns ---
# Ethereum address: 0x + 20 bytes hex. Accept any case; normalize to
# lowercase so comparisons across layers are stable. We deliberately
# do NOT verify EIP-55 checksum here: a user pasting an address with
# wrong case is a UX problem, not a security problem, and rejecting it
# would surprise users whose wallets show the address differently.
_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")

# 16 bytes = 128 bits. Same entropy budget as the relay's nonce.
_NONCE_RE = re.compile(r"^[0-9a-f]{32}$")

# Session IDs: also 16 bytes. UUID would be fine too; hex is smaller.
_SESSION_ID_RE = re.compile(r"^[0-9a-f]{32}$")

# Chain IDs supported at the domain level. Anything positive works;
# the *policy* of which chains this deployment accepts is a config
# concern, not a domain concern. BSC mainnet=56, testnet=97,
# Ethereum mainnet=1, Polygon=137. Domain only enforces the shape.
_MIN_CHAIN_ID = 1
_MAX_CHAIN_ID = 2**31 - 1


# --- Factories ---

def make_address(value: str) -> Address:
    """Validate and normalize an Ethereum address to lowercase.

    Lowercasing is part of the domain contract: every Address in the
    system is lowercase. Adapters that need checksummed form (for
    display) re-checksum explicitly. This avoids the classic bug
    where `address != other_address` because of casing.
    """
    if not isinstance(value, str) or not _ADDRESS_RE.match(value):
        raise InvalidAddress(
            "address must be 0x-prefixed 40-hex-char string"
        )
    return Address(value.lower())


def make_nonce(value: str) -> Nonce:
    if not isinstance(value, str) or not _NONCE_RE.match(value):
        raise InvalidNonce(
            "nonce must be 32 lowercase hex characters"
        )
    return Nonce(value)


def make_nonce_fresh() -> Nonce:
    """Generate a fresh, cryptographically secure nonce.

    `secrets.token_hex(16)` uses the OS CSPRNG. Never use `random`
    for anything security-sensitive, even in tests that touch code
    paths that will run in production.
    """
    return Nonce(secrets.token_hex(16))


def make_chain_id(value: int) -> ChainId:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidChainId("chain id must be an integer")
    if not (_MIN_CHAIN_ID <= value <= _MAX_CHAIN_ID):
        raise InvalidChainId(
            f"chain id must be between {_MIN_CHAIN_ID} and {_MAX_CHAIN_ID}"
        )
    return ChainId(value)


def make_session_id(value: str) -> SessionId:
    if not isinstance(value, str) or not _SESSION_ID_RE.match(value):
        raise InvalidSessionId(
            "session id must be 32 lowercase hex characters"
        )
    return SessionId(value)


def make_session_id_fresh() -> SessionId:
    """Generate a fresh session ID. 128 bits of entropy."""
    return SessionId(secrets.token_hex(16))
