import time

from auth_service.adapters.outbound.in_memory import SystemClock


def test_system_clock_returns_recent_time():
    clock = SystemClock()
    now = clock.now()
    assert abs(now - time.time()) < 1.0


def test_system_clock_is_monotonic_non_decreasing():
    clock = SystemClock()
    a = clock.now()
    b = clock.now()
    assert b >= a
