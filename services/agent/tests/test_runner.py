from pathlib import Path

from app.models import Job
from app.runner import Runner


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


class FakeGh:
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

    def create_pull_request(self, branch, default_branch, issue_number):
        self.calls.append(("create_pull_request", branch, default_branch, issue_number))
        return self.pr_number


class FakeCommandRunner:
    def __init__(self, working_dir="/workspaces"):
        self.working_dir = working_dir
        self.output_file = None
        self.calls = []

    def run(self, cmd, input=None):
        self.calls.append((list(cmd), input))


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


def test_build_prompt(tmp_path):
    runner, db, gh, git, command_runner = make_runner(tmp_path)
    prompt = runner._build_prompt(42, "the body")
    assert "# GitHub Issue #42" in prompt
    assert "the body" in prompt


def test_format_issue_text(tmp_path):
    runner, db, gh, git, command_runner = make_runner(tmp_path)
    issue = {
        "number": 42,
        "title": "Refactor things",
        "body": "Please refactor.",
        "comments": [{"body": "First comment"}, {"body": "Second comment"}],
    }

    text = runner._format_issue_text(issue)

    assert "Title: Refactor things" in text
    assert "Body: Please refactor." in text
    assert "Comments" in text
    assert "First comment" in text
    assert "Second comment" in text


def test_branch_name_for_issue(tmp_path):
    runner, db, gh, git, command_runner = make_runner(tmp_path)

    assert runner.branch_name_for_issue("Add the Bitter Lesson") == "feature/add-the-bitter-lesson"
    assert runner.branch_name_for_issue("  Fix  This   Bug  ") == "feature/fix-this-bug"
    assert runner.branch_name_for_issue("Needs: Proper Casing!") == "feature/needs-proper-casing"


def test_make_artifact_path(tmp_path):
    runner, db, gh, git, command_runner = make_runner(tmp_path)
    path = runner._make_artifact_path("abc-123")
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
    assert gh.calls == [("fetch_issue", 42)]
    assert "# GitHub Issue #42" in job.prompt
    assert "Title: Fix the bug" in job.prompt
    assert "the issue" in job.prompt
    assert db.running == [job]


def test_dequeue_job_marks_failed_on_error(tmp_path):
    job = Job(job_id="abc-123", prompt=None, issue_number=42)
    runner, db, gh, git, command_runner = make_runner(tmp_path, job=job)

    class Boom(FakeGh):
        def fetch_issue(self, issue_number):
            raise Exception("gh is down")

    runner._gh = Boom()

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
    assert ("create_branch", "feature/fix-the-bug") in git.calls
    assert ("push_to_origin", "feature/fix-the-bug") in git.calls
    assert ("create_pull_request", "feature/fix-the-bug", "main", 42) in gh.calls
    assert ("fetch_issue", 42) in gh.calls
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
