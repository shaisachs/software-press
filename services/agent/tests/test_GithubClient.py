import json

import pytest

from app.GithubClient import GithubClient

from tests.conftest import make_result


def test_ensure_gh_auth_skips_without_token(recording_runner, monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)

    gh = GithubClient(recording_runner)
    gh._ensure_gh_auth()

    recording_runner.run.assert_not_called()


def test_ensure_gh_auth_skips_when_already_authenticated(recording_runner, monkeypatch, mocker):
    monkeypatch.setenv("GH_TOKEN", "secret")
    recording_runner.on("auth status", make_result(mocker, returncode=0))

    gh = GithubClient(recording_runner)
    gh._ensure_gh_auth()

    recording_runner.run.assert_any_call(["gh", "auth", "status"])
    assert not [c.args[0] for c in recording_runner.run.call_args_list if "login" in c.args[0]]


def test_ensure_gh_auth_logs_in_when_unauthenticated(recording_runner, monkeypatch, mocker):
    monkeypatch.setenv("GH_TOKEN", "secret")
    recording_runner.on("auth status", make_result(mocker, returncode=1))

    gh = GithubClient(recording_runner)
    gh._ensure_gh_auth()

    login_calls = [c.args[0] for c in recording_runner.run.call_args_list if "login" in c.args[0]]
    assert len(login_calls) == 1
    assert login_calls[0] == ["gh", "auth", "login", "--with-token"]


def test_fetch_issue_returns_well_formed_json(recording_runner, monkeypatch, mocker):
    monkeypatch.setenv("GH_TOKEN", "secret")
    recording_runner.on("auth status", make_result(mocker, returncode=0))
    payload = {
        "number": 42,
        "title": "Refactor things",
        "body": "Please refactor.",
        "comments": [{"body": "First comment"}, {"body": "Second comment"}],
    }
    recording_runner.on("issue view", make_result(mocker, stdout=json.dumps(payload)))

    gh = GithubClient(recording_runner)
    issue = gh.fetch_issue(42)

    recording_runner.run.assert_any_call(["gh", "auth", "status"])
    assert issue == payload
    recording_runner.run.assert_any_call(
        ["gh", "issue", "view", "42", "--comments", "--json", "number,title,body,comments"]
    )


def test_fetch_issue_raises_on_error(recording_runner, monkeypatch, mocker):
    monkeypatch.setenv("GH_TOKEN", "secret")
    recording_runner.on("auth status", make_result(mocker, returncode=0))
    recording_runner.on("issue view", make_result(mocker, returncode=1, stderr="boom"))

    gh = GithubClient(recording_runner)
    try:
        gh.fetch_issue(42)
    except Exception as e:
        assert "gh issue view failed" in str(e)
    else:
        raise AssertionError("expected an exception")


def test_create_pull_request_returns_pr_number(recording_runner, monkeypatch, mocker):
    monkeypatch.setenv("GH_TOKEN", "secret")
    recording_runner.on("auth status", make_result(mocker, returncode=0))
    recording_runner.on(
        "pr create",
        make_result(mocker, stdout="https://github.com/acme/repo/pull/123\n"),
    )

    gh = GithubClient(recording_runner)
    pr_number = gh.create_pull_request(
        "feature/issue-42", "main", "Do something", 42
    )

    recording_runner.run.assert_any_call(["gh", "auth", "status"])
    assert pr_number == 123


def test_create_pull_request_uses_fill_without_issue(recording_runner, monkeypatch, mocker):
    monkeypatch.setenv("GH_TOKEN", "secret")
    recording_runner.on("auth status", make_result(mocker, returncode=0))
    recording_runner.on(
        "pr create",
        make_result(mocker, stdout="https://github.com/acme/repo/pull/123\n"),
    )

    gh = GithubClient(recording_runner)
    gh.create_pull_request("feature/foo", "main", "Foo", None)

    fill_calls = [c.args[0] for c in recording_runner.run.call_args_list if "--fill" in c.args[0]]
    assert len(fill_calls) == 1


def test_create_pull_request_returns_none_on_error(recording_runner, monkeypatch, mocker):
    monkeypatch.setenv("GH_TOKEN", "secret")
    recording_runner.on("auth status", make_result(mocker, returncode=0))
    recording_runner.on("pr create", make_result(mocker, returncode=1))

    gh = GithubClient(recording_runner)
    pr_number = gh.create_pull_request(
        "feature/issue-42", "main", "Do something", 42
    )

    assert pr_number is None


def test_create_issue_comment_posts_to_issue(recording_runner, monkeypatch, mocker):
    monkeypatch.setenv("GH_TOKEN", "secret")
    recording_runner.on("auth status", make_result(mocker, returncode=0))
    recording_runner.on("issue comment", make_result(mocker, stdout="posted"))

    gh = GithubClient(recording_runner)
    gh.create_issue_comment(42, "Proposed approach: refactor the parser.")

    recording_runner.run.assert_any_call(["gh", "auth", "status"])
    recording_runner.run.assert_any_call(
        ["gh", "issue", "comment", "42", "--body", "Proposed approach: refactor the parser."]
    )


def test_create_issue_comment_raises_on_error(recording_runner, monkeypatch, mocker):
    monkeypatch.setenv("GH_TOKEN", "secret")
    recording_runner.on("auth status", make_result(mocker, returncode=0))
    recording_runner.on("issue comment", make_result(mocker, returncode=1, stderr="boom"))

    gh = GithubClient(recording_runner)
    with pytest.raises(Exception, match="gh issue comment failed"):
        gh.create_issue_comment(42, "Proposed approach.")
