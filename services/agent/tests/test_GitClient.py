from app.GitClient import GitClient

from tests.conftest import make_result


def make_git(recording_runner):
    return GitClient(recording_runner)


def test_get_default_branch(recording_runner, mocker):
    recording_runner.on(
        "symbolic-ref",
        make_result(mocker, stdout="refs/remotes/origin/main\n"),
    )

    git = make_git(recording_runner)
    assert git.get_default_branch() == "main"


def test_get_default_branch_falls_back_to_main(recording_runner, mocker):
    recording_runner.on(
        "symbolic-ref",
        make_result(mocker, returncode=1),
    )

    git = make_git(recording_runner)
    assert git.get_default_branch() == "main"


def test_create_branch(recording_runner, mocker):
    recording_runner.on(
        "symbolic-ref",
        make_result(mocker, stdout="refs/remotes/origin/main\n"),
    )

    git = make_git(recording_runner)
    default_branch, branch = git.create_branch("feature/add-the-bitter-lesson")

    assert default_branch == "main"
    assert branch == "feature/add-the-bitter-lesson"
    recording_runner.run.assert_any_call(
        ["git", "checkout", "-B", "feature/add-the-bitter-lesson", "origin/main"]
    )


def test_try_stage_changes_true_when_diff_nonzero(recording_runner, mocker):
    recording_runner.on("diff", make_result(mocker, returncode=1))

    git = make_git(recording_runner)
    assert git.try_stage_changes() is True


def test_try_stage_changes_false_when_diff_zero(recording_runner, mocker):
    recording_runner.on("diff", make_result(mocker, returncode=0))

    git = make_git(recording_runner)
    assert git.try_stage_changes() is False


def test_commit_changes(recording_runner, mocker):
    git = make_git(recording_runner)
    git.commit_changes()

    recording_runner.run.assert_any_call(["git", "commit"])


def test_push_to_origin(recording_runner, mocker):
    git = make_git(recording_runner)
    git.push_to_origin("feature/issue-42")

    recording_runner.run.assert_any_call(["git", "push", "--set-upstream", "origin", "feature/issue-42"])


def test_checkout_branch(recording_runner, mocker):
    git = make_git(recording_runner)
    git.checkout_branch("feature/foo")

    recording_runner.run.assert_any_call(["git", "checkout", "feature/foo"])
