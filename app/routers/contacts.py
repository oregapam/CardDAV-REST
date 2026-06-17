import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from app.carddav import CardDAVClient
from app.models import (
    AddressbookInfo,
    ContactCreate,
    ContactIn,
    ContactOut,
    ContactPatch,
    ContactsPage,
    SearchMatch,
    SearchRequest,
    SearchResponse,
    apply_contact_patch,
    merge_contacts,
)
from app.phone import normalize_phone
from app.required_fields import missing_required_fields
from app.vcard import contact_to_vcard, merge_contact_into_vcard, vcard_to_contact

router = APIRouter(prefix="/api/addressbooks", tags=["contacts"])


def get_dav(request: Request) -> CardDAVClient:
    return request.app.state.carddav


def get_name_format(request: Request) -> str:
    return request.app.state.name_format


def get_default_region(request: Request) -> str:
    return request.app.state.default_region


def get_required_fields(request: Request) -> tuple[str, ...]:
    return request.app.state.required_fields


@router.get("", response_model=list[AddressbookInfo])
async def list_addressbooks(dav: CardDAVClient = Depends(get_dav)) -> list[AddressbookInfo]:
    books = await dav.list_addressbooks()
    return [AddressbookInfo(**b) for b in books]


@router.post("/{book}/contacts/search", response_model=SearchResponse)
async def search_contacts(
    book: str,
    req: SearchRequest,
    dav: CardDAVClient = Depends(get_dav),
    name_format: str = Depends(get_name_format),
    default_region: str = Depends(get_default_region),
) -> SearchResponse:
    if req.phone:
        try:
            req.phone = normalize_phone(req.phone, default_region)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid phone number: {req.phone}")
    results = await dav.search(
        book,
        email=req.email,
        phone=req.phone,
        name=req.name,
        match_condition=req.match_condition,
    )
    matches = []
    for uid, vcf in results:
        contact = vcard_to_contact(vcf, name_format)
        matches.append(
            SearchMatch(uid=uid, fn=contact.fn, emails=contact.emails, phones=contact.phones)
        )
    return SearchResponse(
        exists=bool(matches),
        match_count=len(matches),
        matches=matches,
        searched_params=req.model_dump(exclude_none=True),
    )


@router.get("/{book}/contacts", response_model=ContactsPage)
async def list_contacts(
    book: str,
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, description="Quick search across name, email, and phone"),
    dav: CardDAVClient = Depends(get_dav),
    name_format: str = Depends(get_name_format),
) -> ContactsPage:
    results = await dav.quick_search(book, q) if q else await dav.list_all(book)
    all_contacts = []
    for uid, vcf in results:
        contact = vcard_to_contact(vcf, name_format)
        contact.uid = uid
        all_contacts.append(contact)
    total = len(all_contacts)
    warning = f"offset ({offset}) exceeds total ({total})" if total > 0 and offset >= total else None
    return ContactsPage(
        total=total,
        limit=limit,
        offset=offset,
        items=all_contacts[offset : offset + limit],
        warning=warning,
    )


@router.post("/{book}/contacts", status_code=201)
async def create_contact(
    book: str,
    body: ContactCreate,
    dav: CardDAVClient = Depends(get_dav),
    name_format: str = Depends(get_name_format),
    default_region: str = Depends(get_default_region),
    required_fields: tuple[str, ...] = Depends(get_required_fields),
) -> dict:
    for phone in body.phones:
        try:
            phone.value = normalize_phone(phone.value, default_region)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid phone number: {phone.value}")
    missing = missing_required_fields(body, required_fields)
    if missing:
        raise HTTPException(
            status_code=422, detail=f"Missing required field(s): {', '.join(missing)}"
        )
    if body.check_duplicates:
        for email in body.emails:
            results = await dav.search(book, email=email.value)
            if results:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "duplicate contact",
                        "matched_email": email.value,
                        "existing_uid": results[0][0],
                    },
                )
    uid = str(uuid.uuid4())
    vcf = contact_to_vcard(body, uid, name_format)
    await dav.create(book, uid, vcf)
    return {"status": "success", "uid": uid, "filename": f"{uid}.vcf"}


