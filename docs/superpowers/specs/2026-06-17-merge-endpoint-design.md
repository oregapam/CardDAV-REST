# Merge Endpoint Design

**Date:** 2026-06-17  
**Feature:** `POST /api/addressbooks/{book}/contacts/{uid}/merge/{other_uid}`

## Overview

Két duplikált névjegy összevonása egy műveleten belül. A primary (`uid`) megmarad az összevont adatokkal, a secondary (`other_uid`) törlődik.

## Endpoint

```
POST /api/addressbooks/{book}/contacts/{uid}/merge/{other_uid}
```

- `uid` — a megmaradó (primary) névjegy UID-je
- `other_uid` — a törlendő (secondary) névjegy UID-je
- Mindkettő ugyanabból a `{book}`-ból töltődik be; cross-book merge nem támogatott (az URL struktúra inherensen kikényszeríti)

**Response `200`:** `ContactOut` — az összevont névjegy teljes adataival  
**Response `404`:** ha `uid` vagy `other_uid` nem létezik a könyvben  
**Response `409`:** ETag mismatch az írásnál (concurrent módosítás)  
**Response `422`:** ha `uid == other_uid`

## Merge stratégia

### Skalár mezők

`firstname`, `lastname`, `middlename`, `prefix`, `suffix`, `org`, `title`, `birthday`, `note`, `photo`

- Primary értéke marad
- Ha primary üres string (`""`), secondary tölti ki

### Lista mezők

Union, érték alapján deduplikálva. Primary elemei kerülnek be először; secondary elemei közül csak azok, amelyek értéke még nem szerepel.

| Mező | Dedup kulcs |
|------|-------------|
| `emails` | `value` (case-insensitive) |
| `phones` | `value` (egzakt, E.164 normalizált) |
| `addresses` | `(street, city, zip)` kombináció |
| `urls` | egzakt string |
| `categories` | egzakt string |

Ütközés (azonos value, eltérő type): primary type-ja marad.

## Implementáció

### Új függvény: `merge_contacts()` — `app/models.py`

```python
def merge_contacts(primary: Contact, secondary: Contact) -> Contact:
    ...
```

Tiszta függvény, két `Contact` objektumot kap, egy harmadikat ad vissza. Mellé kerül az `apply_contact_patch()` mellé.

### Router flow — `app/routers/contacts.py`

1. `dav.get(book, uid)` → `primary_vcf`, `primary_etag`
2. `dav.get(book, other_uid)` → `secondary_vcf`
3. `primary = vcard_to_contact(primary_vcf, name_format)`
4. `secondary = vcard_to_contact(secondary_vcf, name_format)`
5. `merged = merge_contacts(primary, secondary)`
6. `merged_vcf = merge_contact_into_vcard(primary_vcf, merged, name_format)` — X-* mezők megőrzése
7. `dav.update(book, uid, merged_vcf, primary_etag)`
8. `dav.delete(book, other_uid)`
9. `contact_out = vcard_to_contact(merged_vcf, name_format)` → return `ContactOut`

## Tesztelés

### Unit tesztek — `tests/test_models.py`

`merge_contacts()` önállóan:
- Skalár: primary nyer ha nem üres, secondary tölti ki ha üres
- Lista union: emails, phones, urls, categories összevonás
- Dedup: egzakt egyezés kiszűrése
- Dedup: eltérő type-os ütközés → primary type marad
- Addresses dedup `(street, city, zip)` alapján

### Integrációs tesztek — `tests/test_merge_endpoint.py`

Mock CardDAV client-tel:
- Sikeres merge → 200 + ContactOut
- `uid == other_uid` → 422
- Ismeretlen `uid` → 404
- Ismeretlen `other_uid` → 404
