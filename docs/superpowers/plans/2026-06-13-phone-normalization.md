# Phone Number Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phone numbers submitted through create/update/search endpoints are normalized to E.164 format (e.g. `06301234567` → `+36301234567`) before being sent to the CardDAV server.

**Architecture:** A new `app/phone.py` module wraps the `phonenumbers` library with a single `normalize_phone(value, default_region)` function. It's invoked at the router layer (not as a Pydantic validator) because the default region comes from `Settings` via the same dependency-injection pattern already used for `name_format`. Invalid numbers cause a `422` response; empty values are a no-op; numbers already in `+...` form pass through unchanged.

**Tech Stack:** `phonenumbers` (Google libphonenumber Python port), FastAPI `Depends`, existing `Settings` dataclass pattern.

Spec: `docs/superpowers/specs/2026-06-13-phone-normalization-design.md`

---

### Task 1: Add the `phonenumbers` dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add the dependency**

Edit `requirements.txt` to add this line after `vobject>=0.9.6`:

```
phonenumbers>=8.13
```

- [ ] **Step 2: Install it**

Run: `.venv\Scripts\pip install -r requirements.txt`
Expected: `phonenumbers` downloads and installs without errors.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "build: add phonenumbers dependency"
```

---

### Task 2: `app/phone.py` — normalize_phone()

**Files:**
- Create: `app/phone.py`
- Test: `tests/test_phone.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_phone.py`:

```python
import pytest

from app.phone import normalize_phone


def test_normalize_local_hu_mobile_to_e164():
    assert normalize_phone("06301234567", "HU") == "+36301234567"


def test_normalize_local_hu_landline_to_e164():
    assert normalize_phone("0612345678", "HU") == "+3612345678"


def test_normalize_leaves_already_e164_unchanged():
    assert normalize_phone("+36301234567", "HU") == "+36301234567"


def test_normalize_respects_explicit_region_argument():
    # a "+"-prefixed number is unambiguous regardless of default_region
    assert normalize_phone("+36301234567", "DE") == "+36301234567"


def test_normalize_empty_string_is_noop():
    assert normalize_phone("", "HU") == ""


def test_normalize_blank_string_is_noop():
    assert normalize_phone("   ", "HU") == "   "


def test_normalize_invalid_number_raises_value_error():
    with pytest.raises(ValueError):
        normalize_phone("123", "HU")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_phone.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.phone'`

- [ ] **Step 3: Write the implementation**

Create `app/phone.py`:

```python
import phonenumbers


def normalize_phone(value: str, default_region: str) -> str:
    """Returns the number in E.164 format, or raises ValueError if invalid."""
    if not value.strip():
        return value
    try:
        parsed = phonenumbers.parse(value, default_region)
    except phonenumbers.NumberParseException as exc:
        raise ValueError(f"Invalid phone number: {value}") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError(f"Invalid phone number: {value}")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_phone.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add app/phone.py tests/test_phone.py
git commit -m "feat: add normalize_phone() E.164 normalization helper"
```

---

### Task 3: `Settings.default_region` + `DEFAULT_COUNTRY_CODE` env var

**Files:**
- Modify: `app/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_config.py` (after `test_principal_url_handles_trailing_slash`):

```python
def test_default_region_defaults_to_hu(monkeypatch):
    _set_env(monkeypatch)
    s = load_settings()
    assert s.default_region == "HU"


def test_default_region_reads_env_override(monkeypatch):
    _set_env(monkeypatch, overrides={"DEFAULT_COUNTRY_CODE": "DE"})
    s = load_settings()
    assert s.default_region == "DE"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_config.py -v`
Expected: FAIL with `AttributeError: 'Settings' object has no attribute 'default_region'`

- [ ] **Step 3: Implement the config change**

In `app/config.py`, add `default_region` to the `Settings` dataclass:

```python
@dataclass(frozen=True)
class Settings:
    baikal_url: str
    baikal_user: str
    baikal_pass: str
    api_key: str
    name_format: NameFormat = "western"
    default_region: str = "HU"

    @property
    def principal_url(self) -> str:
        base = self.baikal_url.rstrip("/")
        return f"{base}/addressbooks/{self.baikal_user}/"
```

