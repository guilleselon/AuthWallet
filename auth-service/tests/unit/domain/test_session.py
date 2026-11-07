import pytest

from auth_service.domain.session import Session
from auth_service.domain.types import (
    make_address,
    make_chain_id,
    make_session_id,
)


def _session(*, created_at=1000.0, expires_at=4600.0) -> Session:
    return Session(
        id=make_session_id("c" * 32),
        address=make_address("0x" + "a" * 40),
        chain_id=make_chain_id(56),
        created_at=created_at,
        expires_at=expires_at,
    )


def test_session_construction():
    s = _session()
    assert s.address == "0x" + "a" * 40
    assert s.chain_id == 56


def test_session_is_immutable():
    s = _session()
    with pytest.raises(Exception):  # FrozenInstanceError
        s.address = make_address("0x" + "b" * 40)  # type: ignore[misc]


def test_session_is_hashable():
    s = _session()
    assert hash(s) == hash(s)


def test_is_expired_before_expiry():
    s = _session(created_at=1000.0, expires_at=2000.0)
    assert s.is_expired(1500.0) is False


def test_is_expired_exactly_at_expiry():
    """Boundary: expires_at is inclusive, so at exactly expires_at
    the session is still valid."""
    s = _session(created_at=1000.0, expires_at=2000.0)
    assert s.is_expired(2000.0) is False


def test_is_expired_after_expiry():
    s = _session(created_at=1000.0, expires_at=2000.0)
    assert s.is_expired(2000.001) is True


def test_remaining_seconds_full():
    s = _session(created_at=1000.0, expires_at=2000.0)
    assert s.remaining_seconds(1000.0) == 1000.0


def test_remaining_seconds_partial():
    s = _session(created_at=1000.0, expires_at=2000.0)
    assert s.remaining_seconds(1500.0) == 500.0


def test_remaining_seconds_after_expiry_is_zero_not_negative():
    s = _session(created_at=1000.0, expires_at=2000.0)
    assert s.remaining_seconds(2500.0) == 0.0


def test_two_sessions_with_same_fields_are_equal():
    a = _session()
    b = _session()
    assert a == b
