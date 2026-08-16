from pathlib import Path

from app import config
from app.command_runner import CommandRunner
from app.db import Db
from app.GithubClient import GithubClient
from app.GitClient import GitClient
from app.JobStrategy import AdHocPromptStrategy, IssueResolveStrategy, JobStrategy
from app.models import Job

class JobItem:
    def __init__(self, job: Job, gh=None, git=None, command_runner=None, db=None):
        self.job = job

        if job.model is not None and not config.model_is_available(job.model):
            raise Exception(f"model is unavailable: {job.model}")

        self.workspace_dir = self._validate_repo(job.repo)
        self.command_runner = command_runner or CommandRunner(str(self.workspace_dir))
        self.command_runner.working_dir = str(self.workspace_dir)
        self.gh = gh or GithubClient(self.command_runner)
        self.git = git or GitClient(self.command_runner)
        self.db = db or Db()

        self.strategy = self._build_strategy()

    @property
    def model(self) -> str:
        return self.job.model or config.opencode_model()

    def _build_strategy(self) -> JobStrategy:
        if self.job.prompt is not None:
            return AdHocPromptStrategy(self)
        if self.job.issue_number is not None:
            return IssueResolveStrategy(self, gh=self.gh, git=self.git, db=self.db)
        raise Exception("job must have a prompt or an issue number")

    def try_stage_changes(self) -> bool:
        return self.git.try_stage_changes()

    def commit_changes(self):
        self.git.commit_changes()

    def run_prompt(self, prompt: str):
        self.command_runner.run(
            [
                "opencode",
                "--dir", self.command_runner.working_dir,
                "--model", self.model,
                "run",
                "--agent", "build",
                prompt,
            ]
        )

    def run(self):
        self.strategy.setup_item_run()
        prompt = self.strategy.build_prompt()
        self.run_prompt(prompt)

        if self.try_stage_changes():
            self.commit_changes()
            self.strategy.close_item_run()
        else:
            # TODO: proper logging framework, this access pattern kind of sucks
            self.command_runner.output_file.write("No changes staged; skipping commit and pull request.\n")

    @staticmethod
    def _workspace_dir(repo: str) -> Path:
        return config.WORKSPACES_ROOT / repo

    @classmethod
    def _validate_repo(cls, repo: str) -> Path:
        if not repo:
            raise Exception("repo is required")
        workspace_dir = cls._workspace_dir(repo)
        if not workspace_dir.is_dir():
            raise Exception(f"repo directory not found on disk: {workspace_dir}")
        return workspace_dir