In `load_settings()`, read the new env var and pass it through:

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
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_config.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: add DEFAULT_COUNTRY_CODE setting for phone normalization"
```

---

### Task 4: Wire `default_region` into app state

**Files:**
- Modify: `app/main.py:22-23`

- [ ] **Step 1: Update the lifespan setup**

In `app/main.py`, change:

```python
            app.state.carddav = CardDAVClient(settings, http)
            app.state.name_format = settings.name_format
```

to:

```python
            app.state.carddav = CardDAVClient(settings, http)
            app.state.name_format = settings.name_format
            app.state.default_region = settings.default_region
```

- [ ] **Step 2: Run the full test suite to verify nothing broke**

Run: `.venv\Scripts\python.exe -m pytest tests -q`
Expected: all passed (no test references `default_region` on app.state yet, so this is just a smoke check)

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: wire default_region into app state"
```

---

### Task 5: Normalize phones on contact create

**Files:**
- Modify: `app/routers/contacts.py`
- Test: `tests/test_create_endpoint.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_create_endpoint.py` (after `test_create_contact`):

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_create_endpoint.py -v`
Expected: `test_create_contact_normalizes_phone` FAILs (raw `06301234567` sent unchanged); `test_create_contact_invalid_phone_is_422` FAILs (returns 201, not 422)

- [ ] **Step 3: Implement normalization in the router**

In `app/routers/contacts.py`, add the import:

```python
from app.phone import normalize_phone
```

Add the dependency function next to `get_name_format`:

```python
def get_default_region(request: Request) -> str:
    return request.app.state.default_region
```

Update `create_contact` to normalize phones before the duplicate check:

```python
@router.post("/{book}/contacts", status_code=201)
async def create_contact(
    book: str,
    body: ContactCreate,
    dav: CardDAVClient = Depends(get_dav),
    name_format: str = Depends(get_name_format),
    default_region: str = Depends(get_default_region),
) -> dict:
    for phone in body.phones:
        try:
            phone.value = normalize_phone(phone.value, default_region)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid phone number: {phone.value}")
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
git commit -m "feat: normalize phone numbers on contact create"
```

---

### Task 6: Normalize phones on contact update

**Files:**
- Modify: `app/routers/contacts.py`
- Test: `tests/test_crud_endpoints.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_crud_endpoints.py` (after `test_update_contact_merges_and_sends_if_match`):

```python
@respx.mock
def test_update_contact_normalizes_phone(client):
    respx.get(BASE + "abc-123.vcf").mock(
        return_value=httpx.Response(200, text=EXISTING_VCF, headers={"ETag": '"v1"'})
    )
    put_route = respx.put(BASE + "abc-123.vcf").mock(return_value=httpx.Response(204))
    resp = client.put(
        "/api/addressbooks/default/contacts/abc-123",
        json={
            "firstname": "Anna",
            "lastname": "Kis",
            "phones": [{"type": "mobile", "value": "06301234567"}],
        },
    )
    assert resp.status_code == 200
    sent = put_route.calls.last.request.content.decode("utf-8")
    assert "+36301234567" in sent


