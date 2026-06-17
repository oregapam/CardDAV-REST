# Stats Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `GET /api/stats` that returns contact counts, size, and modification timestamps per addressbook — using PROPFIND metadata only (no vCard content fetched).

**Architecture:** New `parse_stat_propfind()` top-level function and `CardDAVClient.stat_book()` method in `app/carddav.py` handle the WebDAV layer. New `AddressbookStats`/`StatsResponse` Pydantic models in `app/models.py`. New `app/routers/stats.py` router registered in `main.py`.

**Tech Stack:** FastAPI, Pydantic v2, httpx, respx (test mocking), pytest, Python stdlib `email.utils`

---

## File Map

| File | Change |
|------|--------|
| `app/carddav.py` | Add `parse_stat_propfind()` top-level function + `stat_book()` method on `CardDAVClient` |
| `app/models.py` | Add `AddressbookStats`, `StatsResponse` Pydantic models |
| `app/routers/stats.py` | New file — `GET /api/stats` endpoint |
| `app/main.py` | Import and register stats router |
| `tests/test_carddav_xml.py` | Add `STAT_PROPFIND_*` XML fixtures + unit tests for `parse_stat_propfind()` |
| `tests/test_stats_endpoint.py` | New file — integration tests for `GET /api/stats` |
| `docs/ideas.md` | Mark stats item as done |

---

## Task 1: Unit tests for `parse_stat_propfind()`

**Files:**
- Modify: `tests/test_carddav_xml.py`

- [ ] **Step 1: Add XML fixtures and unit tests to `tests/test_carddav_xml.py`**

Append to the end of `tests/test_carddav_xml.py`:

```python
from app.carddav import parse_stat_propfind

STAT_PROPFIND_TWO = (
    '<?xml version="1.0"?>'
    '<d:multistatus xmlns:d="DAV:">'
    '<d:response>'
    '<d:href>/dav.php/addressbooks/testuser/default/</d:href>'
    '<d:propstat><d:prop>'
    '<d:getlastmodified>Mon, 17 Jun 2026 14:00:00 GMT</d:getlastmodified>'
    '</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>'
    '</d:response>'
    '<d:response>'
    '<d:href>/dav.php/addressbooks/testuser/default/uid1.vcf</d:href>'
    '<d:propstat><d:prop>'
    '<d:getetag>"etag-1"</d:getetag>'
    '<d:getlastmodified>Mon, 17 Jun 2026 14:00:00 GMT</d:getlastmodified>'
    '<d:getcontentlength>512</d:getcontentlength>'
    '</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>'
    '</d:response>'
    '<d:response>'
    '<d:href>/dav.php/addressbooks/testuser/default/uid2.vcf</d:href>'
    '<d:propstat><d:prop>'
    '<d:getetag>"etag-2"</d:getetag>'
    '<d:getlastmodified>Tue, 15 Jan 2024 10:00:00 GMT</d:getlastmodified>'
    '<d:getcontentlength>256</d:getcontentlength>'
    '</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>'
    '</d:response>'
    '</d:multistatus>'
)

STAT_PROPFIND_EMPTY = (
    '<?xml version="1.0"?>'
    '<d:multistatus xmlns:d="DAV:">'
    '<d:response>'
    '<d:href>/dav.php/addressbooks/testuser/default/</d:href>'
    '<d:propstat><d:prop>'
    '<d:getlastmodified>Mon, 17 Jun 2026 14:00:00 GMT</d:getlastmodified>'
    '</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>'
    '</d:response>'
    '</d:multistatus>'
)

STAT_PROPFIND_NO_CONTENTLENGTH = (
    '<?xml version="1.0"?>'
    '<d:multistatus xmlns:d="DAV:">'
    '<d:response>'
    '<d:href>/dav.php/addressbooks/testuser/default/</d:href>'
    '<d:propstat><d:prop>'
    '</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>'
    '</d:response>'
    '<d:response>'
    '<d:href>/dav.php/addressbooks/testuser/default/uid1.vcf</d:href>'
    '<d:propstat><d:prop>'
    '<d:getetag>"etag-1"</d:getetag>'
    '</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>'
    '</d:response>'
    '</d:multistatus>'
)


def test_parse_stat_propfind_count_and_size():
    count, last_mod, oldest_mod, total_size = parse_stat_propfind(STAT_PROPFIND_TWO)
    assert count == 2
    assert total_size == 768


def test_parse_stat_propfind_last_modified():
    _, last_mod, _, _ = parse_stat_propfind(STAT_PROPFIND_TWO)
    assert last_mod is not None
    assert last_mod.startswith("2026-06-17")


def test_parse_stat_propfind_oldest_modified():
    _, _, oldest_mod, _ = parse_stat_propfind(STAT_PROPFIND_TWO)
    assert oldest_mod is not None
    assert oldest_mod.startswith("2024-01-15")


def test_parse_stat_propfind_empty_book():
    count, last_mod, oldest_mod, total_size = parse_stat_propfind(STAT_PROPFIND_EMPTY)
    assert count == 0
    assert last_mod is None
    assert oldest_mod is None
    assert total_size == 0


def test_parse_stat_propfind_no_content_length():
    count, _, _, total_size = parse_stat_propfind(STAT_PROPFIND_NO_CONTENTLENGTH)
    assert count == 1
    assert total_size == 0
```

