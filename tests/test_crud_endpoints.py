import httpx
import respx

from tests.conftest import BASE, PRINCIPAL

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

PROPFIND_TWO_BOOKS = (
    '<?xml version="1.0"?>'
    '<d:multistatus xmlns:d="DAV:">'
    "<d:response>"
    "<d:href>/dav.php/addressbooks/testuser/</d:href>"
    "<d:propstat><d:prop><d:displayname>testuser</d:displayname></d:prop>"
    "<d:status>HTTP/1.1 200 OK</d:status></d:propstat>"
    "</d:response>"
    "<d:response>"
    "<d:href>/dav.php/addressbooks/testuser/default/</d:href>"
    "<d:propstat><d:prop><d:displayname>Default</d:displayname></d:prop>"
    "<d:status>HTTP/1.1 200 OK</d:status></d:propstat>"
    "</d:response>"
    "<d:response>"
    "<d:href>/dav.php/addressbooks/testuser/leads/</d:href>"
    "<d:propstat><d:prop><d:displayname>Leads</d:displayname></d:prop>"
    "<d:status>HTTP/1.1 200 OK</d:status></d:propstat>"
    "</d:response>"
    "</d:multistatus>"
)


@respx.mock
def test_list_addressbooks(client):
    respx.route(method="PROPFIND", url=PRINCIPAL).mock(
        return_value=httpx.Response(207, text=PROPFIND_TWO_BOOKS)
    )
    resp = client.get("/api/addressbooks")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert {"name": "default", "displayname": "Default"} in body
    assert {"name": "leads", "displayname": "Leads"} in body


@respx.mock
def test_list_all_contacts_returns_all(client):
    respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_TWO)
    )
    resp = client.get("/api/addressbooks/default/contacts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["limit"] == 50
    assert body["offset"] == 0
    uids = {c["uid"] for c in body["items"]}
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
    resp = client.get("/api/addressbooks/default/contacts")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"total": 0, "limit": 50, "offset": 0, "items": [], "warning": None}


@respx.mock
def test_list_contacts_pagination_limit(client):
    respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_TWO)
    )
    resp = client.get("/api/addressbooks/default/contacts?limit=1&offset=0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["limit"] == 1
    assert len(body["items"]) == 1


@respx.mock
def test_list_contacts_pagination_offset(client):
    respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_TWO)
    )
    resp = client.get("/api/addressbooks/default/contacts?limit=1&offset=1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1
    assert body["items"][0]["uid"] == "def-456"


@respx.mock
def test_list_contacts_offset_beyond_total_returns_warning(client):
    respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_TWO)
    )
    resp = client.get("/api/addressbooks/default/contacts?offset=100")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["items"] == []
    assert body["warning"] == "offset (100) exceeds total (2)"


@respx.mock
def test_list_contacts_no_warning_when_offset_in_range(client):
    respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_TWO)
    )
    resp = client.get("/api/addressbooks/default/contacts?offset=0")
    assert resp.json()["warning"] is None


@respx.mock
def test_list_contacts_q_uses_report(client):
    respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_TWO)
    )
    resp = client.get("/api/addressbooks/default/contacts?q=anna")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["warning"] is None


@respx.mock
def test_list_contacts_q_body_contains_anyof_contains(client):
    route = respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_TWO)
    )
    client.get("/api/addressbooks/default/contacts?q=anna")
    xml = route.calls.last.request.content.decode("utf-8")
    assert 'test="anyof"' in xml
    assert 'match-type="contains"' in xml
    assert "anna" in xml


@respx.mock
def test_get_contact_vcard_returns_raw_vcf(client):
    respx.get(BASE + "abc-123.vcf").mock(
        return_value=httpx.Response(200, text=EXISTING_VCF, headers={"ETag": '"v1"'})
    )
    resp = client.get("/api/addressbooks/default/contacts/abc-123/vcard")
    assert resp.status_code == 200
    assert "text/vcard" in resp.headers["content-type"]
    assert resp.text == EXISTING_VCF
    assert resp.headers["etag"] == '"v1"'
    assert resp.headers["content-disposition"] == 'attachment; filename="abc-123.vcf"'


@respx.mock
def test_get_contact_vcard_missing_is_404(client):
    respx.get(BASE + "nincs.vcf").mock(return_value=httpx.Response(404))
    assert client.get("/api/addressbooks/default/contacts/nincs/vcard").status_code == 404


@respx.mock
def test_get_contact(client):
    respx.get(BASE + "abc-123.vcf").mock(
        return_value=httpx.Response(200, text=EXISTING_VCF, headers={"ETag": '"v1"'})
    )
    resp = client.get("/api/addressbooks/default/contacts/abc-123")
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
    assert client.get("/api/addressbooks/default/contacts/nincs").status_code == 404


@respx.mock
def test_update_contact_merges_and_sends_if_match(client):
    respx.get(BASE + "abc-123.vcf").mock(
        return_value=httpx.Response(200, text=EXISTING_VCF, headers={"ETag": '"v1"'})
    )
    put_route = respx.put(BASE + "abc-123.vcf").mock(return_value=httpx.Response(204))
    resp = client.put(
        "/api/addressbooks/default/contacts/abc-123",
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
    resp = client.put(
        "/api/addressbooks/default/contacts/abc-123",
        json={"firstname": "Anna", "lastname": "Nagy"},
    )
    assert resp.status_code == 409


@respx.mock
def test_update_missing_contact_is_404(client):
    respx.get(BASE + "nincs.vcf").mock(return_value=httpx.Response(404))
    resp = client.put("/api/addressbooks/default/contacts/nincs", json={"firstname": "Anna"})
    assert resp.status_code == 404


@respx.mock
def test_move_contact(client):
    leads_base = "http://baikal/dav.php/addressbooks/testuser/leads/"
    respx.get(BASE + "abc-123.vcf").mock(
        return_value=httpx.Response(200, text=EXISTING_VCF, headers={"ETag": '"v1"'})
    )
    respx.put(leads_base + "abc-123.vcf").mock(return_value=httpx.Response(201))
    respx.delete(BASE + "abc-123.vcf").mock(return_value=httpx.Response(204))
    resp = client.post("/api/addressbooks/default/contacts/abc-123/move/leads")
    assert resp.status_code == 200
    assert resp.json() == {"status": "moved", "uid": "abc-123", "from": "default", "to": "leads"}


@respx.mock
def test_delete_contact(client):
    respx.delete(BASE + "abc-123.vcf").mock(return_value=httpx.Response(204))
    resp = client.delete("/api/addressbooks/default/contacts/abc-123")
    assert resp.status_code == 200
    assert resp.json() == {"status": "deleted", "uid": "abc-123"}


@respx.mock
def test_delete_missing_contact_is_404(client):
    respx.delete(BASE + "nincs.vcf").mock(return_value=httpx.Response(404))
    assert client.delete("/api/addressbooks/default/contacts/nincs").status_code == 404
