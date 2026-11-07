import pytest

from relay.adapters.outbound.in_memory import InMemoryRateLimiter
from relay.domain.errors import RateLimited
from relay.domain.types import ProjectId


def _project(name="p1"):
    return ProjectId(name)


def _clock():
    state = {"t": 0.0}
    def now():
        return state["t"]
    def advance(n):
        state["t"] += n
    return now, advance


@pytest.mark.asyncio
async def test_under_capacity_does_not_raise():
    limiter = InMemoryRateLimiter(capacity=10, refill_rate=1.0)
    for _ in range(10):
        await limiter.check(_project(), "publish")


@pytest.mark.asyncio
async def test_exceeding_capacity_raises():
    limiter = InMemoryRateLimiter(capacity=3, refill_rate=0.001)
    for _ in range(3):
        await limiter.check(_project(), "publish")
    with pytest.raises(RateLimited):
        await limiter.check(_project(), "publish")


@pytest.mark.asyncio
async def test_buckets_are_isolated_per_project():
    limiter = InMemoryRateLimiter(capacity=2, refill_rate=0.001)
    for _ in range(2):
        await limiter.check(_project("a"), "publish")
    # project b has its own bucket.
    await limiter.check(_project("b"), "publish")
    await limiter.check(_project("b"), "publish")


@pytest.mark.asyncio
async def test_buckets_are_isolated_per_operation():
    limiter = InMemoryRateLimiter(capacity=2, refill_rate=0.001)
    for _ in range(2):
        await limiter.check(_project(), "publish")
    # Different operation, same project: separate bucket.
    await limiter.check(_project(), "subscribe")


@pytest.mark.asyncio
async def test_refill_restores_tokens_over_time():
    now, advance = _clock()
    limiter = InMemoryRateLimiter(capacity=2, refill_rate=1.0, clock=now)
    for _ in range(2):
        await limiter.check(_project(), "publish")
    with pytest.raises(RateLimited):
        await limiter.check(_project(), "publish")

    advance(2.0)  # 2 seconds → 2 tokens refilled
    await limiter.check(_project(), "publish")
    await limiter.check(_project(), "publish")


@pytest.mark.asyncio
async def test_cost_consumes_multiple_tokens():
    limiter = InMemoryRateLimiter(capacity=10, refill_rate=0.001)
    await limiter.check(_project(), "batch", cost=7)
    with pytest.raises(RateLimited):
        await limiter.check(_project(), "batch", cost=4)  # only 3 left


@pytest.mark.asyncio
async def test_reset_clears_project_buckets():
    limiter = InMemoryRateLimiter(capacity=1, refill_rate=0.001)
    await limiter.check(_project(), "publish")
    with pytest.raises(RateLimited):
        await limiter.check(_project(), "publish")
    await limiter.reset(_project())
    await limiter.check(_project(), "publish")  # works again
