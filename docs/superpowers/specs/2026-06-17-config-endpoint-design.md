# Config Endpoint Design

**Date:** 2026-06-17  
**Feature:** `GET /api/config`

## Overview

Visszaadja az aktív runtime konfigurációs értékeket, hogy n8n node-ok dinamikusan tudjanak formot építeni. A `REQUIRED_FIELDS` jelenleg nem látszik az OpenAPI sémában — ez az endpoint teszi láthatóvá.

## Endpoint

```
GET /api/config
```

**Response `200`:**
```json
{
  "name_format": "western",
  "default_region": "HU",
  "required_fields": ["emails", "phones"]
}
```

**Mezők:**

| Mező | Forrás | Lehetséges értékek |
|------|--------|--------------------|
| `name_format` | `app.state.name_format` | `"western"`, `"eastern"`, `"eastern_full"` |
| `default_region` | `app.state.default_region` | ISO 3166-1 alpha-2 kód, pl. `"HU"` |
| `required_fields` | `app.state.required_fields` | `Contact` modell mezőnevei, üres lista ha nincs beállítva |

**Auth:** A meglévő `X-API-Key` middleware védi (nem szerepel a `public` path-ok közt).

**Nincs `502` eset** — az endpoint nem kommunikál a CardDAV szerverrel.

## Implementáció

### Új model — `app/models.py`

```python
class ConfigResponse(BaseModel):
    name_format: str
    default_region: str
    required_fields: list[str]
```

A `name_format` `str`-ként tárolódik (nem `Literal`), mert a modell csak az értéket adja vissza — a validáció a `Settings`-ben történik startup-kor.

### Új router — `app/routers/config.py`

`prefix="/api"`, `GET /config`. Olvassa `request.app.state`-ből a három értéket, visszaadja `ConfigResponse`-ként.

```python
@router.get("/config", response_model=ConfigResponse)
async def get_config(request: Request) -> ConfigResponse:
    return ConfigResponse(
        name_format=request.app.state.name_format,
        default_region=request.app.state.default_region,
        required_fields=list(request.app.state.required_fields),
    )
```

### `app/main.py` frissítés

`from app.routers.config import router as config_router` + `app.include_router(config_router)`.

## Tesztelés

### Unit teszt — `tests/test_config_endpoint.py`

`TestClient`-tel, `app.state` direkt beállításával:

- `test_config_returns_all_fields`: `name_format`, `default_region`, `required_fields` mind szerepel a response-ban
- `test_config_required_fields_empty`: ha `required_fields=()`, a response-ban `[]` jön
- `test_config_requires_auth`: `X-API-Key` nélkül `401`
