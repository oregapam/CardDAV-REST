from fastapi import APIRouter, Depends, Request

from app.carddav import CardDAVClient
from app.models import AddressbookStats, StatsResponse

router = APIRouter(prefix="/api", tags=["stats"])


def get_dav(request: Request) -> CardDAVClient:
    return request.app.state.carddav


@router.get("/stats", response_model=StatsResponse)
async def get_stats(dav: CardDAVClient = Depends(get_dav)) -> StatsResponse:
    books = await dav.list_addressbooks()
    addressbook_stats = []
    total_contacts = 0
    total_size = 0
    for book in books:
        count, last_mod, oldest_mod, size = await dav.stat_book(book["name"])
        total_contacts += count
        total_size += size
        addressbook_stats.append(AddressbookStats(
            name=book["name"],
            displayname=book["displayname"],
            contact_count=count,
            last_modified=last_mod,
            oldest_modified=oldest_mod,
            total_size_bytes=size,
        ))
    return StatsResponse(
        total_contacts=total_contacts,
        total_size_bytes=total_size,
        addressbooks=addressbook_stats,
    )
