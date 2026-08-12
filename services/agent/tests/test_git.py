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


def test_create_branch(recording_runner):
    recording_runner.on(
        "symbolic-ref",
        make_result(stdout="refs/remotes/origin/main\n"),
    )

    git = make_git(recording_runner)
    default_branch, branch = git.create_branch("feature/add-the-bitter-lesson")

    assert default_branch == "main"
    assert branch == "feature/add-the-bitter-lesson"
    assert ["git", "checkout", "-B", "feature/add-the-bitter-lesson", "origin/main"] in [
        c for (c, _in) in recording_runner.calls
    ]


def test_try_stage_changes_true_when_diff_nonzero(recording_runner):
    recording_runner.on("diff", make_result(returncode=1))

    git = make_git(recording_runner)
    assert git.try_stage_changes() is True


def test_try_stage_changes_false_when_diff_zero(recording_runner):
    recording_runner.on("diff", make_result(returncode=0))

    git = make_git(recording_runner)
    assert git.try_stage_changes() is False


def test_commit_changes(recording_runner):
    git = make_git(recording_runner)
    git.commit_changes()

    assert ["git", "commit"] in [c for (c, _in) in recording_runner.calls]


def test_push_to_origin(recording_runner):
    git = make_git(recording_runner)
    git.push_to_origin("feature/issue-42")

    assert ["git", "push", "--set-upstream", "origin", "feature/issue-42"] in [
        c for (c, _in) in recording_runner.calls
    ]
