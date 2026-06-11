# CardDAV-REST Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** FastAPI adapter that exposes a JSON REST API (search + full CRUD) for contacts stored on a Baïkal CardDAV server, so n8n never touches XML/WebDAV.

**Architecture:** Modular FastAPI package: `config.py` (env, fail-fast), `models.py` (Pydantic), `vcard.py` (Contact ↔ vCard 3.0 via vobject), `carddav.py` (REPORT XML building + httpx WebDAV client + error mapping), `routers/contacts.py` (endpoints). API key middleware protects everything except `/health`. Spec: `docs/superpowers/specs/2026-06-11-carddav-rest-adapter-design.md`.

**Tech Stack:** Python 3.12, FastAPI, httpx (async), vobject, xml.etree, pytest + pytest-asyncio + respx, Docker Compose with `ckulka/baikal:nginx`.

**Conventions for every task:**
- Run tests from the repo root with the venv active: `python -m pytest tests -v` (or a single test with `python -m pytest tests/test_x.py::test_name -v`). `python -m pytest` is required (not bare `pytest`) so the repo root lands on `sys.path`.
- Windows host; commands shown are PowerShell-compatible.
- Commit after every green test run. Append to each commit message:

```
Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

---

### Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`, `requirements-dev.txt`, `pytest.ini`, `app/__init__.py`, `app/routers/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Create requirements files**

`requirements.txt`:

```
fastapi>=0.115
uvicorn[standard]>=0.30
httpx>=0.27
vobject>=0.9.6
```

`requirements-dev.txt`:

```
-r requirements.txt
pytest>=8
pytest-asyncio>=0.24
respx>=0.21
```

- [ ] **Step 2: Create pytest.ini**

```ini
[pytest]
asyncio_mode = auto
pythonpath = .
```

- [ ] **Step 3: Create empty packages**

Create `app/__init__.py`, `app/routers/__init__.py`, `tests/__init__.py` — all three empty files.

- [ ] **Step 4: Create venv and install dependencies**

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
```

Expected: install succeeds. (All later `python` commands assume the venv is active: `.venv\Scripts\Activate.ps1`.)

- [ ] **Step 5: Verify pytest runs**

Run: `python -m pytest tests -v`
Expected: `no tests ran` (exit code 5 is fine at this point).

- [ ] **Step 6: Commit**

```powershell
git add requirements.txt requirements-dev.txt pytest.ini app tests
git commit -m "chore: scaffold project structure and dependencies"
```

---

### Task 2: Settings (config.py)

**Files:**
- Create: `app/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_config.py`:

```python
import pytest

from app.config import Settings, load_settings

REQUIRED = {
    "BAIKAL_URL": "http://baikal/dav.php",
    "BAIKAL_USER": "testuser",
    "BAIKAL_PASS": "testpass",
    "API_KEY": "test-key",
}


def _set_env(monkeypatch, overrides=None, remove=()):
    env = {**REQUIRED, **(overrides or {})}
    for key in remove:
        env.pop(key, None)
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("BAIKAL_ADDRESSBOOK", raising=False)


def test_load_settings_reads_env(monkeypatch):
    _set_env(monkeypatch)
    s = load_settings()
    assert s.baikal_url == "http://baikal/dav.php"
    assert s.baikal_user == "testuser"
    assert s.baikal_pass == "testpass"
    assert s.api_key == "test-key"
    assert s.baikal_addressbook == "default"


def test_addressbook_default_overridable(monkeypatch):
    _set_env(monkeypatch)
    monkeypatch.setenv("BAIKAL_ADDRESSBOOK", "munka")
    assert load_settings().baikal_addressbook == "munka"


def test_missing_required_var_fails_fast(monkeypatch):
    _set_env(monkeypatch, remove=("BAIKAL_PASS",))
    with pytest.raises(RuntimeError, match="BAIKAL_PASS"):
        load_settings()


def test_addressbook_url_handles_trailing_slash(monkeypatch):
    _set_env(monkeypatch, overrides={"BAIKAL_URL": "http://baikal/dav.php/"})
    s = load_settings()
    assert s.addressbook_url == "http://baikal/dav.php/addressbooks/testuser/default/"


def test_settings_dataclass_direct():
    s = Settings(
        baikal_url="http://baikal/dav.php",
        baikal_user="u",
        baikal_pass="p",
        baikal_addressbook="ab",
        api_key="k",
    )
    assert s.addressbook_url == "http://baikal/dav.php/addressbooks/u/ab/"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.config'`

- [ ] **Step 3: Implement app/config.py**

```python
import os
from dataclasses import dataclass

_REQUIRED_VARS = ("BAIKAL_URL", "BAIKAL_USER", "BAIKAL_PASS", "API_KEY")


@dataclass(frozen=True)
class Settings:
    baikal_url: str
    baikal_user: str
    baikal_pass: str
    baikal_addressbook: str
    api_key: str

    @property
    def addressbook_url(self) -> str:
        base = self.baikal_url.rstrip("/")
        return f"{base}/addressbooks/{self.baikal_user}/{self.baikal_addressbook}/"


def load_settings() -> Settings:
    missing = [name for name in _REQUIRED_VARS if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )
    return Settings(
        baikal_url=os.environ["BAIKAL_URL"],
        baikal_user=os.environ["BAIKAL_USER"],
        baikal_pass=os.environ["BAIKAL_PASS"],
        baikal_addressbook=os.getenv("BAIKAL_ADDRESSBOOK", "default"),
        api_key=os.environ["API_KEY"],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```powershell
git add app/config.py tests/test_config.py
git commit -m "feat: settings loaded from environment with fail-fast validation"
```

---

### Task 3: Pydantic models (models.py)

**Files:**
- Create: `app/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_models.py`:

```python
import pytest
from pydantic import ValidationError

