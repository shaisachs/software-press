from app.db import Db
from app.models import Job


class FakeCursor:
    def __init__(self):
        self.execute_calls = []
        self.fetchone_result = None
        self.committed = False

    def execute(self, sql, params=None):
        self.execute_calls.append((sql, params))

    def fetchone(self):
        return self.fetchone_result

    def commit(self):
        self.committed = True


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.closed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self._cursor.committed = True

    def close(self):
        self.closed = True


def make_db(monkeypatch, cursor=None):
    cursor = cursor or FakeCursor()
    conn = FakeConn(cursor)
    monkeypatch.setattr("app.db.get_conn", lambda: conn)
    return Db(), cursor, conn


def test_fetch_job_builds_job(monkeypatch):
    cursor = FakeCursor()
    cursor.fetchone_result = ("hello", 42)
    db, cursor, conn = make_db(monkeypatch, cursor)

    job = db.fetch_job("abc-123")

    assert isinstance(job, Job)
    assert job.job_id == "abc-123"
    assert job.prompt == "hello"
    assert job.issue_number == 42
    assert conn.closed
    assert cursor.execute_calls[0][1] == ("abc-123",)


def test_fetch_job_returns_none_when_missing(monkeypatch):
    cursor = FakeCursor()
    cursor.fetchone_result = None
    db, _cursor, conn = make_db(monkeypatch, cursor)

    assert db.fetch_job("missing") is None
    assert conn.closed


def test_mark_running_updates_job(monkeypatch):
    db, cursor, conn = make_db(monkeypatch)
    job = Job(job_id="abc-123", artifact_path="/artifacts/20260811-abc-123")

    db.mark_running(job)

    sql, params = cursor.execute_calls[0]
    assert "UPDATE jobs" in sql
    assert params == ("/artifacts/20260811-abc-123", "abc-123")
    assert cursor.committed
    assert conn.closed


def test_complete_job_updates_status(monkeypatch):
    db, cursor, conn = make_db(monkeypatch)

    db.complete_job("abc-123", "completed", None, pr_number=99)

    sql, params = cursor.execute_calls[0]
    assert "UPDATE jobs" in sql
    assert params == ("completed", None, 99, "abc-123")
    assert cursor.committed
    assert conn.closed


def test_complete_job_swallows_db_errors(monkeypatch):
    cursor = FakeCursor()

    def boom(sql, params=None):
        raise Exception("db is down")

    cursor.execute = boom
    db, _cursor, conn = make_db(monkeypatch, cursor)

    db.complete_job("abc-123", "failed", "boom")
    assert conn.closed
