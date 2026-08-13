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


def test_model_is_optional():
    req = CreateJobRequest(prompt="write hello world")

    assert req.model is None


def test_model_in_provider_model_format_is_valid():
    req = CreateJobRequest(prompt="write hello world", model="deepseek/deepseek-v4-flash")

    assert req.model == "deepseek/deepseek-v4-flash"


def test_model_without_provider_slash_is_invalid():
    with pytest.raises(ValidationError) as exc_info:
        CreateJobRequest(prompt="hi", model="deepseek-v4-flash")

    assert "provider/model" in str(exc_info.value)


def test_model_with_empty_provider_is_invalid():
    with pytest.raises(ValidationError):
        CreateJobRequest(prompt="hi", model="/deepseek-v4-flash")


def test_model_with_empty_model_name_is_invalid():
    with pytest.raises(ValidationError):
        CreateJobRequest(prompt="hi", model="deepseek/")
