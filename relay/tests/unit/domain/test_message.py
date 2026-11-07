import pytest

from relay.domain.message import PublishedMessage, PublishRequest
from relay.domain.types import make_payload, make_tag, make_topic, make_ttl


def _topic():
    return make_topic("a" * 64)


def test_publish_request_construction():
    req = PublishRequest(
        topic=_topic(),
        payload=make_payload("aG9sYQ=="),
        ttl=make_ttl(300),
        tag=make_tag(1108),
        prompt=True,
    )
    assert req.prompt is True
    assert req.topic == "a" * 64


def test_published_message_is_immutable():
    msg = PublishedMessage(
        id=1,
        topic=_topic(),
        payload="aG9sYQ==",
        ttl=300,
        tag=1108,
        prompt=False,
    )
    with pytest.raises(Exception):  # FrozenInstanceError
        msg.id = 2  # type: ignore[misc]


def test_published_message_is_hashable():
    # frozen+slots makes it hashable, useful for set/dict membership.
    msg = PublishedMessage(
        id=1,
        topic=_topic(),
        payload="aG9sYQ==",
        ttl=300,
        tag=1108,
        prompt=False,
    )
    assert hash(msg) == hash(msg)
