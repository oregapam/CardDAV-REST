# Config Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `GET /api/config` endpoint, amely visszaadja az aktív `name_format`, `default_region` és `required_fields` beállításokat.

**Architecture:** Új `ConfigResponse` Pydantic modell az `app/models.py`-ban; új router `app/routers/config.py`-ban (ugyanolyan mintán, mint `stats.py`); regisztrálva `app/main.py`-ban. Nincs CardDAV hívás — az endpoint csak `request.app.state`-ből olvas.

**Tech Stack:** FastAPI, Pydantic v2, pytest + FastAPI `TestClient`, `conftest.py` `client_with_env` fixture.

---

### Task 1: ConfigResponse model + config router + endpoint (TDD)

**Files:**
- Modify: `app/models.py` (végéhez hozzáadni)
- Create: `app/routers/config.py`
- Modify: `app/main.py` (router regisztrálás)
- Create: `tests/test_config_endpoint.py`

#### Kontextus

A `conftest.py` (`tests/conftest.py`) három fixture-t definiál:
- `client` — API key-jel (`X-API-Key: test-key`), alap `TEST_ENV` env-vel
- `anon_client` — API key nélkül, alap `TEST_ENV` env-vel
- `client_with_env(extra_env: dict) -> TestClient` — factory, extra env vars merge-elve a `TEST_ENV`-be

Az alap `TEST_ENV`:
```python
TEST_ENV = {
    "BAIKAL_URL": "http://baikal/dav.php",
    "BAIKAL_USER": "testuser",
    "BAIKAL_PASS": "testpass",
    "API_KEY": "test-key",
    "NAME_FORMAT": "western",
}
```
Nincs benne `REQUIRED_FIELDS` és `DEFAULT_COUNTRY_CODE` — ezek defaultolnak (`""` ill. `"HU"`).

A `TestClient` context managerként is használható (`with client_with_env({}) as c:`).

A meglévő `app/models.py` végén (180. sor után) van a `StatsResponse` — az új `ConfigResponse` utána jön.

A meglévő `app/routers/stats.py` mintája:
```python
from fastapi import APIRouter, Request
router = APIRouter(prefix="/api", tags=["stats"])

@router.get("/stats", response_model=StatsResponse)
async def get_stats(dav: CardDAVClient = Depends(get_dav)) -> StatsResponse:
    ...
```

- [ ] **Step 1: Írj failing teszteket**

Hozd létre a `tests/test_config_endpoint.py` fájlt:

```python
def test_config_default_values(client_with_env):
    with client_with_env({}) as c:
        c.headers["X-API-Key"] = "test-key"
        resp = c.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name_format"] == "western"
    assert body["default_region"] == "HU"
    assert body["required_fields"] == []


def test_config_with_required_fields(client_with_env):
    with client_with_env({"REQUIRED_FIELDS": "emails,phones"}) as c:
        c.headers["X-API-Key"] = "test-key"
        resp = c.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["required_fields"] == ["emails", "phones"]


def test_config_requires_auth(anon_client):
    resp = anon_client.get("/api/config")
    assert resp.status_code == 401
```

- [ ] **Step 2: Futtasd a teszteket — verifykáld, hogy fail-elnek**

```
pytest tests/test_config_endpoint.py -v
```

Várt eredmény: mindhárom FAIL — `404` (endpoint nem létezik) vagy `ImportError`.

- [ ] **Step 3: Add hozzá a `ConfigResponse` modellt az `app/models.py` végéhez**

A `StatsResponse` blokk (177–180. sor) után:

```python
class ConfigResponse(BaseModel):
    name_format: str
    default_region: str
    required_fields: list[str]
```

- [ ] **Step 4: Hozd létre az `app/routers/config.py` fájlt**

```python
from fastapi import APIRouter, Request

from app.models import ConfigResponse

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config", response_model=ConfigResponse)
async def get_config(request: Request) -> ConfigResponse:
    return ConfigResponse(
        name_format=request.app.state.name_format,
        default_region=request.app.state.default_region,
        required_fields=list(request.app.state.required_fields),
    )
```

- [ ] **Step 5: Regisztráld a routert az `app/main.py`-ban**

A meglévő importok után (10–11. sor táján) add hozzá:

```python
from app.routers.config import router as config_router
```

A `app.include_router(stats_router)` sor (31. sor táján) után:

```python
app.include_router(config_router)
```

- [ ] **Step 6: Futtasd a teszteket — verifykáld, hogy pass-olnak**

```
pytest tests/test_config_endpoint.py -v
```

Várt eredmény: mindhárom PASS.

- [ ] **Step 7: Futtasd a teljes tesztsuite-ot**

```
pytest
```

Várt eredmény: minden teszt PASS (regresszió nincs).

- [ ] **Step 8: Commit**

```bash
git add tests/test_config_endpoint.py app/models.py app/routers/config.py app/main.py
git commit -m "feat: add GET /api/config endpoint"
```

---

### Task 2: Jelöld kész-nek az ideas.md-ben

**Files:**
- Modify: `docs/ideas.md`

- [ ] **Step 1: Keresd meg a sort és változtasd `- [x]`-re**

A `docs/ideas.md` Megfigyelhetőség szekciójában cseréld le:

```markdown
- [ ] **`GET /api/config`** — visszaadja az aktív `required_fields`, `default_region`, `name_format` beállításokat, hogy egy n8n node dinamikusan tudjon formot építeni (a `REQUIRED_FIELDS` jelenleg nem látszik az OpenAPI sémában)
```

erre:

```markdown
- [x] **`GET /api/config`** — visszaadja az aktív `required_fields`, `default_region`, `name_format` beállításokat, hogy egy n8n node dinamikusan tudjon formot építeni (a `REQUIRED_FIELDS` jelenleg nem látszik az OpenAPI sémában)
```

- [ ] **Step 2: Commit**

```bash
git add docs/ideas.md
git commit -m "docs: mark config endpoint as done"
```
