import re
from typing import Optional, Tuple


class JobStrategy:
    def __init__(self, job_item):
        self.job_item = job_item

    def setup_item_run(self):
        pass

    def build_prompt(self) -> str:
        return None

    def commits_changes(self) -> bool:
        return True

    def close_item_run(self, output: Optional[str] = None):
        pass


class AdHocPromptStrategy(JobStrategy):
    def build_prompt(self) -> str:
        return self.job_item.job.prompt


class IssueResolveStrategy(JobStrategy):
    def __init__(self, job_item, gh=None, git=None, db=None):
        super().__init__(job_item)
        self.gh = gh if gh is not None else job_item.gh
        self.git = git if git is not None else job_item.git
        self.db = db if db is not None else job_item.db
        self.issue = None
        self.branch = None
        self.default_branch = None

    @property
    def _job(self):
        return self.job_item.job

    @property
    def _issue(self):
        if self.issue is None:
            self.issue = self.fetch_issue(self._job.issue_number)
        return self.issue

    def fetch_issue(self, issue_number: int) -> dict:
        return self.gh.fetch_issue(issue_number)

    def create_branch(self, branch: str) -> Tuple[str, str]:
        return self.git.create_branch(branch)

    def push_to_origin(self, branch: str):
        self.git.push_to_origin(branch)

    def checkout_branch(self, branch: str):
        self.git.checkout_branch(branch)

    def create_pull_request(
        self,
        branch: str,
        default_branch: str,
        title: str,
        issue_number: Optional[int],
    ) -> Optional[int]:
        return self.gh.create_pull_request(branch, default_branch, title, issue_number)

    def record_pr_number(self, pr_number: int):
        self.db.record_pr_number(self._job.job_id, pr_number)

    def setup_item_run(self):
        branch = self.branch_name_for_issue(self._issue["title"])
        (self.default_branch, self.branch) = self.create_branch(branch)

    def build_prompt(self) -> str:
        return (
            "A GitHub issue has been filed against this repository - the body and comments are below. "
            "Please resolve it by making the necessary changes to the code. "
            "The changes will be committed and a pull request will be created for them.\n\n"
            f"# GitHub Issue #{self._job.issue_number}\n\n"
            f"{self._format_issue_text(self._issue)}"
        )

    def close_item_run(self, output: Optional[str] = None):
        self.push_to_origin(self.branch)

        title = self._issue["title"]
        pr_number = self.create_pull_request(
            self.branch, self.default_branch, title, self._job.issue_number
        )
        if pr_number is not None:
            self.record_pr_number(pr_number)

        self.checkout_branch(self.default_branch)

    @staticmethod
    def _format_issue_text(issue: dict) -> str:
        output = ""
        output += f"Title: {issue['title']}\n"
        output += f"Body: {issue['body']}\n"

        if issue["comments"]:
            output += "Comments\n"
            for comment in issue["comments"]:
                output += comment["body"]

        return output

    @staticmethod
    def _build_prompt(issue_number: int, issue_text: str) -> str:
        return (
            "A GitHub issue has been filed against this repository - the body and comments are below. "
            "Please resolve it by making the necessary changes to the code. "
            "The changes will be committed and a pull request will be created for them.\n\n"
            f"# GitHub Issue #{issue_number}\n\n"
            f"{issue_text}"
        )

    @staticmethod
    def branch_name_for_issue(issue_title: str) -> str:
        kebab = re.sub(r"[^a-z0-9]+", "-", issue_title.lower()).strip("-")
        return f"feature/{kebab}"


class IssueArchitectStrategy(JobStrategy):
    def __init__(self, job_item, gh=None, git=None, db=None):
        super().__init__(job_item)
        self.gh = gh if gh is not None else job_item.gh
        self.git = git if git is not None else job_item.git
        self.db = db if db is not None else job_item.db
        self.issue = None

    @property
    def _job(self):
        return self.job_item.job

    @property
    def _issue(self):
        if self.issue is None:
            self.issue = self.gh.fetch_issue(self._job.issue_number)
        return self.issue

    def commits_changes(self) -> bool:
        return False

    def build_prompt(self) -> str:
        return (
            "A GitHub issue has been filed against this repository - the body and comments are below. "
            "Research the codebase and propose an implementation approach to resolve it. "
            "Do not write or commit any code. Instead, describe the approach you would take, "
            "the files you would modify, and any trade-offs to consider.\n\n"
            f"# GitHub Issue #{self._job.issue_number}\n\n"
            f"{IssueResolveStrategy._format_issue_text(self._issue)}"
        )

    def close_item_run(self, output: Optional[str] = None):
        if output:
            self.gh.create_issue_comment(self._job.issue_number, output)
