import json
import os
import re
from typing import Optional, TextIO

from app.command_runner import CommandRunner


class Gh:
    def __init__(self, command_runner: CommandRunner):
        self.command_runner = command_runner

    def ensure_gh_auth(self):
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

    def fetch_issue_text(self, issue_number: int) -> str:
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

        issue = json.loads(result.stdout)

        output = ""
        output += f"Title: {issue['title']}\n"
        output += f"Body: {issue['body']}\n"

        if issue["comments"]:
            output += "Comments\n"
            for comment in issue["comments"]:
                output += comment["body"]

        return output

    def create_pull_request(
        self,
        branch: str,
        default_branch: str,
        issue_number: Optional[int],
        output_file: TextIO,
    ) -> Optional[int]:
        cmd = ["gh", "pr", "create", "--base", default_branch, "--head", branch]
        if issue_number:
            cmd += [
                "--title", f"Resolve issue #{issue_number}",
                "--body", f"Closes #{issue_number}",
            ]
        else:
            cmd += ["--fill"]

        result = self.command_runner.run(cmd, output_file)

        if result.returncode != 0:
            return None

        match = re.search(r"pull/(\d+)", result.stdout)
        return int(match.group(1)) if match else None
