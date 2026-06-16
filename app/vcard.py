import base64

import vobject

from app.models import Address, Contact, ContactOut, TypedValue

NAME_FORMAT_DEFAULT = "western"

MANAGED_PROPS = ("n", "fn", "email", "tel", "adr", "org", "title", "bday", "url", "note", "photo", "categories")


def build_fn(contact: Contact, name_format: str = NAME_FORMAT_DEFAULT) -> str:
    if name_format == "eastern":
        parts = [contact.lastname, contact.firstname]
    elif name_format == "eastern_full":
        parts = [contact.prefix, contact.lastname, contact.firstname, contact.suffix]
    else:  # western
        parts = [contact.prefix, contact.firstname, contact.middlename, contact.lastname, contact.suffix]
    return " ".join(p for p in parts if p)


def contact_to_vcard(contact: Contact, uid: str, name_format: str = NAME_FORMAT_DEFAULT) -> str:
    card = vobject.vCard()
    card.add("uid").value = uid
    _fill_card(card, contact, name_format)
    return card.serialize()


def _fill_card(card, contact: Contact, name_format: str = NAME_FORMAT_DEFAULT) -> None:
    n = card.add("n")
    n.value = vobject.vcard.Name(
        family=contact.lastname,
        given=contact.firstname,
        additional=contact.middlename,
        prefix=contact.prefix,
        suffix=contact.suffix,
    )
    card.add("fn").value = build_fn(contact, name_format)
    for email in contact.emails:
        el = card.add("email")
        el.value = email.value
        el.params["TYPE"] = [email.type.upper()]
    for phone in contact.phones:
        el = card.add("tel")
        el.value = phone.value
        el.params["TYPE"] = [phone.type.upper()]
    for addr in contact.addresses:
        el = card.add("adr")
        el.value = vobject.vcard.Address(
            street=addr.street,
            city=addr.city,
            region=addr.state,
            code=addr.zip,
            country=addr.country,
        )
        el.params["TYPE"] = [addr.type.upper()]
    if contact.org:
        card.add("org").value = [contact.org]
    if contact.title:
        card.add("title").value = contact.title
    if contact.birthday:
        card.add("bday").value = contact.birthday
    for url in contact.urls:
        card.add("url").value = url
    if contact.note:
        card.add("note").value = contact.note
    if contact.photo:
        el = card.add("photo")
        if contact.photo.startswith(("http://", "https://")):
            el.value = contact.photo
            el.params["VALUE"] = ["uri"]
        else:
            el.value = base64.b64decode(contact.photo)
            el.encoding_param = "b"
    if contact.categories:
        card.add("categories").value = list(contact.categories)


def _first(value):
    return value[0] if isinstance(value, list) else value


def _type_of(el) -> str:
    types = [t.lower() for t in el.params.get("TYPE", []) if t.lower() not in ("internet", "pref")]
    return types[0] if types else "other"


def vcard_to_contact(vcf: str, name_format: str = NAME_FORMAT_DEFAULT) -> ContactOut:
    card = vobject.readOne(vcf)
    c = card.contents

    def text(prop: str) -> str:
        return c[prop][0].value if prop in c else ""

    firstname = lastname = middlename = prefix = suffix = ""
    if "n" in c:
        name = c["n"][0].value
        firstname = _first(name.given) or ""
        lastname = _first(name.family) or ""
        middlename = _first(name.additional) or ""
        prefix = _first(name.prefix) or ""
        suffix = _first(name.suffix) or ""

    addresses = []
    for el in c.get("adr", []):
        a = el.value
        addresses.append(
            Address(
                type=_type_of(el),
                street=_first(a.street) or "",
                city=_first(a.city) or "",
                zip=_first(a.code) or "",
                state=_first(a.region) or "",
                country=_first(a.country) or "",
            )
        )

    photo = ""
    if "photo" in c:
        value = c["photo"][0].value
        photo = base64.b64encode(value).decode("ascii") if isinstance(value, bytes) else value

    org = ""
    if "org" in c:
        org = _first(c["org"][0].value) or ""

    computed_fn = build_fn(
        Contact(prefix=prefix, firstname=firstname, middlename=middlename, lastname=lastname, suffix=suffix),
        name_format,
    ) or text("fn")

    return ContactOut(
        uid=text("uid"),
        fn=computed_fn,
        firstname=firstname,
        lastname=lastname,
        middlename=middlename,
        prefix=prefix,
        suffix=suffix,
        emails=[TypedValue(type=_type_of(el), value=el.value) for el in c.get("email", [])],
        phones=[TypedValue(type=_type_of(el), value=el.value) for el in c.get("tel", [])],
        addresses=addresses,
        org=org,
        title=text("title"),
        birthday=text("bday"),
        urls=[el.value for el in c.get("url", [])],
        note=text("note"),
        photo=photo,
        categories=list(c["categories"][0].value) if "categories" in c else [],
    )


def merge_contact_into_vcard(existing_vcf: str, contact: Contact, name_format: str = NAME_FORMAT_DEFAULT) -> str:
    card = vobject.readOne(existing_vcf)
    for prop in MANAGED_PROPS:
        if prop in card.contents:
            del card.contents[prop]
    _fill_card(card, contact, name_format)
    return card.serialize()
