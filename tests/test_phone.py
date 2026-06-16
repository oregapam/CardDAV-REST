import pytest

from app.phone import normalize_phone


def test_normalize_local_hu_mobile_to_e164():
    assert normalize_phone("06301234567", "HU") == "+36301234567"


def test_normalize_local_hu_landline_to_e164():
    assert normalize_phone("0612345678", "HU") == "+3612345678"


def test_normalize_leaves_already_e164_unchanged():
    assert normalize_phone("+36301234567", "HU") == "+36301234567"


def test_normalize_respects_explicit_region_argument():
    # a "+"-prefixed number is unambiguous regardless of default_region
    assert normalize_phone("+36301234567", "DE") == "+36301234567"


def test_normalize_empty_string_is_noop():
    assert normalize_phone("", "HU") == ""


def test_normalize_blank_string_is_noop():
    assert normalize_phone("   ", "HU") == "   "


def test_normalize_invalid_number_raises_value_error():
    with pytest.raises(ValueError):
        normalize_phone("123", "HU")
