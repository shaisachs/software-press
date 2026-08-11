import psycopg2

from app.config import POSTGRES_DB, POSTGRES_HOST, POSTGRES_PASSWORD, POSTGRES_USER
from app.models import Job


def get_conn():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


class Db:
    def __init__(self):
        self._get_conn = get_conn

    def fetch_job(self, job_id: str) -> Job:
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT prompt, issue_number FROM jobs WHERE id = %s",
                (job_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return Job(job_id=job_id, prompt=row[0], issue_number=row[1])
        finally:
            conn.close()

    def mark_running(self, job: Job):
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                UPDATE jobs
                SET status = 'running',
                    started_at = NOW(),
                    artifact_path = %s
                WHERE id = %s
                """,
                (str(job.artifact_path), job.job_id),
            )
            conn.commit()
        finally:
            conn.close()

    def complete_job(self, job_id: str, status: str, error_desc: str, pr_number=None):
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                UPDATE jobs
                SET status = %s,
                    error = %s,
                    pr_number = COALESCE(%s, pr_number),
                    completed_at = NOW()
                WHERE id = %s
                """,
                (status, error_desc, pr_number, job_id),
            )
            conn.commit()
        except Exception as e:
            print("Error completing job! " + str(e))
        finally:
            conn.close()
