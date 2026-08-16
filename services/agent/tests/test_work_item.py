import pytest

from app import config
from app.models import Job
from app.work_item import WorkItem

from tests.conftest import (
    VALID_REPO,
    make_command_runner,
    make_gh,
    make_git,
    use_workspaces,
)


def make_job(**overrides):
    defaults = dict(job_id="abc-123", prompt="write hello world", repo=VALID_REPO)
    defaults.update(overrides)
    return Job(**defaults)


def make_work_item(mocker, job, gh=None, git=None, command_runner=None):
    return WorkItem(
        job=job,
        gh=gh if gh is not None else make_gh(mocker),
        git=git if git is not None else make_git(mocker),
        command_runner=command_runner if command_runner is not None else make_command_runner(mocker),
    )


def test_build_prompt():
    prompt = WorkItem._build_prompt(42, "the body")
    assert "# GitHub Issue #42" in prompt
    assert "the body" in prompt


def test_format_issue_text():
    issue = {
        "number": 42,
        "title": "Refactor things",
        "body": "Please refactor.",
        "comments": [{"body": "First comment"}, {"body": "Second comment"}],
    }

    text = WorkItem._format_issue_text(issue)

    assert "Title: Refactor things" in text
    assert "Body: Please refactor." in text
    assert "Comments" in text
    assert "First comment" in text
    assert "Second comment" in text


def test_format_issue_text_without_comments():
    issue = {"number": 42, "title": "Refactor things", "body": "Please refactor.", "comments": []}

    text = WorkItem._format_issue_text(issue)

    assert "Title: Refactor things" in text
    assert "Body: Please refactor." in text
    assert "Comments" not in text


def test_branch_name_for_issue():
    assert WorkItem.branch_name_for_issue("Add the Bitter Lesson") == "feature/add-the-bitter-lesson"
    assert WorkItem.branch_name_for_issue("  Fix  This   Bug  ") == "feature/fix-this-bug"
    assert WorkItem.branch_name_for_issue("Needs: Proper Casing!") == "feature/needs-proper-casing"


def test_make_artifact_path(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ARTIFACT_ROOT", tmp_path / "artifacts")

    path = WorkItem._make_artifact_path("abc-123")

    assert str(path).startswith(str(tmp_path))
    assert str(path).endswith("abc-123")


def test_workspace_dir(tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)

    assert WorkItem._workspace_dir(VALID_REPO) == tmp_path / VALID_REPO


def test_model_defaults_to_opencode_model(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job(model=None)

    work_item = make_work_item(mocker, job)

    assert work_item.model == config.opencode_model()


def test_model_uses_job_model(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "model_is_available", lambda model: True)
    job = make_job(model="deepseek/deepseek-v4-pro")

    work_item = make_work_item(mocker, job)

    assert work_item.model == "deepseek/deepseek-v4-pro"


def test_init_sets_artifact_path_and_creates_dir(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job()

    work_item = make_work_item(mocker, job)

    assert work_item.job is job
    assert job.artifact_path is not None
    assert job.artifact_path.is_dir()


def test_init_reuses_existing_artifact_path(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    artifact_path = tmp_path / "artifacts"
    artifact_path.mkdir()
    job = make_job(artifact_path=artifact_path)

    work_item = make_work_item(mocker, job)

    assert job.artifact_path == artifact_path
    assert work_item.job is job


def test_init_sets_command_runner_working_dir(mocker, tmp_path, monkeypatch):
    repo_dir = use_workspaces(monkeypatch, tmp_path)
    command_runner = make_command_runner(mocker)
    job = make_job()

    work_item = make_work_item(mocker, job, command_runner=command_runner)

    assert work_item.command_runner is command_runner
    assert command_runner.working_dir == str(repo_dir)


def test_init_injects_gh_and_git(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    gh = make_gh(mocker)
    git = make_git(mocker)
    job = make_job()

    work_item = make_work_item(mocker, job, gh=gh, git=git)

    assert work_item.gh is gh
    assert work_item.git is git


def test_init_constructs_default_dependencies(tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job()

    work_item = WorkItem(job=job)

    assert work_item.command_runner is not None
    assert work_item.gh is not None
    assert work_item.git is not None
    assert work_item.command_runner.working_dir == str(tmp_path / VALID_REPO)


def test_init_fetches_issue_when_prompt_missing(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    gh = make_gh(mocker)
    job = make_job(prompt=None, issue_number=42)

    work_item = make_work_item(mocker, job, gh=gh)

    assert work_item.gh is gh
    gh.fetch_issue.assert_called_once_with(42)
    assert "# GitHub Issue #42" in job.prompt
    assert "Title: Fix the bug" in job.prompt
    assert "the issue" in job.prompt


def test_init_does_not_fetch_issue_when_prompt_present(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    gh = make_gh(mocker)
    job = make_job(prompt="already set", issue_number=42)

    work_item = make_work_item(mocker, job, gh=gh)

    gh.fetch_issue.assert_not_called()
    assert job.prompt == "already set"


def test_init_raises_when_repo_missing(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job(repo=None)

    with pytest.raises(Exception, match="repo is required"):
        make_work_item(mocker, job)


def test_init_raises_when_repo_not_on_disk(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job(repo="owner/not-cloned")

    with pytest.raises(Exception, match="not found on disk"):
        make_work_item(mocker, job)


def test_init_raises_when_model_unavailable(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "model_is_available", lambda model: False)
    job = make_job(model="deepseek/not-a-model")

    with pytest.raises(Exception, match="model is unavailable: deepseek/not-a-model"):
        make_work_item(mocker, job)


def test_init_accepts_available_model(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "model_is_available", lambda model: True)
    job = make_job(model="deepseek/deepseek-v4-pro")

    work_item = make_work_item(mocker, job)

    assert work_item.model == "deepseek/deepseek-v4-pro"
