import pytest
from pydantic import ValidationError

from app.models import (
    Address,
    Contact,
    ContactCreate,
    ContactIn,
    ContactOut,
    ContactPatch,
    SearchRequest,
    TypedValue,
    apply_contact_patch,
    merge_contacts,
)


def test_contact_base_allows_all_empty():
    c = Contact()
    assert c.firstname == ""
    assert c.emails == []
    assert c.categories == []


def test_contact_in_requires_a_name():
    with pytest.raises(ValidationError):
        ContactIn(emails=[TypedValue(type="work", value="a@b.hu")])
    assert ContactIn(firstname="Anna").firstname == "Anna"
    assert ContactIn(lastname="Kis").lastname == "Kis"


def test_contact_create_duplicate_flag_defaults_false():
    c = ContactCreate(firstname="Anna")
    assert c.check_duplicates is False


def test_contact_out_carries_uid_fn_etag():
    c = ContactOut(uid="abc", fn="Anna Kis", etag='"v1"')
    assert (c.uid, c.fn, c.etag) == ("abc", "Anna Kis", '"v1"')


def test_typed_value_and_address_defaults():
    assert TypedValue(value="x").type == "other"
    a = Address(street="Fő utca 1.", city="Budapest", zip="1011")
    assert a.type == "home"
    assert a.country == ""


def test_search_request_requires_at_least_one_filter():
    with pytest.raises(ValidationError):
        SearchRequest()
    assert SearchRequest(email="a@b.hu").match_condition == "allof"


def test_search_request_rejects_bad_match_condition():
    with pytest.raises(ValidationError):
        SearchRequest(email="a@b.hu", match_condition="sometimes")
    assert SearchRequest(name="Anna", match_condition="anyof").match_condition == "anyof"


def test_contact_patch_rejects_empty_body():
    with pytest.raises(ValidationError):
        ContactPatch()


def test_contact_patch_accepts_single_field():
    p = ContactPatch(org="ACME")
    assert p.org == "ACME"
    assert "org" in p.model_fields_set


def test_apply_contact_patch_leaves_unset_fields_untouched():
    existing = Contact(firstname="Anna", lastname="Kis", org="Old Kft.")
    patch = ContactPatch(org="New Kft.")
    apply_contact_patch(existing, patch)
    assert existing.firstname == "Anna"
    assert existing.lastname == "Kis"
    assert existing.org == "New Kft."


def test_apply_contact_patch_clears_field_sent_as_empty_string():
    existing = Contact(firstname="Anna", org="ACME")
    patch = ContactPatch(org="")
    apply_contact_patch(existing, patch)
    assert existing.org == ""


def test_apply_contact_patch_clears_field_sent_as_null():
    existing = Contact(firstname="Anna", org="ACME")
    patch = ContactPatch(org=None)
    apply_contact_patch(existing, patch)
    assert existing.org == ""


def test_apply_contact_patch_replaces_list_field_wholesale():
    existing = Contact(emails=[TypedValue(type="work", value="old@ceg.hu")])
    patch = ContactPatch(emails=[TypedValue(type="home", value="new@ceg.hu")])
    apply_contact_patch(existing, patch)
    assert len(existing.emails) == 1
    assert existing.emails[0].value == "new@ceg.hu"


def test_apply_contact_patch_clears_list_field_sent_empty():
    existing = Contact(emails=[TypedValue(value="a@b.hu")])
    patch = ContactPatch(emails=[])
    apply_contact_patch(existing, patch)
    assert existing.emails == []


def test_apply_contact_patch_multiple_fields_at_once():
    existing = Contact(firstname="Anna", lastname="Kis", org="Old", title="Dev")
    patch = ContactPatch(org="New", title="Lead")
    apply_contact_patch(existing, patch)
    assert existing.org == "New"
    assert existing.title == "Lead"
    assert existing.firstname == "Anna"


def test_merge_scalar_primary_wins():
    primary = Contact(firstname="Anna", org="ACME")
    secondary = Contact(firstname="Anna", org="ACME Kft.", note="régi ügyfél")
    result = merge_contacts(primary, secondary)
    assert result.org == "ACME"
    assert result.note == "régi ügyfél"


