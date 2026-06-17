from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator


class TypedValue(BaseModel):
    type: str = "other"
    value: str

    @field_validator("value")
    @classmethod
    def value_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("value must not be empty")
        return v


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


def merge_contacts(primary: Contact, secondary: Contact) -> Contact:
    result = primary.model_copy(deep=True)

    for field in ("firstname", "lastname", "middlename", "prefix", "suffix",
                  "org", "title", "birthday", "note", "photo"):
        if not getattr(result, field):
            setattr(result, field, getattr(secondary, field))

    seen_emails = {e.value.lower() for e in result.emails}
    extra_emails = [e for e in secondary.emails if e.value.lower() not in seen_emails]
    result.emails = list(result.emails) + extra_emails

    # Phones are assumed to be E.164-normalized before merge (enforced at create/update).
    seen_phones = {p.value for p in result.phones}
    extra_phones = [p for p in secondary.phones if p.value not in seen_phones]
    result.phones = list(result.phones) + extra_phones

    seen_addrs = {(a.street, a.city, a.zip) for a in result.addresses}
    extra_addrs = [a for a in secondary.addresses if (a.street, a.city, a.zip) not in seen_addrs]
    result.addresses = list(result.addresses) + extra_addrs

    seen_urls = set(result.urls)
    extra_urls = [u for u in secondary.urls if u not in seen_urls]
    result.urls = list(result.urls) + extra_urls

    seen_cats = set(result.categories)
    extra_cats = [c for c in secondary.categories if c not in seen_cats]
    result.categories = list(result.categories) + extra_cats

    return result


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


class AddressbookStats(BaseModel):
    name: str
    displayname: str
    contact_count: int
    last_modified: str | None
    oldest_modified: str | None
    total_size_bytes: int


class StatsResponse(BaseModel):
    total_contacts: int
    total_size_bytes: int
    addressbooks: list[AddressbookStats]


class ConfigResponse(BaseModel):
    name_format: str
    default_region: str
    required_fields: list[str]
