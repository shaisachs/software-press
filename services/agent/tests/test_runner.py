from unittest import mock

from app import config
from app.models import Job
from app.runner import JobRunner
from app.work_item import WorkItem

from tests.conftest import (
    VALID_REPO,
    make_command_runner,
    make_db,
    make_gh,
    make_git,
    make_queue,
    use_workspaces,
)


def make_work_item(mocker, job, gh=None, git=None, command_runner=None):
    return WorkItem(
        job=job,
        gh=gh if gh is not None else make_gh(mocker),
        git=git if git is not None else make_git(mocker),
        command_runner=command_runner if command_runner is not None else make_command_runner(mocker),
    )


def make_runner(mocker, tmp_path, job=None, queue_job_id="abc-123"):
    queue = make_queue(mocker, queue_job_id)
    db = make_db(mocker, job)
    gh = make_gh(mocker)
    git = make_git(mocker)
    command_runner = make_command_runner(mocker)

    def factory(job):
        return WorkItem(job=job, gh=gh, git=git, command_runner=command_runner)

    runner = JobRunner(queue=queue, db=db, work_item_factory=factory)
    return runner, db, gh, git, command_runner


def test_dequeue_job_returns_none_when_queue_empty(mocker, tmp_path):
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path, queue_job_id=None)
    assert runner.dequeue_job() is None
    db.fetch_job.assert_not_called()


def test_dequeue_job_returns_none_while_busy(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt="write hello world", repo=VALID_REPO)
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path, job=job)

    first = runner.dequeue_job()

    assert first is not None
    assert first.job is job
    assert runner.busy
    db.fetch_job.assert_called_once_with("abc-123")

    second = runner.dequeue_job()
    assert second is None
    assert runner.busy
    db.fetch_job.assert_called_once_with("abc-123")


def test_complete_job_clears_busy(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt="write hello world", repo=VALID_REPO)
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path, job=job)

    assert runner.dequeue_job() is not None
    assert runner.busy

    runner.complete_job("abc-123", "completed", None, pr_number=99)

    assert not runner.busy
    assert runner.dequeue_job() is not None
    db.fetch_job.assert_has_calls([mock.call("abc-123"), mock.call("abc-123")])


def test_dequeue_job_uses_stored_prompt(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt="write hello world", repo=VALID_REPO)
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path, job=job)

    work_item = runner.dequeue_job()

    assert work_item.job is job
    assert job.prompt == "write hello world"
    gh.fetch_issue.assert_not_called()
    db.mark_running.assert_called_once_with(job)
    assert job.artifact_path is not None
    assert job.artifact_path.is_dir()


def test_dequeue_job_fetches_issue_text_when_prompt_missing(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt=None, issue_number=42, repo=VALID_REPO)
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path, job=job)

    work_item = runner.dequeue_job()

    assert work_item.job is job
    gh.fetch_issue.assert_called_once_with(42)
    assert "# GitHub Issue #42" in job.prompt
    assert "Title: Fix the bug" in job.prompt
    assert "the issue" in job.prompt
    db.mark_running.assert_called_once_with(job)


def test_dequeue_job_marks_failed_on_error(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt=None, issue_number=42, repo=VALID_REPO)
    queue = make_queue(mocker, "abc-123")
    db = make_db(mocker, job)
    gh = mocker.Mock()
    gh.fetch_issue.side_effect = Exception("gh is down")

    def factory(job):
        return WorkItem(
            job=job,
            gh=gh,
            git=make_git(mocker),
            command_runner=make_command_runner(mocker),
        )

    runner = JobRunner(queue=queue, db=db, work_item_factory=factory)

    assert runner.dequeue_job() is None
    assert not runner.busy
    db.complete_job.assert_called_once_with("abc-123", "failed", "gh is down", None)


def test_dequeue_job_marks_failed_when_repo_missing_on_disk(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt="write hello world", repo="owner/not-cloned")
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path, job=job)

    assert runner.dequeue_job() is None
    db.mark_running.assert_not_called()
    db.complete_job.assert_called_once()
    args = db.complete_job.call_args.args
    assert args[0] == "abc-123"
    assert args[1] == "failed"
    assert "not found on disk" in args[2]


