import subprocess
from typing import List, Optional, TextIO


class CommandRunner:
    def __init__(self, working_dir: str):
        self.working_dir = working_dir

    def run(
        self,
        cmd: List[str],
        output_file: Optional[TextIO] = None,
        input: Optional[str] = None,
    ):
        result = subprocess.run(
            cmd,
            cwd=self.working_dir,
            capture_output=True,
            text=True,
            input=input,
        )
        if output_file is not None:
            output_file.write("$ " + " ".join(cmd) + "\n")
            output_file.write(result.stdout)
            output_file.write(result.stderr)
            output_file.write("\n\n")
        return result