from app.models import (
    Address,
    Contact,
    ContactCreate,
    ContactIn,
    ContactOut,
    SearchRequest,
    TypedValue,
)


def test_contact_base_allows_all_empty():
    c = Contact()
    assert c.firstname == ""
    assert c.emails == []
    assert c.categories == []


def test_contact_in_requires_a_name():
    with pytest.raises(ValidationError):
        ContactIn(emails=[TypedValue(type="work", value="a@b.hu")])
    assert ContactIn(firstname="Anna").firstname == "Anna"
    assert ContactIn(lastname="Kis").lastname == "Kis"


def test_contact_create_duplicate_flag_defaults_false():
    c = ContactCreate(firstname="Anna")
    assert c.check_duplicates is False


def test_contact_out_carries_uid_fn_etag():
    c = ContactOut(uid="abc", fn="Anna Kis", etag='"v1"')
    assert (c.uid, c.fn, c.etag) == ("abc", "Anna Kis", '"v1"')


def test_typed_value_and_address_defaults():
    assert TypedValue(value="x").type == "other"
    a = Address(street="Fő utca 1.", city="Budapest", zip="1011")
    assert a.type == "home"
    assert a.country == ""


def test_search_request_requires_at_least_one_filter():
    with pytest.raises(ValidationError):
        SearchRequest()
    assert SearchRequest(email="a@b.hu").match_condition == "allof"


def test_search_request_rejects_bad_match_condition():
    with pytest.raises(ValidationError):
        SearchRequest(email="a@b.hu", match_condition="sometimes")
    assert SearchRequest(name="Anna", match_condition="anyof").match_condition == "anyof"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models'`

- [ ] **Step 3: Implement app/models.py**

```python
from typing import Literal, Optional

from pydantic import BaseModel, model_validator


class TypedValue(BaseModel):
    type: str = "other"
    value: str


class Address(BaseModel):
    type: str = "home"
    street: str = ""
    city: str = ""
    zip: str = ""
    state: str = ""
    country: str = ""


class Contact(BaseModel):
    firstname: str = ""
    lastname: str = ""
    middlename: str = ""
    prefix: str = ""
    suffix: str = ""
    emails: list[TypedValue] = []
    phones: list[TypedValue] = []
    addresses: list[Address] = []
    org: str = ""
    title: str = ""
    birthday: str = ""
    urls: list[str] = []
    note: str = ""
    photo: str = ""
    categories: list[str] = []


class ContactIn(Contact):
    @model_validator(mode="after")
    def require_name(self) -> "ContactIn":
        if not (self.firstname or self.lastname):
            raise ValueError("At least one of firstname or lastname is required")
        return self


class ContactCreate(ContactIn):
    check_duplicates: bool = False


class ContactOut(Contact):
    uid: str = ""
    fn: str = ""
    etag: str = ""


class SearchRequest(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    match_condition: Literal["allof", "anyof"] = "allof"

    @model_validator(mode="after")
    def require_filter(self) -> "SearchRequest":
        if not (self.email or self.phone or self.name):
            raise ValueError("At least one of email, phone or name is required")
        return self


class SearchMatch(BaseModel):
    uid: str
    fn: str = ""
    emails: list[TypedValue] = []
    phones: list[TypedValue] = []


class SearchResponse(BaseModel):
    exists: bool
    match_count: int
    matches: list[SearchMatch]
    searched_params: dict
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_models.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```powershell
git add app/models.py tests/test_models.py
git commit -m "feat: pydantic models for contacts and search"
```

---

### Task 4: vCard serialization (vcard.py — Contact → vCard)

**Files:**
- Create: `app/vcard.py`
- Test: `tests/test_vcard.py`

**Domain notes for the implementer:**
- vobject's `vCard()` serializes as vCard 3.0 with `VERSION:3.0` and CRLF (`\r\n`) line endings automatically.
- `FN` is assembled in vCard convention order: `prefix firstname middlename lastname suffix`.
- Photo: base64 input string → decoded to bytes, vobject re-encodes on serialize when `encoding_param = "b"`; http(s) URL input → stored as `VALUE=uri` reference (never downloaded).

- [ ] **Step 1: Write the failing tests**

`tests/test_vcard.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_vcard.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.vcard'`

- [ ] **Step 3: Implement app/vcard.py**

```python
import base64

import vobject

from app.models import Contact


def build_fn(contact: Contact) -> str:
    parts = [contact.prefix, contact.firstname, contact.middlename, contact.lastname, contact.suffix]
    return " ".join(p for p in parts if p)


def contact_to_vcard(contact: Contact, uid: str) -> str:
    card = vobject.vCard()
    card.add("uid").value = uid
    _fill_card(card, contact)
    return card.serialize()


def _fill_card(card, contact: Contact) -> None:
    n = card.add("n")
    n.value = vobject.vcard.Name(
        family=contact.lastname,
        given=contact.firstname,
        additional=contact.middlename,
        prefix=contact.prefix,
        suffix=contact.suffix,
    )
    card.add("fn").value = build_fn(contact)
    for email in contact.emails:
        el = card.add("email")
        el.value = email.value
        el.params["TYPE"] = [email.type.upper()]
    for phone in contact.phones:
        el = card.add("tel")
        el.value = phone.value
        el.params["TYPE"] = [phone.type.upper()]
    for addr in contact.addresses:
        el = card.add("adr")
        el.value = vobject.vcard.Address(
            street=addr.street,
            city=addr.city,
            region=addr.state,
            code=addr.zip,
            country=addr.country,
        )
        el.params["TYPE"] = [addr.type.upper()]
    if contact.org:
        card.add("org").value = [contact.org]
    if contact.title:
        card.add("title").value = contact.title
    if contact.birthday:
        card.add("bday").value = contact.birthday
    for url in contact.urls:
        card.add("url").value = url
    if contact.note:
        card.add("note").value = contact.note
    if contact.photo:
        el = card.add("photo")
        if contact.photo.startswith(("http://", "https://")):
            el.value = contact.photo
            el.params["VALUE"] = ["uri"]
        else:
            el.value = base64.b64decode(contact.photo)
            el.encoding_param = "b"
    if contact.categories:
        card.add("categories").value = list(contact.categories)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_vcard.py -v`
