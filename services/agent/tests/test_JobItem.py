import pytest
from unittest import mock

from app import config
from app.models import Job
from app.JobItem import JobItem
from app.JobStrategy import AdHocPromptStrategy, IssueArchitectStrategy, IssueResolveStrategy

from tests.conftest import (
    VALID_REPO,
    make_command_runner,
    make_db,
    make_gh,
    make_git,
    make_result,
    use_workspaces,
)


def make_job(**overrides):
    defaults = dict(job_id="abc-123", prompt="write hello world", repo=VALID_REPO, type="adHoc")
    defaults.update(overrides)
    return Job(**defaults)


def make_job_item(mocker, job, gh=None, git=None, command_runner=None, db=None):
    return JobItem(
        job=job,
        gh=gh if gh is not None else make_gh(mocker),
        git=git if git is not None else make_git(mocker),
        command_runner=command_runner if command_runner is not None else make_command_runner(mocker),
        db=db if db is not None else make_db(mocker),
    )


def test_workspace_dir(tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)

    assert JobItem._workspace_dir(VALID_REPO) == tmp_path / VALID_REPO


def test_model_defaults_to_opencode_model(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job(model=None)

    job_item = make_job_item(mocker, job)

    assert job_item.model == config.opencode_model()


def test_model_uses_job_model(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "model_is_available", lambda model: True)
    job = make_job(model="deepseek/deepseek-v4-pro")

    job_item = make_job_item(mocker, job)

    assert job_item.model == "deepseek/deepseek-v4-pro"


def test_init_does_not_create_artifact_dir(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job()

    job_item = make_job_item(mocker, job)

    assert job_item.job is job
    assert job.artifact_path is None


def test_init_reuses_existing_artifact_path(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    artifact_path = tmp_path / "artifacts"
    artifact_path.mkdir()
    job = make_job(artifact_path=artifact_path)

    job_item = make_job_item(mocker, job)

    assert job.artifact_path == artifact_path
    assert job_item.job is job


def test_init_sets_command_runner_working_dir(mocker, tmp_path, monkeypatch):
    repo_dir = use_workspaces(monkeypatch, tmp_path)
    command_runner = make_command_runner(mocker)
    job = make_job()

    job_item = make_job_item(mocker, job, command_runner=command_runner)

    assert job_item.command_runner is command_runner
    assert command_runner.working_dir == str(repo_dir)


def test_init_injects_dependencies(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    gh = make_gh(mocker)
    git = make_git(mocker)
    db = make_db(mocker)
    job = make_job()

    job_item = make_job_item(mocker, job, gh=gh, git=git, db=db)

    assert job_item.gh is gh
    assert job_item.git is git
    assert job_item.db is db


def test_init_constructs_default_dependencies(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job()

    job_item = JobItem(job=job, db=mocker.Mock())

    assert job_item.command_runner is not None
    assert job_item.gh is not None
    assert job_item.git is not None
    assert job_item.db is not None
    assert job_item.command_runner.working_dir == str(tmp_path / VALID_REPO)


def test_init_does_not_fetch_issue_when_prompt_present(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    gh = make_gh(mocker)
    job = make_job(prompt="already set", issue_number=None)

    job_item = make_job_item(mocker, job, gh=gh)

    gh.fetch_issue.assert_not_called()
    assert job.prompt == "already set"


def test_init_raises_when_repo_missing(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job(repo=None)

    with pytest.raises(Exception, match="repo is required"):
        make_job_item(mocker, job)


def test_init_raises_when_repo_not_on_disk(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job(repo="owner/not-cloned")

    with pytest.raises(Exception, match="not found on disk"):
        make_job_item(mocker, job)


def test_init_raises_when_model_unavailable(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "model_is_available", lambda model: False)
    job = make_job(model="deepseek/not-a-model")

    with pytest.raises(Exception, match="model is unavailable: deepseek/not-a-model"):
        make_job_item(mocker, job)


def test_init_accepts_available_model(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "model_is_available", lambda model: True)
    job = make_job(model="deepseek/deepseek-v4-pro")

    job_item = make_job_item(mocker, job)

    assert job_item.model == "deepseek/deepseek-v4-pro"


def test_init_selects_adhoc_prompt_strategy_when_type_adhoc(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job(prompt="write hello world", issue_number=None, type="adHoc")

    job_item = make_job_item(mocker, job)

    assert isinstance(job_item.strategy, AdHocPromptStrategy)


def test_init_selects_issue_resolve_strategy_when_type_issue_resolver(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job(prompt=None, issue_number=42, type="issueResolver")

    job_item = make_job_item(mocker, job)

    assert isinstance(job_item.strategy, IssueResolveStrategy)


def test_init_selects_issue_architect_strategy_when_type_issue_architect(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job(prompt=None, issue_number=42, type="issueArchitect")

    job_item = make_job_item(mocker, job)

    assert isinstance(job_item.strategy, IssueArchitectStrategy)


def test_init_raises_when_unknown_type(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job(type="bogus")

    with pytest.raises(Exception, match="unknown job type: bogus"):
        make_job_item(mocker, job)


def test_init_raises_when_type_missing(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job(type=None)

    with pytest.raises(Exception, match="unknown job type: None"):
        make_job_item(mocker, job)


def test_run_prompt_invokes_opencode(mocker, tmp_path, monkeypatch):
    repo_dir = use_workspaces(monkeypatch, tmp_path)
    command_runner = make_command_runner(mocker)
    job_item = make_job_item(mocker, make_job(), command_runner=command_runner)

    job_item.run_prompt("write hello world")

    assert command_runner.run.call_count == 1
    args = command_runner.run.call_args.args[0]
    assert args[0] == "opencode"
    assert args[1] == "--dir"
    assert args[2] == str(repo_dir)
    assert args[3] == "--model"
    assert args[4] == config.opencode_model()
    assert args[5] == "run"
    assert args[6] == "--agent"
    assert args[7] == "build"
    assert args[8] == "write hello world"


def test_run_with_issue_number_creates_pr_and_records_it(mocker, tmp_path, monkeypatch):
    repo_dir = use_workspaces(monkeypatch, tmp_path)
    artifact_path = tmp_path / "artifacts"
    artifact_path.mkdir()
    job = make_job(prompt=None, issue_number=42, artifact_path=artifact_path, type="issueResolver")
    gh = make_gh(mocker)
    git = make_git(mocker)
    db = make_db(mocker)
    command_runner = make_command_runner(mocker)
    job_item = make_job_item(mocker, job, gh=gh, git=git, command_runner=command_runner, db=db)

    job_item.run()

    gh.fetch_issue.assert_called_once_with(42)
    git.create_branch.assert_called_once_with("feature/fix-the-bug", "main")
    git.push_to_origin.assert_called_once_with("feature/fix-the-bug")
    gh.create_pull_request.assert_called_once_with("feature/fix-the-bug", "main", "Fix the bug", 42)
    git.checkout_branch.assert_called_once_with("main")
    db.record_pr_number.assert_called_once_with("abc-123", 99)
    opencode_calls = [c.args[0] for c in command_runner.run.call_args_list if c.args[0][0] == "opencode"]
    assert len(opencode_calls) == 1
    assert opencode_calls[0][2] == str(repo_dir)
    assert opencode_calls[0][4] == config.opencode_model()
    assert not (artifact_path / "prompt.txt").exists()
    assert not (artifact_path / "output.txt").exists()


def test_run_with_branch_checks_out_requested_branch(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job(prompt="fix it", issue_number=None, branch="develop")
    gh = make_gh(mocker)
    git = make_git(mocker)
    db = make_db(mocker)
    job_item = make_job_item(mocker, job, gh=gh, git=git, db=db)

    job_item.run()

    git.resolve_branch.assert_has_calls([mock.call("develop"), mock.call("develop")])
    git.checkout_branch.assert_has_calls([mock.call("develop"), mock.call("develop")])


def test_run_with_issue_number_and_branch_bases_pr_on_requested_branch(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    artifact_path = tmp_path / "artifacts"
    artifact_path.mkdir()
    job = make_job(
        prompt=None, issue_number=42, artifact_path=artifact_path, type="issueResolver", branch="develop"
    )
    gh = make_gh(mocker)
    git = make_git(mocker)
    git.create_branch.side_effect = lambda branch, base: (base, branch)
    db = make_db(mocker)
    command_runner = make_command_runner(mocker)
    job_item = make_job_item(mocker, job, gh=gh, git=git, command_runner=command_runner, db=db)

    job_item.run()

    gh.fetch_issue.assert_called_once_with(42)
    git.create_branch.assert_called_once_with("feature/fix-the-bug", "develop")
    git.push_to_origin.assert_called_once_with("feature/fix-the-bug")
    gh.create_pull_request.assert_called_once_with("feature/fix-the-bug", "develop", "Fix the bug", 42)
    git.checkout_branch.assert_called_once_with("develop")
    db.record_pr_number.assert_called_once_with("abc-123", 99)


def test_run_without_issue_number_commits_locally(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job(prompt="fix it", issue_number=None)
    gh = make_gh(mocker)
    git = make_git(mocker)
    db = make_db(mocker)
    job_item = make_job_item(mocker, job, gh=gh, git=git, db=db)

    job_item.run()

    gh.fetch_issue.assert_not_called()
    git.create_branch.assert_not_called()
    git.push_to_origin.assert_not_called()
    gh.create_pull_request.assert_not_called()
    git.commit_changes.assert_called_once_with()
    git.checkout_branch.assert_has_calls([mock.call("main"), mock.call("main")])
    db.record_pr_number.assert_not_called()


def test_run_skips_commit_and_pr_when_no_changes(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job(prompt=None, issue_number=42, type="issueResolver")
    gh = make_gh(mocker)
    git = make_git(mocker)
    git.try_stage_changes.return_value = False
    db = make_db(mocker)
    job_item = make_job_item(mocker, job, gh=gh, git=git, db=db)

    job_item.run()

    git.commit_changes.assert_not_called()
    gh.create_pull_request.assert_not_called()
    db.record_pr_number.assert_not_called()


def test_run_uses_selected_model(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "model_is_available", lambda model: True)
    job = make_job(prompt="fix it", model="deepseek/deepseek-v4-pro")
    command_runner = make_command_runner(mocker)
    job_item = make_job_item(mocker, job, command_runner=command_runner)

    job_item.run()

    opencode_calls = [c.args[0] for c in command_runner.run.call_args_list if c.args[0][0] == "opencode"]
    assert len(opencode_calls) == 1
    assert opencode_calls[0][4] == "deepseek/deepseek-v4-pro"


def test_run_with_issue_architect_posts_comment_and_commits_nothing(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job(prompt=None, issue_number=42, type="issueArchitect")
    gh = make_gh(mocker)
    git = make_git(mocker)
    db = make_db(mocker)
    command_runner = make_command_runner(mocker)
    command_runner.run.return_value = make_result(mocker, stdout="Proposed approach: use a state machine.")
    job_item = make_job_item(mocker, job, gh=gh, git=git, command_runner=command_runner, db=db)

    job_item.run()

    gh.fetch_issue.assert_called_once_with(42)
    gh.create_issue_comment.assert_called_once_with(42, "Proposed approach: use a state machine.")
    git.try_stage_changes.assert_not_called()
    git.commit_changes.assert_not_called()
    git.create_branch.assert_not_called()
    git.push_to_origin.assert_not_called()
    gh.create_pull_request.assert_not_called()
    db.record_pr_number.assert_not_called()


def test_run_with_issue_architect_skips_comment_when_no_output(mocker, tmp_path, monkeypatch):
    use_workspaces(monkeypatch, tmp_path)
    job = make_job(prompt=None, issue_number=42, type="issueArchitect")
    gh = make_gh(mocker)
    git = make_git(mocker)
    command_runner = make_command_runner(mocker)
    command_runner.run.return_value = make_result(mocker, stdout="")
    job_item = make_job_item(mocker, job, gh=gh, git=git, command_runner=command_runner)

    job_item.run()

    gh.fetch_issue.assert_called_once_with(42)
    gh.create_issue_comment.assert_not_called()
    git.try_stage_changes.assert_not_called()
    git.commit_changes.assert_not_called()
