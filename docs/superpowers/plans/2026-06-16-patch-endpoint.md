# PATCH Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `PATCH /api/addressbooks/{book}/contacts/{uid}` so a single field (e.g. `org`) can be updated without resending the entire contact, unlike `PUT` which replaces every managed field.

**Architecture:** A new `ContactPatch` Pydantic model (all fields `Optional`) tracks exactly which fields were present in the request via Pydantic's `model_fields_set`. A new `apply_contact_patch()` function overlays only those fields onto the existing contact (fetched and parsed from the current vCard). The merged result is validated (name rule + `REQUIRED_FIELDS`) and handed to the *existing* `merge_contact_into_vcard()` — no new vCard-level merge logic is needed, since that function already accepts any `Contact` representing the desired final state.

**Tech Stack:** Pydantic v2 (`model_fields_set` for partial-update tracking), FastAPI `Depends`, existing vCard merge/normalize/required-fields helpers.

Spec: `docs/superpowers/specs/2026-06-16-patch-endpoint-design.md`

---

### Task 1: `ContactPatch` model + `apply_contact_patch()`

**Files:**
- Modify: `app/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_models.py`. First, update the import block at the top of the
file from:

```python
from app.models import (
    Address,
    Contact,
    ContactCreate,
    ContactIn,
    ContactOut,
    SearchRequest,
    TypedValue,
)
```

to:

```python
from app.models import (
    Address,
    Contact,
    ContactCreate,
    ContactIn,
    ContactOut,
    ContactPatch,
    SearchRequest,
    TypedValue,
    apply_contact_patch,
)
```

Then add these test functions at the end of the file:

```python
def test_contact_patch_rejects_empty_body():
    with pytest.raises(ValidationError):
        ContactPatch()


def test_contact_patch_accepts_single_field():
    p = ContactPatch(org="ACME")
    assert p.org == "ACME"
    assert "org" in p.model_fields_set


def test_apply_contact_patch_leaves_unset_fields_untouched():
    existing = Contact(firstname="Anna", lastname="Kis", org="Old Kft.")
    patch = ContactPatch(org="New Kft.")
    apply_contact_patch(existing, patch)
    assert existing.firstname == "Anna"
    assert existing.lastname == "Kis"
    assert existing.org == "New Kft."


def test_apply_contact_patch_clears_field_sent_as_empty_string():
    existing = Contact(firstname="Anna", org="ACME")
    patch = ContactPatch(org="")
    apply_contact_patch(existing, patch)
    assert existing.org == ""


def test_apply_contact_patch_clears_field_sent_as_null():
    existing = Contact(firstname="Anna", org="ACME")
    patch = ContactPatch(org=None)
    apply_contact_patch(existing, patch)
    assert existing.org == ""


def test_apply_contact_patch_replaces_list_field_wholesale():
    existing = Contact(emails=[TypedValue(type="work", value="old@ceg.hu")])
    patch = ContactPatch(emails=[TypedValue(type="home", value="new@ceg.hu")])
    apply_contact_patch(existing, patch)
    assert len(existing.emails) == 1
    assert existing.emails[0].value == "new@ceg.hu"


def test_apply_contact_patch_clears_list_field_sent_empty():
    existing = Contact(emails=[TypedValue(value="a@b.hu")])
    patch = ContactPatch(emails=[])
    apply_contact_patch(existing, patch)
    assert existing.emails == []


def test_apply_contact_patch_multiple_fields_at_once():
    existing = Contact(firstname="Anna", lastname="Kis", org="Old", title="Dev")
    patch = ContactPatch(org="New", title="Lead")
    apply_contact_patch(existing, patch)
    assert existing.org == "New"
    assert existing.title == "Lead"
    assert existing.firstname == "Anna"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'ContactPatch' from 'app.models'`

- [ ] **Step 3: Write the implementation**

In `app/models.py`, insert the following right after the `Contact` class
definition and before `class ContactIn(Contact):`:

