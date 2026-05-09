import redis
import os

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=6379,
    decode_responses=True,
)

QUEUE_NAME = "jobs"

def enqueue_job(job_id: str):
    r.rpush(QUEUE_NAME, job_id)