import pytest
from pydantic import ValidationError

from app.models import CreateJobRequest


def test_prompt_only_is_valid():
    req = CreateJobRequest(prompt="write hello world")

    assert req.prompt == "write hello world"
    assert req.issueNumber is None


def test_issue_number_only_is_valid():
    req = CreateJobRequest(issueNumber=42)

    assert req.issueNumber == 42
    assert req.prompt is None


def test_neither_prompt_nor_issue_raises():
    with pytest.raises(ValidationError) as exc_info:
        CreateJobRequest()

    assert "exactly one" in str(exc_info.value)


def test_both_prompt_and_issue_raises():
    with pytest.raises(ValidationError) as exc_info:
        CreateJobRequest(prompt="hi", issueNumber=1)

    assert "exactly one" in str(exc_info.value)


def test_issue_number_must_be_positive():
    with pytest.raises(ValidationError):
        CreateJobRequest(issueNumber=0)

    with pytest.raises(ValidationError):
        CreateJobRequest(issueNumber=-5)


def test_issue_number_must_be_int():
    with pytest.raises(ValidationError):
        CreateJobRequest(issueNumber="not a number")
