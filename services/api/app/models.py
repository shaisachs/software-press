import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

MODEL_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9:_.-]+$")


class CreateJobRequest(BaseModel):
    prompt: Optional[str] = None
    issueNumber: Optional[int] = Field(default=None, gt=0)
    model: Optional[str] = None

    @field_validator("model")
    @classmethod
    def model_must_be_provider_model(cls, v):
        if v is not None and not MODEL_PATTERN.match(v):
            raise ValueError("model must be in provider/model format")
        return v

    @model_validator(mode="after")
    def exactly_one_of_prompt_or_issue(self):
        prompt_set = self.prompt is not None
        issue_set = self.issueNumber is not None
        if prompt_set == issue_set:
            raise ValueError("exactly one of 'prompt' or 'issueNumber' must be specified")
        return self
