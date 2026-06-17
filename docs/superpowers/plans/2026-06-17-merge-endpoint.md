# Merge Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `POST /api/addressbooks/{book}/contacts/{uid}/merge/{other_uid}` that combines two duplicate contacts, keeps the primary, deletes the secondary.

**Architecture:** `merge_contacts()` pure function added to `app/models.py` handles the data merge logic; the router endpoint fetches both contacts, calls `merge_contacts()`, writes back via `merge_contact_into_vcard()` (preserving X-* fields), then deletes the secondary.

**Tech Stack:** FastAPI, Pydantic v2, vobject, respx (test mocking), pytest

---

## File Map

| File | Change |
|------|--------|
| `app/models.py` | Add `merge_contacts(primary, secondary) -> Contact` |
| `app/routers/contacts.py` | Add `merge_contact` endpoint + import `merge_contacts` |
| `tests/test_models.py` | Add unit tests for `merge_contacts()` |
| `tests/test_merge_endpoint.py` | New file — integration tests for the endpoint |
| `docs/ideas.md` | Mark merge item as done |

---

## Task 1: Unit tests for `merge_contacts()`

**Files:**
- Modify: `tests/test_models.py`

- [ ] **Step 1: Add unit tests to `tests/test_models.py`**

Append the following to the end of the file:

```python
from app.models import merge_contacts


def test_merge_scalar_primary_wins():
    primary = Contact(firstname="Anna", org="ACME")
    secondary = Contact(firstname="Anna", org="ACME Kft.", note="régi ügyfél")
    result = merge_contacts(primary, secondary)
    assert result.org == "ACME"
    assert result.note == "régi ügyfél"


def test_merge_scalar_secondary_fills_empty():
    primary = Contact(firstname="Anna", lastname="")
    secondary = Contact(firstname="Anna", lastname="Kis")
    result = merge_contacts(primary, secondary)
    assert result.lastname == "Kis"


def test_merge_emails_union():
    primary = Contact(emails=[TypedValue(type="work", value="anna@ceg.hu")])
    secondary = Contact(emails=[TypedValue(type="home", value="anna@gmail.com")])
    result = merge_contacts(primary, secondary)
    assert len(result.emails) == 2
    assert result.emails[0].value == "anna@ceg.hu"
    assert result.emails[1].value == "anna@gmail.com"


def test_merge_emails_dedup_exact_primary_type_wins():
    primary = Contact(emails=[TypedValue(type="work", value="anna@ceg.hu")])
    secondary = Contact(emails=[TypedValue(type="home", value="anna@ceg.hu")])
    result = merge_contacts(primary, secondary)
    assert len(result.emails) == 1
    assert result.emails[0].type == "work"


def test_merge_emails_dedup_case_insensitive():
    primary = Contact(emails=[TypedValue(type="work", value="Anna@Ceg.Hu")])
    secondary = Contact(emails=[TypedValue(type="home", value="anna@ceg.hu")])
    result = merge_contacts(primary, secondary)
    assert len(result.emails) == 1


def test_merge_phones_union():
    primary = Contact(phones=[])
    secondary = Contact(phones=[TypedValue(type="mobile", value="+36301234567")])
    result = merge_contacts(primary, secondary)
    assert len(result.phones) == 1
    assert result.phones[0].value == "+36301234567"


def test_merge_phones_dedup_primary_type_wins():
    primary = Contact(phones=[TypedValue(type="work", value="+36301234567")])
    secondary = Contact(phones=[TypedValue(type="mobile", value="+36301234567")])
    result = merge_contacts(primary, secondary)
    assert len(result.phones) == 1
    assert result.phones[0].type == "work"


def test_merge_addresses_union():
    addr1 = Address(type="home", street="Fő u. 1.", city="Budapest", zip="1011")
    addr2 = Address(type="work", street="Váci út 10.", city="Budapest", zip="1133")
    primary = Contact(addresses=[addr1])
    secondary = Contact(addresses=[addr2])
    result = merge_contacts(primary, secondary)
    assert len(result.addresses) == 2


def test_merge_addresses_dedup_by_street_city_zip():
    addr = Address(type="home", street="Fő u. 1.", city="Budapest", zip="1011")
    addr_dup = Address(type="work", street="Fő u. 1.", city="Budapest", zip="1011")
    primary = Contact(addresses=[addr])
    secondary = Contact(addresses=[addr_dup])
    result = merge_contacts(primary, secondary)
    assert len(result.addresses) == 1
    assert result.addresses[0].type == "home"


def test_merge_urls_union_and_dedup():
    primary = Contact(urls=["https://example.com"])
    secondary = Contact(urls=["https://example.com", "https://other.com"])
    result = merge_contacts(primary, secondary)
    assert len(result.urls) == 2
    assert "https://example.com" in result.urls
    assert "https://other.com" in result.urls


def test_merge_categories_union_and_dedup():
    primary = Contact(categories=["leads", "vip"])
    secondary = Contact(categories=["vip", "customers"])
    result = merge_contacts(primary, secondary)
    assert set(result.categories) == {"leads", "vip", "customers"}


def test_merge_does_not_mutate_inputs():
    primary = Contact(firstname="Anna", emails=[TypedValue(value="anna@ceg.hu")])
    secondary = Contact(firstname="Anna", emails=[TypedValue(value="anna@gmail.com")])
    merge_contacts(primary, secondary)
    assert len(primary.emails) == 1
```

