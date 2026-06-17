import pytest
from pydantic import ValidationError

from app.models import Address, Contact, TypedValue
from app.required_fields import missing_required_fields


def test_no_required_fields_returns_empty():
    contact = Contact()
    assert missing_required_fields(contact, ()) == []


def test_empty_string_field_is_missing():
    contact = Contact(org="")
    assert missing_required_fields(contact, ("org",)) == ["org"]


def test_filled_string_field_is_present():
    contact = Contact(org="ACME")
    assert missing_required_fields(contact, ("org",)) == []


def test_whitespace_only_string_field_is_missing():
    contact = Contact(org="   ")
    assert missing_required_fields(contact, ("org",)) == ["org"]


def test_empty_typed_value_list_is_missing():
    contact = Contact(emails=[])
    assert missing_required_fields(contact, ("emails",)) == ["emails"]


def test_typed_value_with_blank_value_raises():
    with pytest.raises(ValidationError, match="value must not be empty"):
        TypedValue(value="")


def test_typed_value_list_with_real_value_is_present():
    contact = Contact(emails=[TypedValue(value="a@b.hu")])
    assert missing_required_fields(contact, ("emails",)) == []


def test_empty_str_list_is_missing():
    contact = Contact(categories=[])
    assert missing_required_fields(contact, ("categories",)) == ["categories"]


def test_str_list_with_only_blank_entries_is_missing():
    contact = Contact(categories=[""])
    assert missing_required_fields(contact, ("categories",)) == ["categories"]


def test_str_list_with_real_entry_is_present():
    contact = Contact(categories=["vip"])
    assert missing_required_fields(contact, ("categories",)) == []


def test_empty_address_list_is_missing():
    contact = Contact(addresses=[])
    assert missing_required_fields(contact, ("addresses",)) == ["addresses"]


def test_address_list_with_one_entry_is_present():
    contact = Contact(addresses=[Address()])
    assert missing_required_fields(contact, ("addresses",)) == []


def test_multiple_missing_fields_returned_in_order():
    contact = Contact()
    assert missing_required_fields(contact, ("emails", "org", "phones")) == [
        "emails",
        "org",
        "phones",
    ]


def test_mixed_present_and_missing_fields():
    contact = Contact(org="ACME")
    assert missing_required_fields(contact, ("emails", "org")) == ["emails"]
