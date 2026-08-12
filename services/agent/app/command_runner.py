import subprocess
from typing import List, Optional, TextIO


class CommandRunner:
    def __init__(self, working_dir: str, output_file: Optional[TextIO] = None):
        self.working_dir = working_dir
        self.output_file = output_file

    def run(
        self,
        cmd: List[str],
        input: Optional[str] = None,
    ):
        result = subprocess.run(
            cmd,
            cwd=self.working_dir,
            capture_output=True,
            text=True,
            input=input,
        )
        if self.output_file is not None:
            self.output_file.write("$ " + " ".join(cmd) + "\n")
            self.output_file.write(result.stdout)
            self.output_file.write(result.stderr)
            self.output_file.write("\n\n")
        return result
