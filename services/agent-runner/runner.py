# runtime/worker.py

import re
import subprocess
from pathlib import Path
import time
import os
import redis
import psycopg2
from datetime import datetime

from gh import ensure_gh_auth, fetch_issue_text

PROVIDER = os.getenv("OPENCODE_PROVIDER", "deepseek")
MODEL = os.getenv("OPENCODE_MODEL", "deepseek-v4-flash")
WORKSPACES_ROOT = Path("/workspaces")
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

def build_prompt(issue_number: int, issue_text: str) -> str:
    return (
        "A GitHub issue has been filed against this repository - the body and comments are below. "
        "Please resolve it by making the necessary changes to the code. "
        "The changes will be committed and a pull request will be created for them.\n\n"
        f"# GitHub Issue #{issue_number}\n\n"
        f"{issue_text}"
    )

def dequeue_job():
    try:
        _, job_id = r.blpop(QUEUE_NAME)
    except redis.exceptions.RedisError:
        return (None, None, None, None)

    if not job_id:
        return (None, None, None, None)

    conn = get_conn()
    cur = conn.cursor()

    effective_prompt = None
    try:
        cur.execute(
            "SELECT prompt, issue_number FROM jobs WHERE id = %s",
            (job_id,),
        )

        row = cur.fetchone()
        prompt = row[0]
        issue_number = row[1]

        if prompt is None and issue_number is not None:
            workspaces = str(WORKSPACES_ROOT)
            ensure_gh_auth()
            issue_text = fetch_issue_text(issue_number, workspaces)
            effective_prompt = build_prompt(issue_number, issue_text)
        else:
            effective_prompt = prompt


        now_stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        job_subdir = f"{now_stamp}-{job_id}"

        artifact_path = ARTIFACT_ROOT / job_subdir
        artifact_path.mkdir(parents=True, exist_ok=True)

        cur.execute(
            """
            UPDATE jobs
            SET status = 'running',
                started_at = NOW(),
                artifact_path = %s
            WHERE id = %s
            """,
            (str(artifact_path), job_id),
        )
        conn.commit()        
    except Exception as e:
        complete_job(job_id, 'failed', str(e))
        return (None, None, None, None)

    return (job_id, effective_prompt, artifact_path, issue_number)

def cmd_run(cmd, workspaces, output_file):
    result = subprocess.run(
        cmd,
        cwd=workspaces,
        capture_output=True,
        text=True,
    )
    output_file.write("$ " + " ".join(cmd) + "\n")
    output_file.write(result.stdout)
    output_file.write(result.stderr)
    output_file.write("\n\n")
    return result

def get_default_branch(workspaces):
    subprocess.run(
        ["git", "remote", "set-head", "origin", "-a"],
        cwd=workspaces,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        cwd=workspaces,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip().split("/")[-1]
    return "main"

def branch_for_job(issue_number):
    return f"feature/issue-{issue_number}"
    
def create_branch(workspaces, issue_number, output_file):
    default_branch = get_default_branch(workspaces)
    branch = branch_for_job(issue_number)
    cmd_run(["git", "checkout", "-B", branch, f"origin/{default_branch}"], workspaces, output_file)
    return (default_branch, branch)

def run_prompt(workspaces, model, prompt, output_file):
    cmd_run(
        [
            "opencode",
            "--dir", workspaces,
            "--model", model,
            "run",
            "--agent", "build",
            prompt
        ],
        workspaces,
        output_file)

def try_stage_changes(workspaces: str, output_file) -> bool:
    cmd_run(["git", "add", "-A"], workspaces, output_file)

    has_changes = cmd_run(["git", "diff", "--staged", "--quiet"], workspaces, output_file)
    return has_changes.returncode != 0

def commit_changes(workspaces, output_file):
    cmd_run(["git", "commit"], workspaces, output_file)

def push_to_origin(workspaces, branch, output_file):
    cmd_run(
        ["git", "push", "--set-upstream", "origin", branch],
        workspaces,
        output_file,
    )

def create_pull_request(workspaces, branch, default_branch, issue_number, output_file):
    cmd = ["gh", "pr", "create", "--base", default_branch, "--head", branch]
    if issue_number:
        cmd += [
            "--title", f"Resolve issue #{issue_number}",
            "--body", f"Closes #{issue_number}",
        ]
    else:
        cmd += ["--fill"]

    result = cmd_run(cmd, workspaces, output_file)

    if result.returncode != 0:
        return None

    match = re.search(r"pull/(\d+)", result.stdout)
    return int(match.group(1)) if match else None

def run_job(prompt, artifact_path, issue_number):
    pr_number = None

    try:
        workspaces = str(WORKSPACES_ROOT)

        prompt_file = artifact_path / "prompt.txt"
        prompt_file.write_text(prompt)

        ensure_gh_auth()

        opencode_model = PROVIDER + "/" + MODEL

        output_file_path = artifact_path / "output.txt"
        with open(output_file_path, "w", encoding="utf-8") as output_file:
            if issue_number is not None:
                (default_branch, branch) = create_branch(workspaces, issue_number, output_file)

            run_prompt(workspaces, opencode_model, prompt, output_file)

            if not try_stage_changes(workspaces, output_file):
                output_file.write("No changes staged; skipping commit and pull request.\n")
                return None

            commit_changes(workspaces, output_file)

            if issue_number is not None:
                push_to_origin(workspaces, branch, output_file)
                pr_number = create_pull_request(workspaces, branch, default_branch, issue_number, output_file)
    except Exception as e:
        print("Error running job! " + str(e))
        return None

    return pr_number

def complete_job(job_id, status, error_desc, pr_number=None):
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            UPDATE jobs
            SET status = %s,
                error = %s,
                pr_number = COALESCE(%s, pr_number),
                completed_at = NOW()
            WHERE id = %s
            """,
            (status, error_desc, pr_number, job_id),
        )

        conn.commit()
    except Exception as e:
        print("Error completing job! " + e)

while True:
    ## TODO: proper data model
    job_id, prompt, artifact_path, issue_number = dequeue_job()

    if job_id:
        pr_number = run_job(prompt, artifact_path, issue_number)
        complete_job(job_id, 'completed', None, pr_number)

    time.sleep(2)
