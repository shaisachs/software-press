from unittest import mock

from app.queue_redis import QUEUE_NAME, enqueue_job


def test_enqueue_job_rpushes_to_queue():
    fake_r = mock.Mock()

    with mock.patch("app.queue_redis.r", fake_r):
        enqueue_job("abc-123")

    fake_r.rpush.assert_called_once_with(QUEUE_NAME, "abc-123")