@router.get("/{book}/contacts/{uid}/vcard")
async def get_contact_vcard(
    book: str,
    uid: str,
    dav: CardDAVClient = Depends(get_dav),
) -> Response:
    vcf, etag = await dav.get(book, uid)
    headers = {"Content-Disposition": f'attachment; filename="{uid}.vcf"'}
    if etag:
        headers["ETag"] = etag
    return Response(content=vcf, media_type="text/vcard; charset=utf-8", headers=headers)


@router.get("/{book}/contacts/{uid}", response_model=ContactOut)
async def get_contact(
    book: str,
    uid: str,
    dav: CardDAVClient = Depends(get_dav),
    name_format: str = Depends(get_name_format),
) -> ContactOut:
    vcf, etag = await dav.get(book, uid)
    contact = vcard_to_contact(vcf, name_format)
    contact.uid = uid
    contact.etag = etag
    return contact


@router.put("/{book}/contacts/{uid}")
async def update_contact(
    book: str,
    uid: str,
    body: ContactIn,
    dav: CardDAVClient = Depends(get_dav),
    name_format: str = Depends(get_name_format),
    default_region: str = Depends(get_default_region),
    required_fields: tuple[str, ...] = Depends(get_required_fields),
) -> dict:
    for phone in body.phones:
        try:
            phone.value = normalize_phone(phone.value, default_region)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid phone number: {phone.value}")
    missing = missing_required_fields(body, required_fields)
    if missing:
        raise HTTPException(
            status_code=422, detail=f"Missing required field(s): {', '.join(missing)}"
        )
    existing_vcf, etag = await dav.get(book, uid)
    merged = merge_contact_into_vcard(existing_vcf, body, name_format)
    await dav.update(book, uid, merged, etag)
    return {"status": "updated", "uid": uid}


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
        raise HTTPException(
            status_code=422, detail="At least one of firstname or lastname is required"
        )
    missing = missing_required_fields(existing_contact, required_fields)
    if missing:
        raise HTTPException(
            status_code=422, detail=f"Missing required field(s): {', '.join(missing)}"
        )
    merged_vcf = merge_contact_into_vcard(existing_vcf, existing_contact, name_format)
    await dav.update(book, uid, merged_vcf, etag)
    return {"status": "updated", "uid": uid}


@router.post("/{book}/contacts/{uid}/merge/{other_uid}", response_model=ContactOut)
async def merge_contact(
    book: str,
    uid: str,
    other_uid: str,
    dav: CardDAVClient = Depends(get_dav),
    name_format: str = Depends(get_name_format),
) -> ContactOut:
    if uid == other_uid:
        raise HTTPException(status_code=422, detail="uid and other_uid must be different")
    primary_vcf, primary_etag = await dav.get(book, uid)
    secondary_vcf, _ = await dav.get(book, other_uid)
    primary = vcard_to_contact(primary_vcf, name_format)
    secondary = vcard_to_contact(secondary_vcf, name_format)
    merged = merge_contacts(primary, secondary)
    merged_vcf = merge_contact_into_vcard(primary_vcf, merged, name_format)
    await dav.update(book, uid, merged_vcf, primary_etag)
    # Non-atomic: if delete fails the primary is already updated.
    # Caller can retry — merge is idempotent at the data level.
    await dav.delete(book, other_uid)
    contact_out = vcard_to_contact(merged_vcf, name_format)
    contact_out.uid = uid
    return contact_out


@router.post("/{book}/contacts/{uid}/move/{target_book}")
async def move_contact(
    book: str,
    uid: str,
    target_book: str,
    dav: CardDAVClient = Depends(get_dav),
) -> dict:
    vcf, _ = await dav.get(book, uid)
    await dav.create(target_book, uid, vcf)
    await dav.delete(book, uid)
    return {"status": "moved", "uid": uid, "from": book, "to": target_book}


@router.delete("/{book}/contacts/{uid}")
async def delete_contact(
    book: str,
    uid: str,
    dav: CardDAVClient = Depends(get_dav),
) -> dict:
    await dav.delete(book, uid)
    return {"status": "deleted", "uid": uid}
