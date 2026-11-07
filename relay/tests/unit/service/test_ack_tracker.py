from relay.domain.types import make_topic
from relay.service import AckTracker


def _topic():
    return make_topic("a" * 64)


def test_record_and_query():
    t = _topic()
    tracker = AckTracker()

    tracker.record("c1", t, 1)

    assert tracker.has_acked("c1", t, 1) is True
    assert tracker.has_acked("c2", t, 1) is False


def test_record_is_idempotent():
    t = _topic()
    tracker = AckTracker()

    tracker.record("c1", t, 1)
    tracker.record("c1", t, 1)

    assert tracker.ack_count(t, 1) == 1


def test_multiple_connections_accumulate():
    t = _topic()
    tracker = AckTracker()

    tracker.record("c1", t, 1)
    tracker.record("c2", t, 1)

    assert tracker.ack_count(t, 1) == 2


def test_forget_connection_removes_only_its_acks():
    t = _topic()
    tracker = AckTracker()
    tracker.record("c1", t, 1)
    tracker.record("c2", t, 1)

    removed = tracker.forget_connection("c1")

    assert removed == 1
    assert not tracker.has_acked("c1", t, 1)
    assert tracker.has_acked("c2", t, 1)
    assert tracker.ack_count(t, 1) == 1


def test_forget_message_drops_acks():
    t = _topic()
    tracker = AckTracker()
    tracker.record("c1", t, 1)
    tracker.record("c2", t, 1)

    tracker.forget_message(t, 1)

    assert tracker.ack_count(t, 1) == 0


def test_stats_counts_aggregate():
    t = _topic()
    tracker = AckTracker()
    tracker.record("c1", t, 1)
    tracker.record("c2", t, 1)
    tracker.record("c1", t, 2)

    stats = tracker.stats()

    assert stats == {"topics": 1, "messages": 2, "acks": 3}
