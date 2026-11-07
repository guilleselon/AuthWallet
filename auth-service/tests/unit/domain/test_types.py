import pytest

from auth_service.domain.errors import (
    InvalidAddress,
    InvalidChainId,
    InvalidNonce,
    InvalidSessionId,
)
from auth_service.domain.types import (
    make_address,
    make_chain_id,
    make_nonce,
    make_nonce_fresh,
    make_session_id,
    make_session_id_fresh,
)


# ---------- address ----------

def test_address_valid_lowercase():
    assert make_address("0x" + "a" * 40) == "0x" + "a" * 40


def test_address_valid_mixed_case_is_normalized_to_lowercase():
    # EIP-55 checksummed form: mix of upper and lower.
    checksummed = "0xAbC1230000000000000000000000000000000000"
    assert make_address(checksummed) == checksummed.lower()


def test_address_uppercase_hex_is_normalized():
    upper = "0x" + "A" * 40
    assert make_address(upper) == "0x" + "a" * 40


@pytest.mark.parametrize("bad", [
    "", "0x", "0x" + "a" * 39, "0x" + "a" * 41,
    "a" * 40,                    # no 0x prefix
    "0X" + "a" * 40,             # uppercase X
    "0x" + "g" * 40,             # non-hex
    "0x" + "a" * 40 + " ",       # trailing space
    123,                          # not a string
    None,
])
def test_address_invalid(bad):
    with pytest.raises(InvalidAddress):
        make_address(bad)  # type: ignore[arg-type]


# ---------- nonce ----------

def test_nonce_valid():
    assert make_nonce("a" * 32) == "a" * 32


@pytest.mark.parametrize("bad", [
    "", "a" * 31, "a" * 33, "A" * 32, "z" * 32,
    123, None,
])
def test_nonce_invalid(bad):
    with pytest.raises(InvalidNonce):
        make_nonce(bad)  # type: ignore[arg-type]


def test_make_nonce_fresh_has_correct_shape():
    n = make_nonce_fresh()
    assert len(n) == 32
    assert all(c in "0123456789abcdef" for c in n)


def test_make_nonce_fresh_does_not_repeat():
    seen = {make_nonce_fresh() for _ in range(100)}
    assert len(seen) == 100


# ---------- chain id ----------

@pytest.mark.parametrize("good", [1, 56, 97, 137, 2**31 - 1])
def test_chain_id_valid(good):
    assert make_chain_id(good) == good


@pytest.mark.parametrize("bad", [
    0, -1, 2**31, 1.5, "56", True, False, None,
])
def test_chain_id_invalid(bad):
    with pytest.raises(InvalidChainId):
        make_chain_id(bad)  # type: ignore[arg-type]


# ---------- session id ----------

def test_session_id_valid():
    assert make_session_id("b" * 32) == "b" * 32


@pytest.mark.parametrize("bad", [
    "", "b" * 31, "b" * 33, "B" * 32, "z" * 32,
    123, None,
])
def test_session_id_invalid(bad):
    with pytest.raises(InvalidSessionId):
        make_session_id(bad)  # type: ignore[arg-type]


def test_make_session_id_fresh_has_correct_shape():
    sid = make_session_id_fresh()
    assert len(sid) == 32
    assert all(c in "0123456789abcdef" for c in sid)


def test_make_session_id_fresh_does_not_repeat():
    seen = {make_session_id_fresh() for _ in range(100)}
    assert len(seen) == 100
