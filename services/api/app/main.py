from fastapi import FastAPI
import os
import redis
from uuid import uuid4
from app.db_layer import get_conn
from app.queue_redis import enqueue_job
from app.models import CreateJobRequest

app = FastAPI()

redis_client = redis.Redis.from_url(os.environ["REDIS_URL"])

@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {
        "postgres": "configured",
        "redis": redis_client.ping(),
    }


@app.post("/jobs")
def create_job(req: CreateJobRequest):
    job_id = str(uuid4())

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO jobs (id, prompt, status)
        VALUES (%s, %s, 'queued')
        """,
        (job_id, req.prompt),
    )

    conn.commit()

    enqueue_job(job_id)

    return {
        "job_id": job_id,
        "status": "queued",
    }

@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            prompt,
            status,
            artifact_path,
            error
        FROM jobs
        WHERE id = %s
        """,
        (job_id,),
    )

    row = cur.fetchone()

    if not row:
        return {"error": "not found"}

    return {
        "id": row[0],
        "prompt": row[1],
        "status": row[2],
        "artifact_path": row[3],
        "error": row[4],
    }