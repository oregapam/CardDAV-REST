import httpx
import respx

from tests.conftest import BASE
from tests.test_crud_endpoints import EXISTING_VCF


@respx.mock
def test_patch_contact_updates_single_field_without_name(client):
    respx.get(BASE + "abc-123.vcf").mock(
        return_value=httpx.Response(200, text=EXISTING_VCF, headers={"ETag": '"v1"'})
    )
    put_route = respx.put(BASE + "abc-123.vcf").mock(return_value=httpx.Response(204))
    resp = client.patch(
        "/api/addressbooks/default/contacts/abc-123",
        json={"org": "Kókány Bt."},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "updated", "uid": "abc-123"}
    sent = put_route.calls.last.request.content.decode("utf-8")
    assert "Kókány Bt." in sent
    assert "FN:Anna Kis" in sent
    assert "X-CUSTOM:keep-me" in sent


@respx.mock
def test_patch_contact_normalizes_phone(client):
    respx.get(BASE + "abc-123.vcf").mock(
        return_value=httpx.Response(200, text=EXISTING_VCF, headers={"ETag": '"v1"'})
    )
    put_route = respx.put(BASE + "abc-123.vcf").mock(return_value=httpx.Response(204))
    resp = client.patch(
        "/api/addressbooks/default/contacts/abc-123",
        json={"phones": [{"type": "mobile", "value": "06301234567"}]},
    )
    assert resp.status_code == 200
    sent = put_route.calls.last.request.content.decode("utf-8")
    assert "+36301234567" in sent


@respx.mock
def test_patch_contact_invalid_phone_is_422(client):
    respx.get(BASE + "abc-123.vcf").mock(
        return_value=httpx.Response(200, text=EXISTING_VCF, headers={"ETag": '"v1"'})
    )
    resp = client.patch(
        "/api/addressbooks/default/contacts/abc-123",
        json={"phones": [{"type": "mobile", "value": "123"}]},
    )
    assert resp.status_code == 422
    assert "Invalid phone number" in resp.json()["detail"]


@respx.mock
def test_patch_contact_clearing_both_names_is_422(client):
    respx.get(BASE + "abc-123.vcf").mock(
        return_value=httpx.Response(200, text=EXISTING_VCF, headers={"ETag": '"v1"'})
    )
    resp = client.patch(
        "/api/addressbooks/default/contacts/abc-123",
        json={"firstname": "", "lastname": ""},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "At least one of firstname or lastname is required"


def test_patch_contact_empty_body_is_422(client):
    resp = client.patch("/api/addressbooks/default/contacts/abc-123", json={})
    assert resp.status_code == 422


def test_patch_contact_missing_required_field_is_422(client_with_env):
    with client_with_env({"REQUIRED_FIELDS": "emails"}) as c:
        c.headers["X-API-Key"] = "test-key"
        with respx.mock:
            respx.get(BASE + "abc-123.vcf").mock(
                return_value=httpx.Response(200, text=EXISTING_VCF, headers={"ETag": '"v1"'})
            )
            resp = c.patch(
                "/api/addressbooks/default/contacts/abc-123",
                json={"emails": []},
            )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Missing required field(s): emails"


@respx.mock
def test_patch_contact_missing_contact_is_404(client):
    respx.get(BASE + "nincs.vcf").mock(return_value=httpx.Response(404))
    resp = client.patch("/api/addressbooks/default/contacts/nincs", json={"org": "X"})
    assert resp.status_code == 404


@respx.mock
def test_patch_contact_conflict_is_409(client):
    respx.get(BASE + "abc-123.vcf").mock(
        return_value=httpx.Response(200, text=EXISTING_VCF, headers={"ETag": '"v1"'})
    )
    respx.put(BASE + "abc-123.vcf").mock(return_value=httpx.Response(412))
    resp = client.patch(
        "/api/addressbooks/default/contacts/abc-123",
        json={"org": "X"},
    )
    assert resp.status_code == 409