- [ ] **Step 2: Verify the tests fail (function not yet defined)**

```
pytest tests/test_models.py -k "merge" -v
```

Expected: `ImportError` or `FAILED` — `merge_contacts` not found in `app.models`.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_models.py
git commit -m "test: add unit tests for merge_contacts()"
```

---

## Task 2: Implement `merge_contacts()` in `app/models.py`

**Files:**
- Modify: `app/models.py`

- [ ] **Step 1: Add `merge_contacts()` after `apply_contact_patch()`**

Insert after the `apply_contact_patch` function (after line 75), before `class ContactIn`:

```python
def merge_contacts(primary: Contact, secondary: Contact) -> Contact:
    result = primary.model_copy()

    for field in ("firstname", "lastname", "middlename", "prefix", "suffix",
                  "org", "title", "birthday", "note", "photo"):
        if not getattr(result, field):
            setattr(result, field, getattr(secondary, field))

    seen_emails = {e.value.lower() for e in result.emails}
    extra_emails = [e for e in secondary.emails if e.value.lower() not in seen_emails]
    result.emails = list(result.emails) + extra_emails

    seen_phones = {p.value for p in result.phones}
    extra_phones = [p for p in secondary.phones if p.value not in seen_phones]
    result.phones = list(result.phones) + extra_phones

    seen_addrs = {(a.street, a.city, a.zip) for a in result.addresses}
    extra_addrs = [a for a in secondary.addresses if (a.street, a.city, a.zip) not in seen_addrs]
    result.addresses = list(result.addresses) + extra_addrs

    seen_urls = set(result.urls)
    extra_urls = [u for u in secondary.urls if u not in seen_urls]
    result.urls = list(result.urls) + extra_urls

    seen_cats = set(result.categories)
    extra_cats = [c for c in secondary.categories if c not in seen_cats]
    result.categories = list(result.categories) + extra_cats

    return result
```

- [ ] **Step 2: Run unit tests**

```
pytest tests/test_models.py -k "merge" -v
```

Expected: all `merge_contacts` tests PASS.

- [ ] **Step 3: Run full test suite to check for regressions**

```
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add app/models.py
git commit -m "feat: add merge_contacts() to models"
```

---

## Task 3: Integration tests for the merge endpoint

**Files:**
- Create: `tests/test_merge_endpoint.py`

- [ ] **Step 1: Create `tests/test_merge_endpoint.py`**

```python
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
```

- [ ] **Step 2: Verify the tests fail (endpoint not yet defined)**

```
pytest tests/test_merge_endpoint.py -v
```

Expected: all tests FAIL with 404 or 405 (route not found).

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_merge_endpoint.py
git commit -m "test: add integration tests for merge endpoint"
```

---

## Task 4: Implement the merge endpoint in `app/routers/contacts.py`

**Files:**
- Modify: `app/routers/contacts.py`

- [ ] **Step 1: Add `merge_contacts` to the import from `app.models`**

In `app/routers/contacts.py`, replace the existing `from app.models import (...)` block with:

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
    merge_contacts,
)
```

- [ ] **Step 2: Add the merge endpoint after `patch_contact`**

Append the following after the `patch_contact` function and before `move_contact`:

```python
@router.post("/{book}/contacts/{uid}/merge/{other_uid}", response_model=ContactOut)
async def merge_contact(
    book: str,
    uid: str,
    other_uid: str,
    dav: CardDAVClient = Depends(get_dav),
    name_format: str = Depends(get_name_format),
) -> ContactOut:
    if uid == other_uid:
        raise HTTPException(status_code=422, detail="uid and other_uid must be different")
    primary_vcf, primary_etag = await dav.get(book, uid)
    secondary_vcf, _ = await dav.get(book, other_uid)
    primary = vcard_to_contact(primary_vcf, name_format)
    secondary = vcard_to_contact(secondary_vcf, name_format)
    merged = merge_contacts(primary, secondary)
    merged_vcf = merge_contact_into_vcard(primary_vcf, merged, name_format)
    await dav.update(book, uid, merged_vcf, primary_etag)
    await dav.delete(book, other_uid)
    contact_out = vcard_to_contact(merged_vcf, name_format)
    contact_out.uid = uid
    return contact_out
```

- [ ] **Step 3: Run integration tests**

```
pytest tests/test_merge_endpoint.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 4: Run full test suite**

```
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routers/contacts.py
git commit -m "feat: add merge endpoint"
```

---

## Task 5: Update docs

**Files:**
- Modify: `docs/ideas.md`

- [ ] **Step 1: Mark merge idea as done in `docs/ideas.md`**

Replace:
```markdown
- [ ] **`POST /api/addressbooks/{book}/contacts/{uid}/merge/{other_uid}`** — két duplikált kontakt összevonása (megtartja az egyiket, törli a másikat)
```

With:
```markdown
- [x] **`POST /api/addressbooks/{book}/contacts/{uid}/merge/{other_uid}`** — két duplikált kontakt összevonása (megtartja az egyiket, törli a másikat)
```

- [ ] **Step 2: Commit**

```bash
git add docs/ideas.md
git commit -m "docs: mark merge endpoint as done"
```