def test_dequeue_job_marks_failed_when_repo_missing(mocker, tmp_path, monkeypatch):
    job = Job(job_id="abc-123", prompt="write hello world", repo=None)
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path, job=job)

    assert runner.dequeue_job() is None
    db.mark_running.assert_not_called()
    db.complete_job.assert_called_once_with("abc-123", "failed", "repo is required", None)


def test_dequeue_job_marks_failed_when_model_unavailable(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt="write hello world", repo=VALID_REPO, model="deepseek/not-a-model")
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path, job=job)

    monkeypatch.setattr(config, "model_is_available", lambda model: False)

    assert runner.dequeue_job() is None
    db.mark_running.assert_not_called()
    db.complete_job.assert_called_once_with("abc-123", "failed", "model is unavailable: deepseek/not-a-model", None)


def test_dequeue_job_accepts_available_model(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt="write hello world", repo=VALID_REPO, model="deepseek/deepseek-v4-pro")
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path, job=job)

    monkeypatch.setattr(config, "model_is_available", lambda model: True)

    work_item = runner.dequeue_job()

    assert work_item.job is job
    db.mark_running.assert_called_once_with(job)


def test_complete_job_delegates_to_db(mocker, tmp_path):
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path)

    runner.complete_job("abc-123", "completed", None, pr_number=99)

    db.complete_job.assert_called_once_with("abc-123", "completed", None, 99)
    assert not runner.busy


def test_run_job_with_issue_number(mocker, tmp_path, monkeypatch):
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
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path, job=job)
    work_item = make_work_item(mocker, job, gh=gh, git=git, command_runner=command_runner)

    pr_number = runner.run_job(work_item)

    assert pr_number == 99
    assert command_runner.working_dir == str(repo_dir)
    assert (artifact_path / "prompt.txt").read_text() == "fix it"
    assert (artifact_path / "output.txt").exists()
    git.create_branch.assert_called_once_with("feature/fix-the-bug")
    git.push_to_origin.assert_called_once_with("feature/fix-the-bug")
    gh.create_pull_request.assert_called_once_with("feature/fix-the-bug", "main", "Fix the bug", 42)
    gh.fetch_issue.assert_called_once_with(42)
    opencode_calls = [c.args[0] for c in command_runner.run.call_args_list if c.args[0][0] == "opencode"]
    assert len(opencode_calls) == 1
    assert opencode_calls[0][2] == str(repo_dir)
    assert opencode_calls[0][4] == config.opencode_model()


def test_run_job_uses_selected_model(mocker, tmp_path, monkeypatch):
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
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path, job=job)
    work_item = make_work_item(mocker, job, gh=gh, git=git, command_runner=command_runner)

    pr_number = runner.run_job(work_item)

    assert pr_number is None
    opencode_calls = [c.args[0] for c in command_runner.run.call_args_list if c.args[0][0] == "opencode"]
    assert len(opencode_calls) == 1
    assert opencode_calls[0][4] == "deepseek/deepseek-v4-pro"


def test_run_job_without_issue_number(mocker, tmp_path, monkeypatch):
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
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path, job=job)
    work_item = make_work_item(mocker, job, gh=gh, git=git, command_runner=command_runner)

    pr_number = runner.run_job(work_item)

    assert pr_number is None
    git.create_branch.assert_not_called()
    git.push_to_origin.assert_not_called()
    gh.create_pull_request.assert_not_called()
    git.commit_changes.assert_called_once_with()


def test_run_job_skips_commit_and_pr_when_no_changes(mocker, tmp_path, monkeypatch):
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
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path, job=job)
    git.try_stage_changes.return_value = False
    work_item = make_work_item(mocker, job, gh=gh, git=git, command_runner=command_runner)

    pr_number = runner.run_job(work_item)

    assert pr_number is None
    git.commit_changes.assert_not_called()
    assert "No changes staged" in (artifact_path / "output.txt").read_text()