Expected: 5 passed. If a vobject API detail differs (e.g. photo bytes handling), fix the implementation — not the test's intent — until green.

- [ ] **Step 5: Commit**

```powershell
git add app/vcard.py tests/test_vcard.py
git commit -m "feat: serialize Contact models to vCard 3.0 via vobject"
```

---

### Task 5: vCard parsing (vcard.py — vCard → ContactOut) + roundtrip

**Files:**
- Modify: `app/vcard.py` (append parser functions)
- Test: `tests/test_vcard.py` (append tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_vcard.py`:

```python
from app.models import ContactOut
from app.vcard import vcard_to_contact

SAMPLE_VCF = (
    "BEGIN:VCARD\r\n"
    "VERSION:3.0\r\n"
    "UID:abc-123\r\n"
    "FN:Anna Kis\r\n"
    "N:Kis;Anna;;;\r\n"
    "EMAIL;TYPE=INTERNET;TYPE=WORK:anna@ceg.hu\r\n"
    "TEL;TYPE=CELL:+36301111111\r\n"
    "X-CUSTOM:keep-me\r\n"
    "END:VCARD\r\n"
)


def test_parse_basic_fields():
    c = vcard_to_contact(SAMPLE_VCF)
    assert isinstance(c, ContactOut)
    assert c.uid == "abc-123"
    assert c.fn == "Anna Kis"
    assert c.firstname == "Anna"
    assert c.lastname == "Kis"
    assert c.emails == [TypedValue(type="work", value="anna@ceg.hu")]
    assert c.phones == [TypedValue(type="cell", value="+36301111111")]


def test_parse_tolerates_minimal_card():
    vcf = "BEGIN:VCARD\r\nVERSION:3.0\r\nFN:Csak Nev\r\nEND:VCARD\r\n"
    c = vcard_to_contact(vcf)
    assert c.fn == "Csak Nev"
    assert c.uid == ""
    assert c.emails == []


def test_roundtrip_full_contact():
    vcf = contact_to_vcard(FULL_CONTACT, uid="round-1")
    c = vcard_to_contact(vcf)
    assert c.uid == "round-1"
    assert c.firstname == FULL_CONTACT.firstname
    assert c.lastname == FULL_CONTACT.lastname
    assert c.middlename == FULL_CONTACT.middlename
    assert c.prefix == FULL_CONTACT.prefix
    assert c.suffix == FULL_CONTACT.suffix
    assert c.emails == FULL_CONTACT.emails
    assert c.phones == FULL_CONTACT.phones
    assert c.addresses == FULL_CONTACT.addresses
    assert c.org == FULL_CONTACT.org
    assert c.title == FULL_CONTACT.title
    assert c.birthday == FULL_CONTACT.birthday
    assert c.urls == FULL_CONTACT.urls
    assert c.note == FULL_CONTACT.note
    assert c.categories == FULL_CONTACT.categories


def test_roundtrip_photo_base64():
    import base64

    raw = base64.b64encode(b"fake-jpeg-bytes").decode("ascii")
    vcf = contact_to_vcard(Contact(firstname="Anna", photo=raw), uid="p-3")
    assert vcard_to_contact(vcf).photo == raw
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_vcard.py -v`
Expected: new tests FAIL — `ImportError: cannot import name 'vcard_to_contact'`

- [ ] **Step 3: Implement the parser in app/vcard.py**

Append (and extend the imports at the top of the file to `from app.models import Address, Contact, ContactOut, TypedValue`):

```python
def _first(value):
    return value[0] if isinstance(value, list) else value


def _type_of(el) -> str:
    types = [t.lower() for t in el.params.get("TYPE", []) if t.lower() not in ("internet", "pref")]
    return types[0] if types else "other"


def vcard_to_contact(vcf: str) -> ContactOut:
    card = vobject.readOne(vcf)
    c = card.contents

    def text(prop: str) -> str:
        return c[prop][0].value if prop in c else ""

    firstname = lastname = middlename = prefix = suffix = ""
    if "n" in c:
        name = c["n"][0].value
        firstname = _first(name.given) or ""
        lastname = _first(name.family) or ""
        middlename = _first(name.additional) or ""
        prefix = _first(name.prefix) or ""
        suffix = _first(name.suffix) or ""

    addresses = []
    for el in c.get("adr", []):
        a = el.value
        addresses.append(
            Address(
                type=_type_of(el),
                street=_first(a.street) or "",
                city=_first(a.city) or "",
                zip=_first(a.code) or "",
                state=_first(a.region) or "",
                country=_first(a.country) or "",
            )
        )

    photo = ""
    if "photo" in c:
        value = c["photo"][0].value
        photo = base64.b64encode(value).decode("ascii") if isinstance(value, bytes) else value

    org = ""
    if "org" in c:
        org = _first(c["org"][0].value) or ""

    return ContactOut(
        uid=text("uid"),
        fn=text("fn"),
        firstname=firstname,
        lastname=lastname,
        middlename=middlename,
        prefix=prefix,
        suffix=suffix,
        emails=[TypedValue(type=_type_of(el), value=el.value) for el in c.get("email", [])],
        phones=[TypedValue(type=_type_of(el), value=el.value) for el in c.get("tel", [])],
        addresses=addresses,
        org=org,
        title=text("title"),
        birthday=text("bday"),
        urls=[el.value for el in c.get("url", [])],
        note=text("note"),
        photo=photo,
        categories=list(c["categories"][0].value) if "categories" in c else [],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_vcard.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```powershell
git add app/vcard.py tests/test_vcard.py
git commit -m "feat: parse vCard 3.0 back to Contact models with full roundtrip"
```

---

### Task 6: Merge for updates (vcard.py — merge_contact_into_vcard)

**Files:**
- Modify: `app/vcard.py`
- Test: `tests/test_vcard.py` (append tests)

**Semantics:** PUT is a full replace of the *managed* properties (N, FN, EMAIL, TEL, ADR, ORG, TITLE, BDAY, URL, NOTE, PHOTO, CATEGORIES). Everything else in the existing card (UID, REV, X-* props synced from phones) is preserved untouched. A field omitted from the request body therefore clears that managed property.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_vcard.py`:

```python
from app.vcard import merge_contact_into_vcard


def test_merge_replaces_managed_and_keeps_unmanaged():
    new = Contact(
        firstname="Anna",
        lastname="Nagy",
        emails=[TypedValue(type="work", value="uj@ceg.hu")],
    )
    merged = merge_contact_into_vcard(SAMPLE_VCF, new)
    assert "X-CUSTOM:keep-me" in merged
    assert "UID:abc-123" in merged
    assert "FN:Anna Nagy" in merged
    assert "uj@ceg.hu" in merged
    assert "anna@ceg.hu" not in merged
    assert "TEL" not in merged  # phones omitted from the body -> cleared


def test_merge_result_is_valid_vcard():
    merged = merge_contact_into_vcard(SAMPLE_VCF, Contact(firstname="Anna", lastname="Nagy"))
    c = vcard_to_contact(merged)
    assert c.uid == "abc-123"
    assert c.firstname == "Anna"
    assert c.lastname == "Nagy"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_vcard.py -v`
Expected: new tests FAIL — `ImportError: cannot import name 'merge_contact_into_vcard'`

- [ ] **Step 3: Implement in app/vcard.py**

Add near the top of the file:

```python
MANAGED_PROPS = ("n", "fn", "email", "tel", "adr", "org", "title", "bday", "url", "note", "photo", "categories")
```

Add the function:

```python
def merge_contact_into_vcard(existing_vcf: str, contact: Contact) -> str:
    card = vobject.readOne(existing_vcf)
    for prop in MANAGED_PROPS:
        if prop in card.contents:
            del card.contents[prop]
    _fill_card(card, contact)
    return card.serialize()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_vcard.py -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```powershell
git add app/vcard.py tests/test_vcard.py
git commit -m "feat: merge contact updates into existing vCard preserving unmanaged props"
```

---

### Task 7: Search XML building and multistatus parsing (carddav.py)

**Files:**
- Create: `app/carddav.py`
- Test: `tests/test_carddav_xml.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_carddav_xml.py`:

```python
import xml.etree.ElementTree as ET

from app.carddav import build_search_xml, parse_multistatus

C = "{urn:ietf:params:xml:ns:carddav}"
D = "{DAV:}"


def test_all_filters_allof():
    xml_bytes = build_search_xml(email="a@b.hu", phone="+361", name="Anna", match_condition="allof")
    root = ET.fromstring(xml_bytes)
    assert root.tag == f"{C}addressbook-query"
    prop = root.find(f"{D}prop")
    assert prop.find(f"{D}getetag") is not None
    assert prop.find(f"{C}address-data") is not None
    filt = root.find(f"{C}filter")
    assert filt.get("test") == "allof"
    pfs = filt.findall(f"{C}prop-filter")
    assert [pf.get("name") for pf in pfs] == ["EMAIL", "TEL", "FN"]
    email_tm = pfs[0].find(f"{C}text-match")
    assert email_tm.get("match-type") == "equals"
    assert email_tm.get("collation") == "i;unicode-casemap"
    assert email_tm.text == "a@b.hu"
    assert pfs[1].find(f"{C}text-match").get("match-type") == "contains"
    assert pfs[2].find(f"{C}text-match").get("match-type") == "contains"


def test_single_filter_anyof():
    root = ET.fromstring(build_search_xml(email=None, phone=None, name="Anna", match_condition="anyof"))
    filt = root.find(f"{C}filter")
    assert filt.get("test") == "anyof"
    pfs = filt.findall(f"{C}prop-filter")
    assert [pf.get("name") for pf in pfs] == ["FN"]


def test_search_value_is_escaped_not_injected():
    xml_bytes = build_search_xml(email='"]><evil/>', phone=None, name=None, match_condition="allof")
    root = ET.fromstring(xml_bytes)  # must stay well-formed
    tm = root.find(f"{C}filter/{C}prop-filter/{C}text-match")
    assert tm.text == '"]><evil/>'


MULTISTATUS_ONE = (
    '<?xml version="1.0"?>'
    '<d:multistatus xmlns:d="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav">'
    "<d:response>"
    "<d:href>/dav.php/addressbooks/testuser/default/abc-123.vcf</d:href>"
    "<d:propstat><d:prop>"
    '<d:getetag>"etag-1"</d:getetag>'
    "<card:address-data>BEGIN:VCARD\nVERSION:3.0\nUID:abc-123\nFN:Teszt János\n"
    "N:Teszt;János;;;\nEMAIL;TYPE=HOME:teszt@email.hu\nTEL;TYPE=CELL:+36301234567\n"
    "END:VCARD\n</card:address-data>"
    "</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>"
    "</d:response>"
    "</d:multistatus>"
)

MULTISTATUS_EMPTY = (
    '<?xml version="1.0"?>'
    '<d:multistatus xmlns:d="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav"></d:multistatus>'
)


def test_parse_multistatus_one_match():
    results = parse_multistatus(MULTISTATUS_ONE)
    assert len(results) == 1
    uid, vcf = results[0]
    assert uid == "abc-123"
    assert "FN:Teszt János" in vcf


def test_parse_multistatus_empty():
    assert parse_multistatus(MULTISTATUS_EMPTY) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_carddav_xml.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.carddav'`

- [ ] **Step 3: Implement XML helpers in app/carddav.py**

```python
import xml.etree.ElementTree as ET

NS = {"d": "DAV:", "c": "urn:ietf:params:xml:ns:carddav"}
_D = "{DAV:}"
_C = "{urn:ietf:params:xml:ns:carddav}"


def build_search_xml(
    email: str | None,
    phone: str | None,
    name: str | None,
    match_condition: str,
) -> bytes:
    root = ET.Element(f"{_C}addressbook-query")
    prop = ET.SubElement(root, f"{_D}prop")
    ET.SubElement(prop, f"{_D}getetag")
    ET.SubElement(prop, f"{_C}address-data")
    filt = ET.SubElement(root, f"{_C}filter", {"test": match_condition})

    def add_filter(prop_name: str, value: str, match_type: str) -> None:
        pf = ET.SubElement(filt, f"{_C}prop-filter", {"name": prop_name})
        tm = ET.SubElement(
            pf,
            f"{_C}text-match",
            {"collation": "i;unicode-casemap", "match-type": match_type},
        )
        tm.text = value

    if email:
        add_filter("EMAIL", email, "equals")
    if phone:
        add_filter("TEL", phone, "contains")
    if name:
        add_filter("FN", name, "contains")

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def parse_multistatus(xml_text: str) -> list[tuple[str, str]]:
    root = ET.fromstring(xml_text)
    results: list[tuple[str, str]] = []
    for response in root.findall("d:response", NS):
        href = response.findtext("d:href", "", NS)
        vcf = response.findtext(".//c:address-data", None, NS)
        if vcf is None:
            continue
        uid = href.rstrip("/").rsplit("/", 1)[-1].removesuffix(".vcf")
        results.append((uid, vcf))
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_carddav_xml.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```powershell
git add app/carddav.py tests/test_carddav_xml.py
git commit -m "feat: addressbook-query XML builder and multistatus parser"
```

---

### Task 8: CardDAV client (carddav.py — CardDAVClient + error mapping)

**Files:**
- Modify: `app/carddav.py`
- Test: `tests/test_carddav_client.py`

**Error mapping contract:** connection problems / timeouts / upstream 401-403 / other 4xx-5xx → `UpstreamError` (becomes HTTP 502); upstream 404 → `NotFoundError` (404); upstream 412 → `ConflictError` (409). Auth details are logged, never put in the exception message.

- [ ] **Step 1: Write the failing tests**

`tests/test_carddav_client.py`:

```python
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
from tests.test_carddav_xml import MULTISTATUS_EMPTY, MULTISTATUS_ONE

SETTINGS = Settings(
    baikal_url="http://baikal/dav.php",
    baikal_user="testuser",
    baikal_pass="testpass",
    baikal_addressbook="default",
    api_key="test-key",
)
BASE = "http://baikal/dav.php/addressbooks/testuser/default/"


@pytest.fixture
async def dav():
    async with httpx.AsyncClient() as http:
        yield CardDAVClient(SETTINGS, http)


@respx.mock
async def test_search_returns_uid_vcf_pairs(dav):
    route = respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_ONE)
    )
    results = await dav.search(email="teszt@email.hu")
    assert results[0][0] == "abc-123"
    req = route.calls.last.request
    assert req.headers["Depth"] == "1"
    assert b"addressbook-query" in req.content


