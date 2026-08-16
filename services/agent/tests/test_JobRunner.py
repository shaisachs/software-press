from unittest import mock

from app import config
from app.models import Job
from app.JobRunner import JobRunner
from app.JobItem import JobItem
from app.JobStrategy import IssueResolveStrategy

from tests.conftest import (
    VALID_REPO,
    make_command_runner,
    make_db,
    make_gh,
    make_git,
    make_queue,
    use_workspaces,
)


def make_job_item(mocker, job, gh=None, git=None, command_runner=None, db=None):
    return JobItem(
        job=job,
        gh=gh if gh is not None else make_gh(mocker),
        git=git if git is not None else make_git(mocker),
        command_runner=command_runner if command_runner is not None else make_command_runner(mocker),
        db=db if db is not None else make_db(mocker),
    )


def make_runner(mocker, tmp_path, job=None, queue_job_id="abc-123"):
    queue = make_queue(mocker, queue_job_id)
    db = make_db(mocker, job)
    gh = make_gh(mocker)
    git = make_git(mocker)
    command_runner = make_command_runner(mocker)

    def factory(job, db=None):
        return JobItem(job=job, gh=gh, git=git, command_runner=command_runner, db=db)

    runner = JobRunner(queue=queue, db=db, job_item_factory=factory)
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

    runner.complete_job("abc-123", "completed", None)

    assert not runner.busy
    assert runner.dequeue_job() is not None
    db.fetch_job.assert_has_calls([mock.call("abc-123"), mock.call("abc-123")])


def test_dequeue_job_uses_stored_prompt(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt="write hello world", repo=VALID_REPO)
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path, job=job)

    job_item = runner.dequeue_job()

    assert job_item.job is job
    assert job.prompt == "write hello world"
    gh.fetch_issue.assert_not_called()
    db.mark_running.assert_called_once_with(job)


def test_dequeue_job_defers_issue_resolution_to_strategy(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt=None, issue_number=42, repo=VALID_REPO)
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path, job=job)

    job_item = runner.dequeue_job()

    assert job_item.job is job
    assert isinstance(job_item.strategy, IssueResolveStrategy)
    gh.fetch_issue.assert_not_called()
    assert job.prompt is None
    db.mark_running.assert_called_once_with(job)


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
    db.complete_job.assert_called_once_with("abc-123", "failed", "Error dequeueing job! repo is required")


def test_dequeue_job_marks_failed_when_model_unavailable(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt="write hello world", repo=VALID_REPO, model="deepseek/not-a-model")
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path, job=job)

    monkeypatch.setattr(config, "model_is_available", lambda model: False)

    assert runner.dequeue_job() is None
    db.mark_running.assert_not_called()
    db.complete_job.assert_called_once_with("abc-123", "failed", "Error dequeueing job! model is unavailable: deepseek/not-a-model")


def test_dequeue_job_accepts_available_model(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt="write hello world", repo=VALID_REPO, model="deepseek/deepseek-v4-pro")
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path, job=job)

    monkeypatch.setattr(config, "model_is_available", lambda model: True)

    job_item = runner.dequeue_job()

    assert job_item.job is job
    db.mark_running.assert_called_once_with(job)


def test_complete_job_delegates_to_db(mocker, tmp_path):
    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path)

    runner.complete_job("abc-123", "completed", None)

    db.complete_job.assert_called_once_with("abc-123", "completed", None)
    assert not runner.busy


def test_run_job_delegates_to_job_item(mocker, tmp_path):
    artifact_path = tmp_path / "artifacts"
    artifact_path.mkdir()
    job_item = mocker.Mock()
    job_item.job = Job(
        job_id="abc-123", prompt="write hello world", repo=VALID_REPO, artifact_path=artifact_path
    )
    job_item.command_runner = mocker.Mock()

    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path)

    result = runner.run_job(job_item)

    job_item.run.assert_called_once_with()
    assert result is None


def test_run_job_writes_prompt_and_output_artifacts(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt="write hello world", repo=VALID_REPO)
    command_runner = make_command_runner(mocker)
    job_item = make_job_item(mocker, job, command_runner=command_runner)

    runner, db, gh, git, _ = make_runner(mocker, tmp_path, job=job)
    runner.run_job(job_item)

    artifact_path = next((tmp_path / "artifacts").glob("*-abc-123"))
    assert (artifact_path / "prompt.txt").read_text() == "write hello world"
    assert (artifact_path / "output.txt").exists()


def test_run_job_emits_command_output_to_output_file(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    artifact_path = tmp_path / "artifacts"
    artifact_path.mkdir()
    job = Job(
        job_id="abc-123", prompt="write hello world", repo=VALID_REPO, artifact_path=artifact_path
    )
    command_runner = make_command_runner(mocker)
    seen_output_files = []
    command_runner.run.side_effect = lambda cmd, input=None: seen_output_files.append(
        command_runner.output_file
    )
    job_item = make_job_item(mocker, job, command_runner=command_runner)

    runner, db, gh, git, _ = make_runner(mocker, tmp_path, job=job)
    runner.run_job(job_item)

    assert seen_output_files
    assert all(output_file is not None for output_file in seen_output_files)
    assert job_item.command_runner.output_file is None


def test_run_job_writes_no_changes_message(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt="write hello world", repo=VALID_REPO)
    git = make_git(mocker)
    git.try_stage_changes.return_value = False
    job_item = make_job_item(mocker, job, git=git)

    runner, db, gh, _, _ = make_runner(mocker, tmp_path, job=job)
    runner.run_job(job_item)

    artifact_path = next((tmp_path / "artifacts").glob("*-abc-123"))
    assert "No changes staged" in (artifact_path / "output.txt").read_text()


def test_run_job_skips_no_changes_message_when_changes_staged(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = Job(job_id="abc-123", prompt="write hello world", repo=VALID_REPO)
    job_item = make_job_item(mocker, job)

    runner, db, gh, git, _ = make_runner(mocker, tmp_path, job=job)
    runner.run_job(job_item)

    artifact_path = next((tmp_path / "artifacts").glob("*-abc-123"))
    assert "No changes staged" not in (artifact_path / "output.txt").read_text()


def test_run_job_returns_none_when_job_item_raises(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    artifact_path = tmp_path / "artifacts"
    artifact_path.mkdir()
    job = Job(
        job_id="abc-123", prompt="write hello world", repo=VALID_REPO, artifact_path=artifact_path
    )
    job_item = mocker.Mock()
    job_item.job = job
    job_item.command_runner = mocker.Mock()
    job_item.run.side_effect = Exception("boom")

    runner, db, gh, git, command_runner = make_runner(mocker, tmp_path, job=job)

    result = runner.run_job(job_item)

    assert result is None
    db.complete_job.assert_called_once_with("abc-123", "failed", "Error running job! boom")

def test_make_artifact_path(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ARTIFACT_ROOT", tmp_path / "artifacts")

    path = JobRunner._make_artifact_path("abc-123")

    assert str(path).startswith(str(tmp_path))
    assert str(path).endswith("abc-123")
