# n8n-nodes-carddav-rest

n8n community node for the [CardDAV REST](https://github.com/oregapam/CardDAV-REST) adapter. Manage contacts stored in Baïkal from n8n workflows — no hand-crafted HTTP Request nodes required.

## Installation

### From n8n

**Settings → Community Nodes → Install** → package name: `n8n-nodes-carddav-rest`

### Local testing with Docker

The `n8n-node/` directory includes a `Dockerfile` and `docker-compose.yml` that build a custom n8n image with the node baked in. Build the TypeScript first, then build and start the image:

```bash
cd n8n-node
npm install
npm run build
docker compose build
docker compose up -d
```

n8n will be available at `http://localhost:5678`. The **CardDAV REST** node will appear in the node picker without any additional installation step — do **not** use Settings → Community Nodes → Install.

After changing the node source, rebuild and restart:

```bash
npm run build
docker compose build
docker compose up -d
```

Existing workflows and credentials are preserved — only the image is replaced. The `n8n-data` volume is not touched.

To test against a running CardDAV REST adapter (started via the root `docker-compose.yml`), set the credential **Base URL** to:

```
http://host.docker.internal:8000
```

This works on macOS and Windows out of the box. On Linux, `extra_hosts: host.docker.internal:host-gateway` is already set in the compose file — no extra configuration needed.

**Full local stack (both compose files):**

```bash
# Terminal 1 — adapter + Baïkal
docker compose up -d          # from repo root

# Terminal 2 — n8n with the community node
cd n8n-node
npm run build
docker compose build
docker compose up -d
```

### Local development (hot reload)

```bash
cd n8n-node
npm install
npm run dev
```

This starts an n8n instance with the node loaded at `http://localhost:5678` and rebuilds automatically on file changes.

## Authentication

The node uses the **CardDAV REST API** credential with two fields:

| Field | Description |
|-------|-------------|
| Base URL | URL of the CardDAV REST adapter (e.g. `http://localhost:8000`) |
| API Key | Sent as the `X-API-Key` header on every request |

## Resources and Operations

### Contact

All contact operations require selecting an **Address Book** (dynamic dropdown populated from the server).

| Operation | Description |
|-----------|-------------|
| **List** | List contacts with pagination and optional quick search |
| **Get** | Retrieve a single contact by UID |
| **Create** | Create a new contact |
| **Update (Full Replace)** | Replace all fields of an existing contact |
| **Update Fields** | Update only the specified fields (PATCH) |
| **Delete** | Delete a contact |
| **Search** | Search by name, email, or phone with AND/OR logic |
| **Merge Duplicates** | Merge two contacts — keeps the primary, deletes the duplicate |
| **Move to Addressbook** | Move a contact to a different address book |
| **Download vCard** | Download a contact as a `.vcf` file (binary output) |

### Addressbook

| Operation | Description |
|-----------|-------------|
| **List** | List all available address books |

### Stats

| Operation | Description |
|-----------|-------------|
| **Get** | Return contact count, last/oldest modification date, and total size per address book |

### Config

| Operation | Description |
|-----------|-------------|
| **Get** | Return active server configuration (`name_format`, `default_region`, `required_fields`) |

## Contact Fields

### Core fields (Create / Update)

| Field | Required | Notes |
|-------|----------|-------|
| First Name | yes* | *At least one of First Name or Last Name must be provided |
| Last Name | no | |
| Phone Numbers | no | Multiple entries, each with type (cell/home/work/other) and number |
| Email Addresses | no | Multiple entries, each with type (home/work/other) and address |
| Addresses | no | Multiple entries with street, city, ZIP, state, country |
| Additional Fields | no | Birthday, categories, note, organization, title, photo URL, URLs, etc. |

> The server's `REQUIRED_FIELDS` configuration may make additional fields mandatory (e.g. `phones`, `emails`). The server returns a 422 error if a required field is missing.

### Update Fields (PATCH) — only listed fields are changed

Add fields to the **Fields to Update** collection. Fields not listed remain untouched on the server.

### Search parameters

- **Name** — partial match, word-order independent for multi-word queries
- **Email** — exact match
- **Phone** — partial match
- **Match Condition** — `All Of (AND)` / `Any Of (OR)`

## Error Handling

| HTTP status | Behavior |
|-------------|----------|
| 401 | Invalid API key |
| 404 | Contact not found |
| 409 | Duplicate contact detected or concurrent modification conflict |
| 422 | Validation error (e.g. missing required field) |
| 502 | Baïkal server unreachable — check that Baïkal is running |

## Development

```bash
cd n8n-node
npm install
npm test          # Run Jest test suite (34 tests)
npm run build     # Compile TypeScript to dist/
npm run dev       # Start n8n with hot reload
npm run lint      # Run ESLint
npm run lint:fix  # Auto-fix linting issues
```

## Publishing to npm

```bash
npm run build
npm publish --access public
```

## Related

- [CardDAV REST adapter](../README.md) — the FastAPI-based Baïkal adapter this node calls

## License

[MIT](LICENSE.md)