@respx.mock
def test_update_contact_invalid_phone_is_422(client):
    respx.get(BASE + "abc-123.vcf").mock(
        return_value=httpx.Response(200, text=EXISTING_VCF, headers={"ETag": '"v1"'})
    )
    resp = client.put(
        "/api/addressbooks/default/contacts/abc-123",
        json={
            "firstname": "Anna",
            "lastname": "Kis",
            "phones": [{"type": "mobile", "value": "123"}],
        },
    )
    assert resp.status_code == 422
    assert "Invalid phone number" in resp.json()["detail"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_crud_endpoints.py -v`
Expected: `test_update_contact_normalizes_phone` FAILs; `test_update_contact_invalid_phone_is_422` FAILs (returns 200, not 422)

- [ ] **Step 3: Implement normalization in update_contact**

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
) -> dict:
    for phone in body.phones:
        try:
            phone.value = normalize_phone(phone.value, default_region)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid phone number: {phone.value}")
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
git commit -m "feat: normalize phone numbers on contact update"
```

---

### Task 7: Normalize phone filter on search

**Files:**
- Modify: `app/routers/contacts.py`
- Test: `tests/test_search_endpoint.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_search_endpoint.py` (after `test_search_not_found`):

```python
@respx.mock
def test_search_normalizes_phone_filter(client):
    route = respx.route(method="REPORT", url=BASE).mock(
        return_value=httpx.Response(207, text=MULTISTATUS_EMPTY)
    )
    resp = client.post(
        "/api/addressbooks/default/contacts/search",
        json={"phone": "06301234567"},
    )
    assert resp.status_code == 200
    sent = route.calls.last.request.content.decode("utf-8")
    assert "+36301234567" in sent
    assert resp.json()["searched_params"]["phone"] == "+36301234567"


def test_search_invalid_phone_is_422(client):
    resp = client.post(
        "/api/addressbooks/default/contacts/search",
        json={"phone": "123"},
    )
    assert resp.status_code == 422
    assert "Invalid phone number" in resp.json()["detail"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_search_endpoint.py -v`
Expected: `test_search_normalizes_phone_filter` FAILs (raw `06301234567` sent, `searched_params` shows raw value); `test_search_invalid_phone_is_422` FAILs (returns 200, not 422)

- [ ] **Step 3: Implement normalization in search_contacts**

In `app/routers/contacts.py`, update `search_contacts`:

```python
@router.post("/{book}/contacts/search", response_model=SearchResponse)
async def search_contacts(
    book: str,
    req: SearchRequest,
    dav: CardDAVClient = Depends(get_dav),
    name_format: str = Depends(get_name_format),
    default_region: str = Depends(get_default_region),
) -> SearchResponse:
    if req.phone:
        try:
            req.phone = normalize_phone(req.phone, default_region)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid phone number: {req.phone}")
    results = await dav.search(
        book,
        email=req.email,
        phone=req.phone,
        name=req.name,
        match_condition=req.match_condition,
    )
    matches = []
    for uid, vcf in results:
        contact = vcard_to_contact(vcf, name_format)
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_search_endpoint.py -v`
Expected: all passed

- [ ] **Step 5: Run the full suite to check for regressions**

Run: `.venv\Scripts\python.exe -m pytest tests -q`
Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add app/routers/contacts.py tests/test_search_endpoint.py
git commit -m "feat: normalize phone filter on contact search"
```

---

### Task 8: Documentation

**Files:**
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `docs/ideas.md`

- [ ] **Step 1: Document the env var in `.env.example`**

Add at the end of `.env.example`:

```
# Default region for phone number normalization (ISO 3166-1 alpha-2 code)
# Used when a phone number has no country code, e.g. "06301234567" -> "+36301234567"
DEFAULT_COUNTRY_CODE=HU
```

- [ ] **Step 2: Document the env var in `README.md`**

In the "Environment variables" table, add a row after `NAME_FORMAT`:

```markdown
| `DEFAULT_COUNTRY_CODE` | no | `HU` | ISO 3166-1 alpha-2 region used to normalize phone numbers without a country code |
```

Add a new subsection after "### NAME_FORMAT options":

```markdown
### Phone number normalization

Phone numbers in `phones[].value` are normalized to E.164 format
(`+<countrycode><number>`, no spaces) whenever a contact is created, updated,
or used as a search filter (`POST /contacts/search`). Numbers without a
country code are interpreted using `DEFAULT_COUNTRY_CODE`.

```
06301234567  →  +36301234567   (DEFAULT_COUNTRY_CODE=HU)
+36301234567 →  +36301234567   (already E.164, unchanged)
```

A phone number that cannot be parsed or validated for the configured region
returns `422` with `{"detail": "Invalid phone number: <value>"}`. The
free-text quick search (`GET /contacts?q=`) is not affected, since `q` may
match a name or email rather than a phone number.
```

- [ ] **Step 3: Check off the idea in `docs/ideas.md`**

Change:

```markdown
- [ ] **Telefonnormalizálás** — beíráskor automatikusan egységes formátumra hozza a számokat (pl. `06301234567` → `+36301234567`)
```

to:

```markdown
- [x] **Telefonnormalizálás** — beíráskor automatikusan egységes formátumra hozza a számokat (pl. `06301234567` → `+36301234567`)
```

- [ ] **Step 4: Commit**

```bash
git add .env.example README.md docs/ideas.md
git commit -m "docs: document phone normalization and DEFAULT_COUNTRY_CODE"
```

---

### Task 9: Final verification

- [ ] **Step 1: Run the full test suite**

Run: `.venv\Scripts\python.exe -m pytest tests -q`
Expected: all tests pass, no warnings about missing modules

- [ ] **Step 2: Confirm no leftover debug code**

Run: `git diff main --stat` (or `git log --oneline -10`) to review the full set of commits from this plan and confirm each one is scoped to its task.
