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


class AddressbookInfo(BaseModel):
    name: str
    displayname: str


class ContactsPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ContactOut]
    warning: Optional[str] = None


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
