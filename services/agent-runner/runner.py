import os
import json
import redis
import psycopg2
from datetime import datetime
import httpx
from minio import Minio


QUEUE_NAME = "jobs"

minio_client = Minio(
    os.environ["MINIO_ENDPOINT"],
    access_key=os.environ["MINIO_ACCESS_KEY"],
    secret_key=os.environ["MINIO_SECRET_KEY"],
    secure=False,
)

OLLAMA_BASE_URL = os.environ["OLLAMA_BASE_URL"]

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=6379,
    decode_responses=True,
)

def get_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        dbname=os.getenv("POSTGRES_DB", "software_press"),
        user=os.getenv("POSTGRES_USER", "sp_user"),
        password=os.getenv("POSTGRES_PASSWORD", "sp_password"),
    )

def run_job(prompt: str, artifact_path: str) -> str:
    with httpx.Client(timeout=120) as client:
        response = client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": "llama3.1:8b",
                "prompt": prompt,
                "stream": False,
            },
        )

    data = response.json()

    output = data.get("response", "")

    os.makedirs("/app/artifacts", exist_ok=True)

    artifact_path = "/app" + artifact_path

    with open(artifact_path, "w") as f:
        f.write(output)

    return f"Agent output for prompt:\n\n{output}"

while True:
    _, job_id = r.blpop(QUEUE_NAME)

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            UPDATE jobs
            SET status = 'running',
                started_at = NOW()
            WHERE id = %s
            """,
            (job_id,),
        )
        conn.commit()

        cur.execute(
            "SELECT prompt FROM jobs WHERE id = %s",
            (job_id,),
        )

        prompt = cur.fetchone()[0]
        artifact_path = f"/artifacts/{job_id}.txt"

        output = run_job(prompt, artifact_path)

        with open(artifact_path, "w") as f:
            f.write(output)

        cur.execute(
            """
            UPDATE jobs
            SET status = 'completed',
                completed_at = NOW(),
                artifact_path = %s
            WHERE id = %s
            """,
            (artifact_path, job_id),
        )

        conn.commit()

    except Exception as e:
        cur.execute(
            """
            UPDATE jobs
            SET status = 'failed',
                error = %s,
                completed_at = NOW()
            WHERE id = %s
            """,
            (str(e), job_id),
        )

        conn.commit()