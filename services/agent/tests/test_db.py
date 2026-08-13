from app.db import Db
from app.models import Job


class FakeCursor:
    def __init__(self):
        self.execute_calls = []
        self.fetchone_result = None
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def execute(self, sql, params=None):
        self.execute_calls.append((sql, params))

    def fetchone(self):
        return self.fetchone_result

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.closed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self._cursor.committed = True

    def rollback(self):
        self._cursor.rolled_back = True

    def close(self):
        self.closed = True


def make_db(cursor=None):
    cursor = cursor or FakeCursor()
    conn = FakeConn(cursor)
    return Db(get_conn=lambda: conn), cursor, conn


def test_fetch_job_builds_job():
    cursor = FakeCursor()
    cursor.fetchone_result = ("hello", 42, "deepseek/deepseek-v4-flash")
    db, cursor, conn = make_db(cursor)

    job = db.fetch_job("abc-123")

    assert isinstance(job, Job)
    assert job.job_id == "abc-123"
    assert job.prompt == "hello"
    assert job.issue_number == 42
    assert job.model == "deepseek/deepseek-v4-flash"
    assert not conn.closed
    assert cursor.closed
    assert cursor.execute_calls[0][1] == ("abc-123",)


def test_fetch_job_returns_none_model_when_unspecified():
    cursor = FakeCursor()
    cursor.fetchone_result = ("hello", 42, None)
    db, cursor, conn = make_db(cursor)

    job = db.fetch_job("abc-123")

    assert job.model is None


def test_fetch_job_returns_none_when_missing():
    cursor = FakeCursor()
    cursor.fetchone_result = None
    db, _cursor, conn = make_db(cursor)

    assert db.fetch_job("missing") is None
    assert not conn.closed


def test_mark_running_updates_job():
    db, cursor, conn = make_db()
    job = Job(job_id="abc-123", artifact_path="/artifacts/20260811-abc-123")

    db.mark_running(job)

    sql, params = cursor.execute_calls[0]
    assert "UPDATE jobs" in sql
    assert params == ("/artifacts/20260811-abc-123", "abc-123")
    assert cursor.committed
    assert not conn.closed


def test_complete_job_updates_status():
    db, cursor, conn = make_db()

    db.complete_job("abc-123", "completed", None, pr_number=99)

    sql, params = cursor.execute_calls[0]
    assert "UPDATE jobs" in sql
    assert params == ("completed", None, 99, "abc-123")
    assert cursor.committed
    assert not conn.closed


def test_complete_job_swallows_db_errors():
    cursor = FakeCursor()

    def boom(sql, params=None):
        raise Exception("db is down")

    cursor.execute = boom
    db, _cursor, conn = make_db(cursor)

    db.complete_job("abc-123", "failed", "boom")
    assert not conn.closed
    assert cursor.rolled_back


def test_reuses_single_connection():
    conn = FakeConn(FakeCursor())
    calls = []

    def factory():
        calls.append(1)
        return conn

    db = Db(get_conn=factory)

    db.fetch_job("abc-123")
    db.mark_running(Job(job_id="abc-123"))
    db.complete_job("abc-123", "completed", None)

    assert len(calls) == 1
    assert not conn.closed


def test_connection_is_recreated_when_closed():
    conn = FakeConn(FakeCursor())
    calls = []

    def factory():
        calls.append(1)
        return conn

    db = Db(get_conn=factory)
    conn.closed = True

    db.complete_job("abc-123", "completed", None)

    assert len(calls) == 2
