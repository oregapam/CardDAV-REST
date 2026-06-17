# Stats Endpoint Design

**Date:** 2026-06-17  
**Feature:** `GET /api/stats`

## Overview

Olcsó aggregátor endpoint: megmutatja az összes addressbook névjegyszámát, méretét és módosítási idejét — anélkül, hogy a vCard tartalmát letöltené. Hasznos n8n dashboardhoz és monitoring-hoz.

## Endpoint

```
GET /api/stats
```

**Response `200`:**
```json
{
  "total_contacts": 150,
  "total_size_bytes": 76800,
  "addressbooks": [
    {
      "name": "default",
      "displayname": "Default",
      "contact_count": 42,
      "last_modified": "2026-06-17T14:00:00+00:00",
      "oldest_modified": "2024-01-15T10:00:00+00:00",
      "total_size_bytes": 76800
    }
  ]
}
```

**Mezők:**

| Mező | Forrás | Viselkedés ha üres/hiányzó |
|------|--------|--------------------------|
| `contact_count` | .vcf resource-ok száma a PROPFIND response-ban | 0 |
| `last_modified` | .vcf resource-ok `getlastmodified` maximuma, ISO 8601 | `null` |
| `oldest_modified` | .vcf resource-ok `getlastmodified` minimuma, ISO 8601 | `null` |
| `total_size_bytes` | .vcf resource-ok `getcontentlength` összege | 0 |
| `total_contacts` | az összes addressbook `contact_count` összege | 0 |

**Response `502`:** ha a CardDAV szerver nem elérhető (meglévő UpstreamError handler kezeli)

## Implementáció

### Adatforrás: PROPFIND Depth:1

A stats adatok WebDAV metadata-ból jönnek — a vCard tartalmát **nem töltjük le**. Az összes szükséges adat lekérhető egyetlen PROPFIND kéréssel per addressbook:

```xml
<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:">
  <d:prop>
    <d:getetag/>
    <d:getlastmodified/>
    <d:getcontentlength/>
  </d:prop>
</d:propfind>
```

`PROPFIND` a `{principal}{book}/` URL-re, `Depth: 1` headerrel. A 207 Multistatus response a collection resource-t (href `/.../.../`) és a .vcf file-okat tartalmazza. A collection resource-t (href `/`-re végző) kiszűrjük, csak a `.vcf` file-ok számítanak bele a statisztikákba.

### Új függvény: `parse_stat_propfind()` — `app/carddav.py`

```python
def parse_stat_propfind(xml_text: str) -> tuple[int, str | None, str | None, int]:
    ...
```

Visszatér: `(contact_count, last_modified_iso, oldest_modified_iso, total_size_bytes)`.

- `getlastmodified` HTTP-date formátumból (`Mon, 17 Jun 2026 14:00:00 GMT`) ISO 8601-re konvertálva `email.utils.parsedate_to_datetime` segítségével
- Ha egy resource-nál hiányzik a `getlastmodified`, kihagyandó a min/max számításból
- `getcontentlength` hiánya: 0-nak számít az összegben

### Új metódus: `CardDAVClient.stat_book()` — `app/carddav.py`

```python
async def stat_book(self, book: str) -> tuple[int, str | None, str | None, int]:
    ...
```

PROPFIND `Depth: 1` → `parse_stat_propfind()` → tuple visszaadása.

### Új modellek — `app/models.py`

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

### Új router — `app/routers/stats.py`

`prefix="/api"`, `GET /stats`. Hívja `dav.list_addressbooks()`, majd minden bookra `dav.stat_book(name)`, aggregálja a totálokat.

### `app/main.py` frissítés

Stats router importálása és `app.include_router()`.

## Tesztelés

### Unit tesztek — `tests/test_carddav_xml.py`

`parse_stat_propfind()` XML parsing önállóan:
- 2 kontakt: count=2, total_size_bytes az összeg
- `last_modified` a frissebb kontakt dátuma
- `oldest_modified` a régebbi kontakt dátuma
- Üres könyv (csak collection resource): count=0, mindkettő=None, size=0
- Hiányzó `getcontentlength`: 0-nak számít, count helyes

### Integrációs tesztek — `tests/test_stats_endpoint.py`

respx mock-kal (PROPFIND method mockja: `respx.route(method="PROPFIND", url=...)`):
- Sikeres 1 könyv → 200, teljes response ellenőrzés
- 2 addressbook → `total_contacts` az összeg, `len(addressbooks)==2`
- Üres addressbook → `contact_count=0`, `last_modified=null`, `oldest_modified=null`
- Upstream hiba → 502
