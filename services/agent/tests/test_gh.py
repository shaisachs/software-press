import json

from app.gh import GithubClient

from tests.conftest import make_result


def test_ensure_gh_auth_skips_without_token(recording_runner, monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)

    gh = GithubClient(recording_runner)
    gh._ensure_gh_auth()

    assert recording_runner.calls == []


def test_ensure_gh_auth_skips_when_already_authenticated(recording_runner, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "secret")
    recording_runner.on("auth status", make_result(returncode=0))

    gh = GithubClient(recording_runner)
    gh._ensure_gh_auth()

    assert ["gh", "auth", "status"] in [c for (c, _in) in recording_runner.calls]
    assert not [c for (c, _in) in recording_runner.calls if "login" in c]


def test_ensure_gh_auth_logs_in_when_unauthenticated(recording_runner, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "secret")
    recording_runner.on("auth status", make_result(returncode=1))

    gh = GithubClient(recording_runner)
    gh._ensure_gh_auth()

    login_call = [c for (c, _in) in recording_runner.calls if "login" in c]
    assert len(login_call) == 1
    assert login_call[0] == ["gh", "auth", "login", "--with-token"]


def test_fetch_issue_returns_well_formed_json(recording_runner, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "secret")
    recording_runner.on("auth status", make_result(returncode=0))
    payload = {
        "number": 42,
        "title": "Refactor things",
        "body": "Please refactor.",
        "comments": [{"body": "First comment"}, {"body": "Second comment"}],
    }
    recording_runner.on("issue view", make_result(stdout=json.dumps(payload)))

    gh = GithubClient(recording_runner)
    issue = gh.fetch_issue(42)

    assert ["gh", "auth", "status"] in [c for (c, _in) in recording_runner.calls]
    assert issue == payload
    assert ["gh", "issue", "view", "42", "--comments", "--json", "number,title,body,comments"] in [
        c for (c, _in) in recording_runner.calls
    ]


def test_fetch_issue_raises_on_error(recording_runner, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "secret")
    recording_runner.on("auth status", make_result(returncode=0))
    recording_runner.on("issue view", make_result(returncode=1, stderr="boom"))

    gh = GithubClient(recording_runner)
    try:
        gh.fetch_issue(42)
    except Exception as e:
        assert "gh issue view failed" in str(e)
    else:
        raise AssertionError("expected an exception")


def test_create_pull_request_returns_pr_number(recording_runner, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "secret")
    recording_runner.on("auth status", make_result(returncode=0))
    recording_runner.on(
        "pr create",
        make_result(stdout="https://github.com/acme/repo/pull/123\n"),
    )

    gh = GithubClient(recording_runner)
    pr_number = gh.create_pull_request(
        "feature/issue-42", "main", "Do something", 42
    )

    assert ["gh", "auth", "status"] in [c for (c, _in) in recording_runner.calls]
    assert pr_number == 123


def test_create_pull_request_uses_fill_without_issue(recording_runner, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "secret")
    recording_runner.on("auth status", make_result(returncode=0))
    recording_runner.on(
        "pr create",
        make_result(stdout="https://github.com/acme/repo/pull/123\n"),
    )

    gh = GithubClient(recording_runner)
    gh.create_pull_request("feature/foo", "main", "Foo", None)

    fill_call = [c for (c, _in) in recording_runner.calls if "--fill" in c]
    assert len(fill_call) == 1


def test_create_pull_request_returns_none_on_error(recording_runner, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "secret")
    recording_runner.on("auth status", make_result(returncode=0))
    recording_runner.on("pr create", make_result(returncode=1))

    gh = GithubClient(recording_runner)
    pr_number = gh.create_pull_request(
        "feature/issue-42", "main", "Do something", 42
    )

    assert pr_number is None
