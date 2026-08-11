from pathlib import Path

from app.models import Job
from app.runner import Runner, build_prompt, make_artifact_path


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

    def create_branch(self, issue_number, output_file):
        self.calls.append(("create_branch", issue_number))
        return ("main", "feature/issue-42")

    def try_stage_changes(self, output_file):
        self.calls.append(("try_stage_changes",))
        return self.has_changes

    def commit_changes(self, output_file):
        self.calls.append(("commit_changes",))

    def push_to_origin(self, branch, output_file):
        self.calls.append(("push_to_origin", branch))


class FakeGh:
    def __init__(self, pr_number=99, issue_text="the issue"):
        self.pr_number = pr_number
        self.issue_text = issue_text
        self.calls = []

    def ensure_gh_auth(self):
        self.calls.append(("ensure_gh_auth",))

    def fetch_issue_text(self, issue_number):
        self.calls.append(("fetch_issue_text", issue_number))
        return self.issue_text

    def create_pull_request(self, branch, default_branch, issue_number, output_file):
        self.calls.append(("create_pull_request", branch, default_branch, issue_number))
        return self.pr_number


class FakeCommandRunner:
    def __init__(self, working_dir="/workspaces"):
        self.working_dir = working_dir
        self.calls = []

    def run(self, cmd, output_file=None, input=None):
        self.calls.append((list(cmd), output_file))


def make_runner(tmp_path, job=None, queue_job_id="abc-123"):
    queue = FakeQueue(queue_job_id)
    db = FakeDb(job)
    gh = FakeGh()
    git = FakeGit()
    command_runner = FakeCommandRunner()
    runner = Runner(
        queue=queue,
        db=db,
        gh=gh,
        git=git,
        command_runner=command_runner,
    )
    return runner, db, gh, git, command_runner


def test_build_prompt():
    prompt = build_prompt(42, "the body")
    assert "# GitHub Issue #42" in prompt
    assert "the body" in prompt


def test_make_artifact_path():
    path = make_artifact_path("abc-123")
    assert str(path).endswith("abc-123")
    assert "/" in str(path)


def test_dequeue_job_returns_none_when_queue_empty(tmp_path):
    runner, db, gh, git, command_runner = make_runner(tmp_path, queue_job_id=None)
    assert runner.dequeue_job() is None
    assert db.fetched_ids == []


def test_dequeue_job_uses_stored_prompt(tmp_path):
    job = Job(job_id="abc-123", prompt="write hello world")
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)

    result = runner.dequeue_job()

    assert result is job
    assert job.prompt == "write hello world"
    assert gh.calls == []
    assert db.running == [job]
    assert job.artifact_path is not None


def test_dequeue_job_fetches_issue_text_when_prompt_missing(tmp_path):
    job = Job(job_id="abc-123", prompt=None, issue_number=42)
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)

    result = runner.dequeue_job()

    assert result is job
    assert gh.calls == [("ensure_gh_auth",), ("fetch_issue_text", 42)]
    assert "# GitHub Issue #42" in job.prompt
    assert db.running == [job]


def test_dequeue_job_marks_failed_on_error(tmp_path):
    job = Job(job_id="abc-123", prompt=None, issue_number=42)
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)
    gh.issue_text = None

    class Boom(FakeGh):
        def fetch_issue_text(self, issue_number):
            raise Exception("gh is down")

    runner.gh = Boom()

    assert runner.dequeue_job() is None
    assert db.completed == [("abc-123", "failed", "gh is down", None)]


def test_complete_job_delegates_to_db(tmp_path):
    runner, db, gh, git, command_runner = make_runner(tmp_path)

    runner.complete_job("abc-123", "completed", None, pr_number=99)

    assert db.completed == [("abc-123", "completed", None, 99)]


def test_run_job_with_issue_number(tmp_path):
    artifact_path = tmp_path / "artifacts"
    artifact_path.mkdir()
    job = Job(
        job_id="abc-123",
        prompt="fix it",
        issue_number=42,
        artifact_path=artifact_path,
    )
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)

    pr_number = runner.run_job(job)

    assert pr_number == 99
    assert (artifact_path / "prompt.txt").read_text() == "fix it"
    assert (artifact_path / "output.txt").exists()
    assert gh.calls[0] == ("ensure_gh_auth",)
    assert ("create_branch", 42) in git.calls
    assert ("push_to_origin", "feature/issue-42") in git.calls
    assert ("create_pull_request", "feature/issue-42", "main", 42) in gh.calls
    assert any(c[0][0] == "opencode" for c in command_runner.calls)


def test_run_job_without_issue_number(tmp_path):
    artifact_path = tmp_path / "artifacts"
    artifact_path.mkdir()
    job = Job(
        job_id="abc-123",
        prompt="fix it",
        issue_number=None,
        artifact_path=artifact_path,
    )
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)

    pr_number = runner.run_job(job)

    assert pr_number is None
    assert not [c for c in git.calls if c[0] == "create_branch"]
    assert not [c for c in git.calls if c[0] == "push_to_origin"]
    assert not [c for c in gh.calls if c[0] == "create_pull_request"]
    assert ("commit_changes",) in git.calls


def test_run_job_skips_commit_and_pr_when_no_changes(tmp_path):
    artifact_path = tmp_path / "artifacts"
    artifact_path.mkdir()
    job = Job(
        job_id="abc-123",
        prompt="fix it",
        issue_number=42,
        artifact_path=artifact_path,
    )
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)
    git.has_changes = False

    pr_number = runner.run_job(job)

    assert pr_number is None
    assert not [c for c in git.calls if c[0] == "commit_changes"]
    assert "No changes staged" in (artifact_path / "output.txt").read_text()
