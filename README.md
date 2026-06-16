# CardDAV-REST

FastAPI adapter that lets automation platforms (n8n) manage contacts on a
Baïkal CardDAV server through a clean JSON REST API. Phones keep syncing
natively over CardDAV; n8n never touches XML/WebDAV.

Multiple address books are supported — each book is a separate namespace in the
URL, so you can keep leads, customers, and personal contacts isolated while
managing them all through one adapter instance.

Design spec: `docs/superpowers/specs/2026-06-11-carddav-rest-adapter-design.md`

---

## Running

```bash
cp .env.example .env   # then edit values
docker build -t carddav-rest:latest .
docker compose up -d
```

First-time Baïkal setup: open http://localhost:8800, finish the wizard,
create the user and address books referenced in `.env`.

Interactive API docs (Swagger UI): **http://localhost:8000/docs**

---

## Authentication

Every `/api/*` endpoint requires the `X-API-Key` header. `/health`, `/docs`, and `/redoc` are public.

```bash
curl http://localhost:8000/api/addressbooks \
  -H "X-API-Key: your-api-key"
```

A missing or wrong key returns `401 Invalid or missing API key`.

---

## Endpoints overview

Quick reference for integration builders (e.g. an n8n node) — see "API Reference"
below for full request/response detail on each.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/addressbooks` | List available address books |
| `GET` | `/api/addressbooks/{book}/contacts` | List contacts (pagination + `q` quick search) |
| `POST` | `/api/addressbooks/{book}/contacts/search` | Structured search by email/phone/name |
| `POST` | `/api/addressbooks/{book}/contacts` | Create a contact |
| `GET` | `/api/addressbooks/{book}/contacts/{uid}/vcard` | Download raw vCard |
| `GET` | `/api/addressbooks/{book}/contacts/{uid}` | Get a contact |
| `PUT` | `/api/addressbooks/{book}/contacts/{uid}` | Update a contact |
| `POST` | `/api/addressbooks/{book}/contacts/{uid}/move/{target_book}` | Move a contact to another book |
| `DELETE` | `/api/addressbooks/{book}/contacts/{uid}` | Delete a contact |
| `GET` | `/health` | Health check (no API key) |

---

## API Reference

### GET /api/addressbooks

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

### GET /api/addressbooks/{book}/contacts

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

# Quick search — returns all contacts where name, email, or phone contains "anna"
curl "http://localhost:8000/api/addressbooks/leads/contacts?q=anna" \
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
      "fn": "Anna Kis",
      "firstname": "Anna",
      "lastname": "Kis",
      "emails": [{ "type": "work", "value": "anna@ceg.hu" }],
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

`total` is always the full count across all pages. `items` is empty when `offset` exceeds `total`,
and `warning` contains a human-readable message in that case.

---

### POST /api/addressbooks/{book}/contacts/search

Search for contacts by email, phone, and/or name. At least one filter is required.

#### `match_condition: "allof"` — AND logic (default)

Returns contacts that match **all** supplied filters simultaneously. Use this when
you know multiple attributes of the same person and want a precise hit.

```bash
curl -X POST http://localhost:8000/api/addressbooks/leads/contacts/search \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "anna@ceg.hu",
    "name": "Anna",
    "match_condition": "allof"
  }'
```

#### `match_condition: "anyof"` — OR logic

Returns contacts that match **at least one** of the supplied filters. Use this for
deduplication checks before creating a contact.

```bash
curl -X POST http://localhost:8000/api/addressbooks/leads/contacts/search \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "anna@ceg.hu",
    "phone": "+36301234567",
    "name": "Anna",
    "match_condition": "anyof"
  }'
```

**Filter semantics**

| Filter | Match type | Notes |
|--------|-----------|-------|
| `email` | Exact match | Case-insensitive |
| `phone` | Contains | Partial number works, e.g. `"1234567"`. Normalized to E.164 before searching — see [Phone number normalization](#phone-number-normalization) |
| `name` | Contains | Matches against the full name (FN field) |

**Response `200`**

```json
{
  "exists": true,
  "match_count": 1,
  "matches": [
    {
      "uid": "62352c20-a424-403a-8adb-00909bc483b8",
      "fn": "Anna Kis",
      "emails": [{ "type": "work", "value": "anna@ceg.hu" }],
      "phones": []
    }
  ],
  "searched_params": {
    "email": "anna@ceg.hu",
    "name": "Anna",
    "match_condition": "allof"
  }
}
```

---

### POST /api/addressbooks/{book}/contacts

Creates a new contact. `firstname` or `lastname` (or both) is required.

```bash
curl -X POST http://localhost:8000/api/addressbooks/leads/contacts \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "firstname": "Anna",
    "lastname": "Kis",
    "emails": [
      { "type": "work", "value": "anna@ceg.hu" }
    ],
    "phones": [
      { "type": "mobile", "value": "+36301234567" }
    ],
    "org": "ACME Kft.",
    "note": "VIP ügyfél",
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

