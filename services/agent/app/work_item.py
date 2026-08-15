import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from app import config
from app.command_runner import CommandRunner
from app.GithubClient import GithubClient
from app.GitClient import GitClient
from app.models import Job


class WorkItem:
    def __init__(self, job: Job, gh=None, git=None, command_runner=None):
        self.job = job

        if job.model is not None and not config.model_is_available(job.model):
            raise Exception(f"model is unavailable: {job.model}")

        self.workspace_dir = self._validate_repo(job.repo)
        self.command_runner = command_runner or CommandRunner(str(self.workspace_dir))
        self.command_runner.working_dir = str(self.workspace_dir)
        self.gh = gh or GithubClient(self.command_runner)
        self.git = git or GitClient(self.command_runner)

        if job.artifact_path is None:
            job.artifact_path = self._make_artifact_path(job.job_id)
            job.artifact_path.mkdir(parents=True, exist_ok=True)

        if job.issue_number is not None and job.prompt is None:
            issue = self.gh.fetch_issue(job.issue_number)
            job.prompt = self._build_prompt(job.issue_number, self._format_issue_text(issue))

    @property
    def model(self) -> str:
        return self.job.model or config.opencode_model()

    @staticmethod
    def _workspace_dir(repo: str) -> Path:
        return config.WORKSPACES_ROOT / repo

    @classmethod
    def _validate_repo(cls, repo: str) -> Path:
        if not repo:
            raise Exception("repo is required")
        workspace_dir = cls._workspace_dir(repo)
        if not workspace_dir.is_dir():
            raise Exception(f"repo directory not found on disk: {workspace_dir}")
        return workspace_dir

    @staticmethod
    def _make_artifact_path(job_id: str) -> Path:
        now_stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return config.ARTIFACT_ROOT / f"{now_stamp}-{job_id}"

    @staticmethod
    def _format_issue_text(issue: dict) -> str:
        output = ""
        output += f"Title: {issue['title']}\n"
        output += f"Body: {issue['body']}\n"

        if issue["comments"]:
            output += "Comments\n"
            for comment in issue["comments"]:
                output += comment["body"]

        return output

    @staticmethod
    def _build_prompt(issue_number: int, issue_text: str) -> str:
        return (
            "A GitHub issue has been filed against this repository - the body and comments are below. "
            "Please resolve it by making the necessary changes to the code. "
            "The changes will be committed and a pull request will be created for them.\n\n"
            f"# GitHub Issue #{issue_number}\n\n"
            f"{issue_text}"
        )

    @staticmethod
    def branch_name_for_issue(issue_title: str) -> str:
        kebab = re.sub(r"[^a-z0-9]+", "-", issue_title.lower()).strip("-")
        return f"feature/{kebab}"
