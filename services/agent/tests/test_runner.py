from app import config
from app.models import Job
from app.runner import JobRunner
from app.work_item import WorkItem

from tests.conftest import (
    VALID_REPO,
    FakeCommandRunner,
    FakeDb,
    FakeGit,
    FakeGithubClient,
    FakeQueue,
    use_workspaces,
)


def make_work_item(job, gh=None, git=None, command_runner=None):
    return WorkItem(
        job=job,
        gh=gh if gh is not None else FakeGithubClient(),
        git=git if git is not None else FakeGit(),
        command_runner=command_runner if command_runner is not None else FakeCommandRunner(),
    )


def make_runner(tmp_path, job=None, queue_job_id="abc-123"):
    queue = FakeQueue(queue_job_id)
    db = FakeDb(job)
    gh = FakeGithubClient()
    git = FakeGit()
    command_runner = FakeCommandRunner()

    def factory(job):
        return WorkItem(job=job, gh=gh, git=git, command_runner=command_runner)

    runner = JobRunner(queue=queue, db=db, work_item_factory=factory)
    return runner, db, gh, git, command_runner


def test_dequeue_job_returns_none_when_queue_empty(tmp_path):
    runner, db, gh, git, command_runner = make_runner(tmp_path, queue_job_id=None)
    assert runner.dequeue_job() is None
    assert db.fetched_ids == []


def test_dequeue_job_returns_none_while_busy(tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt="write hello world", repo=VALID_REPO)
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)

    first = runner.dequeue_job()

    assert first is not None
    assert first.job is job
    assert runner.busy
    assert db.fetched_ids == ["abc-123"]

    second = runner.dequeue_job()
    assert second is None
    assert runner.busy
    assert db.fetched_ids == ["abc-123"]


def test_complete_job_clears_busy(tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt="write hello world", repo=VALID_REPO)
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)

    assert runner.dequeue_job() is not None
    assert runner.busy

    runner.complete_job("abc-123", "completed", None, pr_number=99)

    assert not runner.busy
    assert runner.dequeue_job() is not None
    assert db.fetched_ids == ["abc-123", "abc-123"]


def test_dequeue_job_uses_stored_prompt(tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt="write hello world", repo=VALID_REPO)
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)

    work_item = runner.dequeue_job()

    assert work_item.job is job
    assert job.prompt == "write hello world"
    assert gh.calls == []
    assert db.running == [job]
    assert job.artifact_path is not None
    assert job.artifact_path.is_dir()


def test_dequeue_job_fetches_issue_text_when_prompt_missing(tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt=None, issue_number=42, repo=VALID_REPO)
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)

    work_item = runner.dequeue_job()

    assert work_item.job is job
    assert gh.calls == [("fetch_issue", 42)]
    assert "# GitHub Issue #42" in job.prompt
    assert "Title: Fix the bug" in job.prompt
    assert "the issue" in job.prompt
    assert db.running == [job]


def test_dequeue_job_marks_failed_on_error(tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt=None, issue_number=42, repo=VALID_REPO)
    queue = FakeQueue("abc-123")
    db = FakeDb(job)

    class Boom(FakeGithubClient):
        def fetch_issue(self, issue_number):
            raise Exception("gh is down")

    def factory(job):
        return WorkItem(job=job, gh=Boom(), git=FakeGit(), command_runner=FakeCommandRunner())

    runner = JobRunner(queue=queue, db=db, work_item_factory=factory)

    assert runner.dequeue_job() is None
    assert not runner.busy
    assert db.completed == [("abc-123", "failed", "gh is down", None)]


def test_dequeue_job_marks_failed_when_repo_missing_on_disk(tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt="write hello world", repo="owner/not-cloned")
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)

    assert runner.dequeue_job() is None
    assert db.running == []
    assert len(db.completed) == 1
    job_id, status, error, _pr = db.completed[0]
    assert job_id == "abc-123"
    assert status == "failed"
    assert "not found on disk" in error


def test_dequeue_job_marks_failed_when_repo_missing(tmp_path, monkeypatch):
    job = Job(job_id="abc-123", prompt="write hello world", repo=None)
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)

    assert runner.dequeue_job() is None
    assert db.running == []
    assert db.completed == [("abc-123", "failed", "repo is required", None)]


