import json

from relay.domain.message import PublishedMessage
from relay.domain.types import MessageId, make_topic
from relay.protocol import build_subscription_notification


def test_notification_is_valid_json():
    topic = make_topic("a" * 64)
    msg = PublishedMessage(
        id=MessageId(5), topic=topic, payload="aG9sYQ==",
        ttl=60, tag=1108, prompt=False,
    )
    wire = build_subscription_notification(msg)
    data = json.loads(wire)
    assert data["jsonrpc"] == "2.0"
    assert data["method"] == "irn_subscription"


def test_notification_includes_expected_fields():
    topic = make_topic("a" * 64)
    msg = PublishedMessage(
        id=MessageId(5), topic=topic, payload="aG9sYQ==",
        ttl=60, tag=1108, prompt=False,
    )
    data = json.loads(build_subscription_notification(msg))
    params = data["params"]
    assert params["id"] == topic
    assert params["data"]["topic"] == topic
    assert params["data"]["message"] == "aG9sYQ=="
    assert params["data"]["tag"] == 1108
