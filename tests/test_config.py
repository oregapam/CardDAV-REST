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
    monkeypatch.delenv("BAIKAL_ADDRESSBOOK", raising=False)


def test_load_settings_reads_env(monkeypatch):
    _set_env(monkeypatch)
    s = load_settings()
    assert s.baikal_url == "http://baikal/dav.php"
    assert s.baikal_user == "testuser"
    assert s.baikal_pass == "testpass"
    assert s.api_key == "test-key"
    assert s.baikal_addressbook == "default"


def test_addressbook_default_overridable(monkeypatch):
    _set_env(monkeypatch)
    monkeypatch.setenv("BAIKAL_ADDRESSBOOK", "munka")
    assert load_settings().baikal_addressbook == "munka"


def test_missing_required_var_fails_fast(monkeypatch):
    _set_env(monkeypatch, remove=("BAIKAL_PASS",))
    with pytest.raises(RuntimeError, match="BAIKAL_PASS"):
        load_settings()


def test_addressbook_url_handles_trailing_slash(monkeypatch):
    _set_env(monkeypatch, overrides={"BAIKAL_URL": "http://baikal/dav.php/"})
    s = load_settings()
    assert s.addressbook_url == "http://baikal/dav.php/addressbooks/testuser/default/"


def test_settings_dataclass_direct():
    s = Settings(
        baikal_url="http://baikal/dav.php",
        baikal_user="u",
        baikal_pass="p",
        baikal_addressbook="ab",
        api_key="k",
    )
    assert s.addressbook_url == "http://baikal/dav.php/addressbooks/u/ab/"
