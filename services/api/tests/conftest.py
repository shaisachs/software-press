import os
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest
from fastapi.testclient import TestClient

from app import main


class FakeCursor:
    def __init__(self, fetchone_result=None):
        self.execute_calls = []
        self.fetchone_result = fetchone_result
        self.committed = False
        self.closed = False

    def execute(self, sql, params=None):
        self.execute_calls.append((sql, params))

    def fetchone(self):
        return self.fetchone_result

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


class FakeConn:
    def __init__(self, cursor=None):
        self._cursor = cursor or FakeCursor()
        self.closed = False
        self.commits = 0

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture(autouse=True)
def mocked_deps(monkeypatch):
    conn = FakeConn()
    monkeypatch.setattr(main, "get_conn", lambda: conn)

    redis_client = mock.Mock()
    redis_client.ping.return_value = True
    monkeypatch.setattr(main, "redis_client", redis_client)

    enqueue_job = mock.Mock()
    monkeypatch.setattr(main, "enqueue_job", enqueue_job)

    return {
        "conn": conn,
        "redis_client": redis_client,
        "enqueue_job": enqueue_job,
    }