@respx.mock
async def test_search_empty(dav):
    respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_EMPTY)
    )
    assert await dav.search(name="Senki") == []


@respx.mock
async def test_get_returns_vcf_and_etag(dav):
    respx.get(BASE + "abc.vcf").mock(
        return_value=httpx.Response(200, text="BEGIN:VCARD\r\nEND:VCARD\r\n", headers={"ETag": '"v1"'})
    )
    vcf, etag = await dav.get("abc")
    assert vcf.startswith("BEGIN:VCARD")
    assert etag == '"v1"'


@respx.mock
async def test_create_sends_if_none_match(dav):
    route = respx.put(BASE + "abc.vcf").mock(return_value=httpx.Response(201))
    await dav.create("abc", "BEGIN:VCARD\r\nEND:VCARD\r\n")
    req = route.calls.last.request
    assert req.headers["If-None-Match"] == "*"
    assert req.headers["Content-Type"].startswith("text/vcard")


@respx.mock
async def test_update_sends_if_match(dav):
    route = respx.put(BASE + "abc.vcf").mock(return_value=httpx.Response(204))
    await dav.update("abc", "BEGIN:VCARD\r\nEND:VCARD\r\n", etag='"v1"')
    assert route.calls.last.request.headers["If-Match"] == '"v1"'


