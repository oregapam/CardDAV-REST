# Required Fields Configuration — Design

**Goal:** Operators can declare a set of contact fields that must be present
for a contact to be created or updated, via a `REQUIRED_FIELDS` environment
variable. Requests missing any required field are rejected with `422`.

## Library / approach

No new dependency. A small pure-Python helper inspects a `Contact` instance and
reports which required fields are absent. The check runs at the router layer,
following the same dependency-injection pattern already used for `name_format`
and `default_region`.

## Configuration

`app/config.py` — new field on `Settings`:

```python
required_fields: tuple[str, ...] = ()
```

Loaded from env var `REQUIRED_FIELDS` (comma-separated `Contact` field names,
e.g. `REQUIRED_FIELDS=emails,phones`). Optional; defaults to empty (no extra
requirements — fully backward compatible).

**Parsing rules:**
- Split on `,`, `strip()` each entry, drop empty entries (tolerates
  `emails, phones,` with trailing comma and spaces).
- Validate at startup: every name must be a real `Contact` model field
  (`Contact.model_fields`). An unknown name (e.g. typo `email` instead of
  `emails`) raises `RuntimeError`, matching the fail-fast behavior of
  `NAME_FORMAT`. This is important because we use the exact model field names,
  so typos must fail loudly rather than silently never-match.

Wired into `app.state.required_fields` in `app/main.py`, alongside the existing
`name_format` / `default_region` assignments.

## Relationship to the built-in name rule

The existing Pydantic rule — `firstname` OR `lastname` must be non-empty —
stays unchanged and always applies (a nameless contact can never be created).
`REQUIRED_FIELDS` adds further **AND-connected** constraints on top.

Listing `firstname` or `lastname` in `REQUIRED_FIELDS` is allowed and simply
imposes a stricter AND-constraint over the built-in OR rule (e.g.
`REQUIRED_FIELDS=lastname` means lastname alone becomes mandatory). The two
rules compose; they do not conflict.

## New module: `app/required_fields.py`

```python
def missing_required_fields(contact: Contact, required: tuple[str, ...]) -> list[str]:
    """Returns the names of required fields that are absent on the contact,
    preserving the order given in `required`. Empty list = all present."""
```

The helper is HTTP-agnostic: it returns the list of missing names and never
raises. The router decides whether to turn a non-empty result into a `422`.
It reports **all** missing fields at once (not fail-on-first), so the caller
gets a complete picture in a single response.

### "Present" definition (type-dispatched, not hard-coded per field)

For each required field name, read the attribute off the `Contact` instance and
apply the rule for its type:

| Field type | Examples | "Present" means |
|---|---|---|
| `str` | `org`, `title`, `birthday`, `note`, `photo`, `firstname`, `lastname`, `middlename`, `prefix`, `suffix` | `value.strip()` is non-empty |
| list of `TypedValue` | `emails`, `phones` | at least one element whose `.value.strip()` is non-empty |
| list of `str` | `urls`, `categories` | at least one element that is a non-empty (stripped) string |
| list of `Address` | `addresses` | the list is non-empty (no sub-field inspection — `Address` has no single "value" field) |

Dispatch is by inspecting the actual value (is it a `str`; is it a list; what do
its elements look like), so there is no per-field-name branching.

## Where it's applied

Applied at the router layer, in both endpoints that write managed contact data:

| Endpoint | Validates |
|---|---|
| `POST /{book}/contacts` (create) | the request body |
| `PUT /{book}/contacts/{uid}` (update) | the request body |

**Why the request body, not the merged result, on update:** `update_contact`
calls `merge_contact_into_vcard`, which deletes every managed vCard property
(except `FN`) and re-fills them from the request body. So the body fully
determines the resulting managed fields — validating the body is equivalent to
validating the result, and simpler. PUT is a full replace of managed fields,
not an additive merge.

A new `get_required_fields(request: Request) -> tuple[str, ...]` dependency
(mirroring `get_default_region`) supplies the configured tuple.

### Ordering relative to phone normalization

In both endpoints, **phone normalization runs first**, then the required-fields
check. This means that for input like `phones=[{"value": "123"}]` with
`REQUIRED_FIELDS=phones`, the caller gets the more useful
`Invalid phone number: 123` error rather than a generic "missing" message. The
two checks otherwise target disjoint conditions (empty list vs. list with a bad
value).

## Error handling

If `missing_required_fields(...)` returns a non-empty list, the endpoint returns
`422` with:

```json
{"detail": "Missing required field(s): emails, org"}
```

The names appear in `REQUIRED_FIELDS` order. The whole create/update request is
rejected — no partial writes.

## n8n discoverability (noted, not built now)

`REQUIRED_FIELDS` is a deployment-level policy that is **invisible in the
OpenAPI schema**. An n8n node built from the schema will not know which fields a
given deployment requires; it discovers the rule only by receiving a `422` at
runtime. For v1 the contract is therefore the `422` detail message itself —
which is why the helper reports the complete list of missing fields.

A future `GET /api/config` endpoint (or an extension of `/health`) that returns
the active `required_fields` would let an n8n node build its form dynamically.
This is out of scope here and will be added to `docs/ideas.md` as a follow-up,
not implemented in this work.

## Testing

- `app/required_fields.py` unit tests: each "present" rule — non-empty vs empty
  `str` field; `emails`/`phones` with a non-empty `.value` vs empty list vs
  list containing only `{"value": ""}`; `urls`/`categories` non-empty vs `[""]`;
  `addresses` non-empty vs empty; multiple missing fields returned in order;
  empty `required` returns `[]`.
- Router tests (create and update): missing required field → `422` with the
  expected detail; all required present → `201`/`200`; phone-invalid-and-required
  yields the phone error (ordering); empty `REQUIRED_FIELDS` leaves existing
  behavior unchanged.
- Config tests: default empty tuple; parsing with whitespace and trailing comma;
  unknown field name → `RuntimeError`.