def test_merge_scalar_secondary_fills_empty():
    primary = Contact(firstname="Anna", lastname="")
    secondary = Contact(firstname="Anna", lastname="Kis")
    result = merge_contacts(primary, secondary)
    assert result.lastname == "Kis"


def test_merge_scalar_secondary_fills_multiple_empty_fields():
    primary = Contact(firstname="Anna", prefix="", title="", birthday="")
    secondary = Contact(firstname="Anna", prefix="Dr.", title="Engineer", birthday="1990-01-01")
    result = merge_contacts(primary, secondary)
    assert result.prefix == "Dr."
    assert result.title == "Engineer"
    assert result.birthday == "1990-01-01"


def test_merge_emails_union():
    primary = Contact(emails=[TypedValue(type="work", value="anna@ceg.hu")])
    secondary = Contact(emails=[TypedValue(type="home", value="anna@gmail.com")])
    result = merge_contacts(primary, secondary)
    assert len(result.emails) == 2
    assert result.emails[0].value == "anna@ceg.hu"
    assert result.emails[1].value == "anna@gmail.com"


def test_merge_emails_dedup_exact_primary_type_wins():
    primary = Contact(emails=[TypedValue(type="work", value="anna@ceg.hu")])
    secondary = Contact(emails=[TypedValue(type="home", value="anna@ceg.hu")])
    result = merge_contacts(primary, secondary)
    assert len(result.emails) == 1
    assert result.emails[0].type == "work"


def test_merge_emails_dedup_case_insensitive():
    primary = Contact(emails=[TypedValue(type="work", value="Anna@Ceg.Hu")])
    secondary = Contact(emails=[TypedValue(type="home", value="anna@ceg.hu")])
    result = merge_contacts(primary, secondary)
    assert len(result.emails) == 1
    assert result.emails[0].value == "Anna@Ceg.Hu"  # primary value preserved


def test_merge_phones_union():
    primary = Contact(phones=[])
    secondary = Contact(phones=[TypedValue(type="mobile", value="+36301234567")])
    result = merge_contacts(primary, secondary)
    assert len(result.phones) == 1
    assert result.phones[0].value == "+36301234567"


def test_merge_phones_dedup_primary_type_wins():
    primary = Contact(phones=[TypedValue(type="work", value="+36301234567")])
    secondary = Contact(phones=[TypedValue(type="mobile", value="+36301234567")])
    result = merge_contacts(primary, secondary)
    assert len(result.phones) == 1
    assert result.phones[0].type == "work"


def test_merge_addresses_union():
    addr1 = Address(type="home", street="Fő u. 1.", city="Budapest", zip="1011")
    addr2 = Address(type="work", street="Váci út 10.", city="Budapest", zip="1133")
    primary = Contact(addresses=[addr1])
    secondary = Contact(addresses=[addr2])
    result = merge_contacts(primary, secondary)
    assert len(result.addresses) == 2


def test_merge_addresses_dedup_by_street_city_zip():
    addr = Address(type="home", street="Fő u. 1.", city="Budapest", zip="1011")
    addr_dup = Address(type="work", street="Fő u. 1.", city="Budapest", zip="1011")
    primary = Contact(addresses=[addr])
    secondary = Contact(addresses=[addr_dup])
    result = merge_contacts(primary, secondary)
    assert len(result.addresses) == 1
    assert result.addresses[0].type == "home"


def test_merge_urls_union_and_dedup():
    primary = Contact(urls=["https://example.com"])
    secondary = Contact(urls=["https://example.com", "https://other.com"])
    result = merge_contacts(primary, secondary)
    assert len(result.urls) == 2
    assert "https://example.com" in result.urls
    assert "https://other.com" in result.urls


def test_merge_categories_union_and_dedup():
    primary = Contact(categories=["leads", "vip"])
    secondary = Contact(categories=["vip", "customers"])
    result = merge_contacts(primary, secondary)
    assert set(result.categories) == {"leads", "vip", "customers"}


def test_merge_does_not_mutate_inputs():
    primary = Contact(firstname="Anna", emails=[TypedValue(value="anna@ceg.hu")])
    secondary = Contact(firstname="Anna", emails=[TypedValue(value="anna@gmail.com")])
    merge_contacts(primary, secondary)
    assert len(primary.emails) == 1
