from typing import Optional, Tuple

from app.command_runner import CommandRunner


class GitClient:
    def __init__(self, command_runner: CommandRunner):
        self.command_runner = command_runner

    def get_default_branch(self) -> str:
        self.command_runner.run(["git", "remote", "set-head", "origin", "-a"])
        result = self.command_runner.run(
            ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"]
        )
        if result.returncode == 0:
            return result.stdout.strip().split("/")[-1]
        return "main"

    def resolve_branch(self, requested: Optional[str]) -> str:
        if requested:
            return requested
        return self.get_default_branch()

    def create_branch(self, branch: str, base: str) -> Tuple[str, str]:
        result = self.command_runner.run(
            ["git", "checkout", "-B", branch, f"origin/{base}"]
        )
        if result.returncode != 0:
            raise Exception(f"failed to create branch {branch} from origin/{base}")
        return (base, branch)

    def try_stage_changes(self) -> bool:
        self.command_runner.run(["git", "add", "-A"])
        has_changes = self.command_runner.run(["git", "diff", "--staged", "--quiet"])
        return has_changes.returncode != 0

    def commit_changes(self):
        self.command_runner.run(["git", "commit"])

    def push_to_origin(self, branch: str):
        self.command_runner.run(
            ["git", "push", "--set-upstream", "origin", branch]
        )

    def checkout_branch(self, branch: str):
        result = self.command_runner.run(["git", "checkout", branch])
        if result.returncode != 0:
            raise Exception(f"failed to checkout branch: {branch}")