@respx.mock
async def test_delete(dav):
    route = respx.delete(BASE + "abc.vcf").mock(return_value=httpx.Response(204))
    await dav.delete("abc")
    assert route.called


@respx.mock
async def test_404_maps_to_not_found(dav):
    respx.get(BASE + "nincs.vcf").mock(return_value=httpx.Response(404))
    with pytest.raises(NotFoundError):
        await dav.get("nincs")


@respx.mock
async def test_412_maps_to_conflict(dav):
    respx.put(BASE + "abc.vcf").mock(return_value=httpx.Response(412))
    with pytest.raises(ConflictError):
        await dav.update("abc", "BEGIN:VCARD\r\nEND:VCARD\r\n", etag='"old"')


@respx.mock
async def test_connect_error_maps_to_upstream(dav):
    respx.get(BASE + "abc.vcf").mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(UpstreamError):
        await dav.get("abc")


@respx.mock
async def test_auth_failure_maps_to_upstream_without_leaking(dav):
    respx.get(BASE + "abc.vcf").mock(return_value=httpx.Response(401))
    with pytest.raises(UpstreamError) as exc_info:
        await dav.get("abc")
    assert "testpass" not in str(exc_info.value)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_carddav_client.py -v`
Expected: FAIL — `ImportError: cannot import name 'CardDAVClient'`

- [ ] **Step 3: Implement the client in app/carddav.py**

Append (extend the imports at the top with `import logging`, `import httpx`, `from app.config import Settings`):

```python
logger = logging.getLogger("carddav")


