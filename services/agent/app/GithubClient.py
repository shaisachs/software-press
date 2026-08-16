import json
import os
import re
from typing import Optional

from app.command_runner import CommandRunner


class GithubClient:
    def __init__(self, command_runner: CommandRunner):
        self.command_runner = command_runner

    def _ensure_gh_auth(self):
        token = os.getenv("GH_TOKEN")
        if not token:
            return

        res = self.command_runner.run(["gh", "auth", "status"])
        if res.returncode == 0:
            return

        self.command_runner.run(
            ["gh", "auth", "login", "--with-token"],
            input=token,
        )

    def fetch_issue(self, issue_number: int) -> dict:
        self._ensure_gh_auth()

        result = self.command_runner.run(
            [
                "gh",
                "issue",
                "view",
                str(issue_number),
                "--comments",
                "--json",
                "number,title,body,comments",
            ]
        )

        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown gh error"
            raise Exception(f"gh issue view failed: {detail}")

        return json.loads(result.stdout)

    def create_issue_comment(self, issue_number: int, body: str):
        self._ensure_gh_auth()

        result = self.command_runner.run(
            ["gh", "issue", "comment", str(issue_number), "--body", body]
        )

        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown gh error"
            raise Exception(f"gh issue comment failed: {detail}")

        return result.stdout

    def create_pull_request(
        self,
        branch: str,
        default_branch: str,
        title: str,
        issue_number: Optional[int],
    ) -> Optional[int]:
        self._ensure_gh_auth()

        cmd = ["gh", "pr", "create", "--base", default_branch, "--head", branch]
        if issue_number:
            cmd += [
                "--title", title,
                "--body", f"Closes #{issue_number}",
            ]
        else:
            cmd += ["--fill"]

        result = self.command_runner.run(cmd)

        if result.returncode != 0:
            return None

        match = re.search(r"pull/(\d+)", result.stdout)
        return int(match.group(1)) if match else None
