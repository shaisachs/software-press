from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Job:
    job_id: str
    prompt: Optional[str] = None
    issue_number: Optional[int] = None
    repo: Optional[str] = None
    artifact_path: Optional[Path] = None
    pr_number: Optional[int] = None
    status: Optional[str] = None
    error: Optional[str] = None
