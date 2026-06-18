# API Reference

Full request/response detail for every endpoint. For an interactive playground, open **http://localhost:8000/docs** (Swagger UI) after starting the adapter.

- [Authentication](#authentication)
- [GET /api/addressbooks](#get-apiadressbooks)
- [GET /api/addressbooks/{book}/contacts](#get-apiadressbooksbookcontacts)
- [POST /api/addressbooks/{book}/contacts/search](#post-apiadressbooksbookcontactssearch)
- [POST /api/addressbooks/{book}/contacts](#post-apiadressbooksbookcontacts)
- [GET /api/addressbooks/{book}/contacts/{uid}/vcard](#get-apiadressbooksbookcontactsuidvcard)
- [GET /api/addressbooks/{book}/contacts/{uid}](#get-apiadressbooksbookcontactsuid)
- [PUT /api/addressbooks/{book}/contacts/{uid}](#put-apiadressbooksbookcontactsuid)
- [PATCH /api/addressbooks/{book}/contacts/{uid}](#patch-apiadressbooksbookcontactsuid)
- [POST …/merge/{other_uid}](#post-mergeother_uid)
- [POST …/move/{target_book}](#post-movetarget_book)
- [DELETE /api/addressbooks/{book}/contacts/{uid}](#delete-apiadressbooksbookcontactsuid)
- [GET /api/stats](#get-apistats)
- [GET /api/config](#get-apiconfig)
- [GET /health](#get-health)
- [Error responses](#error-responses)

---

## Authentication

Every `/api/*` endpoint requires the `X-API-Key` header. `/health`, `/docs`, and `/redoc` are public.

```bash
curl http://localhost:8000/api/addressbooks \
  -H "X-API-Key: your-api-key"
```

A missing or wrong key returns `401 Invalid or missing API key`.

---

## GET /api/addressbooks

Lists all address books available for the configured Baïkal user.

```bash
curl http://localhost:8000/api/addressbooks \
  -H "X-API-Key: $API_KEY"
```

**Response `200`**

```json
[
  { "name": "default", "displayname": "Default" },
  { "name": "leads",   "displayname": "Leads" }
]
```

---

## GET /api/addressbooks/{book}/contacts

Returns contacts from the address book with pagination support.

| Parameter | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `limit` | integer | `50` | 1–1000 | Maximum number of contacts to return |
| `offset` | integer | `0` | ≥ 0 | Number of contacts to skip |
| `q` | string | — | — | Quick search: matches against name, email, and phone (contains, case-insensitive, OR logic) |

```bash
# First page
curl "http://localhost:8000/api/addressbooks/leads/contacts?limit=50&offset=0" \
  -H "X-API-Key: $API_KEY"

# Second page
curl "http://localhost:8000/api/addressbooks/leads/contacts?limit=50&offset=50" \
  -H "X-API-Key: $API_KEY"

# Quick search — returns all contacts where name, email, or phone contains "jane"
curl "http://localhost:8000/api/addressbooks/leads/contacts?q=jane" \
  -H "X-API-Key: $API_KEY"
```

**Response `200`**

```json
{
  "total": 142,
  "limit": 50,
  "offset": 0,
  "warning": null,
  "items": [
    {
      "uid": "62352c20-a424-403a-8adb-00909bc483b8",
      "fn": "Jane Smith",
      "firstname": "Jane",
      "lastname": "Smith",
      "emails": [{ "type": "work", "value": "jane@example.com" }],
      "phones": [],
      "addresses": [],
      "org": "",
      "title": "",
      "birthday": "",
      "urls": [],
      "note": "",
      "photo": "",
      "categories": [],
      "etag": ""
    }
  ]
}
```

`total` is always the full count across all pages. `items` is empty when `offset` exceeds `total`, and `warning` contains a human-readable message in that case.

---

## POST /api/addressbooks/{book}/contacts/search

Search for contacts by email, phone, and/or name. At least one filter is required.

### `match_condition: "allof"` — AND logic (default)

Returns contacts that match **all** supplied filters simultaneously. Use this when you know multiple attributes of the same person and want a precise hit.

```bash
curl -X POST http://localhost:8000/api/addressbooks/leads/contacts/search \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane@example.com",
    "name": "Jane",
    "match_condition": "allof"
  }'
```

### `match_condition: "anyof"` — OR logic

Returns contacts that match **at least one** of the supplied filters. Use this for deduplication checks before creating a contact.

```bash
curl -X POST http://localhost:8000/api/addressbooks/leads/contacts/search \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane@example.com",
    "phone": "+36301234567",
    "name": "Jane",
    "match_condition": "anyof"
  }'
```

**Filter semantics**

| Filter | Match type | Notes |
|--------|-----------|-------|
| `email` | Exact match | Case-insensitive |
| `phone` | Contains | Partial number works, e.g. `"1234567"`. Normalized to E.164 before searching. |
| `name` | Contains, word-order-independent | Multi-word queries require all words to appear in the full name, in any order. `"smith ja"` matches `"Jane Smith"`. |

**Response `200`**

```json
{
  "exists": true,
  "match_count": 1,
  "matches": [
    {
      "uid": "62352c20-a424-403a-8adb-00909bc483b8",
      "fn": "Jane Smith",
      "emails": [{ "type": "work", "value": "jane@example.com" }],
      "phones": []
    }
  ],
  "searched_params": {
    "email": "jane@example.com",
    "name": "Jane",
    "match_condition": "allof"
  }
}
```

---

## POST /api/addressbooks/{book}/contacts

Creates a new contact. `firstname` or `lastname` (or both) is required.

```bash
curl -X POST http://localhost:8000/api/addressbooks/leads/contacts \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "firstname": "Jane",
    "lastname": "Smith",
    "emails": [
      { "type": "work", "value": "jane@example.com" }
    ],
    "phones": [
      { "type": "mobile", "value": "+36301234567" }
    ],
    "org": "ACME Ltd.",
    "note": "VIP customer",
    "categories": ["leads", "vip"]
  }'
```

**Response `201`**

```json
{
  "status": "success",
  "uid": "62352c20-a424-403a-8adb-00909bc483b8",
  "filename": "62352c20-a424-403a-8adb-00909bc483b8.vcf"
}
```

### `check_duplicates: true` — duplicate prevention

When set to `true`, the adapter searches for an existing contact with the same email address **or phone number** before creating. If a match is found, it returns `409 Conflict` instead of creating a duplicate.

```bash
curl -X POST http://localhost:8000/api/addressbooks/leads/contacts \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "firstname": "Jane",
    "lastname": "Smith",
    "emails": [{ "type": "work", "value": "jane@example.com" }],
    "check_duplicates": true
  }'
```

**Response `409`** (duplicate matched by email)

```json
{
  "detail": {
    "error": "duplicate contact",
    "matched_email": "jane@example.com",
    "existing_uid": "62352c20-a424-403a-8adb-00909bc483b8"
  }
}
```

**Response `409`** (duplicate matched by phone)

```json
{
  "detail": {
    "error": "duplicate contact",
    "matched_phone": "+36301234567",
    "existing_uid": "62352c20-a424-403a-8adb-00909bc483b8"
  }
}
```

### Contact fields reference

| Field | Type | Notes |
|-------|------|-------|
| `firstname` | string | Required if `lastname` is empty |
| `lastname` | string | Required if `firstname` is empty |
| `middlename` | string | |
| `prefix` | string | e.g. `"Dr."` |
| `suffix` | string | e.g. `"Jr."` |
| `emails` | `[{type, value}]` | Types: `work`, `home`, `other` |
| `phones` | `[{type, value}]` | Types: `work`, `home`, `mobile`, `fax`, `other` |
| `addresses` | `[{type, street, city, zip, state, country}]` | Types: `work`, `home`, `other` |
| `org` | string | Company / organization |
| `title` | string | Job title |
| `birthday` | string | `YYYY-MM-DD` |
| `urls` | `[string]` | List of URLs |
| `note` | string | Free-text note |
| `photo` | string | URL or base64-encoded image |
| `categories` | `[string]` | Tags / groups |
| `check_duplicates` | boolean | Default `false`; checks by email and phone before creating |

---

## GET /api/addressbooks/{book}/contacts/{uid}/vcard

Downloads the raw vCard file for a contact.

```bash
curl http://localhost:8000/api/addressbooks/leads/contacts/62352c20.../vcard \
  -H "X-API-Key: $API_KEY" \
  -o contact.vcf
```

**Response `200`** — `text/vcard; charset=utf-8` body. Includes `ETag` and `Content-Disposition: attachment; filename="<uid>.vcf"` headers.

**Response `404`** if the UID does not exist.

---

## GET /api/addressbooks/{book}/contacts/{uid}

Fetches a single contact by UID.

```bash
curl http://localhost:8000/api/addressbooks/leads/contacts/62352c20-... \
  -H "X-API-Key: $API_KEY"
```

**Response `200`** — full `ContactOut` object (same shape as the list endpoint, includes `etag`).

**Response `404`** if the UID does not exist.

---

## PUT /api/addressbooks/{book}/contacts/{uid}

Updates an existing contact. All managed fields are replaced; unmanaged vCard properties (e.g. `X-*` custom fields) are preserved. The adapter fetches the current ETag before writing and sends `If-Match` to prevent lost updates.

```bash
curl -X PUT http://localhost:8000/api/addressbooks/leads/contacts/62352c20-... \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "firstname": "Jane",
    "lastname": "Doe"
  }'
```

**Response `200`** `{"status": "updated", "uid": "..."}` · **`404`** not found · **`409`** ETag mismatch.

---

## PATCH /api/addressbooks/{book}/contacts/{uid}

Partially updates a contact — only the fields included in the request body are changed; everything else (including unmanaged `X-*` vCard properties) stays as it was. Use this instead of `PUT` when you only need to change one or two fields without resending the entire contact.

```bash
curl -X PATCH http://localhost:8000/api/addressbooks/leads/contacts/62352c20-... \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"org": "ACME Ltd."}'
```

**Field semantics**

| Body state | Effect |
|---|---|
| Field absent from the JSON | Left untouched |
| Field present as `null`/`""`/`[]` | Cleared |
| Field present with a value | Replaced entirely (list fields are not merged item-by-item) |

At least one field must be present in the body, or the request returns `422`.

`firstname`/`lastname` and `REQUIRED_FIELDS` are validated against the **resulting** contact, not the patch body alone — so patching just `org` on a contact that already has a name succeeds without resending it.

**Response `200`** `{"status": "updated", "uid": "..."}` · **`404`** not found · **`409`** ETag mismatch · **`422`** empty body, invalid phone number, or the resulting contact is missing a required field.

---

## POST …/merge/{other_uid}

`POST /api/addressbooks/{book}/contacts/{uid}/merge/{other_uid}`

Merges two contacts into one. The contact at `uid` is kept and updated with data from `other_uid`; the contact at `other_uid` is then deleted.

**Merge strategy:** structured fields (`firstname`, `lastname`, `org`, etc.) are filled from `other_uid` only if the primary contact has them empty. List fields (`emails`, `phones`, `addresses`, `urls`, `categories`) are union-merged — duplicates are deduplicated (emails by lowercase value, phones by exact E.164 value, addresses by street+city+zip).

```bash
curl -X POST \
  "http://localhost:8000/api/addressbooks/leads/contacts/62352c20-.../merge/aabbcc11-..." \
  -H "X-API-Key: $API_KEY"
```

**Response `200`** — the merged contact as a full `ContactOut` object.

**Response `404`** if either UID does not exist. **Response `422`** if `uid` and `other_uid` are the same.

---

## POST …/move/{target_book}

`POST /api/addressbooks/{book}/contacts/{uid}/move/{target_book}`

Moves a contact from one address book to another. The UID is preserved.

```bash
curl -X POST \
  "http://localhost:8000/api/addressbooks/leads/contacts/62352c20-.../move/customers" \
  -H "X-API-Key: $API_KEY"
```

**Response `200`**

```json
{
  "status": "moved",
  "uid": "62352c20-...",
  "from": "leads",
  "to": "customers"
}
```

**Response `404`** if the source contact does not exist. **Response `409`** if a contact with the same UID already exists in the target book.

---

## DELETE /api/addressbooks/{book}/contacts/{uid}

Deletes a contact permanently.

```bash
curl -X DELETE \
  http://localhost:8000/api/addressbooks/leads/contacts/62352c20-... \
  -H "X-API-Key: $API_KEY"
```

**Response `200`** `{"status": "deleted", "uid": "..."}` · **`404`** not found.

---

## GET /api/stats

Returns contact counts, total vCard sizes, and modification timestamps for each address book — without downloading vCard content.

```bash
curl http://localhost:8000/api/stats \
  -H "X-API-Key: $API_KEY"
```

**Response `200`**

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

| Field | Description |
|-------|-------------|
| `total_contacts` | Sum of all contacts across all address books |
| `total_size_bytes` | Sum of all vCard file sizes in bytes |
| `contact_count` | Number of contacts in this address book |
| `last_modified` | ISO 8601 timestamp of the most recently modified contact, or `null` if empty |
| `oldest_modified` | ISO 8601 timestamp of the least recently modified contact, or `null` if empty |

**Response `502`** if the CardDAV server is unreachable.

---

## GET /api/config

Returns the active runtime configuration. Useful for nodes/clients that need to inspect `required_fields` at runtime (it is not visible in the OpenAPI schema).

```bash
curl http://localhost:8000/api/config \
  -H "X-API-Key: $API_KEY"
```

**Response `200`**

```json
{
  "name_format": "eastern",
  "default_region": "HU",
  "required_fields": ["emails", "phones"]
}
```

| Field | Description |
|-------|-------------|
| `name_format` | Active `NAME_FORMAT` value (`western`, `eastern`, or `eastern_full`) |
| `default_region` | Active `DEFAULT_COUNTRY_CODE` value |
| `required_fields` | Active `REQUIRED_FIELDS` as a list; empty list if not configured |

---

## GET /health

Health check, no API key required.

```bash
curl http://localhost:8000/health
```

**Response `200`** `{"status": "ok"}`

---

## Error responses

| Status | Meaning |
|--------|---------|
| `401` | Missing or invalid `X-API-Key` |
| `404` | Contact UID not found |
| `409` | Duplicate contact (create), ETag mismatch (update), or UID collision in target book (move) |
| `422` | Validation error (missing required fields, no search filter, empty phone/email value, etc.) |
| `502` | CardDAV server unreachable, rejected credentials, or rejected the vCard |

A `502` detail message passes through whatever the upstream CardDAV server reported. A sabre/dav-based server (like Baïkal) requires the vCard to contain exactly one `FN` property — the adapter always rebuilds `FN` from the structured name fields on every write, so this should not occur in practice.
