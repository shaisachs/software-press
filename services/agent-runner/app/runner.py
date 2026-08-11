import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from app import config
from app.command_runner import CommandRunner
from app.db import Db
from app.gh import Gh
from app.git import Git
from app.models import Job
from app.queue_redis import Queue


def build_prompt(issue_number: int, issue_text: str) -> str:
    return (
        "A GitHub issue has been filed against this repository - the body and comments are below. "
        "Please resolve it by making the necessary changes to the code. "
        "The changes will be committed and a pull request will be created for them.\n\n"
        f"# GitHub Issue #{issue_number}\n\n"
        f"{issue_text}"
    )


def make_artifact_path(job_id: str) -> Path:
    now_stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return config.ARTIFACT_ROOT / f"{now_stamp}-{job_id}"


class Runner:
    def __init__(self, queue: Queue, db: Db, gh: Gh, git: Git, command_runner: CommandRunner):
        self.queue = queue
        self._db = db
        self._gh = gh
        self._git = git
        self._command_runner = command_runner

    @classmethod
    def build(cls):
        command_runner = CommandRunner(str(config.WORKSPACES_ROOT))
        return cls(
            queue=Queue(),
            db=Db(),
            gh=Gh(command_runner),
            git=Git(command_runner),
            command_runner=command_runner,
        )

    def dequeue_job(self) -> Optional[Job]:
        job_id = self.queue.dequeue()
        if not job_id:
            return None

        job = self._db.fetch_job(job_id)
        if job is None:
            return None

        try:
            if job.prompt is None and job.issue_number is not None:
                issue_text = self._gh.fetch_issue_text(job.issue_number)
                job.prompt = build_prompt(job.issue_number, issue_text)

            job.artifact_path = make_artifact_path(job_id)
            job.artifact_path.mkdir(parents=True, exist_ok=True)

            self._db.mark_running(job)
        except Exception as e:
            self.complete_job(job_id, 'failed', str(e))
            return None

        return job

    def _run_prompt(self, model: str, prompt: str, output_file):
        self._command_runner.run(
            [
                "opencode",
                "--dir", self._command_runner.working_dir,
                "--model", model,
                "run",
                "--agent", "build",
                prompt,
            ],
            output_file,
        )

    def run_job(self, job: Job) -> Optional[int]:
        pr_number = None

        try:
            artifact_path = job.artifact_path
            prompt_file = artifact_path / "prompt.txt"
            prompt_file.write_text(job.prompt)

            opencode_model = config.opencode_model()

            output_file_path = artifact_path / "output.txt"
            with open(output_file_path, "w", encoding="utf-8") as output_file:
                if job.issue_number is not None:
                    (default_branch, branch) = self._git.create_branch(job.issue_number, output_file)

                self._run_prompt(opencode_model, job.prompt, output_file)

                if not self._git.try_stage_changes(output_file):
                    output_file.write("No changes staged; skipping commit and pull request.\n")
                    return None

                self._git.commit_changes(output_file)

                if job.issue_number is not None:
                    self._git.push_to_origin(branch, output_file)
                    pr_number = self._gh.create_pull_request(branch, default_branch, job.issue_number, output_file)
        except Exception as e:
            print("Error running job! " + str(e))
            return None

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
