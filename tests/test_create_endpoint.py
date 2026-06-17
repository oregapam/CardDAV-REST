import re

import httpx
import respx

from tests.conftest import BASE
from tests.test_carddav_xml import MULTISTATUS_EMPTY, MULTISTATUS_ONE

VCF_URL = re.compile(re.escape(BASE) + r"[0-9a-f-]+\.vcf")


@respx.mock
def test_create_contact(client):
    route = respx.put(url__regex=VCF_URL.pattern).mock(return_value=httpx.Response(201))
    resp = client.post(
        "/api/addressbooks/default/contacts",
        json={
            "firstname": "Anna",
            "lastname": "Kis",
            "emails": [{"type": "work", "value": "anna@ceg.hu"}],
            "phones": [{"type": "cell", "value": "+36301111111"}],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "success"
    assert body["filename"] == body["uid"] + ".vcf"
    req = route.calls.last.request
    assert req.headers["If-None-Match"] == "*"
    sent = req.content.decode("utf-8")
    assert "FN:Anna Kis" in sent
    assert f"UID:{body['uid']}" in sent
    assert "VERSION:3.0" in sent


@respx.mock
def test_create_contact_normalizes_phone(client):
    route = respx.put(url__regex=VCF_URL.pattern).mock(return_value=httpx.Response(201))
    resp = client.post(
        "/api/addressbooks/default/contacts",
        json={
            "firstname": "Anna",
            "lastname": "Kis",
            "phones": [{"type": "mobile", "value": "06301234567"}],
        },
    )
    assert resp.status_code == 201
    sent = route.calls.last.request.content.decode("utf-8")
    assert "+36301234567" in sent


def test_create_contact_invalid_phone_is_422(client):
    resp = client.post(
        "/api/addressbooks/default/contacts",
        json={
            "firstname": "Anna",
            "lastname": "Kis",
            "phones": [{"type": "mobile", "value": "123"}],
        },
    )
    assert resp.status_code == 422
    assert "Invalid phone number" in resp.json()["detail"]


def test_create_contact_missing_required_field_is_422(client_with_env):
    with client_with_env({"REQUIRED_FIELDS": "emails"}) as c:
        c.headers["X-API-Key"] = "test-key"
        resp = c.post(
            "/api/addressbooks/default/contacts",
            json={"firstname": "Anna", "lastname": "Kis"},
        )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Missing required field(s): emails"


@respx.mock
def test_create_contact_with_required_field_present_succeeds(client_with_env):
    with client_with_env({"REQUIRED_FIELDS": "emails"}) as c:
        c.headers["X-API-Key"] = "test-key"
        route = respx.put(url__regex=VCF_URL.pattern).mock(return_value=httpx.Response(201))
        resp = c.post(
            "/api/addressbooks/default/contacts",
            json={
                "firstname": "Anna",
                "lastname": "Kis",
                "emails": [{"type": "work", "value": "anna@ceg.hu"}],
            },
        )
        assert route.called
    assert resp.status_code == 201


def test_create_contact_invalid_phone_reported_before_missing_field(client_with_env):
    with client_with_env({"REQUIRED_FIELDS": "emails"}) as c:
        c.headers["X-API-Key"] = "test-key"
        resp = c.post(
            "/api/addressbooks/default/contacts",
            json={
                "firstname": "Anna",
                "lastname": "Kis",
                "phones": [{"type": "mobile", "value": "123"}],
            },
        )
    assert resp.status_code == 422
    assert "Invalid phone number" in resp.json()["detail"]


def test_create_without_name_is_422(client):
    resp = client.post(
        "/api/addressbooks/default/contacts", json={"emails": [{"value": "a@b.hu"}]}
    )
    assert resp.status_code == 422


@respx.mock
def test_create_with_duplicate_check_conflict(client):
    respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_ONE)
    )
    resp = client.post(
        "/api/addressbooks/default/contacts",
        json={
            "firstname": "Teszt",
            "lastname": "János",
            "check_duplicates": True,
            "emails": [{"type": "home", "value": "teszt@email.hu"}],
        },
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["existing_uid"] == "abc-123"


@respx.mock
def test_create_with_duplicate_check_no_match_creates(client):
    respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_EMPTY)
    )
    respx.put(url__regex=VCF_URL.pattern).mock(return_value=httpx.Response(201))
    resp = client.post(
        "/api/addressbooks/default/contacts",
        json={
            "firstname": "Anna",
            "lastname": "Kis",
            "check_duplicates": True,
            "emails": [{"type": "work", "value": "uj@ceg.hu"}],
        },
    )
    assert resp.status_code == 201


@respx.mock
def test_create_with_duplicate_check_phone_conflict(client):
    respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_ONE)
    )
    resp = client.post(
        "/api/addressbooks/default/contacts",
        json={
            "firstname": "Teszt",
            "lastname": "János",
            "check_duplicates": True,
            "phones": [{"type": "cell", "value": "+36301234567"}],
        },
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["matched_phone"] == "+36301234567"
    assert resp.json()["detail"]["existing_uid"] == "abc-123"


@respx.mock
def test_create_with_duplicate_check_phone_no_match_creates(client):
    respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_EMPTY)
    )
    respx.put(url__regex=VCF_URL.pattern).mock(return_value=httpx.Response(201))
    resp = client.post(
        "/api/addressbooks/default/contacts",
        json={
            "firstname": "Anna",
            "lastname": "Kis",
            "check_duplicates": True,
            "phones": [{"type": "home", "value": "+36201112222"}],
        },
    )
    assert resp.status_code == 201


@respx.mock
def test_create_uid_collision_is_409(client):
    respx.put(url__regex=VCF_URL.pattern).mock(return_value=httpx.Response(412))
    resp = client.post(
        "/api/addressbooks/default/contacts", json={"firstname": "Anna", "lastname": "Kis"}
    )
    assert resp.status_code == 409
