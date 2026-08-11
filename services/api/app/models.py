from typing import Optional

from pydantic import BaseModel, Field, model_validator


class CreateJobRequest(BaseModel):
    prompt: Optional[str] = None
    issueNumber: Optional[int] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def exactly_one_of_prompt_or_issue(self):
        prompt_set = self.prompt is not None
        issue_set = self.issueNumber is not None
        if prompt_set == issue_set:
            raise ValueError("exactly one of 'prompt' or 'issueNumber' must be specified")
        return self
