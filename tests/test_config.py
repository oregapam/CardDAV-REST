import pytest

from app.config import Settings, load_settings

REQUIRED = {
    "BAIKAL_URL": "http://baikal/dav.php",
    "BAIKAL_USER": "testuser",
    "BAIKAL_PASS": "testpass",
    "API_KEY": "test-key",
}


def _set_env(monkeypatch, overrides=None, remove=()):
    env = {**REQUIRED, **(overrides or {})}
    for key in remove:
        env.pop(key, None)
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)


def test_load_settings_reads_env(monkeypatch):
    _set_env(monkeypatch)
    s = load_settings()
    assert s.baikal_url == "http://baikal/dav.php"
    assert s.baikal_user == "testuser"
    assert s.baikal_pass == "testpass"
    assert s.api_key == "test-key"


def test_missing_required_var_fails_fast(monkeypatch):
    _set_env(monkeypatch, remove=("BAIKAL_PASS",))
    with pytest.raises(RuntimeError, match="BAIKAL_PASS"):
        load_settings()


def test_principal_url_handles_trailing_slash(monkeypatch):
    _set_env(monkeypatch, overrides={"BAIKAL_URL": "http://baikal/dav.php/"})
    s = load_settings()
    assert s.principal_url == "http://baikal/dav.php/addressbooks/testuser/"


def test_settings_dataclass_direct():
    s = Settings(
        baikal_url="http://baikal/dav.php",
        baikal_user="u",
        baikal_pass="p",
        api_key="k",
    )
    assert s.principal_url == "http://baikal/dav.php/addressbooks/u/"
