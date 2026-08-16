from app.models import Job
from app.JobStrategy import AdHocPromptStrategy, IssueResolveStrategy

from tests.conftest import make_db, make_gh, make_git


def make_job(**overrides):
    defaults = dict(job_id="abc-123", prompt=None, issue_number=42)
    defaults.update(overrides)
    return Job(**defaults)


def make_job_item(mocker, job, gh=None, git=None, db=None):
    job_item = mocker.Mock()
    job_item.job = job
    job_item.gh = gh if gh is not None else make_gh(mocker)
    job_item.git = git if git is not None else make_git(mocker)
    job_item.db = db if db is not None else make_db(mocker)
    return job_item


def make_strategy(mocker, job=None, gh=None, git=None, db=None):
    job_item = make_job_item(mocker, job if job is not None else make_job(), gh=gh, git=git, db=db)
    return IssueResolveStrategy(job_item)


def test_build_prompt():
    prompt = IssueResolveStrategy._build_prompt(42, "the body")
    assert "# GitHub Issue #42" in prompt
    assert "the body" in prompt


def test_format_issue_text():
    issue = {
        "number": 42,
        "title": "Refactor things",
        "body": "Please refactor.",
        "comments": [{"body": "First comment"}, {"body": "Second comment"}],
    }

    text = IssueResolveStrategy._format_issue_text(issue)

    assert "Title: Refactor things" in text
    assert "Body: Please refactor." in text
    assert "Comments" in text
    assert "First comment" in text
    assert "Second comment" in text


def test_format_issue_text_without_comments():
    issue = {"number": 42, "title": "Refactor things", "body": "Please refactor.", "comments": []}

    text = IssueResolveStrategy._format_issue_text(issue)

    assert "Title: Refactor things" in text
    assert "Body: Please refactor." in text
    assert "Comments" not in text


def test_branch_name_for_issue():
    assert IssueResolveStrategy.branch_name_for_issue("Add the Bitter Lesson") == "feature/add-the-bitter-lesson"
    assert IssueResolveStrategy.branch_name_for_issue("  Fix  This   Bug  ") == "feature/fix-this-bug"
    assert IssueResolveStrategy.branch_name_for_issue("Needs: Proper Casing!") == "feature/needs-proper-casing"


def test_adhoc_prompt_strategy_operations_are_trivial(mocker):
    gh = make_gh(mocker)
    git = make_git(mocker)
    job = make_job(prompt="write hello world")
    job_item = make_job_item(mocker, job, gh=gh, git=git)

    strategy = AdHocPromptStrategy(job_item)

    strategy.setup_item_run()
    assert strategy.build_prompt() == "write hello world"
    strategy.close_item_run()

    gh.fetch_issue.assert_not_called()
    git.create_branch.assert_not_called()
    git.push_to_origin.assert_not_called()
    gh.create_pull_request.assert_not_called()


def test_fetch_issue_delegates_to_gh(mocker):
    gh = make_gh(mocker)
    strategy = make_strategy(mocker, gh=gh)

    issue = strategy.fetch_issue(42)

    gh.fetch_issue.assert_called_once_with(42)
    assert issue is gh.fetch_issue.return_value


def test_create_branch_delegates_to_git(mocker):
    git = make_git(mocker)
    strategy = make_strategy(mocker, git=git)

    result = strategy.create_branch("feature/x")

    git.create_branch.assert_called_once_with("feature/x")
    assert result is git.create_branch.return_value


def test_push_to_origin_delegates_to_git(mocker):
    git = make_git(mocker)
    strategy = make_strategy(mocker, git=git)

    strategy.push_to_origin("feature/x")

    git.push_to_origin.assert_called_once_with("feature/x")


def test_checkout_branch_delegates_to_git(mocker):
    git = make_git(mocker)
    strategy = make_strategy(mocker, git=git)

    strategy.checkout_branch("main")

    git.checkout_branch.assert_called_once_with("main")


def test_create_pull_request_delegates_to_gh(mocker):
    gh = make_gh(mocker)
    strategy = make_strategy(mocker, gh=gh)

    pr_number = strategy.create_pull_request("feature/x", "main", "title", 42)

    gh.create_pull_request.assert_called_once_with("feature/x", "main", "title", 42)
    assert pr_number is gh.create_pull_request.return_value


def test_record_pr_number_delegates_to_db(mocker):
    db = make_db(mocker)
    strategy = make_strategy(mocker, db=db)

    strategy.record_pr_number(99)

    db.record_pr_number.assert_called_once_with("abc-123", 99)


def test_issue_resolve_setup_item_run_creates_branch(mocker):
    gh = make_gh(mocker)
    git = make_git(mocker)
    strategy = make_strategy(mocker, gh=gh, git=git)

    strategy.setup_item_run()

    gh.fetch_issue.assert_called_once_with(42)
    git.create_branch.assert_called_once_with("feature/fix-the-bug")
    assert strategy.default_branch == "main"
    assert strategy.branch == "feature/fix-the-bug"


def test_issue_resolve_build_prompt_from_issue(mocker):
    gh = make_gh(mocker)
    strategy = make_strategy(mocker, gh=gh)

    prompt = strategy.build_prompt()

    gh.fetch_issue.assert_called_once_with(42)
    assert "# GitHub Issue #42" in prompt
    assert "Title: Fix the bug" in prompt
    assert "the issue" in prompt


def test_issue_resolve_close_item_run_creates_pr_and_checks_out(mocker):
    gh = make_gh(mocker)
    git = make_git(mocker)
    db = make_db(mocker)
    strategy = make_strategy(mocker, gh=gh, git=git, db=db)

    strategy.setup_item_run()
    strategy.close_item_run()

    git.push_to_origin.assert_called_once_with("feature/fix-the-bug")
    gh.create_pull_request.assert_called_once_with("feature/fix-the-bug", "main", "Fix the bug", 42)
    db.record_pr_number.assert_called_once_with("abc-123", 99)
    git.checkout_branch.assert_called_once_with("main")
