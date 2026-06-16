import phonenumbers


def normalize_phone(value: str, default_region: str) -> str:
    """Returns the number in E.164 format, or raises ValueError if invalid."""
    if not value.strip():
        return value
    try:
        parsed = phonenumbers.parse(value, default_region)
    except phonenumbers.NumberParseException as exc:
        raise ValueError(f"Invalid phone number: {value}") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError(f"Invalid phone number: {value}")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
