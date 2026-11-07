import base64

import pytest

from relay.domain.errors import (
    InvalidPayload,
    InvalidTag,
    InvalidTTL,
    InvalidTopic,
    PayloadTooLarge,
)
from relay.domain.types import make_payload, make_tag, make_ttl, make_topic


# ---------- topic ----------

def test_topic_valid():
    assert make_topic("a" * 64) == "a" * 64


@pytest.mark.parametrize(
    "bad",
    [
        "a" * 63,
        "a" * 65,
        "A" * 64,
        "z" * 64,
        "",
        "0x" + "a" * 64,
    ],
)
def test_topic_invalid(bad):
    with pytest.raises(InvalidTopic):
        make_topic(bad)


# ---------- payload ----------

def test_payload_valid_canonical():
    # "hola" en base64
    assert make_payload("aG9sYQ==") == "aG9sYQ=="


def test_payload_rejects_missing_padding():
    # 'aG9sYQ' has length 6, not a multiple of 4.
    with pytest.raises(InvalidPayload):
        make_payload("aG9sYQ")


def test_payload_rejects_invalid_base64():
    with pytest.raises(InvalidPayload):
        make_payload("!!!no-es-base64!!!")


def test_payload_rejects_non_string():
    with pytest.raises(InvalidPayload):
        make_payload(b"bytes-not-str")  # type: ignore[arg-type]


def test_payload_too_large():
    # Valid base64 chars, but exceeds the limit.
    with pytest.raises(PayloadTooLarge):
        make_payload("A" * (30 * 1024))


def test_payload_at_limit_ok():
    # Build canonical base64 just under the limit.
    raw = b"\x00" * (((22 * 1024) - 4) * 3 // 4)
    encoded = base64.b64encode(raw).decode("ascii")
    assert len(encoded) <= 22 * 1024
    make_payload(encoded)  # must not raise


# ---------- ttl ----------

@pytest.mark.parametrize("good", [1, 300, 604_800])
def test_ttl_valid(good):
    assert make_ttl(good) == good


@pytest.mark.parametrize("bad", [0, -1, 604_801, 1.5, "300", True, False])
def test_ttl_invalid(bad):
    with pytest.raises(InvalidTTL):
        make_ttl(bad)


# ---------- tag ----------

@pytest.mark.parametrize("good", [1, 1000, 4001, 10_000])
def test_tag_valid(good):
    assert make_tag(good) == good


@pytest.mark.parametrize("bad", [0, -5, 10_001, True, 1.0, "1000"])
def test_tag_invalid(bad):
    with pytest.raises(InvalidTag):
        make_tag(bad)
