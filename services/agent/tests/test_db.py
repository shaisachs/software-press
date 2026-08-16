from app.db import Db
from app.models import Job


def make_db(mocker, fetchone_result=None):
    conn = mocker.Mock()
    conn.closed = False
    cursor = mocker.Mock()
    cursor.fetchone.return_value = fetchone_result
    conn.cursor.return_value = cursor
    return Db(get_conn=lambda: conn), cursor, conn


def test_fetch_job_builds_job(mocker):
    db, cursor, conn = make_db(
        mocker,
        fetchone_result=("hello", 42, "shaisachs/laws-of-software", "deepseek/deepseek-v4-flash", "develop", "issueResolver"),
    )

    job = db.fetch_job("abc-123")

    assert isinstance(job, Job)
    assert job.job_id == "abc-123"
    assert job.prompt == "hello"
    assert job.issue_number == 42
    assert job.repo == "shaisachs/laws-of-software"
    assert job.model == "deepseek/deepseek-v4-flash"
    assert job.branch == "develop"
    assert job.type == "issueResolver"
    assert not conn.closed
    cursor.close.assert_called_once_with()
    sql, params = cursor.execute.call_args.args
    assert "SELECT" in sql
    assert params == ("abc-123",)


def test_fetch_job_returns_none_when_missing(mocker):
    db, cursor, conn = make_db(mocker, fetchone_result=None)

    assert db.fetch_job("missing") is None
    assert not conn.closed


def test_mark_running_updates_job(mocker):
    db, cursor, conn = make_db(mocker)
    job = Job(job_id="abc-123", artifact_path="/artifacts/20260811-abc-123")

    db.mark_running(job)

    sql, params = cursor.execute.call_args.args
    assert "UPDATE jobs" in sql
    assert params == ("/artifacts/20260811-abc-123", "abc-123")
    conn.commit.assert_called_once_with()
    assert not conn.closed


def test_complete_job_updates_status(mocker):
    db, cursor, conn = make_db(mocker)

    db.complete_job("abc-123", "completed", None, pr_number=99)

    sql, params = cursor.execute.call_args.args
    assert "UPDATE jobs" in sql
    assert params == ("completed", None, 99, "abc-123")
    conn.commit.assert_called_once_with()
    assert not conn.closed


def test_record_pr_number_updates_job(mocker):
    db, cursor, conn = make_db(mocker)

    db.record_pr_number("abc-123", 99)

    sql, params = cursor.execute.call_args.args
    assert "UPDATE jobs" in sql
    assert params == (99, "abc-123")
    conn.commit.assert_called_once_with()
    assert not conn.closed


def test_record_pr_number_swallows_db_errors(mocker):
    db, cursor, conn = make_db(mocker)
    cursor.execute.side_effect = Exception("db is down")

    db.record_pr_number("abc-123", 99)

    conn.rollback.assert_called_once_with()
    assert not conn.closed


def test_complete_job_swallows_db_errors(mocker):
    db, cursor, conn = make_db(mocker)
    cursor.execute.side_effect = Exception("db is down")

    db.complete_job("abc-123", "failed", "boom")

    conn.rollback.assert_called_once_with()
    assert not conn.closed


def test_reuses_single_connection(mocker):
    conn = mocker.Mock()
    conn.closed = False
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


def test_connection_is_recreated_when_closed(mocker):
    conn = mocker.Mock()
    conn.closed = True
    calls = []

    def factory():
        calls.append(1)
        return conn

    db = Db(get_conn=factory)

    db.complete_job("abc-123", "completed", None)

    assert len(calls) == 2