```python
class ContactPatch(BaseModel):
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    middlename: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    emails: Optional[list[TypedValue]] = None
    phones: Optional[list[TypedValue]] = None
    addresses: Optional[list[Address]] = None
    org: Optional[str] = None
    title: Optional[str] = None
    birthday: Optional[str] = None
    urls: Optional[list[str]] = None
    note: Optional[str] = None
    photo: Optional[str] = None
    categories: Optional[list[str]] = None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "ContactPatch":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


_FIELD_DEFAULTS: dict[str, object] = {
    "firstname": "", "lastname": "", "middlename": "", "prefix": "", "suffix": "",
    "emails": [], "phones": [], "addresses": [], "org": "", "title": "",
    "birthday": "", "urls": [], "note": "", "photo": "", "categories": [],
}


def apply_contact_patch(existing: Contact, patch: ContactPatch) -> None:
    """Mutates `existing` in place, applying only the fields explicitly
    present in `patch` (per `model_fields_set`). A field provided as
    null/empty clears it; a field not provided is left untouched."""
    for name in patch.model_fields_set:
        value = getattr(patch, name)
        setattr(existing, name, value if value is not None else _FIELD_DEFAULTS[name])
```

The full `app/models.py` should now read, in order: `TypedValue`, `Address`,
`Contact`, `ContactPatch`, `_FIELD_DEFAULTS`, `apply_contact_patch`,
`ContactIn`, `ContactCreate`, `ContactOut`, `AddressbookInfo`,
`ContactsPage`, `SearchRequest`, `SearchMatch`, `SearchResponse` — i.e. every
class and function that already existed stays exactly where it was; you're
only inserting the new pieces between `Contact` and `ContactIn`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_models.py -v`
Expected: all passed

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `.venv\Scripts\python.exe -m pytest tests -q`
Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add app/models.py tests/test_models.py
git commit -m "feat: add ContactPatch model and apply_contact_patch() helper"
```

---

### Task 2: `PATCH /{book}/contacts/{uid}` router endpoint

**Files:**
- Modify: `app/routers/contacts.py`
- Create: `tests/test_patch_endpoint.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_patch_endpoint.py`:

```python
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
```

