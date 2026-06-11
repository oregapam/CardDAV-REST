import base64

import vobject

from app.models import Contact


def build_fn(contact: Contact) -> str:
    parts = [contact.prefix, contact.firstname, contact.middlename, contact.lastname, contact.suffix]
    return " ".join(p for p in parts if p)


def contact_to_vcard(contact: Contact, uid: str) -> str:
    card = vobject.vCard()
    card.add("uid").value = uid
    _fill_card(card, contact)
    return card.serialize()


def _fill_card(card, contact: Contact) -> None:
    n = card.add("n")
    n.value = vobject.vcard.Name(
        family=contact.lastname,
        given=contact.firstname,
        additional=contact.middlename,
        prefix=contact.prefix,
        suffix=contact.suffix,
    )
    card.add("fn").value = build_fn(contact)
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
