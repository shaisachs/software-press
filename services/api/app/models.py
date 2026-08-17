from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

REPO_PATTERN = r"^[\w.-]+/[\w.-]+$"
MODEL_PATTERN = r"^[\w.-]+/[\w.:-]+$"
BRANCH_PATTERN = r"^[\w][\w.-]*(/[\w][\w.-]*)*$"


class CreateJobRequest(BaseModel):
    repo: str = Field(pattern=REPO_PATTERN)
    prompt: Optional[str] = None
    issueNumber: Optional[int] = Field(default=None, gt=0)
    model: Optional[str] = Field(default=None, pattern=MODEL_PATTERN)
    branch: Optional[str] = Field(default=None, pattern=BRANCH_PATTERN)
    type: Literal["adHoc", "issueResolver", "issueArchitect"]

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and (".." in value or "//" in value):
            raise ValueError("branch must not contain '..' or '//'")
        return value

    @model_validator(mode="after")
    def validate_type_and_fields(self):
        if self.type == "adHoc":
            if self.prompt is None:
                raise ValueError("adHoc job requires a 'prompt'")
            if self.issueNumber is not None:
                raise ValueError("adHoc job must not have an 'issueNumber'")
        elif self.type in ("issueResolver", "issueArchitect"):
            if self.issueNumber is None:
                raise ValueError(f"{self.type} job requires an 'issueNumber'")
            if self.prompt is not None:
                raise ValueError(f"{self.type} job must not have a 'prompt'")

        return self