(`EXISTING_VCF` is imported from `tests/test_crud_endpoints.py`, where it's
already defined at module level — this mirrors how `tests/test_search_endpoint.py`
already imports fixtures from `tests/test_carddav_xml.py`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_patch_endpoint.py -v`
Expected: FAIL — `405 Method Not Allowed` on every test, since the `PATCH`
route doesn't exist yet.

- [ ] **Step 3: Implement the router endpoint**

In `app/routers/contacts.py`, update the `from app.models import (...)` block
from:

```python
from app.models import (
    AddressbookInfo,
    ContactCreate,
    ContactIn,
    ContactOut,
    ContactsPage,
    SearchMatch,
    SearchRequest,
    SearchResponse,
)
```

to:

```python
from app.models import (
    AddressbookInfo,
    ContactCreate,
    ContactIn,
    ContactOut,
    ContactPatch,
    ContactsPage,
    SearchMatch,
    SearchRequest,
    SearchResponse,
    apply_contact_patch,
)
```

Then add this new endpoint in `app/routers/contacts.py`, right after the
`update_contact` function and before `move_contact`:

```python
@router.patch("/{book}/contacts/{uid}")
async def patch_contact(
    book: str,
    uid: str,
    body: ContactPatch,
    dav: CardDAVClient = Depends(get_dav),
    name_format: str = Depends(get_name_format),
    default_region: str = Depends(get_default_region),
    required_fields: tuple[str, ...] = Depends(get_required_fields),
) -> dict:
    existing_vcf, etag = await dav.get(book, uid)
    existing_contact = vcard_to_contact(existing_vcf, name_format)
    apply_contact_patch(existing_contact, body)
    if "phones" in body.model_fields_set:
        for phone in existing_contact.phones:
            try:
                phone.value = normalize_phone(phone.value, default_region)
            except ValueError:
                raise HTTPException(status_code=422, detail=f"Invalid phone number: {phone.value}")
    if not (existing_contact.firstname or existing_contact.lastname):
        raise HTTPException(
            status_code=422, detail="At least one of firstname or lastname is required"
        )
    missing = missing_required_fields(existing_contact, required_fields)
    if missing:
        raise HTTPException(
            status_code=422, detail=f"Missing required field(s): {', '.join(missing)}"
        )
    merged_vcf = merge_contact_into_vcard(existing_vcf, existing_contact, name_format)
    await dav.update(book, uid, merged_vcf, etag)
    return {"status": "updated", "uid": uid}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_patch_endpoint.py -v`
Expected: all passed

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `.venv\Scripts\python.exe -m pytest tests -q`
Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add app/routers/contacts.py tests/test_patch_endpoint.py
git commit -m "feat: add PATCH endpoint for partial contact updates"
```

---

### Task 3: Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/ideas.md`

- [ ] **Step 1: Add the row to the endpoints overview table in `README.md`**

In the "## Endpoints overview" table, add a new row right after the `PUT` row:

```markdown
| `PATCH` | `/api/addressbooks/{book}/contacts/{uid}` | Partially update a contact |
```

- [ ] **Step 2: Add a new API Reference section in `README.md`**

Right after the "### PUT /api/addressbooks/{book}/contacts/{uid}" section
(after its `**Response ...**` line and the `---` separator that follows it,
i.e. as its own new section before "### POST /api/addressbooks/{book}/contacts/{uid}/move/{target_book}"),
add:

```markdown
### PATCH /api/addressbooks/{book}/contacts/{uid}

Partially updates a contact — only the fields included in the request body are
changed; everything else (including unmanaged `X-*` vCard properties) stays as
it was. Use this instead of `PUT` when you only need to change one or two
fields without resending the entire contact.

```bash
curl -X PATCH http://localhost:8000/api/addressbooks/leads/contacts/62352c20-... \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"org": "ACME Kft."}'
```

**Field semantics**

| Body state | Effect |
|---|---|
| Field absent from the JSON | Left untouched |
| Field present as `null`/`""`/`[]` | Cleared |
| Field present with a value | Replaced entirely (list fields are not merged item-by-item) |

At least one field must be present in the body, or the request returns `422`.

`firstname`/`lastname` and `REQUIRED_FIELDS` (see above) are validated against
the **resulting** contact, not the patch body alone — so patching just `org`
on a contact that already has a name succeeds without resending it. Validation
only fails if the patch itself drives the contact into an invalid state (e.g.
clearing both `firstname` and `lastname`, or clearing a field listed in
`REQUIRED_FIELDS`).

**Response `200`** `{"status": "updated", "uid": "..."}` · **`404`** not found
· **`409`** ETag mismatch · **`422`** empty body, invalid phone number, or the
resulting contact is missing a required field.

---
```

- [ ] **Step 3: Check off the idea in `docs/ideas.md`**

Change:

```markdown
- [ ] **`PATCH /api/contacts/{uid}`** — részleges frissítés csak a megadott mezőkre, szemben a PUT teljes felülírásával
```

to:

```markdown
- [x] **`PATCH /api/addressbooks/{book}/contacts/{uid}`** — részleges frissítés csak a megadott mezőkre, szemben a PUT teljes felülírásával
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/ideas.md
git commit -m "docs: document PATCH endpoint"
```

---

### Task 4: Final verification

- [ ] **Step 1: Run the full test suite**

Run: `.venv\Scripts\python.exe -m pytest tests -q`
Expected: all tests pass

- [ ] **Step 2: Confirm the commit history is scoped correctly**

Run: `git log --oneline -6` and confirm each commit from this plan is scoped
to its task (model + helper, router endpoint, docs).
