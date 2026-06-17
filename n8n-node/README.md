# n8n-nodes-carddav-rest

n8n community node for the [CardDAV REST](https://github.com/mark/CardDAV-REST) adapter. Manage contacts stored in Baïkal from n8n workflows — no hand-crafted HTTP Request nodes required.

## Installation

### From n8n

**Settings → Community Nodes → Install** → package name: `n8n-nodes-carddav-rest`

### Local development

```bash
cd n8n-node
npm install
npm run dev
```

This starts an n8n instance with the node loaded at `http://localhost:5678`.

Alternatively, mount it into a Docker-based n8n instance:

```bash
docker run -it --rm \
  -p 5678:5678 \
  -v "$(pwd)/n8n-node:/home/node/.n8n/custom/n8n-nodes-carddav-rest" \
  -e N8N_CUSTOM_EXTENSIONS=/home/node/.n8n/custom \
  n8nio/n8n
```

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
npm test          # Run Jest test suite (31 tests)
npm run build     # Compile TypeScript to dist/
npm run dev       # Start n8n with hot reload
npm run lint      # Run ESLint
npm run lint:fix  # Auto-fix linting issues
```

## Publishing to npm

Before publishing, fill in the following fields in `package.json`:

- `author.name` / `author.email`
- `homepage`
- `repository.url`

Then:

```bash
npm run build
npm publish
```

## Related

- [CardDAV REST adapter](../README.md) — the FastAPI-based Baïkal adapter this node calls

## License

[MIT](LICENSE.md)
