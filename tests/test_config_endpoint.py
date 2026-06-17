def test_config_default_values(client_with_env):
    with client_with_env({}) as c:
        c.headers["X-API-Key"] = "test-key"
        resp = c.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name_format"] == "western"
    assert body["default_region"] == "HU"
    assert body["required_fields"] == []


def test_config_with_required_fields(client_with_env):
    with client_with_env({"REQUIRED_FIELDS": "emails,phones"}) as c:
        c.headers["X-API-Key"] = "test-key"
        resp = c.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["required_fields"] == ["emails", "phones"]


def test_config_requires_auth(anon_client):
    resp = anon_client.get("/api/config")
    assert resp.status_code == 401
