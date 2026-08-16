import time
from typing import Optional

from app import config
from app.db import Db
from app.queue_redis import Queue
from app.JobItem import JobItem
from datetime import datetime
from pathlib import Path


class JobRunner:
    def __init__(self, queue: Queue, db: Db, job_item_factory=JobItem):
        self.queue = queue
        self._db = db
        self._job_item_factory = job_item_factory
        self._busy = False

    @property
    def busy(self) -> bool:
        return self._busy

    @classmethod
    def build(cls):
        return cls(queue=Queue(), db=Db())

    @staticmethod
    def _make_artifact_path(job_id: str) -> Path:
        now_stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return config.ARTIFACT_ROOT / f"{now_stamp}-{job_id}"

    def dequeue_job(self) -> Optional[JobItem]:
        if self._busy:
            return None

        job_id = self.queue.dequeue()
        if not job_id:
            return None

        job = self._db.fetch_job(job_id)
        if job is None:
            return None

        try:
            job_item = self._job_item_factory(job, db=self._db)
            self._db.mark_running(job)
        except Exception as e:
            self.complete_job(job_id, 'failed', f"Error dequeueing job! {e}")
            return None

        self._busy = True
        return job_item

    def run_job(self, job_item: JobItem):
        artifact_path = self._make_artifact_path(job_item.job.job_id)
        artifact_path.mkdir(parents=True, exist_ok=True)

        (artifact_path / "prompt.txt").write_text(job_item.job.prompt)

        try:
            with open(artifact_path / "output.txt", "w", encoding="utf-8") as output_file:
                job_item.command_runner.output_file = output_file
                try:
                    job_item.run()
                finally:
                    job_item.command_runner.output_file = None
        except Exception as e:
            self.complete_job(job_item.job.job_id, 'failed', f"Error running job! {e}")

    def complete_job(self, job_id: str, status: str, error_desc: str):
        self._db.complete_job(job_id, status, error_desc)
        self._busy = False


def main():
    runner = JobRunner.build()

    while True:
        job_item = runner.dequeue_job()

        if job_item:
            runner.run_job(job_item)
            runner.complete_job(job_item.job.job_id, 'completed', None)

        time.sleep(2)


if __name__ == "__main__":
    main()
