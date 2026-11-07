"""JSON-RPC 2.0 request/response framing.

Reference: https://www.jsonrpc.org/specification
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from relay.domain.errors import InvalidParams, RelayError


@dataclass(frozen=True)
class Error:
    code: int
    message: str
    data: Any = None


@dataclass(frozen=True)
class Request:
    method: str
    params: dict[str, Any]
    id: int | str | None


@dataclass(frozen=True)
class Response:
    id: int | str | None
    result: Any = None
    error: Error | None = None


def parse_request(raw: Any) -> Request:
    """Parse an incoming JSON-RPC 2.0 request object.

    Raises `InvalidParams` for malformed structure. The caller wraps
    this in a try/except to produce a proper error response.
    """
    if not isinstance(raw, dict):
        raise InvalidParams("request must be a JSON object")
    if raw.get("jsonrpc") != "2.0":
        raise InvalidParams("jsonrpc must be '2.0'")
    method = raw.get("method")
    if not isinstance(method, str):
        raise InvalidParams("method must be a string")
    params = raw.get("params", {})
    if not isinstance(params, dict):
        raise InvalidParams("params must be an object")
    req_id = raw.get("id")
    return Request(method=method, params=params, id=req_id)


def serialize_response(resp: Response) -> dict[str, Any]:
    """Convert a Response to its JSON-RPC wire representation."""
    out: dict[str, Any] = {"jsonrpc": "2.0", "id": resp.id}
    if resp.error is not None:
        err: dict[str, Any] = {
            "code": resp.error.code,
            "message": resp.error.message,
        }
        if resp.error.data is not None:
            err["data"] = resp.error.data
        out["error"] = err
    else:
        out["result"] = resp.result
    return out


def error_response(req_id: int | str | None, exc: RelayError) -> Response:
    """Build a Response from a domain exception, preserving its code."""
    return Response(id=req_id, error=Error(code=exc.code, message=str(exc)))
