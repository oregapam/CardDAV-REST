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
