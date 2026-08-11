import redis
from typing import Optional

from app.config import QUEUE_NAME, REDIS_HOST


class Queue:
    def __init__(self, redis_client=None, queue_name: str = QUEUE_NAME):
        self.queue_name = queue_name
        self.r = redis_client or redis.Redis(
            host=REDIS_HOST,
            port=6379,
            decode_responses=True,
        )

    def dequeue(self) -> Optional[str]:
        try:
            _, job_id = self.r.blpop(self.queue_name)
        except redis.exceptions.RedisError:
            return None

        return job_id