#### `check_duplicates: true` — duplicate prevention

When set to `true`, the adapter searches for an existing contact with the same email
address **before** creating. If a match is found, it returns `409 Conflict` instead
of creating a duplicate.

```bash
curl -X POST http://localhost:8000/api/addressbooks/leads/contacts \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "firstname": "Anna",
    "lastname": "Kis",
    "emails": [{ "type": "work", "value": "anna@ceg.hu" }],
    "check_duplicates": true
  }'
```

**Response `409`** (if a contact with that email already exists)

```json
{
  "detail": {
    "error": "duplicate contact",
    "matched_email": "anna@ceg.hu",
    "existing_uid": "62352c20-a424-403a-8adb-00909bc483b8"
  }
}
```

#### Full contact fields reference

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
| `check_duplicates` | boolean | Default `false`; checks by email before creating |

---

### GET /api/addressbooks/{book}/contacts/{uid}/vcard

Downloads the raw vCard file for a contact.

```bash
curl http://localhost:8000/api/addressbooks/leads/contacts/62352c20.../vcard \
  -H "X-API-Key: $API_KEY" \
  -o contact.vcf
```

**Response `200`** — `text/vcard; charset=utf-8` body. Includes `ETag` and
`Content-Disposition: attachment; filename="<uid>.vcf"` headers.

**Response `404`** if the UID does not exist.

---

### GET /api/addressbooks/{book}/contacts/{uid}

Fetches a single contact by UID.

```bash
curl http://localhost:8000/api/addressbooks/leads/contacts/62352c20-... \
  -H "X-API-Key: $API_KEY"
```

**Response `200`** — full `ContactOut` object (same shape as the list endpoint, includes `etag`).

**Response `404`** if the UID does not exist.

---

### PUT /api/addressbooks/{book}/contacts/{uid}

Updates an existing contact. All managed fields are replaced; unmanaged vCard
properties (e.g. `X-*` custom fields) are preserved. The adapter fetches the
current ETag before writing and sends `If-Match` to prevent lost updates.

```bash
curl -X PUT http://localhost:8000/api/addressbooks/leads/contacts/62352c20-... \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "firstname": "Anna",
    "lastname": "Nagy"
  }'
```

**Response `200`** `{"status": "updated", "uid": "..."}` · **`404`** not found · **`409`** ETag mismatch.

---

### POST /api/addressbooks/{book}/contacts/{uid}/move/{target_book}

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

**Response `404`** if the source contact does not exist.  
**Response `409`** if a contact with the same UID already exists in the target book.

---

### DELETE /api/addressbooks/{book}/contacts/{uid}

Deletes a contact permanently.

```bash
curl -X DELETE \
  http://localhost:8000/api/addressbooks/leads/contacts/62352c20-... \
  -H "X-API-Key: $API_KEY"
```

**Response `200`** `{"status": "deleted", "uid": "..."}` · **`404`** not found.

---

### GET /health

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
| `422` | Validation error (missing required fields, no search filter, etc.) |
| `502` | CardDAV server unreachable or rejected credentials |

---

## Development

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt   # Windows
python -m pytest tests -v
```

---

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BAIKAL_URL` | yes | — | e.g. `http://baikal/dav.php` (internal Docker network) |
| `BAIKAL_USER` | yes | — | Baïkal user the adapter authenticates as |
| `BAIKAL_PASS` | yes | — | Baïkal password |
| `API_KEY` | yes | — | Key clients send in `X-API-Key` |
| `NAME_FORMAT` | no | `western` | Format of the vCard FN field — see below |
| `DEFAULT_COUNTRY_CODE` | no | `HU` | ISO 3166-1 alpha-2 region used to normalize phone numbers without a country code |
| `REQUIRED_FIELDS` | no | _(empty)_ | Comma-separated `Contact` field names that must be present — see below |

### NAME_FORMAT options

Controls how the full name (`fn`) field is assembled from the individual name parts.

| Value | Format | Example |
|-------|--------|---------|
| `western` | Prefix Firstname Middlename Lastname Suffix | `Dr. Anna Maria Kis PhD` |
| `eastern` | Lastname Firstname | `Kis Anna` |
| `eastern_full` | Prefix Lastname Firstname Suffix | `Dr. Kis Anna PhD` |

The structured name parts (`firstname`, `lastname`, etc.) are always stored separately
and are unaffected by this setting. Only the display name (`fn`) changes.

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
