import httpx
import respx

from tests.conftest import BASE

PRIMARY_VCF = (
    "BEGIN:VCARD\r\n"
    "VERSION:3.0\r\n"
    "UID:uid-primary\r\n"
    "FN:Anna Kis\r\n"
    "N:Kis;Anna;;;\r\n"
    "EMAIL;TYPE=WORK:anna@ceg.hu\r\n"
    "X-CUSTOM:keep-me\r\n"
    "END:VCARD\r\n"
)

SECONDARY_VCF = (
    "BEGIN:VCARD\r\n"
    "VERSION:3.0\r\n"
    "UID:uid-secondary\r\n"
    "FN:Anna Kis\r\n"
    "N:Kis;Anna;;;\r\n"
    "EMAIL;TYPE=HOME:anna@gmail.com\r\n"
    "TEL;TYPE=MOBILE:+36301234567\r\n"
    "ORG:ACME Kft.\r\n"
    "END:VCARD\r\n"
)


@respx.mock
def test_merge_contact_success(client):
    respx.get(BASE + "uid-primary.vcf").mock(
        return_value=httpx.Response(200, text=PRIMARY_VCF, headers={"ETag": '"v1"'})
    )
    respx.get(BASE + "uid-secondary.vcf").mock(
        return_value=httpx.Response(200, text=SECONDARY_VCF, headers={"ETag": '"v2"'})
    )
    put_route = respx.put(BASE + "uid-primary.vcf").mock(return_value=httpx.Response(204))
    delete_route = respx.delete(BASE + "uid-secondary.vcf").mock(return_value=httpx.Response(204))

    resp = client.post("/api/addressbooks/default/contacts/uid-primary/merge/uid-secondary")

    assert resp.status_code == 200
    body = resp.json()
    assert body["uid"] == "uid-primary"
    assert body["firstname"] == "Anna"
    assert body["lastname"] == "Kis"
    email_values = [e["value"] for e in body["emails"]]
    assert "anna@ceg.hu" in email_values
    assert "anna@gmail.com" in email_values
    assert body["phones"][0]["value"] == "+36301234567"
    assert body["org"] == "ACME Kft."
    sent = put_route.calls.last.request.content.decode("utf-8")
    assert "X-CUSTOM:keep-me" in sent
    assert delete_route.called


def test_merge_contact_same_uid_is_422(client):
    resp = client.post("/api/addressbooks/default/contacts/uid-primary/merge/uid-primary")
    assert resp.status_code == 422
    assert "different" in resp.json()["detail"]


@respx.mock
def test_merge_contact_primary_not_found_is_404(client):
    respx.get(BASE + "missing.vcf").mock(return_value=httpx.Response(404))
    resp = client.post("/api/addressbooks/default/contacts/missing/merge/uid-secondary")
    assert resp.status_code == 404


@respx.mock
def test_merge_contact_secondary_not_found_is_404(client):
    respx.get(BASE + "uid-primary.vcf").mock(
        return_value=httpx.Response(200, text=PRIMARY_VCF, headers={"ETag": '"v1"'})
    )
    respx.get(BASE + "missing.vcf").mock(return_value=httpx.Response(404))
    resp = client.post("/api/addressbooks/default/contacts/uid-primary/merge/missing")
    assert resp.status_code == 404
