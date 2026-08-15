import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config
from app.command_runner import CommandRunner

VALID_REPO = "shaisachs/laws-of-software"


def make_repo_dir(tmp_path, repo=VALID_REPO):
    repo_dir = tmp_path / repo
    repo_dir.mkdir(parents=True, exist_ok=True)
    return repo_dir


def use_workspaces(monkeypatch, tmp_path, repo=VALID_REPO):
    monkeypatch.setattr(config, "WORKSPACES_ROOT", tmp_path)
    monkeypatch.setattr(config, "ARTIFACT_ROOT", tmp_path / "artifacts")
    return make_repo_dir(tmp_path, repo)


class FakeQueue:
    def __init__(self, job_id=None):
        self.job_id = job_id

    def dequeue(self):
        return self.job_id


class FakeDb:
    def __init__(self, job=None):
        self.job = job
        self.running = []
        self.completed = []
        self.fetched_ids = []

    def fetch_job(self, job_id):
        self.fetched_ids.append(job_id)
        return self.job

    def mark_running(self, job):
        self.running.append(job)

    def complete_job(self, job_id, status, error_desc, pr_number=None):
        self.completed.append((job_id, status, error_desc, pr_number))


class FakeGit:
    def __init__(self):
        self.calls = []
        self.has_changes = True

    def create_branch(self, branch):
        self.calls.append(("create_branch", branch))
        return ("main", branch)

    def try_stage_changes(self):
        self.calls.append(("try_stage_changes",))
        return self.has_changes

    def commit_changes(self):
        self.calls.append(("commit_changes",))

    def push_to_origin(self, branch):
        self.calls.append(("push_to_origin", branch))

    def checkout_branch(self, branch):
        self.calls.append(("checkout_branch", branch))


class FakeGithubClient:
    def __init__(self, pr_number=99, issue=None):
        self.pr_number = pr_number
        self.issue = issue if issue is not None else {
            "number": 42,
            "title": "Fix the bug",
            "body": "the issue",
            "comments": [],
        }
        self.calls = []

    def fetch_issue(self, issue_number):
        self.calls.append(("fetch_issue", issue_number))
        return self.issue

    def create_pull_request(self, branch, default_branch, title, issue_number):
        self.calls.append(("create_pull_request", branch, default_branch, title, issue_number))
        return self.pr_number


class FakeCommandRunner:
    def __init__(self, working_dir="/workspaces"):
        self.working_dir = working_dir
        self.output_file = None
        self.calls = []

    def run(self, cmd, input=None):
        self.calls.append((list(cmd), input))


def make_result(returncode=0, stdout="", stderr=""):
    class Result:
        pass

    result = Result()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


class RecordingCommandRunner(CommandRunner):
    def __init__(self, working_dir="/workspaces", output_file=None):
        super().__init__(working_dir, output_file)
        self.calls = []
        self._handlers = []

    def on(self, match, result):
        self._handlers.append((match, result))
        return self

    def run(self, cmd, input=None):
        self.calls.append((list(cmd), input))
        joined = " ".join(cmd)
        for match, result in self._handlers:
            if match in joined:
                return result
        return make_result()


@pytest.fixture
def recording_runner():
    return RecordingCommandRunner()
