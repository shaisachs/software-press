from unittest import mock

from app.git import Git

from tests.conftest import make_result


def make_git(recording_runner):
    return Git(recording_runner)


def test_get_default_branch(recording_runner):
    recording_runner.on(
        "symbolic-ref",
        make_result(stdout="refs/remotes/origin/main\n"),
    )

    git = make_git(recording_runner)
    assert git.get_default_branch() == "main"


def test_get_default_branch_falls_back_to_main(recording_runner):
    recording_runner.on(
        "symbolic-ref",
        make_result(returncode=1),
    )

    git = make_git(recording_runner)
    assert git.get_default_branch() == "main"


def test_branch_for_job():
    assert Git.branch_for_job(42) == "feature/issue-42"


def test_create_branch(recording_runner):
    recording_runner.on(
        "symbolic-ref",
        make_result(stdout="refs/remotes/origin/main\n"),
    )

    git = make_git(recording_runner)
    output_file = mock.Mock()

    default_branch, branch = git.create_branch(42, output_file)

    assert default_branch == "main"
    assert branch == "feature/issue-42"
    assert ["git", "checkout", "-B", "feature/issue-42", "origin/main"] in [
        c for (c, _of, _in) in recording_runner.calls
    ]


def test_try_stage_changes_true_when_diff_nonzero(recording_runner):
    recording_runner.on("diff", make_result(returncode=1))

    git = make_git(recording_runner)
    assert git.try_stage_changes(mock.Mock()) is True


def test_try_stage_changes_false_when_diff_zero(recording_runner):
    recording_runner.on("diff", make_result(returncode=0))

    git = make_git(recording_runner)
    assert git.try_stage_changes(mock.Mock()) is False


def test_commit_changes(recording_runner):
    git = make_git(recording_runner)
    git.commit_changes(mock.Mock())

    assert ["git", "commit"] in [c for (c, _of, _in) in recording_runner.calls]


def test_push_to_origin(recording_runner):
    git = make_git(recording_runner)
    git.push_to_origin("feature/issue-42", mock.Mock())

    assert ["git", "push", "--set-upstream", "origin", "feature/issue-42"] in [
        c for (c, _of, _in) in recording_runner.calls
    ]
