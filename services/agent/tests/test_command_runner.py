from app.command_runner import CommandRunner

from tests.conftest import make_result


def test_run_uses_working_dir(tmp_path, mocker):
    result = make_result(mocker, returncode=0, stdout="stdout-line\n", stderr="stderr-line\n")
    fake_run = mocker.patch("app.command_runner.subprocess.run", return_value=result)

    output_file = mocker.Mock()
    runner = CommandRunner(str(tmp_path), output_file)
    returned = runner.run(["git", "status"])

    fake_run.assert_called_once_with(
        ["git", "status"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        input=None,
    )
    assert returned is result
    output_file.write.assert_called()


def test_run_without_output_file(tmp_path, mocker):
    result = make_result(mocker, returncode=0, stdout="out", stderr="")
    fake_run = mocker.patch("app.command_runner.subprocess.run", return_value=result)

    runner = CommandRunner(str(tmp_path))
    returned = runner.run(["echo", "hi"])

    assert returned is result
    fake_run.assert_called_once()


def test_run_passes_input(tmp_path, mocker):
    result = make_result(mocker, returncode=0, stdout="ok", stderr="")
    fake_run = mocker.patch("app.command_runner.subprocess.run", return_value=result)

    runner = CommandRunner(str(tmp_path))
    runner.run(["gh", "auth", "login"], input="secret")

    fake_run.assert_called_once_with(
        ["gh", "auth", "login"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        input="secret",
    )
