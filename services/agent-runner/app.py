import os
import subprocess
from uuid import uuid4

import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from db_layer import get_conn
from gh import ensure_gh_auth

app = FastAPI()

QUEUE_NAME = "jobs"
WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", "/workspace")

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=6379,
    decode_responses=True,
)


class CreateIssueRequest(BaseModel):
    issueNumber: int = Field(..., gt=0)


def fetch_issue_text(issue_number: int) -> str:
    result = subprocess.run(
        ["gh", "issue", "view", str(issue_number), "--comments"],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown gh error"
        raise HTTPException(status_code=400, detail=f"gh issue view failed: {detail}")

    return result.stdout.strip()


def build_prompt(issue_number: int, issue_text: str) -> str:
    return (
        "A GitHub issue has been filed against this repository. "
        "Please resolve it by making the necessary changes to the code. "
        "The changes will be committed and a pull request will be created for them.\n\n"
        f"# GitHub Issue #{issue_number}\n\n"
        f"{issue_text}"
    )


def enqueue_job(job_id: str):
    r.rpush(QUEUE_NAME, job_id)


@app.post("/issues")
def create_issue_job(req: CreateIssueRequest):
    issue_number = req.issueNumber

    ensure_gh_auth()

    issue_text = fetch_issue_text(issue_number)
    prompt = build_prompt(issue_number, issue_text)

    job_id = str(uuid4())

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO jobs (id, prompt, status, issue_number)
        VALUES (%s, %s, 'queued', %s)
        """,
        (job_id, prompt, issue_number),
    )

    conn.commit()

    enqueue_job(job_id)

    return {
        "job_id": job_id,
        "status": "queued",
        "issue_number": issue_number,
    }
