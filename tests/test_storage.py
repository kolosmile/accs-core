from importlib import reload


def test_ensure_bucket(monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "key")
    monkeypatch.setenv("MINIO_SECRET_KEY", "secret")
    monkeypatch.setenv("POSTGRES_DSN", "sqlite:///:memory:")
    from accscore import storage

    reload(storage)

    class DummyClient:
        def __init__(self):
            self.created = []

        def bucket_exists(self, name):
            return False

        def make_bucket(self, name):
            self.created.append(name)

    storage.client = DummyClient()
    storage.ensure_bucket("test")
    assert "test" in storage.client.created
