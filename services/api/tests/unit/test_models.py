import pytest
from pydantic import ValidationError

from app.models import CreateJobRequest

VALID_REPO = "shaisachs/laws-of-software"


def test_prompt_only_is_valid():
    req = CreateJobRequest(prompt="write hello world", repo=VALID_REPO)

    assert req.prompt == "write hello world"
    assert req.issueNumber is None
    assert req.repo == VALID_REPO


def test_issue_number_only_is_valid():
    req = CreateJobRequest(issueNumber=42, repo=VALID_REPO)

    assert req.issueNumber == 42
    assert req.prompt is None
    assert req.repo == VALID_REPO


def test_repo_required():
    with pytest.raises(ValidationError):
        CreateJobRequest(prompt="write hello world")


def test_repo_accepts_owner_and_repo_names():
    for repo in [
        "shaisachs/laws-of-software",
        "shaisachs/shaisachs.github.io",
        "octocat/hello-world",
        "acme/repo.with.dots",
        "A-Cme/UPPER_case",
    ]:
        req = CreateJobRequest(prompt="hi", repo=repo)
        assert req.repo == repo


def test_repo_rejects_invalid_formats():
    for repo in [
        "",
        "no-slash",
        "owner/",
        "/repo",
        "owner/repo/extra",
        "owner name/repo",
        "owner/repo name",
        "own$er/repo",
    ]:
        with pytest.raises(ValidationError):
            CreateJobRequest(prompt="hi", repo=repo)


def test_neither_prompt_nor_issue_raises():
    with pytest.raises(ValidationError) as exc_info:
        CreateJobRequest(repo=VALID_REPO)

    assert "issueResolver job requires an 'issueNumber'" in str(exc_info.value)


def test_both_prompt_and_issue_raises():
    with pytest.raises(ValidationError) as exc_info:
        CreateJobRequest(prompt="hi", issueNumber=1, repo=VALID_REPO)

    assert "adHoc job must not have an 'issueNumber'" in str(exc_info.value)


def test_issue_number_must_be_positive():
    with pytest.raises(ValidationError):
        CreateJobRequest(issueNumber=0, repo=VALID_REPO)

    with pytest.raises(ValidationError):
        CreateJobRequest(issueNumber=-5, repo=VALID_REPO)


def test_issue_number_must_be_int():
    with pytest.raises(ValidationError):
        CreateJobRequest(issueNumber="not a number", repo=VALID_REPO)


def test_model_defaults_to_none():
    req = CreateJobRequest(prompt="hi", repo=VALID_REPO)

    assert req.model is None


def test_model_accepts_valid_formats():
    for model in [
        "deepseek/deepseek-v4-flash",
        "deepseek/deepseek-v4-pro",
        "sp-ollama/qwen2.5:0.5b",
        "acme/model.with.dots",
    ]:
        req = CreateJobRequest(prompt="hi", repo=VALID_REPO, model=model)
        assert req.model == model


def test_model_rejects_invalid_formats():
    for model in [
        "",
        "no-slash",
        "provider/",
        "/model",
        "provider/model/extra",
        "provider/model name",
    ]:
        with pytest.raises(ValidationError):
            CreateJobRequest(prompt="hi", repo=VALID_REPO, model=model)


def test_type_inferred_as_adhoc_from_prompt():
    req = CreateJobRequest(prompt="hi", repo=VALID_REPO)

    assert req.type == "adHoc"


def test_type_inferred_as_issue_resolver_from_issue_number():
    req = CreateJobRequest(issueNumber=42, repo=VALID_REPO)

    assert req.type == "issueResolver"


def test_explicit_adhoc_type_with_prompt_is_valid():
    req = CreateJobRequest(type="adHoc", prompt="hi", repo=VALID_REPO)

    assert req.type == "adHoc"
    assert req.prompt == "hi"
    assert req.issueNumber is None


def test_explicit_adhoc_type_with_issue_number_raises():
    with pytest.raises(ValidationError) as exc_info:
        CreateJobRequest(type="adHoc", issueNumber=42, repo=VALID_REPO)

    assert "adHoc job requires a 'prompt'" in str(exc_info.value)


def test_explicit_issue_resolver_type_with_issue_number_is_valid():
    req = CreateJobRequest(type="issueResolver", issueNumber=42, repo=VALID_REPO)

    assert req.type == "issueResolver"
    assert req.issueNumber == 42
    assert req.prompt is None


def test_explicit_issue_resolver_type_with_prompt_raises():
    with pytest.raises(ValidationError) as exc_info:
        CreateJobRequest(type="issueResolver", prompt="hi", repo=VALID_REPO)

    assert "issueResolver job requires an 'issueNumber'" in str(exc_info.value)


def test_explicit_issue_architect_type_with_issue_number_is_valid():
    req = CreateJobRequest(type="issueArchitect", issueNumber=42, repo=VALID_REPO)

    assert req.type == "issueArchitect"
    assert req.issueNumber == 42
    assert req.prompt is None


def test_explicit_issue_architect_type_with_prompt_raises():
    with pytest.raises(ValidationError) as exc_info:
        CreateJobRequest(type="issueArchitect", prompt="hi", issueNumber=42, repo=VALID_REPO)

    assert "issueArchitect job must not have a 'prompt'" in str(exc_info.value)


def test_issue_architect_type_requires_issue_number():
    with pytest.raises(ValidationError) as exc_info:
        CreateJobRequest(type="issueArchitect", repo=VALID_REPO)

    assert "issueArchitect job requires an 'issueNumber'" in str(exc_info.value)


def test_invalid_type_rejected():
    with pytest.raises(ValidationError):
        CreateJobRequest(type="bogus", prompt="hi", repo=VALID_REPO)
