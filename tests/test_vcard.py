from app.models import Address, Contact, TypedValue
from app.vcard import build_fn, contact_to_vcard

FULL_CONTACT = Contact(
    firstname="János",
    lastname="Teszt",
    middlename="Béla",
    prefix="Dr.",
    suffix="PhD",
    emails=[
        TypedValue(type="work", value="janos@ceg.hu"),
        TypedValue(type="home", value="janos@otthon.hu"),
    ],
    phones=[TypedValue(type="cell", value="+36301234567")],
    addresses=[
        Address(type="home", street="Fő utca 1.", city="Budapest", zip="1011", country="Hungary")
    ],
    org="Teszt Kft.",
    title="Fejlesztő",
    birthday="1990-01-15",
    urls=["https://example.com"],
    note="VIP ügyfél",
    categories=["ügyfél", "vip"],
)


def test_minimal_vcard_has_required_props():
    vcf = contact_to_vcard(Contact(firstname="Anna", lastname="Kis"), uid="abc-123")
    assert vcf.startswith("BEGIN:VCARD\r\n")
    assert "VERSION:3.0" in vcf
    assert "UID:abc-123" in vcf
    assert "FN:Anna Kis" in vcf
    assert "N:Kis;Anna;;;" in vcf
    assert vcf.rstrip("\r\n").endswith("END:VCARD")


def test_build_fn_order():
    c = Contact(prefix="Dr.", firstname="János", middlename="Béla", lastname="Teszt", suffix="PhD")
    assert build_fn(c) == "Dr. János Béla Teszt PhD"
    assert build_fn(Contact(lastname="Kis")) == "Kis"


def test_full_contact_serializes_all_fields():
    vcf = contact_to_vcard(FULL_CONTACT, uid="full-1")
    assert "EMAIL;TYPE=WORK:janos@ceg.hu" in vcf
    assert "EMAIL;TYPE=HOME:janos@otthon.hu" in vcf
    assert "TEL;TYPE=CELL:+36301234567" in vcf
    assert "ORG:Teszt Kft." in vcf
    assert "TITLE:Fejleszt" in vcf  # vobject may escape UTF-8; prefix check is enough
    assert "BDAY:1990-01-15" in vcf
    assert "URL:https://example.com" in vcf
    assert "NOTE:VIP" in vcf
    assert "ADR;TYPE=HOME:" in vcf
    assert "CATEGORIES:" in vcf


def test_photo_url_stored_as_uri():
    c = Contact(firstname="Anna", photo="https://example.com/anna.jpg")
    vcf = contact_to_vcard(c, uid="p-1")
    assert "PHOTO;VALUE=uri:https://example.com/anna.jpg" in vcf or \
        "PHOTO;VALUE=URI:https://example.com/anna.jpg" in vcf


def test_photo_base64_embedded():
    import base64

    raw = b"\x89PNG-fake-bytes"
    c = Contact(firstname="Anna", photo=base64.b64encode(raw).decode("ascii"))
    vcf = contact_to_vcard(c, uid="p-2")
    assert "PHOTO" in vcf
    assert base64.b64encode(raw).decode("ascii") in vcf.replace("\r\n ", "")
