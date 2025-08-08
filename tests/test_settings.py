import os
from importlib import reload


def test_settings_env(monkeypatch):
    monkeypatch.setenv("ACC_MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("ACC_MINIO_ACCESS_KEY", "key")
    monkeypatch.setenv("ACC_MINIO_SECRET_KEY", "secret")
    monkeypatch.setenv("ACC_MINIO_SECURE", "true")
    monkeypatch.setenv("ACC_DB_URL", "sqlite:///:memory:")
    from accscore import settings as settings_module

    reload(settings_module)
    s = settings_module.Settings()
    assert s.minio_endpoint == "localhost:9000"
    assert s.postgres_dsn.startswith("sqlite")
    assert s.minio_secure is True
