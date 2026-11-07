"""Message value objects.

The relay has two distinct lifecycle stages for a message:

    1. PublishRequest  — what a client sends to irn_publish.
                          No ID: the relay assigns it.
    2. PublishedMessage — after the relay assigns an ID, about to be routed
                          to subscribers and persisted for batchFetch.

Conflating them forced `id` to be Optional or fabricated, which leaked
an invariant violation into the type system.
"""
from __future__ import annotations

from dataclasses import dataclass

from .types import MessageId, Tag, Topic, TTL


@dataclass(frozen=True, slots=True)
class PublishRequest:
    """Client-provided data. Validated by the protocol layer before use."""

    topic: Topic
    payload: str  # canonical base64; opaque to the relay
    ttl: TTL
    tag: Tag
    prompt: bool  # IRN: whether to attempt immediate delivery to offline peers


@dataclass(frozen=True, slots=True)
class PublishedMessage:
    """A message with an ID assigned by the relay.

    Immutable once created: a router that mutates a message in flight
    is a bug waiting to happen. `frozen` makes it impossible.
    `slots` reduces per-instance memory — relevant when tens of thousands
    of messages are in flight during a burst.
    """

    id: MessageId
    topic: Topic
    payload: str
    ttl: TTL
    tag: Tag
    prompt: bool
