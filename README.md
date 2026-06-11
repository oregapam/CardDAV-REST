# CardDAV-REST

FastAPI adapter that lets automation platforms (n8n) manage contacts on a
Baïkal CardDAV server through a clean JSON REST API. Phones keep syncing
natively over CardDAV; n8n never touches XML/WebDAV.

Design spec: `docs/superpowers/specs/2026-06-11-carddav-rest-adapter-design.md`

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/contacts/search` | Search with dynamic filters (email/phone/name, allof/anyof) |
| `POST` | `/api/contacts` | Create a contact (optional `check_duplicates`) |
| `GET` | `/api/contacts/{uid}` | Fetch one contact as JSON |
| `PUT` | `/api/contacts/{uid}` | Update (etag-protected, preserves unmanaged vCard props) |
| `DELETE` | `/api/contacts/{uid}` | Delete |
| `GET` | `/health` | Health check (no API key required) |

All `/api/*` endpoints require the `X-API-Key` header. Interactive docs: `/docs`.

## Running

```bash
cp .env.example .env   # then edit values
docker build -t carddav-rest:latest .
docker compose up -d
```

First-time Baïkal setup: open http://localhost:8800, finish the wizard,
create the user and address book referenced in `.env`.

## Examples

```bash
# Search
curl -X POST http://localhost:8000/api/contacts/search \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"email": "teszt@email.hu", "match_condition": "allof"}'

# Create
curl -X POST http://localhost:8000/api/contacts \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"firstname": "Anna", "lastname": "Kis", "emails": [{"type": "work", "value": "anna@ceg.hu"}], "check_duplicates": true}'

# Get / update / delete
curl http://localhost:8000/api/contacts/<uid> -H "X-API-Key: $API_KEY"
curl -X PUT http://localhost:8000/api/contacts/<uid> \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"firstname": "Anna", "lastname": "Nagy"}'
curl -X DELETE http://localhost:8000/api/contacts/<uid> -H "X-API-Key: $API_KEY"
```

## Development

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt   # Windows
python -m pytest tests -v
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `BAIKAL_URL` | yes | e.g. `http://baikal/dav.php` (internal Docker network) |
| `BAIKAL_USER` | yes | Baïkal user the adapter authenticates as |
| `BAIKAL_PASS` | yes | Baïkal password |
| `BAIKAL_ADDRESSBOOK` | no (`default`) | Address book id |
| `API_KEY` | yes | Key n8n sends in `X-API-Key` |