class CardDAVError(Exception):
    """Base class for adapter-level CardDAV errors."""


class NotFoundError(CardDAVError):
    """Upstream returned 404."""


class ConflictError(CardDAVError):
    """Upstream returned 412 (etag mismatch or resource already exists)."""


class UpstreamError(CardDAVError):
    """Upstream unreachable or returned an unexpected error."""


class CardDAVClient:
    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        self._http = http
        self._base = settings.addressbook_url

    def _url(self, uid: str) -> str:
        return f"{self._base}{uid}.vcf"

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            resp = await self._http.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            logger.error("CardDAV request failed: %s %s (%s)", method, url, exc)
            raise UpstreamError("CardDAV server unreachable") from exc
        if resp.status_code in (401, 403):
            logger.error("CardDAV auth rejected (%s) for %s %s", resp.status_code, method, url)
            raise UpstreamError("CardDAV server rejected the adapter's credentials")
        if resp.status_code == 404:
            raise NotFoundError("Contact not found")
        if resp.status_code == 412:
            raise ConflictError("Contact was modified concurrently or already exists")
        if resp.status_code >= 400:
            logger.error("CardDAV error %s for %s %s: %s", resp.status_code, method, url, resp.text[:500])
            raise UpstreamError(f"CardDAV server returned HTTP {resp.status_code}")
        return resp

    async def search(
        self,
        email: str | None = None,
        phone: str | None = None,
        name: str | None = None,
        match_condition: str = "allof",
    ) -> list[tuple[str, str]]:
        body = build_search_xml(email, phone, name, match_condition)
        resp = await self._request(
            "REPORT",
            self._base,
            content=body,
            headers={"Depth": "1", "Content-Type": "application/xml; charset=utf-8"},
        )
        return parse_multistatus(resp.text)

    async def get(self, uid: str) -> tuple[str, str]:
        resp = await self._request("GET", self._url(uid))
        return resp.text, resp.headers.get("ETag", "")

    async def create(self, uid: str, vcf: str) -> None:
        await self._request(
            "PUT",
            self._url(uid),
            content=vcf.encode("utf-8"),
            headers={"Content-Type": "text/vcard; charset=utf-8", "If-None-Match": "*"},
        )

    async def update(self, uid: str, vcf: str, etag: str) -> None:
        headers = {"Content-Type": "text/vcard; charset=utf-8"}
        if etag:
            headers["If-Match"] = etag
        await self._request("PUT", self._url(uid), content=vcf.encode("utf-8"), headers=headers)

    async def delete(self, uid: str) -> None:
        await self._request("DELETE", self._url(uid))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_carddav_client.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```powershell
git add app/carddav.py tests/test_carddav_client.py
git commit -m "feat: async CardDAV client with error mapping"
```

---

### Task 9: App factory, API key middleware, health, error handlers (main.py)

**Files:**
- Create: `app/main.py`
- Create: `tests/conftest.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Create tests/conftest.py**

```python
import pytest
from fastapi.testclient import TestClient

TEST_ENV = {
    "BAIKAL_URL": "http://baikal/dav.php",
    "BAIKAL_USER": "testuser",
    "BAIKAL_PASS": "testpass",
    "BAIKAL_ADDRESSBOOK": "default",
    "API_KEY": "test-key",
}

BASE = "http://baikal/dav.php/addressbooks/testuser/default/"


def _make_client(monkeypatch) -> TestClient:
    for key, value in TEST_ENV.items():
        monkeypatch.setenv(key, value)
    from app.main import create_app

    return TestClient(create_app())


@pytest.fixture
def anon_client(monkeypatch):
    with _make_client(monkeypatch) as c:
        yield c


@pytest.fixture
def client(monkeypatch):
    with _make_client(monkeypatch) as c:
        c.headers["X-API-Key"] = "test-key"
        yield c
```

- [ ] **Step 2: Write the failing tests**

`tests/test_app.py`:

```python
def test_health_is_open(anon_client):
    resp = anon_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_missing_api_key_rejected(anon_client):
    resp = anon_client.post("/api/contacts/search", json={"email": "x@y.hu"})
    assert resp.status_code == 401


def test_wrong_api_key_rejected(anon_client):
    resp = anon_client.post(
        "/api/contacts/search",
        json={"email": "x@y.hu"},
        headers={"X-API-Key": "wrong"},
    )
    assert resp.status_code == 401
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_app.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 4: Implement app/main.py**

```python
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.carddav import CardDAVClient, ConflictError, NotFoundError, UpstreamError
from app.config import load_settings


def create_app() -> FastAPI:
    settings = load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with httpx.AsyncClient(
            auth=(settings.baikal_user, settings.baikal_pass),
            timeout=10.0,
        ) as http:
            app.state.carddav = CardDAVClient(settings, http)
            yield

    app = FastAPI(title="CardDAV-REST", lifespan=lifespan)

    @app.middleware("http")
    async def require_api_key(request: Request, call_next):
        if request.url.path != "/health" and request.headers.get("X-API-Key") != settings.api_key:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
        return await call_next(request)

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(UpstreamError)
    async def upstream_handler(request: Request, exc: UpstreamError):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_app.py -v`
Expected: 3 passed (the 401 cases pass because the middleware runs before routing — the route itself does not exist yet).

- [ ] **Step 6: Commit**

