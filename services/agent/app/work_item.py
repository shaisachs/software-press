import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from app import config
from app.command_runner import CommandRunner
from app.db import Db
from app.GithubClient import GithubClient
from app.GitClient import GitClient
from app.models import Job

class WorkItem:
    def __init__(self, job: Job, gh=None, git=None, command_runner=None, db=None):
        self.job = job

        if job.model is not None and not config.model_is_available(job.model):
            raise Exception(f"model is unavailable: {job.model}")

        self.workspace_dir = self._validate_repo(job.repo)
        self.command_runner = command_runner or CommandRunner(str(self.workspace_dir))
        self.command_runner.working_dir = str(self.workspace_dir)
        self.gh = gh or GithubClient(self.command_runner)
        self.git = git or GitClient(self.command_runner)
        self.db = db or Db()

        if job.artifact_path is None:
            job.artifact_path = self._make_artifact_path(job.job_id)
            job.artifact_path.mkdir(parents=True, exist_ok=True)

        if job.issue_number is not None and job.prompt is None:
            issue = self.fetch_issue(job.issue_number)
            job.prompt = self._build_prompt(job.issue_number, self._format_issue_text(issue))

    @property
    def model(self) -> str:
        return self.job.model or config.opencode_model()

    def fetch_issue(self, issue_number: int) -> dict:
        return self.gh.fetch_issue(issue_number)

    def create_branch(self, branch: str) -> Tuple[str, str]:
        return self.git.create_branch(branch)

    def try_stage_changes(self) -> bool:
        return self.git.try_stage_changes()

    def commit_changes(self):
        self.git.commit_changes()

    def push_to_origin(self, branch: str):
        self.git.push_to_origin(branch)

    def checkout_branch(self, branch: str):
        self.git.checkout_branch(branch)

    def create_pull_request(
        self,
        branch: str,
        default_branch: str,
        title: str,
        issue_number: Optional[int],
    ) -> Optional[int]:
        return self.gh.create_pull_request(branch, default_branch, title, issue_number)

    def record_pr_number(self, pr_number: int):
        self.db.record_pr_number(self.job.job_id, pr_number)

    def run_prompt(self):
        self.command_runner.run(
            [
                "opencode",
                "--dir", self.command_runner.working_dir,
                "--model", self.model,
                "run",
                "--agent", "build",
                self.job.prompt,
            ]
        )

    def run(self):
        issue = None
        default_branch = None
        pr_number = None

        if self.job.issue_number is not None:
            issue = self.fetch_issue(self.job.issue_number)
            branch = self.branch_name_for_issue(issue["title"])
            (default_branch, branch) = self.create_branch(branch)

        self.run_prompt()

        if self.try_stage_changes():
            self.commit_changes()

            if self.job.issue_number is not None:
                self.push_to_origin(branch)

                title = f"Resolves #{self.job.issue_number}" if issue is None else issue["title"]
                pr_number = self.create_pull_request(branch, default_branch, title, self.job.issue_number)
                if pr_number is not None:
                    self.record_pr_number(pr_number)
        else:
            # TODO: proper logging framework, this access pattern kind of sucks
            self.command_runner.output_file.write("No changes staged; skipping commit and pull request.\n")

        if default_branch is not None:
            self.checkout_branch(default_branch)

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
