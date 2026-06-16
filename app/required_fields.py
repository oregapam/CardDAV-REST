from app.models import Contact, TypedValue


def missing_required_fields(contact: Contact, required: tuple[str, ...]) -> list[str]:
    """Returns the names of required fields that are absent on the contact,
    preserving the order given in `required`."""
    return [name for name in required if not _is_present(getattr(contact, name))]


def _is_present(value) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        if not value:
            return False
        first = value[0]
        if isinstance(first, TypedValue):
            return any(item.value.strip() for item in value)
        if isinstance(first, str):
            return any(item.strip() for item in value)
        return True  # e.g. Address entries — presence in the list is enough
    return bool(value)