```powershell
git add app/main.py tests/conftest.py tests/test_app.py
git commit -m "feat: app factory with API key middleware, health check and error handlers"
```

---

### Task 10: Search endpoint (routers/contacts.py)

**Files:**
- Create: `app/routers/contacts.py`
- Modify: `app/main.py` (include router)
- Test: `tests/test_search_endpoint.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_search_endpoint.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_search_endpoint.py -v`
Expected: FAIL — 404 responses (route does not exist yet).

- [ ] **Step 3: Implement app/routers/contacts.py**

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from app.carddav import CardDAVClient
from app.models import (
    ContactCreate,
    ContactIn,
    ContactOut,
    SearchMatch,
    SearchRequest,
    SearchResponse,
)
from app.vcard import contact_to_vcard, merge_contact_into_vcard, vcard_to_contact

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


def get_dav(request: Request) -> CardDAVClient:
    return request.app.state.carddav


@router.post("/search", response_model=SearchResponse)
async def search_contacts(
    req: SearchRequest, dav: CardDAVClient = Depends(get_dav)
) -> SearchResponse:
    results = await dav.search(
        email=req.email,
        phone=req.phone,
        name=req.name,
        match_condition=req.match_condition,
    )
    matches = []
    for uid, vcf in results:
        contact = vcard_to_contact(vcf)
        matches.append(
            SearchMatch(uid=uid, fn=contact.fn, emails=contact.emails, phones=contact.phones)
        )
    return SearchResponse(
        exists=bool(matches),
        match_count=len(matches),
        matches=matches,
        searched_params=req.model_dump(exclude_none=True),
    )
```

(`uuid`, `HTTPException`, `ContactCreate`, `ContactIn`, `ContactOut`, `contact_to_vcard`, `merge_contact_into_vcard` are imported now and used in Tasks 11–12.)

- [ ] **Step 4: Register the router in app/main.py**

Add the import at the top:

```python
from app.routers.contacts import router as contacts_router
```

Add inside `create_app()`, right after `app = FastAPI(...)`:

```python
app.include_router(contacts_router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_search_endpoint.py tests/test_app.py -v`
Expected: 7 passed

- [ ] **Step 6: Commit**

```powershell
git add app/routers/contacts.py app/main.py tests/test_search_endpoint.py
git commit -m "feat: contact search endpoint with dynamic CardDAV filters"
```

---

### Task 11: Create endpoint with optional duplicate check

**Files:**
- Modify: `app/routers/contacts.py`
- Test: `tests/test_create_endpoint.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_create_endpoint.py`:

```python
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
        "/api/contacts",
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


def test_create_without_name_is_422(client):
    resp = client.post("/api/contacts", json={"emails": [{"value": "a@b.hu"}]})
    assert resp.status_code == 422


@respx.mock
def test_create_with_duplicate_check_conflict(client):
    respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_ONE)
    )
    resp = client.post(
        "/api/contacts",
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
        "/api/contacts",
        json={
            "firstname": "Anna",
            "lastname": "Kis",
            "check_duplicates": True,
            "emails": [{"type": "work", "value": "uj@ceg.hu"}],
        },
    )
    assert resp.status_code == 201


