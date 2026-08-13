from typing import Optional

from pydantic import BaseModel, Field, model_validator

REPO_PATTERN = r"^[\w.-]+/[\w.-]+$"
MODEL_PATTERN = r"^[\w.-]+/[\w.:-]+$"


class CreateJobRequest(BaseModel):
    repo: str = Field(pattern=REPO_PATTERN)
    prompt: Optional[str] = None
    issueNumber: Optional[int] = Field(default=None, gt=0)
    model: Optional[str] = Field(default=None, pattern=MODEL_PATTERN)

    @model_validator(mode="after")
    def exactly_one_of_prompt_or_issue(self):
        prompt_set = self.prompt is not None
        issue_set = self.issueNumber is not None
        if prompt_set == issue_set:
            raise ValueError("exactly one of 'prompt' or 'issueNumber' must be specified")
        return self
