from typing import Literal, Optional

from pydantic import BaseModel, model_validator


class TypedValue(BaseModel):
    type: str = "other"
    value: str


class Address(BaseModel):
    type: str = "home"
    street: str = ""
    city: str = ""
    zip: str = ""
    state: str = ""
    country: str = ""


class Contact(BaseModel):
    firstname: str = ""
    lastname: str = ""
    middlename: str = ""
    prefix: str = ""
    suffix: str = ""
    emails: list[TypedValue] = []
    phones: list[TypedValue] = []
    addresses: list[Address] = []
    org: str = ""
    title: str = ""
    birthday: str = ""
    urls: list[str] = []
    note: str = ""
    photo: str = ""
    categories: list[str] = []


class ContactIn(Contact):
    @model_validator(mode="after")
    def require_name(self) -> "ContactIn":
        if not (self.firstname or self.lastname):
            raise ValueError("At least one of firstname or lastname is required")
        return self


class ContactCreate(ContactIn):
    check_duplicates: bool = False


class ContactOut(Contact):
    uid: str = ""
    fn: str = ""
    etag: str = ""


class ContactsPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ContactOut]


class SearchRequest(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    match_condition: Literal["allof", "anyof"] = "allof"

    @model_validator(mode="after")
    def require_filter(self) -> "SearchRequest":
        if not (self.email or self.phone or self.name):
            raise ValueError("At least one of email, phone or name is required")
        return self


class SearchMatch(BaseModel):
    uid: str
    fn: str = ""
    emails: list[TypedValue] = []
    phones: list[TypedValue] = []


class SearchResponse(BaseModel):
    exists: bool
    match_count: int
    matches: list[SearchMatch]
    searched_params: dict
