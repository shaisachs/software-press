import redis
from unittest import mock

from app.queue_redis import Queue


def test_dequeue_returns_job_id():
    fake_redis = mock.Mock()
    fake_redis.blpop.return_value = ("jobs", "abc-123")

    queue = Queue(redis_client=fake_redis)

    assert queue.dequeue() == "abc-123"
    fake_redis.blpop.assert_called_once_with("jobs")


def test_dequeue_returns_none_when_no_job():
    fake_redis = mock.Mock()
    fake_redis.blpop.return_value = ("jobs", None)

    queue = Queue(redis_client=fake_redis)

    assert queue.dequeue() is None


def test_dequeue_returns_none_on_redis_error():
    fake_redis = mock.Mock()
    fake_redis.blpop.side_effect = redis.exceptions.RedisError("boom")

    queue = Queue(redis_client=fake_redis)

    assert queue.dequeue() is None
