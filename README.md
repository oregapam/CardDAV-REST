# CardDAV-REST

FastAPI adapter that exposes a clean JSON REST API over a [Baïkal](https://sabre.io/baikal/) CardDAV server. Designed for automation platforms like n8n — no hand-crafted WebDAV or vCard XML required.

Multiple address books are supported. Each book is a separate namespace in the URL, so leads, customers, and personal contacts can be managed through one adapter instance while staying isolated from each other.

---

## Quick Start

### 1. Start the stack

```bash
cp .env.example .env
docker compose up -d
```

Both Baïkal (port 8800) and the adapter (port 8000) start. The adapter will be unhealthy until Baïkal is configured — that's expected.

### 2. Set up Baïkal

Open **http://localhost:8800** and complete the setup wizard. You'll set an admin password and a few basic options. After the wizard, you're taken to the admin panel.

### 3. Create a user

In the Baïkal admin panel, go to **Users and books → + Add user**. Fill in a username and password — these are the credentials the adapter will use to talk to Baïkal (not the admin password). Note them down.

### 4. Create an address book

Still in the user row, click the address books icon and add an address book. The **URL path** (slug) shown below the display name is what the API uses — for example, a book called "Contacts" typically gets the slug `contacts`. You can have multiple books; each becomes a separate namespace in the API.

### 5. Fill in `.env`

Open the `.env` file you copied in step 1 and fill in at minimum:

```env
BAIKAL_USER=the-username-you-created
BAIKAL_PASS=the-password-you-set
API_KEY=any-long-random-string-you-choose
```

`BAIKAL_URL` is already set to the internal Docker network address — leave it as-is.

### 6. Restart the adapter

```bash
docker compose restart carddav-rest
```

### 7. Verify

```bash
curl http://localhost:8000/api/addressbooks \
  -H "X-API-Key: your-api-key"
```

You should see the address book(s) you created listed in the response. The adapter is ready.

---

### Rebuilding after source changes

```bash
docker build -t carddav-rest:latest .
docker compose up -d carddav-rest
```

---

## Authentication

Every `/api/*` endpoint requires the `X-API-Key` header. `/health`, `/docs`, and `/redoc` are public.

```bash
curl http://localhost:8000/api/addressbooks \
  -H "X-API-Key: your-api-key"
```

A missing or wrong key returns `401 Invalid or missing API key`.

---

## API

Quick reference for integration builders. For full request/response details see:
- **Interactive (Swagger UI):** http://localhost:8000/docs
- **Markdown reference:** [docs/api-reference.md](docs/api-reference.md)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/addressbooks` | List available address books |
| `GET` | `/api/addressbooks/{book}/contacts` | List contacts (pagination + `q` quick search) |
| `POST` | `/api/addressbooks/{book}/contacts/search` | Structured search by name, email, or phone |
| `POST` | `/api/addressbooks/{book}/contacts` | Create a contact |
| `GET` | `/api/addressbooks/{book}/contacts/{uid}` | Get a contact |
| `GET` | `/api/addressbooks/{book}/contacts/{uid}/vcard` | Download raw vCard |
| `PUT` | `/api/addressbooks/{book}/contacts/{uid}` | Full update (replaces all managed fields) |
| `PATCH` | `/api/addressbooks/{book}/contacts/{uid}` | Partial update (only listed fields change) |
| `POST` | `/api/addressbooks/{book}/contacts/{uid}/merge/{other_uid}` | Merge two contacts |
| `POST` | `/api/addressbooks/{book}/contacts/{uid}/move/{target_book}` | Move contact to another book |
| `DELETE` | `/api/addressbooks/{book}/contacts/{uid}` | Delete a contact |
| `GET` | `/api/stats` | Contact counts and timestamps per address book |
| `GET` | `/api/config` | Active runtime configuration |
| `GET` | `/health` | Health check (no API key) |

---

## Key Behaviors

### Phone number normalization

Phone numbers are normalized to E.164 format (`+<countrycode><number>`) on every write and search. Numbers without a country code use `DEFAULT_COUNTRY_CODE`.

```
06301234567  →  +36301234567   (DEFAULT_COUNTRY_CODE=HU)
+36301234567 →  +36301234567   (already E.164, unchanged)
```

An unparseable number returns `422 {"detail": "Invalid phone number: <value>"}`.

### Duplicate detection

Pass `check_duplicates: true` when creating a contact. The adapter searches for an existing contact with the same email address **or** phone number and returns `409 Conflict` if found — instead of creating a duplicate.

### Required fields

Beyond the built-in rule that at least one of `firstname` or `lastname` must be present, operators can enforce additional fields via `REQUIRED_FIELDS` (comma-separated). Applies to create, full update, and partial update (validated against the resulting contact, not the patch body alone).

```
REQUIRED_FIELDS=emails,phones
```

A request that violates any required field returns `422 {"detail": "Missing required field(s): emails, org"}`.

### NAME_FORMAT

Controls how the display name (`fn`) is assembled from structured name parts.

| Value | Format | Example |
|-------|--------|---------|
| `western` | Prefix Firstname Middlename Lastname Suffix | `Dr. Jane Marie Smith PhD` |
| `eastern` | Lastname Firstname | `Smith Jane` |
| `eastern_full` | Prefix Lastname Firstname Suffix | `Dr. Smith Jane PhD` |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BAIKAL_URL` | yes | — | e.g. `http://baikal/dav.php` (internal Docker network) |
| `BAIKAL_USER` | yes | — | Baïkal user the adapter authenticates as |
| `BAIKAL_PASS` | yes | — | Baïkal password |
| `API_KEY` | yes | — | Key clients send in `X-API-Key` |
| `NAME_FORMAT` | no | `western` | See [Name format](#name_format) above |
| `DEFAULT_COUNTRY_CODE` | no | `HU` | ISO 3166-1 alpha-2 region for phone normalization |
| `REQUIRED_FIELDS` | no | _(empty)_ | Comma-separated contact field names that must be non-empty |

---

## Development

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt   # Windows
# .venv/bin/pip install -r requirements-dev.txt     # macOS/Linux
python -m pytest tests -v
```

---

## n8n Community Node

The [`n8n-nodes-carddav-rest`](https://www.npmjs.com/package/n8n-nodes-carddav-rest) package wraps this adapter for n8n workflows. Install it from **Settings → Community Nodes** inside n8n, or see the [n8n-node/](n8n-node/) directory for local development instructions.

---

## Publishing

### Docker image (GHCR)

The adapter image is published to [ghcr.io/oregapam/carddav-rest](https://ghcr.io/oregapam/carddav-rest). The `docker-compose.yml` pulls this image by default; local builds can override it with `ADAPTER_IMAGE=carddav-rest:latest`.

**One-time setup — generate a Personal Access Token:**

GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token → scopes: `write:packages`, `read:packages`

```bash
echo "YOUR_TOKEN" | docker login ghcr.io -u oregapam --password-stdin
```

**Build and push:**

```bash
VERSION=0.1.2   # match the release version
docker build -t ghcr.io/oregapam/carddav-rest:${VERSION} \
             -t ghcr.io/oregapam/carddav-rest:latest .
docker push ghcr.io/oregapam/carddav-rest:${VERSION}
docker push ghcr.io/oregapam/carddav-rest:latest
```

**Make the package public** (first time only): GitHub → Profile → Packages → carddav-rest → Package settings → Change visibility → Public

### n8n node (npm)

```bash
cd n8n-node
npm run build
npm publish --access public
```

---

## License

[MIT](LICENSE)
