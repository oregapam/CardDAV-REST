# Required Fields Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Operators can declare, via a `REQUIRED_FIELDS` environment variable, which `Contact` fields must be present for a contact to be created or updated. Requests missing any required field return `422`.

**Architecture:** A new `app/required_fields.py` module exposes a pure, HTTP-agnostic `missing_required_fields(contact, required)` function that type-dispatches on each field's value (string / `TypedValue` list / string list / `Address` list) to decide if it's "present". `Settings.required_fields` (env var `REQUIRED_FIELDS`, comma-separated `Contact` field names, validated at startup) flows into `app.state` and then into the router via `Depends`, the same pattern already used for `name_format` and `default_region`. The router calls the helper in `create_contact` and `update_contact`, after phone normalization, and turns a non-empty result into a `422`.

**Tech Stack:** Pydantic v2 (`Contact.model_fields` for startup validation), FastAPI `Depends`, existing `Settings` dataclass pattern.

Spec: `docs/superpowers/specs/2026-06-16-required-fields-design.md`

---

### Task 1: `app/required_fields.py` — missing_required_fields()

**Files:**
- Create: `app/required_fields.py`
- Test: `tests/test_required_fields.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_required_fields.py`:

```python
from app.models import Address, Contact, TypedValue
from app.required_fields import missing_required_fields


def test_no_required_fields_returns_empty():
    contact = Contact()
    assert missing_required_fields(contact, ()) == []


def test_empty_string_field_is_missing():
    contact = Contact(org="")
    assert missing_required_fields(contact, ("org",)) == ["org"]


def test_filled_string_field_is_present():
    contact = Contact(org="ACME")
    assert missing_required_fields(contact, ("org",)) == []


def test_whitespace_only_string_field_is_missing():
    contact = Contact(org="   ")
    assert missing_required_fields(contact, ("org",)) == ["org"]


def test_empty_typed_value_list_is_missing():
    contact = Contact(emails=[])
    assert missing_required_fields(contact, ("emails",)) == ["emails"]


def test_typed_value_list_with_blank_value_is_missing():
    contact = Contact(emails=[TypedValue(value="")])
    assert missing_required_fields(contact, ("emails",)) == ["emails"]


def test_typed_value_list_with_real_value_is_present():
    contact = Contact(emails=[TypedValue(value="a@b.hu")])
    assert missing_required_fields(contact, ("emails",)) == []


def test_empty_str_list_is_missing():
    contact = Contact(categories=[])
    assert missing_required_fields(contact, ("categories",)) == ["categories"]


def test_str_list_with_only_blank_entries_is_missing():
    contact = Contact(categories=[""])
    assert missing_required_fields(contact, ("categories",)) == ["categories"]


def test_str_list_with_real_entry_is_present():
    contact = Contact(categories=["vip"])
    assert missing_required_fields(contact, ("categories",)) == []


def test_empty_address_list_is_missing():
    contact = Contact(addresses=[])
    assert missing_required_fields(contact, ("addresses",)) == ["addresses"]


def test_address_list_with_one_entry_is_present():
    contact = Contact(addresses=[Address()])
    assert missing_required_fields(contact, ("addresses",)) == []


def test_multiple_missing_fields_returned_in_order():
    contact = Contact()
    assert missing_required_fields(contact, ("emails", "org", "phones")) == [
        "emails",
        "org",
        "phones",
    ]


def test_mixed_present_and_missing_fields():
    contact = Contact(org="ACME")
    assert missing_required_fields(contact, ("emails", "org")) == ["emails"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_required_fields.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.required_fields'`

- [ ] **Step 3: Write the implementation**

Create `app/required_fields.py`:

