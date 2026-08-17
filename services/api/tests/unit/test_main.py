import uuid

VALID_REPO = "shaisachs/laws-of-software"


def test_root(client):
    resp = client.get("/")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_pings_redis(client, mocked_deps):
    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"postgres": "configured", "redis": True}
    mocked_deps["redis_client"].ping.assert_called_once_with()


def test_health_reflects_redis_ping_result(client, mocked_deps):
    mocked_deps["redis_client"].ping.return_value = False

    resp = client.get("/health")

    assert resp.json()["redis"] is False


def test_create_job_with_prompt(client, mocked_deps):
    resp = client.post(
        "/jobs", json={"type": "adHoc", "prompt": "write hello world", "repo": VALID_REPO}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "queued"
    job_id = body["job_id"]
    assert str(uuid.UUID(job_id)) == job_id

    sql, params = mocked_deps["cursor"].execute.call_args.args
    assert "INSERT INTO jobs" in sql
    assert "VALUES (%s, %s, %s, %s, %s, %s, %s, 'queued')" in sql
    assert params == (job_id, "write hello world", None, VALID_REPO, None, None, "adHoc")
    mocked_deps["conn"].commit.assert_called_once_with()
    mocked_deps["enqueue_job"].assert_called_once_with(job_id)


def test_create_job_with_issue_number(client, mocked_deps):
    resp = client.post(
        "/jobs", json={"type": "issueResolver", "issueNumber": 42, "repo": VALID_REPO}
    )

    assert resp.status_code == 200
    body = resp.json()
    job_id = body["job_id"]
    assert str(uuid.UUID(job_id)) == job_id

    sql, params = mocked_deps["cursor"].execute.call_args.args
    assert "INSERT INTO jobs" in sql
    assert params == (job_id, None, 42, VALID_REPO, None, None, "issueResolver")
    mocked_deps["conn"].commit.assert_called_once_with()
    mocked_deps["enqueue_job"].assert_called_once_with(job_id)


def test_create_job_with_issue_architect(client, mocked_deps):
    resp = client.post(
        "/jobs", json={"type": "issueArchitect", "issueNumber": 42, "repo": VALID_REPO}
    )

    assert resp.status_code == 200
    body = resp.json()
    job_id = body["job_id"]
    assert str(uuid.UUID(job_id)) == job_id

    sql, params = mocked_deps["cursor"].execute.call_args.args
    assert "INSERT INTO jobs" in sql
    assert params == (job_id, None, 42, VALID_REPO, None, None, "issueArchitect")
    mocked_deps["conn"].commit.assert_called_once_with()
    mocked_deps["enqueue_job"].assert_called_once_with(job_id)


def test_create_job_with_model(client, mocked_deps):
    resp = client.post(
        "/jobs",
        json={
            "type": "adHoc",
            "prompt": "write hello world",
            "repo": VALID_REPO,
            "model": "deepseek/deepseek-v4-pro",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "queued"
    job_id = body["job_id"]

    sql, params = mocked_deps["cursor"].execute.call_args.args
    assert "INSERT INTO jobs" in sql
    assert params == (job_id, "write hello world", None, VALID_REPO, "deepseek/deepseek-v4-pro", None, "adHoc")
    mocked_deps["conn"].commit.assert_called_once_with()
    mocked_deps["enqueue_job"].assert_called_once_with(job_id)


def test_create_job_with_branch(client, mocked_deps):
    resp = client.post(
        "/jobs",
        json={
            "type": "adHoc",
            "prompt": "write hello world",
            "repo": VALID_REPO,
            "branch": "develop",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "queued"
    job_id = body["job_id"]

    sql, params = mocked_deps["cursor"].execute.call_args.args
    assert "INSERT INTO jobs" in sql
    assert params == (job_id, "write hello world", None, VALID_REPO, None, "develop", "adHoc")
    mocked_deps["conn"].commit.assert_called_once_with()
    mocked_deps["enqueue_job"].assert_called_once_with(job_id)


def test_create_job_rejects_missing_repo(client, mocked_deps):
    resp = client.post("/jobs", json={"type": "adHoc", "prompt": "write hello world"})

    assert resp.status_code == 400
    mocked_deps["cursor"].execute.assert_not_called()
    mocked_deps["enqueue_job"].assert_not_called()


def test_create_job_rejects_invalid_repo(client, mocked_deps):
    resp = client.post(
        "/jobs", json={"type": "adHoc", "prompt": "write hello world", "repo": "not-a-repo"}
    )

    assert resp.status_code == 400
    mocked_deps["cursor"].execute.assert_not_called()
    mocked_deps["enqueue_job"].assert_not_called()


def test_create_job_rejects_invalid_model(client, mocked_deps):
    for model in ["", "no-slash", "provider/", "/model", "provider/model/extra", "provider/model name"]:
        resp = client.post(
            "/jobs",
            json={"type": "adHoc", "prompt": "write hello world", "repo": VALID_REPO, "model": model},
        )

        assert resp.status_code == 400
        mocked_deps["cursor"].execute.assert_not_called()
        mocked_deps["enqueue_job"].assert_not_called()


def test_create_job_rejects_invalid_branch(client, mocked_deps):
    for branch in ["", "with space", "../evil", "branch name", "-leading"]:
        resp = client.post(
            "/jobs",
            json={"type": "adHoc", "prompt": "write hello world", "repo": VALID_REPO, "branch": branch},
        )

        assert resp.status_code == 400
        mocked_deps["cursor"].execute.assert_not_called()
        mocked_deps["enqueue_job"].assert_not_called()


def test_create_job_rejects_missing_type(client, mocked_deps):
    resp = client.post("/jobs", json={"prompt": "write hello world", "repo": VALID_REPO})

    assert resp.status_code == 400
    assert "type" in str(resp.json()["detail"])
    mocked_deps["cursor"].execute.assert_not_called()
    mocked_deps["enqueue_job"].assert_not_called()


def test_create_job_rejects_type_without_its_required_field(client, mocked_deps):
    for payload in [
        {"type": "adHoc", "repo": VALID_REPO},
        {"type": "issueResolver", "repo": VALID_REPO},
        {"type": "issueArchitect", "repo": VALID_REPO},
    ]:
        resp = client.post("/jobs", json=payload)

        assert resp.status_code == 400
        mocked_deps["cursor"].execute.assert_not_called()
        mocked_deps["enqueue_job"].assert_not_called()


def test_create_job_rejects_both_prompt_and_issue(client, mocked_deps):
    resp = client.post(
        "/jobs", json={"type": "adHoc", "prompt": "hi", "issueNumber": 1, "repo": VALID_REPO}
    )

    assert resp.status_code == 400
    assert "adHoc job must not have an 'issueNumber'" in str(resp.json()["detail"])
    mocked_deps["enqueue_job"].assert_not_called()


def test_create_job_rejects_non_positive_issue_number(client, mocked_deps):
    resp = client.post(
        "/jobs", json={"type": "issueResolver", "issueNumber": 0, "repo": VALID_REPO}
    )

    assert resp.status_code == 400
    mocked_deps["enqueue_job"].assert_not_called()


def test_get_job_returns_row(client, mocked_deps):
    mocked_deps["cursor"].fetchone.return_value = (
        "abc-123",
        "write hello world",
        "queued",
        "/artifacts/20260811180005-abc-123",
        None,
        None,
        42,
        VALID_REPO,
        "deepseek/deepseek-v4-pro",
        "develop",
        "issueArchitect",
    )

    resp = client.get("/jobs/abc-123")

    assert resp.status_code == 200
    assert resp.json() == {
        "id": "abc-123",
        "prompt": "write hello world",
        "status": "queued",
        "artifact_path": "/artifacts/20260811180005-abc-123",
        "error": None,
        "pr_number": None,
        "issue_number": 42,
        "repo": VALID_REPO,
        "model": "deepseek/deepseek-v4-pro",
        "branch": "develop",
        "type": "issueArchitect",
    }
    sql, params = mocked_deps["cursor"].execute.call_args.args
    assert "SELECT" in sql
    assert "FROM jobs" in sql
    assert "WHERE id = %s" in sql
    assert params == ("abc-123",)


def test_get_job_returns_error_when_missing(client, mocked_deps):
    resp = client.get("/jobs/missing")

    assert resp.status_code == 200
    assert resp.json() == {"error": "not found"}
    sql, params = mocked_deps["cursor"].execute.call_args.args
    assert params == ("missing",)
