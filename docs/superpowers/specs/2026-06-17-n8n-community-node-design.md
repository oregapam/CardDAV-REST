# n8n Community Node Design: `n8n-nodes-carddav-rest`

## Goal

Build a TypeScript n8n community node that wraps the CardDAV-REST adapter API, enabling n8n workflows to manage Baïkal contacts without writing HTTP Request nodes manually.

## Architecture

The node lives in `n8n-node/` — a self-contained TypeScript package inside the CardDAV-REST monorepo. It has no runtime dependency on the Python codebase; it only calls the adapter's HTTP API. Build output (`dist/`) is excluded from git. The package is published to npm as `n8n-nodes-carddav-rest`.

**Tech stack:** TypeScript, n8n-workflow (peer dep), compiled to CommonJS.

---

## Repo Structure

```
CardDAV-REST/
├── app/                            # FastAPI adapter (existing)
├── tests/                          # Python tests (existing)
├── n8n-node/                       # NEW: n8n TypeScript package
│   ├── package.json                # name: "n8n-nodes-carddav-rest"
│   ├── tsconfig.json
│   ├── src/
│   │   ├── credentials/
│   │   │   └── CardDavRestApi.credentials.ts
│   │   └── nodes/
│   │       └── CardDavRest/
│   │           ├── CardDavRest.node.ts
│   │           └── carddav-rest.svg
│   ├── dist/                       # .gitignore-d
│   └── .npmignore
├── docker-compose.yml
└── README.md
```

`.gitignore` additions: `n8n-node/dist/`, `n8n-node/node_modules/`

---

## Credential: `CardDavRestApi`

Two fields:

| Field | Type | Description |
|-------|------|-------------|
| `baseUrl` | string | e.g. `http://localhost:8000` — no trailing slash |
| `apiKey` | password | Sent as `X-API-Key` header on every request |

No OAuth, no refresh tokens. The adapter handles Baïkal authentication internally.

---

## Node: `CardDavRest`

### Resources and Operations

#### Resource: Contact

All contact operations require an `addressBook` parameter (dynamic dropdown, see below).

| displayName | value | HTTP | Endpoint |
|-------------|-------|------|----------|
| List | `list` | GET | `/api/addressbooks/{book}/contacts` |
| Get | `get` | GET | `/api/addressbooks/{book}/contacts/{uid}` |
| Create | `create` | POST | `/api/addressbooks/{book}/contacts` |
| Update (Full Replace) | `update` | PUT | `/api/addressbooks/{book}/contacts/{uid}` |
| Update Fields | `patch` | PATCH | `/api/addressbooks/{book}/contacts/{uid}` |
| Delete | `delete` | DELETE | `/api/addressbooks/{book}/contacts/{uid}` |
| Search | `search` | POST | `/api/addressbooks/{book}/contacts/search` |
| Merge Duplicates | `merge` | POST | `/api/addressbooks/{book}/contacts/{uid}/merge/{other_uid}` |
| Move to Addressbook | `move` | POST | `/api/addressbooks/{book}/contacts/{uid}/move/{target_book}` |
| Download vCard | `getVcard` | GET | `/api/addressbooks/{book}/contacts/{uid}/vcard` |

#### Resource: Addressbook

| displayName | value | HTTP | Endpoint |
|-------------|-------|------|----------|
| List | `list` | GET | `/api/addressbooks` |

#### Resource: Stats

| displayName | value | HTTP | Endpoint |
|-------------|-------|------|----------|
| Get | `get` | GET | `/api/stats` |

#### Resource: Config

| displayName | value | HTTP | Endpoint |
|-------------|-------|------|----------|
| Get | `get` | GET | `/api/config` |

---

### Parameter: `addressBook` (dynamic dropdown)

Used by all Contact operations and Move. Implemented via `loadOptions`:

```ts
async loadOptions(): Promise<INodePropertyOptions[]> {
  const books = await this.helpers.request({ method: 'GET', url: '/api/addressbooks', ... });
  return books.map(b => ({ name: b.displayname, value: b.name }));
}
```

Shown as a dropdown in the UI; user selects from the list rather than typing.

---

### Contact Fields

#### Always visible (Create, Update Full Replace, Update Fields)

| Parameter | Type | Notes |
|-----------|------|-------|
| `firstname` | string | **Required** (hardcoded by API — at least firstname or lastname must be present) |
| `lastname` | string | Optional but recommended |

#### Fixed Collections (always available in Create/Update)

**Phone Numbers** — one or more entries, each:
- `type` (string, default `"cell"`)
- `value` (string, E.164 format; server normalizes automatically)

**Email Addresses** — one or more entries, each:
- `type` (string, default `"home"`)
- `value` (string)

**Addresses** — one or more entries, each:
- `type` (string, default `"home"`)
- `street`, `city`, `zip`, `state`, `country` (all strings)

#### Additional Fields (collapsible section)

`middlename`, `prefix`, `suffix`, `org`, `title`, `birthday`, `note`, `photo`, `categories` (string array), `urls` (string array)

#### Dynamic required_fields from server config

During `loadOptions`, the node calls `GET /api/config`. Fields listed in `required_fields` (e.g. `["phones", "emails"]`) are rendered with `required: true` in the n8n UI (red asterisk). This is in addition to the hardcoded `firstname`/`lastname` requirement.

If the config call fails (server unreachable), the node falls back gracefully — all fields optional except `firstname`.

---

### Operation-specific parameters

**List:**
- `limit` (number, default 50, range 1–1000)
- `offset` (number, default 0)
- `q` (string, optional — quick search across name/email/phone)

**Search:**
- `name` (string, optional)
- `email` (string, optional)
- `phone` (string, optional)
- `matchCondition` (dropdown: "All Of" / "Any Of", default "All Of")
- At least one of name/email/phone must be provided (validated client-side with hint)

**Merge Duplicates:**
- `uid` (string — primary contact to keep)
- `otherUid` (string — contact to merge in and delete)

**Move to Addressbook:**
- `uid` (string)
- `targetBook` (dynamic dropdown, same loadOptions as `addressBook`)

**Create:**
- `checkDuplicates` (boolean, default false) — returns 409 if email already exists

**Update Fields (PATCH):**
- Same fields as Create, but all optional (at least one required by API)

---

## Error Handling

The node maps adapter HTTP errors to n8n errors with clear messages:

| HTTP status | n8n behavior |
|-------------|-------------|
| 401 | Throw: "Invalid API key — check your CardDavRestApi credential" |
| 404 | Throw: "Contact not found" |
| 409 | Throw: "Duplicate contact detected" (or "Concurrent modification conflict") |
| 422 | Throw: validation message from API body |
| 502 | Throw: "CardDAV server unreachable — check Baïkal is running" |

---

## package.json `n8n` key

```json
{
  "n8n": {
    "n8nNodesApiVersion": 1,
    "credentials": ["dist/credentials/CardDavRestApi.credentials.js"],
    "nodes": ["dist/nodes/CardDavRest/CardDavRest.node.js"]
  }
}
```

---

## Build & Publish

```bash
cd n8n-node
npm install
npm run build      # tsc
npm publish        # publishes n8n-nodes-carddav-rest to npm
```

For local n8n testing: symlink `n8n-node/` into `~/.n8n/custom/` or mount in Docker.

---

## Out of Scope

- Trigger node (Baïkal has no webhooks; polling would require significant complexity)
- Bulk import/export
- vCard file upload as binary input