def test_dequeue_job_marks_failed_when_model_unavailable(tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt="write hello world", repo=VALID_REPO, model="deepseek/not-a-model")
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)

    monkeypatch.setattr(config, "model_is_available", lambda model: False)

    assert runner.dequeue_job() is None
    assert db.running == []
    assert db.completed == [("abc-123", "failed", "model is unavailable: deepseek/not-a-model", None)]


def test_dequeue_job_accepts_available_model(tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt="write hello world", repo=VALID_REPO, model="deepseek/deepseek-v4-pro")
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)

    monkeypatch.setattr(config, "model_is_available", lambda model: True)

    work_item = runner.dequeue_job()

    assert work_item.job is job
    assert db.running == [job]


def test_complete_job_delegates_to_db(tmp_path):
    runner, db, gh, git, command_runner = make_runner(tmp_path)

    runner.complete_job("abc-123", "completed", None, pr_number=99)

    assert db.completed == [("abc-123", "completed", None, 99)]
    assert not runner.busy


def test_run_job_with_issue_number(tmp_path, monkeypatch):
    repo_dir = use_workspaces(monkeypatch, tmp_path)
    artifact_path = tmp_path / "artifacts"
    artifact_path.mkdir()
    job = Job(
        job_id="abc-123",
        prompt="fix it",
        issue_number=42,
        repo=VALID_REPO,
        artifact_path=artifact_path,
    )
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)
    work_item = make_work_item(job, gh=gh, git=git, command_runner=command_runner)

    pr_number = runner.run_job(work_item)

    assert pr_number == 99
    assert command_runner.working_dir == str(repo_dir)
    assert (artifact_path / "prompt.txt").read_text() == "fix it"
    assert (artifact_path / "output.txt").exists()
    assert ("create_branch", "feature/fix-the-bug") in git.calls
    assert ("push_to_origin", "feature/fix-the-bug") in git.calls
    assert ("create_pull_request", "feature/fix-the-bug", "main", "Fix the bug", 42) in gh.calls
    assert ("fetch_issue", 42) in gh.calls
    opencode_calls = [c for (c, _in) in command_runner.calls if c[0] == "opencode"]
    assert len(opencode_calls) == 1
    assert opencode_calls[0][2] == str(repo_dir)
    assert opencode_calls[0][4] == config.opencode_model()


def test_run_job_uses_selected_model(tmp_path, monkeypatch):
    repo_dir = use_workspaces(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "model_is_available", lambda model: True)
    artifact_path = tmp_path / "artifacts"
    artifact_path.mkdir()
    job = Job(
        job_id="abc-123",
        prompt="fix it",
        repo=VALID_REPO,
        model="deepseek/deepseek-v4-pro",
        artifact_path=artifact_path,
    )
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)
    work_item = make_work_item(job, gh=gh, git=git, command_runner=command_runner)

    pr_number = runner.run_job(work_item)

    assert pr_number is None
    opencode_calls = [c for (c, _in) in command_runner.calls if c[0] == "opencode"]
    assert len(opencode_calls) == 1
    assert opencode_calls[0][4] == "deepseek/deepseek-v4-pro"


def test_run_job_without_issue_number(tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    artifact_path = tmp_path / "artifacts"
    artifact_path.mkdir()
    job = Job(
        job_id="abc-123",
        prompt="fix it",
        issue_number=None,
        repo=VALID_REPO,
        artifact_path=artifact_path,
    )
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)
    work_item = make_work_item(job, gh=gh, git=git, command_runner=command_runner)

    pr_number = runner.run_job(work_item)

    assert pr_number is None
    assert not [c for c in git.calls if c[0] == "create_branch"]
    assert not [c for c in git.calls if c[0] == "push_to_origin"]
    assert not [c for c in gh.calls if c[0] == "create_pull_request"]
    assert ("commit_changes",) in git.calls


def test_run_job_skips_commit_and_pr_when_no_changes(tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    artifact_path = tmp_path / "artifacts"
    artifact_path.mkdir()
    job = Job(
        job_id="abc-123",
        prompt="fix it",
        issue_number=42,
        repo=VALID_REPO,
        artifact_path=artifact_path,
    )
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)
    git.has_changes = False
    work_item = make_work_item(job, gh=gh, git=git, command_runner=command_runner)

    pr_number = runner.run_job(work_item)

    assert pr_number is None
    assert not [c for c in git.calls if c[0] == "commit_changes"]
    assert "No changes staged" in (artifact_path / "output.txt").read_text()
