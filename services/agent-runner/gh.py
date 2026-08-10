import os
import subprocess


def ensure_gh_auth():
    token = os.getenv("GH_TOKEN")
    if not token:
        return

    res = subprocess.run(
        ["gh", "auth", "status"],
        capture_output=True,
        text=True,
    )

    if res.returncode == 0:
        return

    subprocess.run(
        ["gh", "auth", "login", "--with-token"],
        input=token,
        capture_output=True,
        text=True,
    )

def fetch_issue_text(issue_number: int) -> str:
    result = subprocess.run(
        ["gh", "issue", "view", str(issue_number), "--comments"],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown gh error"
        raise Exception(f"gh issue view failed: {detail}")

    return result.stdout.strip()
