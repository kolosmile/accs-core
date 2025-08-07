from importlib import reload


def test_check_connection(monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "key")
    monkeypatch.setenv("MINIO_SECRET_KEY", "secret")
    monkeypatch.setenv("POSTGRES_DSN", "sqlite:///:memory:")
    from accscore import db

    reload(db)
    assert db.check_connection() is True
