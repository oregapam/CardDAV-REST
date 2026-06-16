# Phone Number Normalization — Design

**Goal:** Contacts created or updated through the API store phone numbers in a
consistent E.164 format (e.g. `06301234567` → `+36301234567`), regardless of
how the source system (CRM, manual entry) formatted them.

## Library

[`phonenumbers`](https://pypi.org/project/phonenumbers/) (Python port of
Google's libphonenumber). Added to `requirements.txt`. Chosen over a
hand-rolled regex because it understands per-country numbering rules and
validity, not just E.164 syntax.

## Configuration

`app/config.py` — new field on `Settings`:

```python
default_region: str = "HU"
```

Loaded from env var `DEFAULT_COUNTRY_CODE` (ISO 3166-1 alpha-2 region code,
e.g. `HU`, `DE`, `US` — matches `phonenumbers`' native region parameter, not a
calling code). Optional; defaults to `HU`. Wired into `app.state.default_region`
in `app/main.py`, following the same pattern as `name_format` /
`get_name_format`.

## New module: `app/phone.py`

```python
def normalize_phone(value: str, default_region: str) -> str:
    """Returns the number in E.164 format, or raises ValueError if invalid."""
```

Behavior:
- Empty/blank `value` → returned unchanged (no-op, not an error).
- Parsed via `phonenumbers.parse(value, default_region)`.
- If `phonenumbers.is_valid_number(parsed)` is false → raises `ValueError`.
- Otherwise → `phonenumbers.format_number(parsed, PhoneNumberFormat.E164)`.

## Where it's applied

Applied at the **router** level (not as a Pydantic field validator), because
`default_region` comes from `Settings` via dependency injection, the same way
`name_format` already flows into `vcard_to_contact`/`contact_to_vcard`.

| Endpoint | Field normalized |
|---|---|
| `POST /{book}/contacts` (create) | every `phones[].value` |
| `PUT /{book}/contacts/{uid}` (update) | every `phones[].value` |
| `POST /{book}/contacts/search` | `req.phone` |

**Not applied to:**
- `GET /{book}/contacts?q=` — free-text quick search spanning name/email/phone;
  normalizing `q` as a phone number would be wrong when it's actually a name
  or email fragment.
- `ContactOut` / `SearchMatch` (read paths) — existing data already stored in
  CardDAV is returned as-is. Validating on read could turn a working GET into
  a 500/422 for data that predates this feature or came from another client.

## Error handling

If any phone value fails normalization, the endpoint returns `422` with:

```json
{"detail": "Invalid phone number: <value>"}
```

The whole request (create/update/search) is rejected — no partial writes.

## Testing

- `app/phone.py` unit tests: valid HU mobile/landline, already-E.164 input
  (left as `+...`), invalid/too-short input (raises `ValueError`), empty
  string (no-op), non-default region via explicit `default_region` arg.
- Router tests: `POST /contacts` with a `06...` number stores `+36...` in the
  vCard sent upstream; invalid number → `422`; `PUT` update behaves the same;
  `POST /search` with a `06...` phone filter sends the normalized `+36...` in
  the CardDAV REPORT body.
