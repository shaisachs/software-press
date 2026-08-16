from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

REPO_PATTERN = r"^[\w.-]+/[\w.-]+$"
MODEL_PATTERN = r"^[\w.-]+/[\w.:-]+$"


class CreateJobRequest(BaseModel):
    repo: str = Field(pattern=REPO_PATTERN)
    prompt: Optional[str] = None
    issueNumber: Optional[int] = Field(default=None, gt=0)
    model: Optional[str] = Field(default=None, pattern=MODEL_PATTERN)
    type: Optional[Literal["adHoc", "issueResolver", "issueArchitect"]] = None

    @model_validator(mode="after")
    def validate_type_and_fields(self):
        job_type = self.type
        if job_type is None:
            job_type = "adHoc" if self.prompt is not None else "issueResolver"

        if job_type == "adHoc":
            if self.prompt is None:
                raise ValueError("adHoc job requires a 'prompt'")
            if self.issueNumber is not None:
                raise ValueError("adHoc job must not have an 'issueNumber'")
        elif job_type in ("issueResolver", "issueArchitect"):
            if self.issueNumber is None:
                raise ValueError(f"{job_type} job requires an 'issueNumber'")
            if self.prompt is not None:
                raise ValueError(f"{job_type} job must not have a 'prompt'")

        self.type = job_type
        return self
