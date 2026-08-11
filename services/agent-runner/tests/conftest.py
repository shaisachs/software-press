import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.command_runner import CommandRunner


def make_result(returncode=0, stdout="", stderr=""):
    class Result:
        pass

    result = Result()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


class RecordingCommandRunner(CommandRunner):
    def __init__(self, working_dir="/workspaces", output_file=None):
        super().__init__(working_dir, output_file)
        self.calls = []
        self._handlers = []

    def on(self, match, result):
        self._handlers.append((match, result))
        return self

    def run(self, cmd, input=None):
        self.calls.append((list(cmd), input))
        joined = " ".join(cmd)
        for match, result in self._handlers:
            if match in joined:
                return result
        return make_result()


@pytest.fixture
def recording_runner():
    return RecordingCommandRunner()
