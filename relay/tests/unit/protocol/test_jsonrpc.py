import pytest

from relay.domain.errors import InvalidParams, Unauthorized
from relay.protocol import (
    Error,
    Request,
    Response,
    error_response,
    parse_request,
    serialize_response,
)


def test_parse_request_valid():
    raw = {"jsonrpc": "2.0", "id": 1, "method": "irn_publish", "params": {"a": 1}}
    req = parse_request(raw)
    assert req == Request(method="irn_publish", params={"a": 1}, id=1)


def test_parse_request_defaults_params_to_empty():
    raw = {"jsonrpc": "2.0", "id": 2, "method": "irn_subscribe"}
    assert parse_request(raw).params == {}


@pytest.mark.parametrize("bad", [
    None, 42, "string", [1, 2],
])
def test_parse_request_non_object_raises(bad):
    with pytest.raises(InvalidParams):
        parse_request(bad)


@pytest.mark.parametrize("bad", [
    {"id": 1, "method": "m"},
    {"jsonrpc": "1.0", "id": 1, "method": "m"},
    {"jsonrpc": "2.0", "id": 1},
    {"jsonrpc": "2.0", "id": 1, "method": 42},
    {"jsonrpc": "2.0", "id": 1, "method": "m", "params": []},
])
def test_parse_request_malformed_raises(bad):
    with pytest.raises(InvalidParams):
        parse_request(bad)


def test_serialize_success():
    resp = Response(id=1, result={"id": 42})
    assert serialize_response(resp) == {
        "jsonrpc": "2.0", "id": 1, "result": {"id": 42}
    }


def test_serialize_error():
    resp = Response(id=1, error=Error(code=-32602, message="bad"))
    assert serialize_response(resp) == {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {"code": -32602, "message": "bad"},
    }


def test_serialize_error_with_data():
    resp = Response(id=1, error=Error(code=-32602, message="bad", data={"k": "v"}))
    wire = serialize_response(resp)
    assert wire["error"]["data"] == {"k": "v"}


def test_error_response_maps_code():
    resp = error_response(7, InvalidParams("x"))
    assert resp.id == 7
    assert resp.error.code == -32602


def test_error_response_keeps_unauthorized_code():
    resp = error_response(None, Unauthorized("nope"))
    assert resp.error.code == -32001
