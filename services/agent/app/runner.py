import time
from typing import Optional

from app.db import Db
from app.queue_redis import Queue
from app.work_item import WorkItem


class JobRunner:
    def __init__(self, queue: Queue, db: Db, work_item_factory=WorkItem):
        self.queue = queue
        self._db = db
        self._work_item_factory = work_item_factory
        self._busy = False

    @property
    def busy(self) -> bool:
        return self._busy

    @classmethod
    def build(cls):
        return cls(queue=Queue(), db=Db())

    def dequeue_job(self) -> Optional[WorkItem]:
        if self._busy:
            return None

        job_id = self.queue.dequeue()
        if not job_id:
            return None

        job = self._db.fetch_job(job_id)
        if job is None:
            return None

        try:
            work_item = self._work_item_factory(job)
            self._db.mark_running(job)
        except Exception as e:
            self.complete_job(job_id, 'failed', str(e))
            return None

        self._busy = True
        return work_item

    def _run_prompt(self, command_runner, model: str, prompt: str):
        command_runner.run(
            [
                "opencode",
                "--dir", command_runner.working_dir,
                "--model", model,
                "run",
                "--agent", "build",
                prompt,
            ]
        )

    def run_job(self, work_item: WorkItem) -> Optional[int]:
        pr_number = None
        job = work_item.job
        command_runner = work_item.command_runner

        try:
            artifact_path = job.artifact_path
            prompt_file = artifact_path / "prompt.txt"
            prompt_file.write_text(job.prompt)

            output_file_path = artifact_path / "output.txt"
            issue = None
            with open(output_file_path, "w", encoding="utf-8") as output_file:
                command_runner.output_file = output_file

                if job.issue_number is not None:
                    issue = work_item.gh.fetch_issue(job.issue_number)
                    branch = work_item.branch_name_for_issue(issue["title"])
                    (default_branch, branch) = work_item.git.create_branch(branch)

                self._run_prompt(command_runner, work_item.model, job.prompt)

                if work_item.git.try_stage_changes():
                    work_item.git.commit_changes()

                    if job.issue_number is not None:
                        work_item.git.push_to_origin(branch)

                        title = f"Resolves #{job.issue_number}" if issue is None else issue['title']
                        pr_number = work_item.gh.create_pull_request(branch, default_branch, title, job.issue_number)
                else:
                    output_file.write("No changes staged; skipping commit and pull request.\n")

                work_item.git.checkout_branch(default_branch)
        except Exception as e:
            print("Error running job! " + str(e))
            return None
        finally:
            command_runner.output_file = None

        return pr_number

    def complete_job(self, job_id: str, status: str, error_desc: str, pr_number=None):
        self._db.complete_job(job_id, status, error_desc, pr_number)
        self._busy = False


def main():
    runner = JobRunner.build()

    while True:
        work_item = runner.dequeue_job()

        if work_item:
            pr_number = runner.run_job(work_item)
            runner.complete_job(work_item.job.job_id, 'completed', None, pr_number)

        time.sleep(2)


if __name__ == "__main__":
    main()
