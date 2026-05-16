# runtime/worker.py

import json
import subprocess
from pathlib import Path
from datetime import datetime
import time
import os
import redis
import psycopg2

MODEL = os.getenv("OPENCODE_MODEL", "llama3.1:8b")
WORKSPACE_ROOT = Path("/workspace")
ARTIFACT_ROOT = Path("/artifacts")
QUEUE_NAME = "jobs"

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

def dequeue_job():
    prompt = None
    artifact_path = None

    _, job_id = r.blpop(QUEUE_NAME)
    if not job_id:
        return (job_id, prompt, artifact_path)

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
    except Exception as e:
        complete_job(job_id, 'failed', str(e))

    return (job_id, prompt, artifact_path)

def run_job(job_id, prompt, artifact_path):
    workspace = WORKSPACE_ROOT

    output_dir = ARTIFACT_ROOT / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    prompt_file = output_dir / "prompt.txt"
    result_file = output_dir / "result.txt"

    prompt_file.write_text(prompt)
    opencode_model = "ollama/" + MODEL

    cmd = [
        "opencode",
        "--dir",
        str(workspace),
        "--model",
        opencode_model,
        "run",
        prompt,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    ## TODO: move the output to the db instead? maybe we don't need artifacts?
    result_file.write_text(result.stdout + "\n\n" + result.stderr)

def complete_job(job_id, status, error_desc):
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            UPDATE jobs
            SET status = %s,
                error = %s,
                completed_at = NOW()
            WHERE id = %s
            """,
            (status, error_desc, job_id),
        )

        conn.commit()
    except Exception as e:
        print("Error completing job! " + e)

while True:
    ## TODO: proper data model
    job_id, prompt, artifact_path = dequeue_job()

    if job_id:
        run_job(job_id, prompt, artifact_path)
        complete_job(job_id, 'completed', None)

    time.sleep(2)
