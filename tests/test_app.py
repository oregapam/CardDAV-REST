def test_health_is_open(anon_client):
    resp = anon_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_missing_api_key_rejected(anon_client):
    resp = anon_client.post("/api/contacts/search", json={"email": "x@y.hu"})
    assert resp.status_code == 401


def test_wrong_api_key_rejected(anon_client):
    resp = anon_client.post(
        "/api/contacts/search",
        json={"email": "x@y.hu"},
        headers={"X-API-Key": "wrong"},
    )
    assert resp.status_code == 401
