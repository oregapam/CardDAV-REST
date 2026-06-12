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


MULTISTATUS_TWO = (
    '<?xml version="1.0"?>'
    '<d:multistatus xmlns:d="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav">'
    "<d:response>"
    "<d:href>/dav.php/addressbooks/testuser/default/abc-123.vcf</d:href>"
    "<d:propstat><d:prop>"
    "<d:getetag>\"v1\"</d:getetag>"
    "<card:address-data>"
    "BEGIN:VCARD\r\nVERSION:3.0\r\nUID:abc-123\r\nFN:Anna Kis\r\nN:Kis;Anna;;;\r\nEND:VCARD\r\n"
    "</card:address-data>"
    "</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>"
    "</d:response>"
    "<d:response>"
    "<d:href>/dav.php/addressbooks/testuser/default/def-456.vcf</d:href>"
    "<d:propstat><d:prop>"
    "<d:getetag>\"v2\"</d:getetag>"
    "<card:address-data>"
    "BEGIN:VCARD\r\nVERSION:3.0\r\nUID:def-456\r\nFN:Béla Nagy\r\nN:Nagy;Béla;;;\r\nEND:VCARD\r\n"
    "</card:address-data>"
    "</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>"
    "</d:response>"
    "</d:multistatus>"
)


@respx.mock
def test_list_all_contacts_returns_all(client):
    respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_TWO)
    )
    resp = client.get("/api/contacts")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    uids = {c["uid"] for c in body}
    assert uids == {"abc-123", "def-456"}


@respx.mock
def test_list_all_contacts_empty(client):
    empty = (
        '<?xml version="1.0"?>'
        '<d:multistatus xmlns:d="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav"/>'
    )
    respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=empty)
    )
    resp = client.get("/api/contacts")
    assert resp.status_code == 200
    assert resp.json() == []


@respx.mock
def test_get_contact_vcard_returns_raw_vcf(client):
    respx.get(BASE + "abc-123.vcf").mock(
        return_value=httpx.Response(200, text=EXISTING_VCF, headers={"ETag": '"v1"'})
    )
    resp = client.get("/api/contacts/abc-123/vcard")
    assert resp.status_code == 200
    assert "text/vcard" in resp.headers["content-type"]
    assert resp.text == EXISTING_VCF
    assert resp.headers["etag"] == '"v1"'
    assert resp.headers["content-disposition"] == 'attachment; filename="abc-123.vcf"'


@respx.mock
def test_get_contact_vcard_missing_is_404(client):
    respx.get(BASE + "nincs.vcf").mock(return_value=httpx.Response(404))
    assert client.get("/api/contacts/nincs/vcard").status_code == 404


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
