from unittest import mock

from app.command_runner import CommandRunner

from tests.conftest import make_result


def test_run_uses_working_dir(tmp_path, monkeypatch):
    result = make_result(returncode=0, stdout="stdout-line\n", stderr="stderr-line\n")
    fake_run = mock.Mock(return_value=result)
    monkeypatch.setattr("app.command_runner.subprocess.run", fake_run)

    output_file = mock.Mock()
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


def test_run_without_output_file(tmp_path, monkeypatch):
    result = make_result(returncode=0, stdout="out", stderr="")
    fake_run = mock.Mock(return_value=result)
    monkeypatch.setattr("app.command_runner.subprocess.run", fake_run)

    runner = CommandRunner(str(tmp_path))
    returned = runner.run(["echo", "hi"])

    assert returned is result
    fake_run.assert_called_once()


def test_run_passes_input(tmp_path, monkeypatch):
    result = make_result(returncode=0, stdout="ok", stderr="")
    fake_run = mock.Mock(return_value=result)
    monkeypatch.setattr("app.command_runner.subprocess.run", fake_run)

    runner = CommandRunner(str(tmp_path))
    runner.run(["gh", "auth", "login"], input="secret")

    fake_run.assert_called_once_with(
        ["gh", "auth", "login"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        input="secret",
    )
