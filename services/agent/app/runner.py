import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from app import config
from app.command_runner import CommandRunner
from app.db import Db
from app.gh import GithubClient
from app.git import Git
from app.models import Job
from app.queue_redis import Queue


class Runner:
    def __init__(self, queue: Queue, db: Db, gh: GithubClient, git: Git, command_runner: CommandRunner):
        self.queue = queue
        self._db = db
        self._gh = gh
        self._git = git
        self._command_runner = command_runner

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
    def _make_artifact_path(job_id: str) -> Path:
        now_stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return config.ARTIFACT_ROOT / f"{now_stamp}-{job_id}"

    @staticmethod
    def branch_name_for_issue(issue_title: str) -> str:
        kebab = re.sub(r"[^a-z0-9]+", "-", issue_title.lower()).strip("-")
        return f"feature/{kebab}"

    @classmethod
    def build(cls):
        command_runner = CommandRunner(str(config.WORKSPACES_ROOT))
        return cls(
            queue=Queue(),
            db=Db(),
            gh=GithubClient(command_runner),
            git=Git(command_runner),
            command_runner=command_runner,
        )

    @staticmethod
    def _workspace_dir(repo: str) -> Path:
        return config.WORKSPACES_ROOT / repo

    def _validate_repo(self, repo: str) -> Path:
        if not repo:
            raise Exception("repo is required")
        workspace_dir = self._workspace_dir(repo)
        if not workspace_dir.is_dir():
            raise Exception(f"repo directory not found on disk: {workspace_dir}")
        return workspace_dir

    def dequeue_job(self) -> Optional[Job]:
        job_id = self.queue.dequeue()
        if not job_id:
            return None

        job = self._db.fetch_job(job_id)
        if job is None:
            return None

        try:
            if job.model is not None and not config.model_is_available(job.model):
                raise Exception(f"model is unavailable: {job.model}")

            self._validate_repo(job.repo)

            if job.issue_number is not None and job.prompt is None:
                issue = self._gh.fetch_issue(job.issue_number)
                job.prompt = self._build_prompt(job.issue_number, self._format_issue_text(issue))

            job.artifact_path = self._make_artifact_path(job_id)
            job.artifact_path.mkdir(parents=True, exist_ok=True)

            self._db.mark_running(job)
        except Exception as e:
            self.complete_job(job_id, 'failed', str(e))
            return None

        return job

    def _run_prompt(self, model: str, prompt: str):
        self._command_runner.run(
            [
                "opencode",
                "--dir", self._command_runner.working_dir,
                "--model", model,
                "run",
                "--agent", "build",
                prompt,
            ]
        )

    def run_job(self, job: Job) -> Optional[int]:
        pr_number = None

        try:
            workspace_dir = self._validate_repo(job.repo)
            self._command_runner.working_dir = str(workspace_dir)

            artifact_path = job.artifact_path
            prompt_file = artifact_path / "prompt.txt"
            prompt_file.write_text(job.prompt)

            opencode_model = job.model or config.opencode_model()

            output_file_path = artifact_path / "output.txt"
            issue = None
            with open(output_file_path, "w", encoding="utf-8") as output_file:
                self._command_runner.output_file = output_file

                if job.issue_number is not None:
                    issue = self._gh.fetch_issue(job.issue_number)
                    branch = self.branch_name_for_issue(issue["title"])
                    (default_branch, branch) = self._git.create_branch(branch)

                self._run_prompt(opencode_model, job.prompt)

                if not self._git.try_stage_changes():
                    output_file.write("No changes staged; skipping commit and pull request.\n")
                    return None

                self._git.commit_changes()

                if job.issue_number is not None:
                    self._git.push_to_origin(branch)

                    title = f"Resolves #{job.issue_number}" if issue is None else issue['title']
                    pr_number = self._gh.create_pull_request(branch, default_branch, title, job.issue_number)

                    self._git.checkout_branch(default_branch)
        except Exception as e:
            print("Error running job! " + str(e))
            return None
        finally:
            self._command_runner.output_file = None

        return pr_number

    def complete_job(self, job_id: str, status: str, error_desc: str, pr_number=None):
        self._db.complete_job(job_id, status, error_desc, pr_number)


def main():
    runner = Runner.build()

    while True:
        job = runner.dequeue_job()

        if job:
            pr_number = runner.run_job(job)
            runner.complete_job(job.job_id, 'completed', None, pr_number)

        time.sleep(2)


if __name__ == "__main__":
    main()