```python
from app.models import Contact, TypedValue


def missing_required_fields(contact: Contact, required: tuple[str, ...]) -> list[str]:
    """Returns the names of required fields that are absent on the contact,
    preserving the order given in `required`."""
    return [name for name in required if not _is_present(getattr(contact, name))]


def _is_present(value) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        if not value:
            return False
        first = value[0]
        if isinstance(first, TypedValue):
            return any(item.value.strip() for item in value)
        if isinstance(first, str):
            return any(item.strip() for item in value)
        return True  # e.g. Address entries — presence in the list is enough
    return bool(value)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_required_fields.py -v`
Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add app/required_fields.py tests/test_required_fields.py
git commit -m "feat: add missing_required_fields() helper"
```

---

### Task 2: `Settings.required_fields` + `REQUIRED_FIELDS` env var

**Files:**
- Modify: `app/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_config.py` (after `test_default_region_reads_env_override`):

```python
def test_required_fields_defaults_to_empty(monkeypatch):
    _set_env(monkeypatch)
    s = load_settings()
    assert s.required_fields == ()


def test_required_fields_parses_comma_separated(monkeypatch):
    _set_env(monkeypatch, overrides={"REQUIRED_FIELDS": "emails,phones"})
    s = load_settings()
    assert s.required_fields == ("emails", "phones")


def test_required_fields_strips_whitespace_and_trailing_comma(monkeypatch):
    _set_env(monkeypatch, overrides={"REQUIRED_FIELDS": " emails , phones, "})
    s = load_settings()
    assert s.required_fields == ("emails", "phones")


def test_required_fields_rejects_unknown_field_name(monkeypatch):
    _set_env(monkeypatch, overrides={"REQUIRED_FIELDS": "email"})
    with pytest.raises(RuntimeError, match="email"):
        load_settings()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_config.py -v`
Expected: FAIL with `AttributeError: 'Settings' object has no attribute 'required_fields'`

- [ ] **Step 3: Implement the config change**

In `app/config.py`, add the import and a module-level constant near the top:

```python
import os
from dataclasses import dataclass
from typing import Literal

from app.models import Contact

_REQUIRED_VARS = ("BAIKAL_URL", "BAIKAL_USER", "BAIKAL_PASS", "API_KEY")

NameFormat = Literal["western", "eastern", "eastern_full"]
_VALID_NAME_FORMATS: tuple[str, ...] = ("western", "eastern", "eastern_full")
_VALID_CONTACT_FIELDS: frozenset[str] = frozenset(Contact.model_fields.keys())
```

Add `required_fields: tuple[str, ...] = ()` to the `Settings` dataclass (after `default_region: str = "HU"`):

```python
@dataclass(frozen=True)
class Settings:
    baikal_url: str
    baikal_user: str
    baikal_pass: str
    api_key: str
    name_format: NameFormat = "western"
    default_region: str = "HU"
    required_fields: tuple[str, ...] = ()

    @property
    def principal_url(self) -> str:
        base = self.baikal_url.rstrip("/")
        return f"{base}/addressbooks/{self.baikal_user}/"
```

Add a parsing helper function before `load_settings()`:

```python
def _parse_required_fields(raw: str) -> tuple[str, ...]:
    fields = tuple(f.strip() for f in raw.split(",") if f.strip())
    unknown = [f for f in fields if f not in _VALID_CONTACT_FIELDS]
    if unknown:
        raise RuntimeError(
            f"Unknown REQUIRED_FIELDS entries: {', '.join(unknown)}. "
            f"Must be one of: {', '.join(sorted(_VALID_CONTACT_FIELDS))}"
        )
    return fields
