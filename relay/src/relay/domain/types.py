"""Value objects with validation. No external dependencies."""
from __future__ import annotations

import base64
import re
from typing import NewType

from .errors import (
    InvalidPayload,
    InvalidTag,
    InvalidTopic,
    InvalidTTL,
    PayloadTooLarge,
)

# --- Type aliases (for mypy; not runtime-validated) ---
Topic = NewType("Topic", str)
ProjectId = NewType("ProjectId", str)
ConnectionId = NewType("ConnectionId", str)
MessageId = NewType("MessageId", int)
Tag = NewType("Tag", int)
TTL = NewType("TTL", int)

# --- Protocol limits (documented against IRN v2) ---
_TOPIC_RE = re.compile(r"^[0-9a-f]{64}$")  # sha256 → 32 bytes → 64 hex chars

# 22 KiB encoded ≈ 16.5 KiB decoded. Enough for any WC payload
# (pairing URIs, session proposals, SIWE messages).
_MAX_PAYLOAD_ENCODED = 22 * 1024

# IRN allows TTL up to 7 days.
_MIN_TTL_SECONDS = 1
_MAX_TTL_SECONDS = 7 * 24 * 3600  # 604800

# IRN tags are specific protocol values (1000, 1100, 1101, 1108, 1109,
# 1110, 3000, 3001, 4001, 5000, 5001, ...). We validate a coarse range
# here; the protocol layer (L4) enforces the exact set.
_MAX_TAG = 10_000


# --- Factories ---

def make_topic(value: str) -> Topic:
    """A topic is sha256 of the symmetric key derived via X25519.
    Always 32 bytes in lowercase hex. The relay routes by topic
    without ever knowing what's inside.
    """
    if not isinstance(value, str) or not _TOPIC_RE.match(value):
        raise InvalidTopic(
            "topic must be a 32-byte lowercase hex string (sha256)"
        )
    return Topic(value)


def make_payload(value: str) -> str:
    """Validate base64 payload.

    The payload is opaque: the relay never decrypts it. End-to-end
    encryption is between the dapp and the wallet.
    """
    if not isinstance(value, str):
        raise InvalidPayload("payload must be a string")
    if len(value) > _MAX_PAYLOAD_ENCODED:
        raise PayloadTooLarge(
            f"payload exceeds {_MAX_PAYLOAD_ENCODED} encoded bytes"
        )
    try:
        base64.b64decode(value, validate=True)
    except Exception as exc:
        raise InvalidPayload("payload is not valid base64") from exc
    return value


def make_ttl(value: int) -> TTL:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidTTL("ttl must be an integer")
    if not (_MIN_TTL_SECONDS <= value <= _MAX_TTL_SECONDS):
        raise InvalidTTL(
            f"ttl must be between {_MIN_TTL_SECONDS} and {_MAX_TTL_SECONDS}"
        )
    return TTL(value)


def make_tag(value: int) -> Tag:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidTag("tag must be an integer")
    if not (0 < value <= _MAX_TAG):
        raise InvalidTag(f"tag must be between 1 and {_MAX_TAG}")
    return Tag(value)
