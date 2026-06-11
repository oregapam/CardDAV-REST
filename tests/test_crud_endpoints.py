import httpx
import respx

from tests.conftest import BASE

EXISTING_VCF = (
    "BEGIN:VCARD\r\n"
    "VERSION:3.0\r\n"
    "UID:abc-123\r\n"
    "FN:Anna Kis\r\n"
    "N:Kis;Anna;;;\r\n"
    "EMAIL;TYPE=WORK:anna@ceg.hu\r\n"
    "X-CUSTOM:keep-me\r\n"
    "END:VCARD\r\n"
)


@respx.mock
def test_get_contact(client):
    respx.get(BASE + "abc-123.vcf").mock(
        return_value=httpx.Response(200, text=EXISTING_VCF, headers={"ETag": '"v1"'})
    )
    resp = client.get("/api/contacts/abc-123")
    assert resp.status_code == 200
    body = resp.json()
    assert body["uid"] == "abc-123"
    assert body["fn"] == "Anna Kis"
    assert body["firstname"] == "Anna"
    assert body["etag"] == '"v1"'
    assert body["emails"] == [{"type": "work", "value": "anna@ceg.hu"}]


@respx.mock
def test_get_missing_contact_is_404(client):
    respx.get(BASE + "nincs.vcf").mock(return_value=httpx.Response(404))
    assert client.get("/api/contacts/nincs").status_code == 404


@respx.mock
def test_update_contact_merges_and_sends_if_match(client):
    respx.get(BASE + "abc-123.vcf").mock(
        return_value=httpx.Response(200, text=EXISTING_VCF, headers={"ETag": '"v1"'})
    )
    put_route = respx.put(BASE + "abc-123.vcf").mock(return_value=httpx.Response(204))
    resp = client.put(
        "/api/contacts/abc-123",
        json={"firstname": "Anna", "lastname": "Nagy"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "updated", "uid": "abc-123"}
    req = put_route.calls.last.request
    assert req.headers["If-Match"] == '"v1"'
    sent = req.content.decode("utf-8")
    assert "FN:Anna Nagy" in sent
    assert "X-CUSTOM:keep-me" in sent
    assert "UID:abc-123" in sent


@respx.mock
def test_update_conflict_is_409(client):
    respx.get(BASE + "abc-123.vcf").mock(
        return_value=httpx.Response(200, text=EXISTING_VCF, headers={"ETag": '"v1"'})
    )
    respx.put(BASE + "abc-123.vcf").mock(return_value=httpx.Response(412))
    resp = client.put("/api/contacts/abc-123", json={"firstname": "Anna", "lastname": "Nagy"})
    assert resp.status_code == 409


@respx.mock
def test_update_missing_contact_is_404(client):
    respx.get(BASE + "nincs.vcf").mock(return_value=httpx.Response(404))
    resp = client.put("/api/contacts/nincs", json={"firstname": "Anna"})
    assert resp.status_code == 404


@respx.mock
def test_delete_contact(client):
    respx.delete(BASE + "abc-123.vcf").mock(return_value=httpx.Response(204))
    resp = client.delete("/api/contacts/abc-123")
    assert resp.status_code == 200
    assert resp.json() == {"status": "deleted", "uid": "abc-123"}


@respx.mock
def test_delete_missing_contact_is_404(client):
    respx.delete(BASE + "nincs.vcf").mock(return_value=httpx.Response(404))
    assert client.delete("/api/contacts/nincs").status_code == 404
