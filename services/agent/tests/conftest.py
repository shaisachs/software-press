import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config

VALID_REPO = "shaisachs/laws-of-software"

DEFAULT_ISSUE = {
    "number": 42,
    "title": "Fix the bug",
    "body": "the issue",
    "comments": [],
}


def make_repo_dir(tmp_path, repo=VALID_REPO):
    repo_dir = tmp_path / repo
    repo_dir.mkdir(parents=True, exist_ok=True)
    return repo_dir


def use_workspaces(monkeypatch, tmp_path, repo=VALID_REPO):
    monkeypatch.setattr(config, "WORKSPACES_ROOT", tmp_path)
    monkeypatch.setattr(config, "ARTIFACT_ROOT", tmp_path / "artifacts")
    return make_repo_dir(tmp_path, repo)


def make_result(mocker, returncode=0, stdout="", stderr=""):
    return mocker.Mock(returncode=returncode, stdout=stdout, stderr=stderr)


def make_queue(mocker, job_id="abc-123"):
    queue = mocker.Mock()
    queue.dequeue.return_value = job_id
    return queue


def make_db(mocker, job=None):
    db = mocker.Mock()
    db.fetch_job.return_value = job
    return db


def make_gh(mocker, pr_number=99, issue=None):
    gh = mocker.Mock()
    gh.fetch_issue.return_value = issue if issue is not None else DEFAULT_ISSUE
    gh.create_pull_request.return_value = pr_number
    return gh


def make_git(mocker, has_changes=True):
    git = mocker.Mock()
    git.create_branch.return_value = ("main", "feature/fix-the-bug")
    git.try_stage_changes.return_value = has_changes
    git.get_default_branch.return_value = "main"
    git.resolve_branch.side_effect = lambda requested: requested or "main"
    return git


def make_command_runner(mocker):
    return mocker.Mock()


@pytest.fixture
def recording_runner(mocker):
    runner = mocker.Mock()
    handlers = []

    def on(match, result):
        handlers.append((match, result))
        return runner

    def run(cmd, input=None):
        joined = " ".join(cmd)
        for match, result in handlers:
            if match in joined:
                return result
        return make_result(mocker)

    runner.on = on
    runner.run.side_effect = run
    return runner