- [ ] **Step 2: Verify the tests fail (`parse_stat_propfind` not yet defined)**

```
pytest tests/test_carddav_xml.py -k "stat" -v
```

Expected: `ImportError` — `parse_stat_propfind` not found in `app.carddav`.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_carddav_xml.py
git commit -m "test: add unit tests for parse_stat_propfind()"
```

---

## Task 2: Implement `parse_stat_propfind()`, `stat_book()`, and Pydantic models

**Files:**
- Modify: `app/carddav.py`
- Modify: `app/models.py`

- [ ] **Step 1: Add `parse_stat_propfind()` to `app/carddav.py`**

Add this import at the top of `app/carddav.py` (after the existing imports):

```python
from email.utils import parsedate_to_datetime
```

Add this function after `parse_addressbooks()` (before the `logger = ...` line):

```python
def parse_stat_propfind(xml_text: str) -> tuple[int, str | None, str | None, int]:
    root = ET.fromstring(xml_text)
    contact_count = 0
    total_size = 0
    timestamps: list[str] = []

    for response in root.findall("d:response", NS):
        href = response.findtext("d:href", "", NS)
        if href.endswith("/"):
            continue
        contact_count += 1
        lm = response.findtext(".//d:getlastmodified", None, NS)
        if lm:
            timestamps.append(lm)
        cl = response.findtext(".//d:getcontentlength", None, NS)
        if cl:
            total_size += int(cl)

    if not timestamps:
        return contact_count, None, None, total_size

    def to_iso(http_date: str) -> str:
        return parsedate_to_datetime(http_date).isoformat()

    last_mod = to_iso(max(timestamps, key=lambda d: parsedate_to_datetime(d)))
    oldest_mod = to_iso(min(timestamps, key=lambda d: parsedate_to_datetime(d)))
    return contact_count, last_mod, oldest_mod, total_size
```

- [ ] **Step 2: Add `stat_book()` method to `CardDAVClient` in `app/carddav.py`**

Add after the `delete()` method:

```python
async def stat_book(self, book: str) -> tuple[int, str | None, str | None, int]:
    body = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<d:propfind xmlns:d="DAV:">'
        "<d:prop><d:getetag/><d:getlastmodified/><d:getcontentlength/></d:prop>"
        "</d:propfind>"
    )
    resp = await self._request(
        "PROPFIND",
        self._book_url(book),
        content=body.encode("utf-8"),
        headers={"Depth": "1", "Content-Type": "application/xml; charset=utf-8"},
    )
    return parse_stat_propfind(resp.text)
```

- [ ] **Step 3: Add `AddressbookStats` and `StatsResponse` to `app/models.py`**

Append after the `SearchResponse` class (end of file):

```python
class AddressbookStats(BaseModel):
    name: str
    displayname: str
    contact_count: int
    last_modified: str | None
    oldest_modified: str | None
    total_size_bytes: int


class StatsResponse(BaseModel):
    total_contacts: int
    total_size_bytes: int
    addressbooks: list[AddressbookStats]
```

- [ ] **Step 4: Run unit tests**

```
pytest tests/test_carddav_xml.py -k "stat" -v
```

Expected: all 5 `parse_stat_propfind` tests PASS.

- [ ] **Step 5: Run full suite to check for regressions**

```
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add app/carddav.py app/models.py
git commit -m "feat: add parse_stat_propfind(), stat_book(), and stats models"
```

---

## Task 3: Integration tests for `GET /api/stats`

**Files:**
- Create: `tests/test_stats_endpoint.py`

- [ ] **Step 1: Create `tests/test_stats_endpoint.py`**

```python
import httpx
import respx

from tests.conftest import BASE, PRINCIPAL
from tests.test_carddav_xml import PROPFIND_ADDRESSBOOKS, STAT_PROPFIND_EMPTY, STAT_PROPFIND_TWO

LEADS_URL = PRINCIPAL + "leads/"

PROPFIND_ONE_BOOK = (
    '<?xml version="1.0"?>'
    '<d:multistatus xmlns:d="DAV:">'
    '<d:response>'
    '<d:href>/dav.php/addressbooks/testuser/</d:href>'
    '<d:propstat><d:prop><d:displayname>testuser</d:displayname></d:prop>'
    '<d:status>HTTP/1.1 200 OK</d:status></d:propstat>'
    '</d:response>'
    '<d:response>'
    '<d:href>/dav.php/addressbooks/testuser/default/</d:href>'
    '<d:propstat><d:prop><d:displayname>Default</d:displayname></d:prop>'
    '<d:status>HTTP/1.1 200 OK</d:status></d:propstat>'
    '</d:response>'
    '</d:multistatus>'
)


