import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture(autouse=True)
def mocked_deps(monkeypatch, mocker):
    conn = mocker.Mock()
    conn.closed = False
    cursor = mocker.Mock()
    cursor.fetchone.return_value = None
    conn.cursor.return_value = cursor

    monkeypatch.setattr(main, "get_conn", lambda: conn)

    redis_client = mocker.Mock()
    redis_client.ping.return_value = True
    monkeypatch.setattr(main, "redis_client", redis_client)

    enqueue_job = mocker.Mock()
    monkeypatch.setattr(main, "enqueue_job", enqueue_job)

    return {
        "conn": conn,
        "cursor": cursor,
        "redis_client": redis_client,
        "enqueue_job": enqueue_job,
    }
