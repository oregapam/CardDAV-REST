import httpx
import respx

from tests.conftest import BASE, PRINCIPAL
from tests.test_carddav_xml import PROPFIND_ADDRESSBOOKS, STAT_PROPFIND_EMPTY, STAT_PROPFIND_EMPTY_LEADS, STAT_PROPFIND_TWO

LEADS_URL = PRINCIPAL + "leads/"

PROPFIND_ONE_BOOK = (
    '<?xml version="1.0"?>'
    '<d:multistatus xmlns:d="DAV:">'
    '<d:response>'
    '<d:href>/dav.php/addressbooks/testuser/</d:href>'
    '<d:propstat><d:prop><d:displayname>testuser</d:displayname></d:prop>'
    '<d:status>HTTP/1.1 200 OK</d:status></d:propstat>'
    '</d:response>'
    '<d:response>'
    '<d:href>/dav.php/addressbooks/testuser/default/</d:href>'
    '<d:propstat><d:prop><d:displayname>Default</d:displayname></d:prop>'
    '<d:status>HTTP/1.1 200 OK</d:status></d:propstat>'
    '</d:response>'
    '</d:multistatus>'
)


@respx.mock
def test_stats_success(client):
    respx.route(method="PROPFIND", url=PRINCIPAL).mock(
        return_value=httpx.Response(207, text=PROPFIND_ONE_BOOK)
    )
    respx.route(method="PROPFIND", url=BASE).mock(
        return_value=httpx.Response(207, text=STAT_PROPFIND_TWO)
    )
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_contacts"] == 2
    assert body["total_size_bytes"] == 768
    assert len(body["addressbooks"]) == 1
    book = body["addressbooks"][0]
    assert book["name"] == "default"
    assert book["contact_count"] == 2
    assert book["last_modified"].startswith("2026-06-17")
    assert book["oldest_modified"].startswith("2024-01-15")
    assert book["total_size_bytes"] == 768


@respx.mock
def test_stats_two_books_aggregates_total(client):
    respx.route(method="PROPFIND", url=PRINCIPAL).mock(
        return_value=httpx.Response(207, text=PROPFIND_ADDRESSBOOKS)
    )
    respx.route(method="PROPFIND", url=BASE).mock(
        return_value=httpx.Response(207, text=STAT_PROPFIND_TWO)
    )
    respx.route(method="PROPFIND", url=LEADS_URL).mock(
        return_value=httpx.Response(207, text=STAT_PROPFIND_EMPTY_LEADS)
    )
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_contacts"] == 2
    assert len(body["addressbooks"]) == 2


@respx.mock
def test_stats_empty_book(client):
    respx.route(method="PROPFIND", url=PRINCIPAL).mock(
        return_value=httpx.Response(207, text=PROPFIND_ONE_BOOK)
    )
    respx.route(method="PROPFIND", url=BASE).mock(
        return_value=httpx.Response(207, text=STAT_PROPFIND_EMPTY)
    )
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_contacts"] == 0
    book = body["addressbooks"][0]
    assert book["contact_count"] == 0
    assert book["last_modified"] is None
    assert book["oldest_modified"] is None
    assert book["total_size_bytes"] == 0


@respx.mock
def test_stats_upstream_error_is_502(client):
    respx.route(method="PROPFIND", url=PRINCIPAL).mock(
        side_effect=httpx.ConnectError("boom")
    )
    resp = client.get("/api/stats")
    assert resp.status_code == 502