```

In `load_settings()`, add `required_fields=_parse_required_fields(os.getenv("REQUIRED_FIELDS", "")),` as a new keyword argument when constructing `Settings(...)`:

```python
def load_settings() -> Settings:
    missing = [name for name in _REQUIRED_VARS if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )
    raw_format = os.getenv("NAME_FORMAT", "western")
    if raw_format not in _VALID_NAME_FORMATS:
        raise RuntimeError(
            f"Invalid NAME_FORMAT '{raw_format}'. Must be one of: {', '.join(_VALID_NAME_FORMATS)}"
        )
    return Settings(
        baikal_url=os.environ["BAIKAL_URL"],
        baikal_user=os.environ["BAIKAL_USER"],
        baikal_pass=os.environ["BAIKAL_PASS"],
        api_key=os.environ["API_KEY"],
        name_format=raw_format,  # type: ignore[arg-type]
        default_region=os.getenv("DEFAULT_COUNTRY_CODE", "HU"),
        required_fields=_parse_required_fields(os.getenv("REQUIRED_FIELDS", "")),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_config.py -v`
Expected: all passed

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `.venv\Scripts\python.exe -m pytest tests -q`
Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: add REQUIRED_FIELDS setting with startup validation"
```

---

### Task 3: Wire `required_fields` into app state

**Files:**
- Modify: `app/main.py:22-24`

- [ ] **Step 1: Update the lifespan setup**

In `app/main.py`, change:

```python
            app.state.carddav = CardDAVClient(settings, http)
            app.state.name_format = settings.name_format
            app.state.default_region = settings.default_region
```

to:

```python
            app.state.carddav = CardDAVClient(settings, http)
            app.state.name_format = settings.name_format
            app.state.default_region = settings.default_region
            app.state.required_fields = settings.required_fields
```

- [ ] **Step 2: Run the full test suite to verify nothing broke**

Run: `.venv\Scripts\python.exe -m pytest tests -q`
Expected: all passed (no test references `app.state.required_fields` yet, this is just a smoke check)

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: wire required_fields into app state"
```

---

### Task 4: Add a per-test env override fixture for config-dependent tests

**Files:**
- Modify: `tests/conftest.py`

This adds test infrastructure only — no behavior change, so there's no
standalone test for this step. It's needed because the existing `client`
fixture always uses the fixed `TEST_ENV` dict; testing `REQUIRED_FIELDS`
needs a way to set extra env vars per test.

- [ ] **Step 1: Add the fixture**

In `tests/conftest.py`, add this fixture after the existing `client` fixture:

```python
@pytest.fixture
def client_with_env(monkeypatch):
    def _make(extra_env: dict) -> TestClient:
        env = {**TEST_ENV, **extra_env}
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        from app.main import create_app

        return TestClient(create_app())

    return _make
```

The full file should now read:

```python
import pytest
from fastapi.testclient import TestClient

TEST_ENV = {
    "BAIKAL_URL": "http://baikal/dav.php",
    "BAIKAL_USER": "testuser",
    "BAIKAL_PASS": "testpass",
    "API_KEY": "test-key",
    "NAME_FORMAT": "western",
}

PRINCIPAL = "http://baikal/dav.php/addressbooks/testuser/"
BOOK = "default"
BASE = PRINCIPAL + BOOK + "/"  # http://baikal/dav.php/addressbooks/testuser/default/


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


@pytest.fixture
def client_with_env(monkeypatch):
    def _make(extra_env: dict) -> TestClient:
        env = {**TEST_ENV, **extra_env}
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        from app.main import create_app

        return TestClient(create_app())

    return _make
```

Callers use it like:

```python
def test_something(client_with_env):
    with client_with_env({"REQUIRED_FIELDS": "emails"}) as c:
        c.headers["X-API-Key"] = "test-key"
        resp = c.post(...)
```

- [ ] **Step 2: Run the full test suite to verify nothing broke**

Run: `.venv\Scripts\python.exe -m pytest tests -q`
Expected: all passed (the new fixture isn't used by any test yet)

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add client_with_env fixture for per-test env overrides"
```

---

### Task 5: Apply required-fields check on contact create

**Files:**
- Modify: `app/routers/contacts.py`
- Test: `tests/test_create_endpoint.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_create_endpoint.py` (after `test_create_contact_invalid_phone_is_422`):

```python
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
```

(`VCF_URL`, `httpx`, and `respx` are already imported/defined in this file.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_create_endpoint.py -v`
Expected: `test_create_contact_missing_required_field_is_422` FAILs (returns 201, not 422 — `REQUIRED_FIELDS` isn't checked yet); the other two pass already (no behavior change needed for them yet) or fail only if fixture is missing — confirm `client_with_env` exists from Task 4.

- [ ] **Step 3: Implement the check in the router**

In `app/routers/contacts.py`, add the import:

```python
from app.required_fields import missing_required_fields
```

Add this dependency function right after `get_default_region`:

```python
def get_required_fields(request: Request) -> tuple[str, ...]:
    return request.app.state.required_fields
```

Update `create_contact` to check required fields right after phone normalization:

```python
@router.post("/{book}/contacts", status_code=201)
async def create_contact(
    book: str,
    body: ContactCreate,
    dav: CardDAVClient = Depends(get_dav),
    name_format: str = Depends(get_name_format),
    default_region: str = Depends(get_default_region),
    required_fields: tuple[str, ...] = Depends(get_required_fields),
) -> dict:
    for phone in body.phones:
        try:
            phone.value = normalize_phone(phone.value, default_region)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid phone number: {phone.value}")
    missing = missing_required_fields(body, required_fields)
    if missing:
        raise HTTPException(
            status_code=422, detail=f"Missing required field(s): {', '.join(missing)}"
        )
    if body.check_duplicates:
        for email in body.emails:
            results = await dav.search(book, email=email.value)
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
    vcf = contact_to_vcard(body, uid, name_format)
    await dav.create(book, uid, vcf)
    return {"status": "success", "uid": uid, "filename": f"{uid}.vcf"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_create_endpoint.py -v`
Expected: all passed

- [ ] **Step 5: Run the full suite to check for regressions**

Run: `.venv\Scripts\python.exe -m pytest tests -q`
Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add app/routers/contacts.py tests/test_create_endpoint.py
git commit -m "feat: enforce REQUIRED_FIELDS on contact create"
```

---

### Task 6: Apply required-fields check on contact update

**Files:**
- Modify: `app/routers/contacts.py`
- Test: `tests/test_crud_endpoints.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_crud_endpoints.py` (after `test_update_contact_invalid_phone_is_422`):

```python
def test_update_contact_missing_required_field_is_422(client_with_env):
    with client_with_env({"REQUIRED_FIELDS": "emails"}) as c:
        c.headers["X-API-Key"] = "test-key"
        with respx.mock:
            respx.get(BASE + "abc-123.vcf").mock(
                return_value=httpx.Response(200, text=EXISTING_VCF, headers={"ETag": '"v1"'})
            )
            resp = c.put(
                "/api/addressbooks/default/contacts/abc-123",
                json={"firstname": "Anna", "lastname": "Kis"},
            )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Missing required field(s): emails"


def test_update_contact_with_required_field_present_succeeds(client_with_env):
    with client_with_env({"REQUIRED_FIELDS": "emails"}) as c:
        c.headers["X-API-Key"] = "test-key"
        with respx.mock:
            respx.get(BASE + "abc-123.vcf").mock(
                return_value=httpx.Response(200, text=EXISTING_VCF, headers={"ETag": '"v1"'})
            )
            respx.put(BASE + "abc-123.vcf").mock(return_value=httpx.Response(204))
            resp = c.put(
                "/api/addressbooks/default/contacts/abc-123",
                json={
                    "firstname": "Anna",
                    "lastname": "Kis",
                    "emails": [{"type": "work", "value": "anna@ceg.hu"}],
                },
            )
    assert resp.status_code == 200
```

(`BASE`, `EXISTING_VCF`, `httpx`, and `respx` are already imported/defined in this file.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_crud_endpoints.py -v`
Expected: `test_update_contact_missing_required_field_is_422` FAILs (returns 200, not 422 — `REQUIRED_FIELDS` isn't checked on update yet)

- [ ] **Step 3: Implement the check in update_contact**

In `app/routers/contacts.py`, update `update_contact`:

```python
@router.put("/{book}/contacts/{uid}")
async def update_contact(
    book: str,
    uid: str,
    body: ContactIn,
    dav: CardDAVClient = Depends(get_dav),
    name_format: str = Depends(get_name_format),
    default_region: str = Depends(get_default_region),
    required_fields: tuple[str, ...] = Depends(get_required_fields),
) -> dict:
    for phone in body.phones:
        try:
            phone.value = normalize_phone(phone.value, default_region)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid phone number: {phone.value}")
    missing = missing_required_fields(body, required_fields)
    if missing:
        raise HTTPException(
            status_code=422, detail=f"Missing required field(s): {', '.join(missing)}"
        )
    existing_vcf, etag = await dav.get(book, uid)
    merged = merge_contact_into_vcard(existing_vcf, body, name_format)
    await dav.update(book, uid, merged, etag)
    return {"status": "updated", "uid": uid}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_crud_endpoints.py -v`
Expected: all passed

- [ ] **Step 5: Run the full suite to check for regressions**

Run: `.venv\Scripts\python.exe -m pytest tests -q`
Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add app/routers/contacts.py tests/test_crud_endpoints.py
git commit -m "feat: enforce REQUIRED_FIELDS on contact update"
```

---

### Task 7: Documentation

**Files:**
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `docs/ideas.md`

- [ ] **Step 1: Document the env var in `.env.example`**

Add at the end of `.env.example`:

```
# Comma-separated Contact field names that must be present to create/update a
# contact, beyond the built-in "firstname or lastname" rule. Empty = no extra
# requirements. Valid names: firstname, lastname, middlename, prefix, suffix,
# emails, phones, addresses, org, title, birthday, urls, note, photo, categories
REQUIRED_FIELDS=
```

- [ ] **Step 2: Document the env var in `README.md`**

In the "Environment variables" table, add a row after `DEFAULT_COUNTRY_CODE`:

```markdown
| `REQUIRED_FIELDS` | no | _(empty)_ | Comma-separated `Contact` field names that must be present — see below |
```

Add a new subsection after "### Phone number normalization":

```markdown
### Required fields

Beyond the built-in rule that `firstname` or `lastname` must be present,
operators can require additional fields via `REQUIRED_FIELDS` (comma-separated
list of contact field names). Applies to both `POST .../contacts` (create) and
`PUT .../contacts/{uid}` (update).

```
REQUIRED_FIELDS=emails,phones
```

Valid field names: `firstname`, `lastname`, `middlename`, `prefix`, `suffix`,
`emails`, `phones`, `addresses`, `org`, `title`, `birthday`, `urls`, `note`,
`photo`, `categories`. An unrecognized name fails fast at startup.

"Present" means: a non-empty (trimmed) string for string fields; at least one
list entry with a non-empty `value` for `emails`/`phones`; at least one
non-empty string for `urls`/`categories`; a non-empty list for `addresses`.

A request missing any required field returns `422`:

```json
{"detail": "Missing required field(s): emails, org"}
```

This check runs after phone normalization, so an invalid (rather than missing)
phone number reports the more specific `Invalid phone number: ...` error
instead.
```

- [ ] **Step 3: Check off the idea and add the follow-up in `docs/ideas.md`**

Change:

```markdown
- [ ] **Kötelező mező konfiguráció** — `REQUIRED_FIELDS=email` env var: ha nincs email a kontakton, 422-vel visszautasítja
```

to:

```markdown
- [x] **Kötelező mező konfiguráció** — `REQUIRED_FIELDS=emails,phones` env var: ha a megadott mezők nélkül próbálnak kontaktot létrehozni/módosítani, 422-vel visszautasítja
```

Add a new line under the "## Megfigyelhetőség" section (after the `GET /api/stats` line):

```markdown
- [ ] **`GET /api/config`** — visszaadja az aktív `required_fields`, `default_region`, `name_format` beállításokat, hogy egy n8n node dinamikusan tudjon formot építeni (a `REQUIRED_FIELDS` jelenleg nem látszik az OpenAPI sémában)
```

- [ ] **Step 4: Commit**

```bash
git add .env.example README.md docs/ideas.md
git commit -m "docs: document REQUIRED_FIELDS and required fields behavior"
```

---

### Task 8: Final verification

- [ ] **Step 1: Run the full test suite**

Run: `.venv\Scripts\python.exe -m pytest tests -q`
Expected: all tests pass, no warnings about missing modules

- [ ] **Step 2: Confirm the commit history is scoped correctly**

Run: `git log --oneline -10` and confirm each commit from this plan is scoped to its task (helper, config, app-state wiring, test fixture, create, update, docs).
