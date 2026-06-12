import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from app.carddav import CardDAVClient
from app.models import (
    ContactCreate,
    ContactIn,
    ContactOut,
    SearchMatch,
    SearchRequest,
    SearchResponse,
)
from app.vcard import contact_to_vcard, merge_contact_into_vcard, vcard_to_contact

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


def get_dav(request: Request) -> CardDAVClient:
    return request.app.state.carddav


def get_name_format(request: Request) -> str:
    return request.app.state.name_format


@router.post("/search", response_model=SearchResponse)
async def search_contacts(
    req: SearchRequest,
    dav: CardDAVClient = Depends(get_dav),
    name_format: str = Depends(get_name_format),
) -> SearchResponse:
    results = await dav.search(
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


@router.get("", response_model=list[ContactOut])
async def list_contacts(
    dav: CardDAVClient = Depends(get_dav),
    name_format: str = Depends(get_name_format),
) -> list[ContactOut]:
    results = await dav.list_all()
    contacts = []
    for uid, vcf in results:
        contact = vcard_to_contact(vcf, name_format)
        contact.uid = uid
        contacts.append(contact)
    return contacts


@router.post("", status_code=201)
async def create_contact(
    body: ContactCreate,
    dav: CardDAVClient = Depends(get_dav),
    name_format: str = Depends(get_name_format),
) -> dict:
    if body.check_duplicates:
        for email in body.emails:
            results = await dav.search(email=email.value)
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
    await dav.create(uid, vcf)
    return {"status": "success", "uid": uid, "filename": f"{uid}.vcf"}


@router.get("/{uid}/vcard")
async def get_contact_vcard(
    uid: str,
    dav: CardDAVClient = Depends(get_dav),
) -> Response:
    vcf, etag = await dav.get(uid)
    headers = {"Content-Disposition": f'attachment; filename="{uid}.vcf"'}
    if etag:
        headers["ETag"] = etag
    return Response(content=vcf, media_type="text/vcard; charset=utf-8", headers=headers)


@router.get("/{uid}", response_model=ContactOut)
async def get_contact(
    uid: str,
    dav: CardDAVClient = Depends(get_dav),
    name_format: str = Depends(get_name_format),
) -> ContactOut:
    vcf, etag = await dav.get(uid)
    contact = vcard_to_contact(vcf, name_format)
    contact.uid = uid
    contact.etag = etag
    return contact


@router.put("/{uid}")
async def update_contact(
    uid: str,
    body: ContactIn,
    dav: CardDAVClient = Depends(get_dav),
    name_format: str = Depends(get_name_format),
) -> dict:
    existing_vcf, etag = await dav.get(uid)
    merged = merge_contact_into_vcard(existing_vcf, body, name_format)
    await dav.update(uid, merged, etag)
    return {"status": "updated", "uid": uid}


@router.delete("/{uid}")
async def delete_contact(uid: str, dav: CardDAVClient = Depends(get_dav)) -> dict:
    await dav.delete(uid)
    return {"status": "deleted", "uid": uid}
