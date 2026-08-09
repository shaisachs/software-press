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
