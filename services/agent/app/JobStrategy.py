import re


class JobStrategy:
    def __init__(self, job_item):
        self.job_item = job_item

    def setup_item_run(self):
        pass

    def build_prompt(self) -> str:
        return None

    def close_item_run(self):
        pass


class AdHocPromptStrategy(JobStrategy):
    def build_prompt(self) -> str:
        return self._job_item.job.prompt    


class IssueResolveStrategy(JobStrategy):
    def __init__(self, job_item):
        super().__init__(job_item)
        self.issue = None
        self.branch = None
        self.default_branch = None

    @property
    def _job(self):
        return self.job_item.job

    @property
    def _issue(self):
        if self.issue is None:
            self.issue = self.job_item.fetch_issue(self._job.issue_number)
        return self.issue

    def setup_item_run(self):
        branch = self.branch_name_for_issue(self._issue["title"])
        (self.default_branch, self.branch) = self.job_item.create_branch(branch)

    def build_prompt(self) -> str:
        return (
            "A GitHub issue has been filed against this repository - the body and comments are below. "
            "Please resolve it by making the necessary changes to the code. "
            "The changes will be committed and a pull request will be created for them.\n\n"
            f"# GitHub Issue #{self._job.issue_number}\n\n"
            f"{self._format_issue_text(self._issue)}"
        )

    def close_item_run(self):
        self.job_item.push_to_origin(self.branch)

        title = self._issue["title"]
        pr_number = self.job_item.create_pull_request(
            self.branch, self.default_branch, title, self._job.issue_number
        )
        if pr_number is not None:
            self.job_item.record_pr_number(pr_number)

        self.job_item.checkout_branch(self.default_branch)

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
