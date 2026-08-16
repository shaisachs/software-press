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
            work_item = self._work_item_factory(job, db=self._db)
            self._db.mark_running(job)
        except Exception as e:
            self.complete_job(job_id, 'failed', str(e))
            return None

        self._busy = True
        return work_item

    def run_job(self, work_item: WorkItem) -> Optional[int]:
        artifact_path = work_item.job.artifact_path
        (artifact_path / "prompt.txt").write_text(work_item.job.prompt)

        try:
            with open(artifact_path / "output.txt", "w", encoding="utf-8") as output_file:
                work_item.command_runner.output_file = output_file
                try:
                    result = work_item.run()
                finally:
                    work_item.command_runner.output_file = None

                if not result.changes_staged:
                    output_file.write("No changes staged; skipping commit and pull request.\n")

                return result.pr_number
        except Exception as e:
            print("Error running job! " + str(e))
            return None

    def complete_job(self, job_id: str, status: str, error_desc: str):
        self._db.complete_job(job_id, status, error_desc)
        self._busy = False


def main():
    runner = JobRunner.build()

    while True:
        work_item = runner.dequeue_job()

        if work_item:
            runner.run_job(work_item)
            runner.complete_job(work_item.job.job_id, 'completed', None)

        time.sleep(2)


if __name__ == "__main__":
    main()
