import httpx
import respx

from tests.conftest import BASE
from tests.test_carddav_xml import MULTISTATUS_EMPTY, MULTISTATUS_ONE


@respx.mock
def test_search_found(client):
    respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_ONE)
    )
    resp = client.post("/api/contacts/search", json={"email": "teszt@email.hu"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["exists"] is True
    assert body["match_count"] == 1
    match = body["matches"][0]
    assert match["uid"] == "abc-123"
    assert match["fn"] == "Teszt János"
    assert match["emails"] == [{"type": "home", "value": "teszt@email.hu"}]
    assert match["phones"] == [{"type": "cell", "value": "+36301234567"}]
    assert body["searched_params"] == {"email": "teszt@email.hu", "match_condition": "allof"}


@respx.mock
def test_search_not_found(client):
    respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_EMPTY)
    )
    resp = client.post(
        "/api/contacts/search",
        json={"name": "Senki", "phone": "+361", "match_condition": "anyof"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "exists": False,
        "match_count": 0,
        "matches": [],
        "searched_params": {"phone": "+361", "name": "Senki", "match_condition": "anyof"},
    }


def test_search_without_filters_is_422(client):
    resp = client.post("/api/contacts/search", json={})
    assert resp.status_code == 422


@respx.mock
def test_search_baikal_down_is_502(client):
    respx.route(method="REPORT", url=BASE).mock(side_effect=httpx.ConnectError("boom"))
    resp = client.post("/api/contacts/search", json={"email": "x@y.hu"})
    assert resp.status_code == 502
