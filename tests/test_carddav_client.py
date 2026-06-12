import httpx
import pytest
import respx

from app.carddav import (
    CardDAVClient,
    ConflictError,
    NotFoundError,
    UpstreamError,
)
from app.config import Settings
from tests.conftest import BASE, BOOK, PRINCIPAL
from tests.test_carddav_xml import MULTISTATUS_EMPTY, MULTISTATUS_ONE, PROPFIND_ADDRESSBOOKS

SETTINGS = Settings(
    baikal_url="http://baikal/dav.php",
    baikal_user="testuser",
    baikal_pass="testpass",
    api_key="test-key",
)


@pytest.fixture
async def dav():
    async with httpx.AsyncClient() as http:
        yield CardDAVClient(SETTINGS, http)


@respx.mock
async def test_search_returns_uid_vcf_pairs(dav):
    route = respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_ONE)
    )
    results = await dav.search(BOOK, email="teszt@email.hu")
    assert results[0][0] == "abc-123"
    req = route.calls.last.request
    assert req.headers["Depth"] == "1"
    assert b"addressbook-query" in req.content


@respx.mock
async def test_search_empty(dav):
    respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_EMPTY)
    )
    assert await dav.search(BOOK, name="Senki") == []


@respx.mock
async def test_list_addressbooks(dav):
    respx.route(method="PROPFIND", url=PRINCIPAL).mock(
        return_value=httpx.Response(207, text=PROPFIND_ADDRESSBOOKS)
    )
    results = await dav.list_addressbooks()
    assert len(results) == 2
    names = {r["name"] for r in results}
    assert names == {"default", "leads"}


@respx.mock
async def test_get_returns_vcf_and_etag(dav):
    respx.get(BASE + "abc.vcf").mock(
        return_value=httpx.Response(200, text="BEGIN:VCARD\r\nEND:VCARD\r\n", headers={"ETag": '"v1"'})
    )
    vcf, etag = await dav.get(BOOK, "abc")
    assert vcf.startswith("BEGIN:VCARD")
    assert etag == '"v1"'


@respx.mock
async def test_create_sends_if_none_match(dav):
    route = respx.put(BASE + "abc.vcf").mock(return_value=httpx.Response(201))
    await dav.create(BOOK, "abc", "BEGIN:VCARD\r\nEND:VCARD\r\n")
    req = route.calls.last.request
    assert req.headers["If-None-Match"] == "*"
    assert req.headers["Content-Type"].startswith("text/vcard")


@respx.mock
async def test_update_sends_if_match(dav):
    route = respx.put(BASE + "abc.vcf").mock(return_value=httpx.Response(204))
    await dav.update(BOOK, "abc", "BEGIN:VCARD\r\nEND:VCARD\r\n", etag='"v1"')
    assert route.calls.last.request.headers["If-Match"] == '"v1"'


@respx.mock
async def test_delete(dav):
    route = respx.delete(BASE + "abc.vcf").mock(return_value=httpx.Response(204))
    await dav.delete(BOOK, "abc")
    assert route.called


@respx.mock
async def test_404_maps_to_not_found(dav):
    respx.get(BASE + "nincs.vcf").mock(return_value=httpx.Response(404))
    with pytest.raises(NotFoundError):
        await dav.get(BOOK, "nincs")


@respx.mock
async def test_412_maps_to_conflict(dav):
    respx.put(BASE + "abc.vcf").mock(return_value=httpx.Response(412))
    with pytest.raises(ConflictError):
        await dav.update(BOOK, "abc", "BEGIN:VCARD\r\nEND:VCARD\r\n", etag='"old"')


@respx.mock
async def test_connect_error_maps_to_upstream(dav):
    respx.get(BASE + "abc.vcf").mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(UpstreamError):
        await dav.get(BOOK, "abc")


@respx.mock
async def test_auth_failure_maps_to_upstream_without_leaking(dav):
    respx.get(BASE + "abc.vcf").mock(return_value=httpx.Response(401))
    with pytest.raises(UpstreamError) as exc_info:
        await dav.get(BOOK, "abc")
    assert "testpass" not in str(exc_info.value)
