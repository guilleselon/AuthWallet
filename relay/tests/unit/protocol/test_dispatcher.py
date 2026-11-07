import pytest

from relay.domain.errors import InvalidParams, RateLimited
from relay.protocol import Dispatcher, HandlerContext, Request
from relay.domain.types import ConnectionId, ProjectId

from relay.adapters.outbound.in_memory import InMemoryRateLimiter


def _ctx():
    return HandlerContext(
        connection_id=ConnectionId("c1"),
        project_id=ProjectId("p1"),
    )


@pytest.mark.asyncio
async def test_unknown_method_returns_method_not_found():
    d = Dispatcher(InMemoryRateLimiter(capacity=100, refill_rate=100.0))
    req = Request(method="nope", params={}, id=1)
    resp = await d.dispatch(req, _ctx())
    assert resp.error is not None
    assert resp.error.code == -32601


@pytest.mark.asyncio
async def test_successful_dispatch_returns_result():
    d = Dispatcher(InMemoryRateLimiter(capacity=100, refill_rate=100.0))

    async def handler(params, ctx):
        return {"echo": params}

    d.register("echo", handler)
    req = Request(method="echo", params={"x": 1}, id=42)
    resp = await d.dispatch(req, _ctx())
    assert resp.id == 42
    assert resp.result == {"echo": {"x": 1}}
    assert resp.error is None


@pytest.mark.asyncio
async def test_domain_error_becomes_response_error():
    d = Dispatcher(InMemoryRateLimiter(capacity=100, refill_rate=100.0))

    async def bad(params, ctx):
        raise InvalidParams("bad input")

    d.register("bad", bad)
    resp = await d.dispatch(Request(method="bad", params={}, id=1), _ctx())
    assert resp.error.code == -32602
    assert "bad input" in resp.error.message


@pytest.mark.asyncio
async def test_unexpected_exception_becomes_internal_error():
    d = Dispatcher(InMemoryRateLimiter(capacity=100, refill_rate=100.0))

    async def boom(params, ctx):
        raise RuntimeError("leak")

    d.register("boom", boom)
    resp = await d.dispatch(Request(method="boom", params={}, id=1), _ctx())
    assert resp.error.code == -32603
    assert "leak" not in resp.error.message  # no internals leaked


@pytest.mark.asyncio
async def test_rate_limited_returns_error():
    limiter = InMemoryRateLimiter(capacity=1, refill_rate=0.001)
    d = Dispatcher(limiter)

    async def noop(params, ctx):
        return True

    d.register("m", noop)
    await d.dispatch(Request(method="m", params={}, id=1), _ctx())
    resp = await d.dispatch(Request(method="m", params={}, id=2), _ctx())
    assert resp.error.code == -32005
