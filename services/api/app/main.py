from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import os
import redis
from uuid import uuid4
from app.db_layer import get_conn
from app.queue_redis import enqueue_job
from app.models import CreateJobRequest

app = FastAPI()

redis_client = redis.Redis.from_url(os.environ["REDIS_URL"])


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    for err in errors:
        ctx = err.get("ctx")
        if ctx and "error" in ctx:
            ctx["error"] = str(ctx["error"])
    return JSONResponse(
        status_code=400,
        content={"detail": errors},
    )

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
        INSERT INTO jobs (id, prompt, issue_number, model, status)
        VALUES (%s, %s, %s, %s, 'queued')
        """,
        (job_id, req.prompt, req.issueNumber, req.model),
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
            model,
            status,
            artifact_path,
            error,
            pr_number,
            issue_number
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
        "model": row[2],
        "status": row[3],
        "artifact_path": row[4],
        "error": row[5],
        "pr_number": row[6],
        "issue_number": row[7],
    }