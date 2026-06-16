import pytest
from fastapi.testclient import TestClient

TEST_ENV = {
    "BAIKAL_URL": "http://baikal/dav.php",
    "BAIKAL_USER": "testuser",
    "BAIKAL_PASS": "testpass",
    "API_KEY": "test-key",
    "NAME_FORMAT": "western",
}

PRINCIPAL = "http://baikal/dav.php/addressbooks/testuser/"
BOOK = "default"
BASE = PRINCIPAL + BOOK + "/"  # http://baikal/dav.php/addressbooks/testuser/default/


def _make_client(monkeypatch) -> TestClient:
    for key, value in TEST_ENV.items():
        monkeypatch.setenv(key, value)
    from app.main import create_app

    return TestClient(create_app())


@pytest.fixture
def anon_client(monkeypatch):
    with _make_client(monkeypatch) as c:
        yield c


@pytest.fixture
def client(monkeypatch):
    with _make_client(monkeypatch) as c:
        c.headers["X-API-Key"] = "test-key"
        yield c


@pytest.fixture
def client_with_env(monkeypatch):
    def _make(extra_env: dict) -> TestClient:
        env = {**TEST_ENV, **extra_env}
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        from app.main import create_app

        return TestClient(create_app())

    return _make
