import pytest
from fastapi.testclient import TestClient

TEST_ENV = {
    "BAIKAL_URL": "http://baikal/dav.php",
    "BAIKAL_USER": "testuser",
    "BAIKAL_PASS": "testpass",
    "BAIKAL_ADDRESSBOOK": "default",
    "API_KEY": "test-key",
}

BASE = "http://baikal/dav.php/addressbooks/testuser/default/"


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
