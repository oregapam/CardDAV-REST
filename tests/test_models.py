import pytest
from pydantic import ValidationError

from app.models import (
    Address,
    Contact,
    ContactCreate,
    ContactIn,
    ContactOut,
    SearchRequest,
    TypedValue,
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
