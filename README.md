# CardDAV-REST

FastAPI adapter that lets automation platforms (n8n) manage contacts on a
Baïkal CardDAV server through a clean JSON REST API. Phones keep syncing
natively over CardDAV; n8n never touches XML/WebDAV.

Design spec: `docs/superpowers/specs/2026-06-11-carddav-rest-adapter-design.md`

---

## Running

```bash
cp .env.example .env   # then edit values
docker build -t carddav-rest:latest .
docker compose up -d
```

First-time Baïkal setup: open http://localhost:8800, finish the wizard,
create the user and address book referenced in `.env`.

Interactive API docs (Swagger UI): **http://localhost:8000/docs**

---

## Authentication

Every `/api/*` endpoint requires the `X-API-Key` header. `/health`, `/docs`, and `/redoc` are public.

```bash
curl http://localhost:8000/api/contacts \
  -H "X-API-Key: your-api-key"
```

A missing or wrong key returns `401 Invalid or missing API key`.

---

## API Reference

### GET /api/contacts

Returns every contact in the address book as a JSON array.

```bash
curl http://localhost:8000/api/contacts \
  -H "X-API-Key: $API_KEY"
```

**Response `200`**

```json
[
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
```

Returns an empty array `[]` if the address book has no contacts.

---

### POST /api/contacts/search

Search for contacts by email, phone, and/or name. At least one filter is required.

#### `match_condition: "allof"` — AND logic (default)

Returns contacts that match **all** supplied filters simultaneously. Use this when
you know multiple attributes of the same person and want a precise hit.

```bash
# Contact must have this exact email AND their name must contain "Anna"
curl -X POST http://localhost:8000/api/contacts/search \
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
deduplication checks before creating a contact: if you supply all known identifiers,
you will catch any existing record that shares even one of them.

```bash
# Contact has this email OR this phone number OR their name contains "Anna"
curl -X POST http://localhost:8000/api/contacts/search \
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
| `phone` | Contains | Partial number works, e.g. `"1234567"` |
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

When there are no results, `exists` is `false`, `match_count` is `0`, and `matches` is `[]`.

---

### POST /api/contacts

Creates a new contact. `firstname` or `lastname` (or both) is required.

```bash
curl -X POST http://localhost:8000/api/contacts \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "firstname": "Anna",
    "lastname": "Kis",
    "emails": [
      { "type": "work", "value": "anna@ceg.hu" },
      { "type": "home", "value": "anna@gmail.com" }
    ],
    "phones": [
      { "type": "mobile", "value": "+36301234567" }
    ],
    "org": "ACME Kft.",
    "title": "Értékesítési vezető",
    "birthday": "1990-05-14",
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
of creating a duplicate. This is the recommended setting in any automated workflow
(e.g. n8n form submissions) where the same person may be submitted more than once.

Without this flag, every call creates a new record regardless of whether an identical
contact already exists. Two contacts with the same email address are then
indistinguishable — resolving them later requires manual cleanup.

```bash
curl -X POST http://localhost:8000/api/contacts \
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

Use the returned `existing_uid` to fetch or update the existing record instead of
creating a new one.

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

### GET /api/contacts/{uid}/vcard

Downloads the raw vCard file for a contact. Useful when another tool (e.g. n8n HTTP node) needs the original `.vcf` content directly.

```bash
curl http://localhost:8000/api/contacts/62352c20-a424-403a-8adb-00909bc483b8/vcard \
  -H "X-API-Key: $API_KEY" \
  -o contact.vcf
```

**Response `200`** — `text/vcard; charset=utf-8` body with the raw vCard text. Includes `ETag` and `Content-Disposition: attachment; filename="<uid>.vcf"` headers.

**Response `404`** if the UID does not exist.

---

### GET /api/contacts/{uid}

Fetches a single contact by UID.

```bash
curl http://localhost:8000/api/contacts/62352c20-a424-403a-8adb-00909bc483b8 \
  -H "X-API-Key: $API_KEY"
```

**Response `200`** — full `ContactOut` object (same shape as the list endpoint, includes `etag`).

**Response `404`** if the UID does not exist.

---

### PUT /api/contacts/{uid}

Updates an existing contact. The request body contains only the fields you want to
change — all other fields keep their current values. Fields managed by the adapter
(name, email, phone, etc.) are replaced; unmanaged fields in the vCard (e.g. `X-*`
custom properties) are preserved untouched.

The adapter fetches the current ETag before writing and sends `If-Match` to prevent
lost updates if the contact was modified concurrently (e.g. by a phone sync).

```bash
# Change only the last name; everything else stays the same
curl -X PUT http://localhost:8000/api/contacts/62352c20-a424-403a-8adb-00909bc483b8 \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "firstname": "Anna",
    "lastname": "Nagy"
  }'
```

**Response `200`**

```json
{
  "status": "updated",
  "uid": "62352c20-a424-403a-8adb-00909bc483b8"
}
```

**Response `404`** if the UID does not exist.  
**Response `409`** if the contact was modified between your GET and PUT (ETag mismatch).

---

### DELETE /api/contacts/{uid}

Deletes a contact permanently.

```bash
curl -X DELETE http://localhost:8000/api/contacts/62352c20-a424-403a-8adb-00909bc483b8 \
  -H "X-API-Key: $API_KEY"
```

**Response `200`**

```json
{
  "status": "deleted",
  "uid": "62352c20-a424-403a-8adb-00909bc483b8"
}
```

**Response `404`** if the UID does not exist.

---

### GET /health

Health check, no API key required.

```bash
curl http://localhost:8000/health
```

**Response `200`**

```json
{ "status": "ok" }
```

---

## Error responses

| Status | Meaning |
|--------|---------|
| `401` | Missing or invalid `X-API-Key` |
| `404` | Contact UID not found |
| `409` | Duplicate contact (create) or ETag mismatch (update) |
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
| `BAIKAL_ADDRESSBOOK` | no | `default` | Address book id |
| `API_KEY` | yes | — | Key clients send in `X-API-Key` |
| `NAME_FORMAT` | no | `western` | Format of the vCard FN field — see below |

### NAME_FORMAT options

Controls how the full name (`fn`) field is assembled from the individual name parts.

| Value | Format | Example |
|-------|--------|---------|
| `western` | Prefix Firstname Middlename Lastname Suffix | `Dr. Anna Maria Kis PhD` |
| `eastern` | Lastname Firstname | `Kis Anna` |
| `eastern_full` | Prefix Lastname Firstname Suffix | `Dr. Kis Anna PhD` |

The structured name parts (`firstname`, `lastname`, etc.) are always stored separately and are unaffected by this setting. Only the display name (`fn`) changes, which is what phones and other CardDAV clients show.
