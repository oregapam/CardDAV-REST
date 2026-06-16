# PATCH Endpoint — Design

**Goal:** Allow updating a single field (or a few) of an existing contact
without resending the entire contact, unlike `PUT` which replaces every
managed field. `PATCH /api/addressbooks/{book}/contacts/{uid}` updates only
the fields explicitly present in the request body.

## New model: `ContactPatch`

Added to `app/models.py`, alongside `Contact`/`ContactIn`. Every field is
`Optional[...] = None`:

```python
class ContactPatch(BaseModel):
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    middlename: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    emails: Optional[list[TypedValue]] = None
    phones: Optional[list[TypedValue]] = None
    addresses: Optional[list[Address]] = None
    org: Optional[str] = None
    title: Optional[str] = None
    birthday: Optional[str] = None
    urls: Optional[list[str]] = None
    note: Optional[str] = None
    photo: Optional[str] = None
    categories: Optional[list[str]] = None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "ContactPatch":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self
```

`self.model_fields_set` (a Pydantic v2 `BaseModel` attribute) is the set of
field names that were actually present in the input payload — independent of
their value. This is the mechanism that distinguishes "field omitted" from
"field explicitly sent" and drives the empty-body rejection.

## Field semantics

| JSON body state | Effect |
|---|---|
| Field absent from JSON | Field is left untouched on the stored contact |
| Field present, value `null`/`""`/`[]` | Field is cleared (reset to its empty default) |
| Field present, non-empty value | Field is fully replaced by the new value |

List fields (`emails`, `phones`, `addresses`, `urls`, `categories`) are
**replaced wholesale** when present, not merged item-by-item — identical to
how `PUT` already treats these fields. There is no way to append a single
email via `PATCH`; the caller must send the complete desired list for that
field, same as `PUT`.

An empty body (`{}`, no fields present) is rejected with `422` via the
`require_at_least_one_field` validator above — message:
`"At least one field must be provided"`.

## Applying the patch: `apply_contact_patch()`

A new function in `app/models.py`, placed after `ContactPatch`:

```python
_FIELD_DEFAULTS: dict[str, object] = {
    "firstname": "", "lastname": "", "middlename": "", "prefix": "", "suffix": "",
    "emails": [], "phones": [], "addresses": [], "org": "", "title": "",
    "birthday": "", "urls": [], "note": "", "photo": "", "categories": [],
}


def apply_contact_patch(existing: Contact, patch: ContactPatch) -> None:
    """Mutates `existing` in place, applying only the fields explicitly
    present in `patch` (per `model_fields_set`). A field provided as
    null/empty clears it; a field not provided is left untouched."""
    for name in patch.model_fields_set:
        value = getattr(patch, name)
        setattr(existing, name, value if value is not None else _FIELD_DEFAULTS[name])
```

This mutates an existing `Contact`/`ContactOut` instance (built from the
current vCard) in place, producing the final desired state.

## Router: `PATCH /{book}/contacts/{uid}`

Added to `app/routers/contacts.py`, reusing every existing building block —
no new vCard-level merge logic is needed:

```python
@router.patch("/{book}/contacts/{uid}")
async def patch_contact(
    book: str,
    uid: str,
    body: ContactPatch,
    dav: CardDAVClient = Depends(get_dav),
    name_format: str = Depends(get_name_format),
    default_region: str = Depends(get_default_region),
    required_fields: tuple[str, ...] = Depends(get_required_fields),
) -> dict:
    existing_vcf, etag = await dav.get(book, uid)
    existing_contact = vcard_to_contact(existing_vcf, name_format)
    apply_contact_patch(existing_contact, body)
    if "phones" in body.model_fields_set:
        for phone in existing_contact.phones:
            try:
                phone.value = normalize_phone(phone.value, default_region)
            except ValueError:
                raise HTTPException(status_code=422, detail=f"Invalid phone number: {phone.value}")
    if not (existing_contact.firstname or existing_contact.lastname):
        raise HTTPException(status_code=422, detail="At least one of firstname or lastname is required")
    missing = missing_required_fields(existing_contact, required_fields)
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing required field(s): {', '.join(missing)}")
    merged_vcf = merge_contact_into_vcard(existing_vcf, existing_contact, name_format)
    await dav.update(book, uid, merged_vcf, etag)
    return {"status": "updated", "uid": uid}
```

Step-by-step:
1. Fetch the current vCard + ETag (`404` if the UID doesn't exist — handled by
   the existing `NotFoundError` → `404` exception handler, unchanged).
2. Parse it into a full `Contact` (`vcard_to_contact`).
3. Apply only the fields present in the patch (`apply_contact_patch`).
4. If `phones` was one of the patched fields, normalize the resulting phone
   values — same `normalize_phone` helper and `422` error format already used
   by `create_contact`/`update_contact`.
5. **Validate the merged, final state** — not the patch body in isolation —
   against the built-in name rule and `REQUIRED_FIELDS`. This is the key
   reason a `PATCH` of just `{"org": "..."}` succeeds without resending the
   name: the existing `firstname`/`lastname` are untouched by the patch and
   still satisfy the rule. The `422` only triggers if the patch itself drives
   the final state into violating these rules (e.g. explicitly clearing both
   name fields, or clearing a field listed in `REQUIRED_FIELDS`).
6. Reuse `merge_contact_into_vcard(existing_vcf, existing_contact, name_format)`
   exactly as `update_contact` does — it doesn't care whether the `Contact` it
   receives came from a full `PUT` body or a patched-and-merged one; it just
   needs *a* `Contact` representing the desired final state.
7. `dav.update(...)` sends the merged vCard with `If-Match: <etag>` — same
   concurrency protection as `PUT`. A concurrent modification still surfaces
   as `409` via the existing `ConflictError` handler, unchanged.

No new error-handling paths are introduced; `PATCH` reuses the same `404`,
`409`, and `422`-shaped responses already wired up for the other endpoints.

## Testing

- `tests/test_models.py` (or extend an existing model test file) for
  `apply_contact_patch`: field omitted → untouched; field sent empty/null →
  cleared; field sent with value → replaced; list field replaced wholesale
  (old items gone); multiple fields patched at once.
- `ContactPatch` validator: empty body → `ValidationError`/`422`; single field
  → valid.
- Router tests (new test file `tests/test_patch_endpoint.py` or appended to
  `tests/test_crud_endpoints.py`):
  - Patching only `org` succeeds without firstname/lastname in the body, and
    the merged vCard sent upstream still contains the original name.
  - Patching `phones` normalizes the value (reuse the same fixture pattern as
    the `PUT` phone-normalization tests) and an invalid number returns `422`.
  - Clearing both `firstname` and `lastname` via patch (on a contact whose
    only name data is in those two fields) returns `422` with the existing
    "At least one of firstname or lastname is required" message.
  - With `REQUIRED_FIELDS=emails` configured, clearing `emails` via
    `{"emails": []}` returns `422` with `Missing required field(s): emails`;
    patching an unrelated field while `emails` already has data leaves it
    untouched and succeeds.
  - Empty body `{}` → `422`.
  - Missing UID → `404`. ETag mismatch (simulate a `412` from the upstream
    `PUT`) → `409`.
