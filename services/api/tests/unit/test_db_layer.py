import psycopg2

from app import db_layer


def test_get_conn_uses_defaults(monkeypatch, mocker):
    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    monkeypatch.delenv("POSTGRES_DB", raising=False)
    monkeypatch.delenv("POSTGRES_USER", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    fake_connect = mocker.patch.object(psycopg2, "connect")

    db_layer.get_conn()

    fake_connect.assert_called_once_with(
        host="postgres",
        dbname="software_press",
        user="sp_user",
        password="sp_password",
    )


def test_get_conn_uses_env_vars(monkeypatch, mocker):
    monkeypatch.setenv("POSTGRES_HOST", "dbhost")
    monkeypatch.setenv("POSTGRES_DB", "mydb")
    monkeypatch.setenv("POSTGRES_USER", "myuser")
    monkeypatch.setenv("POSTGRES_PASSWORD", "mypass")
    fake_connect = mocker.patch.object(psycopg2, "connect")

    db_layer.get_conn()

    fake_connect.assert_called_once_with(
        host="dbhost",
        dbname="mydb",
        user="myuser",
        password="mypass",
    )
