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


def test_default_region_defaults_to_hu(monkeypatch):
    _set_env(monkeypatch)
    s = load_settings()
    assert s.default_region == "HU"


def test_default_region_reads_env_override(monkeypatch):
    _set_env(monkeypatch, overrides={"DEFAULT_COUNTRY_CODE": "DE"})
    s = load_settings()
    assert s.default_region == "DE"


def test_required_fields_defaults_to_empty(monkeypatch):
    _set_env(monkeypatch)
    s = load_settings()
    assert s.required_fields == ()


def test_required_fields_parses_comma_separated(monkeypatch):
    _set_env(monkeypatch, overrides={"REQUIRED_FIELDS": "emails,phones"})
    s = load_settings()
    assert s.required_fields == ("emails", "phones")


def test_required_fields_strips_whitespace_and_trailing_comma(monkeypatch):
    _set_env(monkeypatch, overrides={"REQUIRED_FIELDS": " emails , phones, "})
    s = load_settings()
    assert s.required_fields == ("emails", "phones")


def test_required_fields_rejects_unknown_field_name(monkeypatch):
    _set_env(monkeypatch, overrides={"REQUIRED_FIELDS": "email"})
    with pytest.raises(RuntimeError, match="email"):
        load_settings()


def test_settings_dataclass_direct():
    s = Settings(
        baikal_url="http://baikal/dav.php",
        baikal_user="u",
        baikal_pass="p",
        api_key="k",
    )
    assert s.principal_url == "http://baikal/dav.php/addressbooks/u/"