@respx.mock
def test_stats_success(client):
    respx.route(method="PROPFIND", url=PRINCIPAL).mock(
        return_value=httpx.Response(207, text=PROPFIND_ONE_BOOK)
    )
    respx.route(method="PROPFIND", url=BASE).mock(
        return_value=httpx.Response(207, text=STAT_PROPFIND_TWO)
    )
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_contacts"] == 2
    assert body["total_size_bytes"] == 768
    assert len(body["addressbooks"]) == 1
    book = body["addressbooks"][0]
    assert book["name"] == "default"
    assert book["contact_count"] == 2
    assert book["last_modified"].startswith("2026-06-17")
    assert book["oldest_modified"].startswith("2024-01-15")
    assert book["total_size_bytes"] == 768


@respx.mock
def test_stats_two_books_aggregates_total(client):
    respx.route(method="PROPFIND", url=PRINCIPAL).mock(
        return_value=httpx.Response(207, text=PROPFIND_ADDRESSBOOKS)
    )
    respx.route(method="PROPFIND", url=BASE).mock(
        return_value=httpx.Response(207, text=STAT_PROPFIND_TWO)
    )
    respx.route(method="PROPFIND", url=LEADS_URL).mock(
        return_value=httpx.Response(207, text=STAT_PROPFIND_EMPTY)
    )
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_contacts"] == 2
    assert len(body["addressbooks"]) == 2


@respx.mock
def test_stats_empty_book(client):
    respx.route(method="PROPFIND", url=PRINCIPAL).mock(
        return_value=httpx.Response(207, text=PROPFIND_ONE_BOOK)
    )
    respx.route(method="PROPFIND", url=BASE).mock(
        return_value=httpx.Response(207, text=STAT_PROPFIND_EMPTY)
    )
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_contacts"] == 0
    book = body["addressbooks"][0]
    assert book["contact_count"] == 0
    assert book["last_modified"] is None
    assert book["oldest_modified"] is None
    assert book["total_size_bytes"] == 0


@respx.mock
def test_stats_upstream_error_is_502(client):
    respx.route(method="PROPFIND", url=PRINCIPAL).mock(
        side_effect=httpx.ConnectError("boom")
    )
    resp = client.get("/api/stats")
    assert resp.status_code == 502
```

- [ ] **Step 2: Verify the tests fail (endpoint not yet defined)**

```
pytest tests/test_stats_endpoint.py -v
```

Expected: all tests FAIL with 404 (route not found) or `MissingPatternError`.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_stats_endpoint.py
git commit -m "test: add integration tests for GET /api/stats"
```

---

## Task 4: Implement `app/routers/stats.py` and update `main.py`

**Files:**
- Create: `app/routers/stats.py`
- Modify: `app/main.py`

- [ ] **Step 1: Create `app/routers/stats.py`**

```python
from fastapi import APIRouter, Depends, Request

from app.carddav import CardDAVClient
from app.models import AddressbookStats, StatsResponse

router = APIRouter(prefix="/api", tags=["stats"])


def get_dav(request: Request) -> CardDAVClient:
    return request.app.state.carddav


@router.get("/stats", response_model=StatsResponse)
async def get_stats(dav: CardDAVClient = Depends(get_dav)) -> StatsResponse:
    books = await dav.list_addressbooks()
    addressbook_stats = []
    total_contacts = 0
    total_size = 0
    for book in books:
        count, last_mod, oldest_mod, size = await dav.stat_book(book["name"])
        total_contacts += count
        total_size += size
        addressbook_stats.append(AddressbookStats(
            name=book["name"],
            displayname=book["displayname"],
            contact_count=count,
            last_modified=last_mod,
            oldest_modified=oldest_mod,
            total_size_bytes=size,
        ))
    return StatsResponse(
        total_contacts=total_contacts,
        total_size_bytes=total_size,
        addressbooks=addressbook_stats,
    )
```

- [ ] **Step 2: Update `app/main.py` to register the stats router**

In `app/main.py`, replace:

```python
from app.routers.contacts import router as contacts_router
```

With:

```python
from app.routers.contacts import router as contacts_router
from app.routers.stats import router as stats_router
```

And replace:

```python
    app.include_router(contacts_router)
```

With:

```python
    app.include_router(contacts_router)
    app.include_router(stats_router)
```

- [ ] **Step 3: Run integration tests**

```
pytest tests/test_stats_endpoint.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 4: Run full test suite**

```
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/routers/stats.py app/main.py
git commit -m "feat: add GET /api/stats endpoint"
```

---

## Task 5: Update docs

**Files:**
- Modify: `docs/ideas.md`

- [ ] **Step 1: Mark stats idea as done in `docs/ideas.md`**

Replace:

```markdown
- [ ] **`GET /api/stats`** — kontaktok száma, utolsó módosítás (hasznos n8n dashboardhoz)
```

With:

```markdown
- [x] **`GET /api/stats`** — kontaktok száma, utolsó módosítás (hasznos n8n dashboardhoz)
```

- [ ] **Step 2: Commit**

```bash
git add docs/ideas.md
git commit -m "docs: mark stats endpoint as done"
```