@respx.mock
def test_create_uid_collision_is_409(client):
    respx.put(url__regex=VCF_URL.pattern).mock(return_value=httpx.Response(412))
    resp = client.post("/api/contacts", json={"firstname": "Anna", "lastname": "Kis"})
    assert resp.status_code == 409
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_create_endpoint.py -v`
Expected: FAIL — 405/404 responses (no POST route on `/api/contacts` yet).

- [ ] **Step 3: Implement the endpoint in app/routers/contacts.py**

Append:

```python
@router.post("", status_code=201)
async def create_contact(body: ContactCreate, dav: CardDAVClient = Depends(get_dav)) -> dict:
    if body.check_duplicates:
        for email in body.emails:
            results = await dav.search(email=email.value)
            if results:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "duplicate contact",
                        "matched_email": email.value,
                        "existing_uid": results[0][0],
                    },
                )
    uid = str(uuid.uuid4())
    vcf = contact_to_vcard(body, uid)
    await dav.create(uid, vcf)
    return {"status": "success", "uid": uid, "filename": f"{uid}.vcf"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_create_endpoint.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```powershell
git add app/routers/contacts.py tests/test_create_endpoint.py
git commit -m "feat: contact creation endpoint with optional duplicate check"
```

---

### Task 12: Get, update and delete endpoints

**Files:**
- Modify: `app/routers/contacts.py`
- Test: `tests/test_crud_endpoints.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_crud_endpoints.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_crud_endpoints.py -v`
Expected: FAIL — 404/405 responses (routes missing).

- [ ] **Step 3: Implement the endpoints in app/routers/contacts.py**

Append:

```python
@router.get("/{uid}", response_model=ContactOut)
async def get_contact(uid: str, dav: CardDAVClient = Depends(get_dav)) -> ContactOut:
    vcf, etag = await dav.get(uid)
    contact = vcard_to_contact(vcf)
    contact.uid = uid
    contact.etag = etag
    return contact


@router.put("/{uid}")
async def update_contact(
    uid: str, body: ContactIn, dav: CardDAVClient = Depends(get_dav)
) -> dict:
    existing_vcf, etag = await dav.get(uid)
    merged = merge_contact_into_vcard(existing_vcf, body)
    await dav.update(uid, merged, etag)
    return {"status": "updated", "uid": uid}


@router.delete("/{uid}")
async def delete_contact(uid: str, dav: CardDAVClient = Depends(get_dav)) -> dict:
    await dav.delete(uid)
    return {"status": "deleted", "uid": uid}
```

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest tests -v`
Expected: all tests pass (57 tests across all files).

- [ ] **Step 5: Commit**

```powershell
git add app/routers/contacts.py tests/test_crud_endpoints.py
git commit -m "feat: get, update and delete contact endpoints with etag handling"
```

---

### Task 13: Docker artifacts and README

**Files:**
- Create: `Dockerfile`, `docker-compose.yml`, `.env.example`
- Modify: `README.md`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create docker-compose.yml**

```yaml
services:
  baikal:
    image: ckulka/baikal:nginx
    restart: unless-stopped
    ports:
      - "8800:80"
    volumes:
      - baikal-config:/var/www/baikal/config
      - baikal-data:/var/www/baikal/Specific
    networks:
      - dav

  carddav-rest:
    image: ${ADAPTER_IMAGE:-carddav-rest:latest}
    restart: unless-stopped
    depends_on:
      - baikal
    ports:
      - "8000:8000"
    environment:
      BAIKAL_URL: http://baikal/dav.php
      BAIKAL_USER: ${BAIKAL_USER}
      BAIKAL_PASS: ${BAIKAL_PASS}
      BAIKAL_ADDRESSBOOK: ${BAIKAL_ADDRESSBOOK:-default}
      API_KEY: ${API_KEY}
    networks:
      - dav
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 5s
      retries: 3

networks:
  dav:

volumes:
  baikal-config:
  baikal-data:
```

- [ ] **Step 3: Create .env.example**

```
# Docker image reference for the adapter (manual build + push)
ADAPTER_IMAGE=carddav-rest:latest

# Baikal credentials used by the adapter (set up the user in the Baikal admin UI first)
BAIKAL_USER=admin
BAIKAL_PASS=change-me
BAIKAL_ADDRESSBOOK=default

# API key the n8n HTTP Request node must send in the X-API-Key header
API_KEY=generate-a-long-random-string
```

- [ ] **Step 4: Update README.md**

Replace the content of `README.md` with:

````markdown
# CardDAV-REST

FastAPI adapter that lets automation platforms (n8n) manage contacts on a
Baïkal CardDAV server through a clean JSON REST API. Phones keep syncing
natively over CardDAV; n8n never touches XML/WebDAV.

Design spec: `docs/superpowers/specs/2026-06-11-carddav-rest-adapter-design.md`

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/contacts/search` | Search with dynamic filters (email/phone/name, allof/anyof) |
| `POST` | `/api/contacts` | Create a contact (optional `check_duplicates`) |
| `GET` | `/api/contacts/{uid}` | Fetch one contact as JSON |
| `PUT` | `/api/contacts/{uid}` | Update (etag-protected, preserves unmanaged vCard props) |
| `DELETE` | `/api/contacts/{uid}` | Delete |
| `GET` | `/health` | Health check (no API key required) |

All `/api/*` endpoints require the `X-API-Key` header. Interactive docs: `/docs`.

## Running

```bash
cp .env.example .env   # then edit values
docker build -t carddav-rest:latest .
docker compose up -d
```

First-time Baïkal setup: open http://localhost:8800, finish the wizard,
create the user and address book referenced in `.env`.

## Examples

```bash
# Search
curl -X POST http://localhost:8000/api/contacts/search \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"email": "teszt@email.hu", "match_condition": "allof"}'

# Create
curl -X POST http://localhost:8000/api/contacts \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"firstname": "Anna", "lastname": "Kis", "emails": [{"type": "work", "value": "anna@ceg.hu"}], "check_duplicates": true}'

# Get / update / delete
curl http://localhost:8000/api/contacts/<uid> -H "X-API-Key: $API_KEY"
curl -X PUT http://localhost:8000/api/contacts/<uid> \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"firstname": "Anna", "lastname": "Nagy"}'
curl -X DELETE http://localhost:8000/api/contacts/<uid> -H "X-API-Key: $API_KEY"
```

## Development

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt   # Windows
python -m pytest tests -v
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `BAIKAL_URL` | yes | e.g. `http://baikal/dav.php` (internal Docker network) |
| `BAIKAL_USER` | yes | Baïkal user the adapter authenticates as |
| `BAIKAL_PASS` | yes | Baïkal password |
| `BAIKAL_ADDRESSBOOK` | no (`default`) | Address book id |
| `API_KEY` | yes | Key n8n sends in `X-API-Key` |
````

- [ ] **Step 5: Verify the Docker build (skip if Docker is unavailable)**

Run: `docker build -t carddav-rest:latest .`
Expected: build succeeds. If Docker is not available on this machine, note it and move on — the compose stack is verified manually later.

- [ ] **Step 6: Commit**

```powershell
git add Dockerfile docker-compose.yml .env.example README.md
git commit -m "feat: docker image, compose stack and documentation"
```

---

### Task 14: Final verification

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest tests -v`
Expected: all tests pass, zero failures.

- [ ] **Step 2: Smoke-test app startup without Docker**

```powershell
$env:BAIKAL_URL = "http://localhost:9999/dav.php"
$env:BAIKAL_USER = "smoke"
$env:BAIKAL_PASS = "smoke"
$env:API_KEY = "smoke-key"
python -c "from app.main import create_app; app = create_app(); print('app created, routes:', sorted({r.path for r in app.routes}))"
```

Expected output includes: `/api/contacts`, `/api/contacts/search`, `/api/contacts/{uid}`, `/health`.

- [ ] **Step 3: Verify fail-fast on missing env**

```powershell
Remove-Item Env:BAIKAL_PASS
python -c "from app.main import create_app; create_app()"
```

Expected: `RuntimeError: Missing required environment variables: BAIKAL_PASS`

- [ ] **Step 4: Commit any remaining changes and report**

Working tree should be clean. If any fixes were needed during verification, commit them, then report results to the user (test counts, anything skipped such as the Docker build).

**Manual integration check (user-driven, after image build):** `docker compose up -d`, complete the Baïkal wizard on http://localhost:8800, create the user + address book, then run the README curl examples and confirm a phone syncing via CardDAV sees the created contact.
