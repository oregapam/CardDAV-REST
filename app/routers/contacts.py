import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

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


@router.post("/search", response_model=SearchResponse)
async def search_contacts(
    req: SearchRequest, dav: CardDAVClient = Depends(get_dav)
) -> SearchResponse:
    results = await dav.search(
        email=req.email,
        phone=req.phone,
        name=req.name,
        match_condition=req.match_condition,
    )
    matches = []
    for uid, vcf in results:
        contact = vcard_to_contact(vcf)
        matches.append(
            SearchMatch(uid=uid, fn=contact.fn, emails=contact.emails, phones=contact.phones)
        )
    return SearchResponse(
        exists=bool(matches),
        match_count=len(matches),
        matches=matches,
        searched_params=req.model_dump(exclude_none=True),
    )
