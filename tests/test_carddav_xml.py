import xml.etree.ElementTree as ET

from app.carddav import build_search_xml, parse_addressbooks, parse_multistatus, parse_stat_propfind

C = "{urn:ietf:params:xml:ns:carddav}"
D = "{DAV:}"


def test_all_filters_allof():
    xml_bytes = build_search_xml(email="a@b.hu", phone="+361", name="Anna", match_condition="allof")
    root = ET.fromstring(xml_bytes)
    assert root.tag == f"{C}addressbook-query"
    prop = root.find(f"{D}prop")
    assert prop.find(f"{D}getetag") is not None
    assert prop.find(f"{C}address-data") is not None
    filt = root.find(f"{C}filter")
    assert filt.get("test") == "allof"
    pfs = filt.findall(f"{C}prop-filter")
    assert [pf.get("name") for pf in pfs] == ["EMAIL", "TEL", "FN"]
    email_tm = pfs[0].find(f"{C}text-match")
    assert email_tm.get("match-type") == "equals"
    assert email_tm.get("collation") == "i;unicode-casemap"
    assert email_tm.text == "a@b.hu"
    assert pfs[1].find(f"{C}text-match").get("match-type") == "contains"
    assert pfs[2].find(f"{C}text-match").get("match-type") == "contains"


def test_single_filter_anyof():
    root = ET.fromstring(build_search_xml(email=None, phone=None, name="Anna", match_condition="anyof"))
    filt = root.find(f"{C}filter")
    assert filt.get("test") == "anyof"
    pfs = filt.findall(f"{C}prop-filter")
    assert [pf.get("name") for pf in pfs] == ["FN"]


def test_search_value_is_escaped_not_injected():
    xml_bytes = build_search_xml(email='"]><evil/>', phone=None, name=None, match_condition="allof")
    root = ET.fromstring(xml_bytes)  # must stay well-formed
    tm = root.find(f"{C}filter/{C}prop-filter/{C}text-match")
    assert tm.text == '"]><evil/>'


MULTISTATUS_ONE = (
    '<?xml version="1.0"?>'
    '<d:multistatus xmlns:d="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav">'
    "<d:response>"
    "<d:href>/dav.php/addressbooks/testuser/default/abc-123.vcf</d:href>"
    "<d:propstat><d:prop>"
    '<d:getetag>"etag-1"</d:getetag>'
    "<card:address-data>BEGIN:VCARD\nVERSION:3.0\nUID:abc-123\nFN:Teszt János\n"
    "N:Teszt;János;;;\nEMAIL;TYPE=HOME:teszt@email.hu\nTEL;TYPE=CELL:+36301234567\n"
    "END:VCARD\n</card:address-data>"
    "</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>"
    "</d:response>"
    "</d:multistatus>"
)

MULTISTATUS_EMPTY = (
    '<?xml version="1.0"?>'
    '<d:multistatus xmlns:d="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav"></d:multistatus>'
)


def test_parse_multistatus_one_match():
    results = parse_multistatus(MULTISTATUS_ONE)
    assert len(results) == 1
    uid, vcf = results[0]
    assert uid == "abc-123"
    assert "FN:Teszt János" in vcf


def test_parse_multistatus_empty():
    assert parse_multistatus(MULTISTATUS_EMPTY) == []


PROPFIND_ADDRESSBOOKS = (
    '<?xml version="1.0"?>'
    '<d:multistatus xmlns:d="DAV:">'
    "<d:response>"
    "<d:href>/dav.php/addressbooks/testuser/</d:href>"
    "<d:propstat><d:prop><d:displayname>testuser</d:displayname></d:prop>"
    "<d:status>HTTP/1.1 200 OK</d:status></d:propstat>"
    "</d:response>"
    "<d:response>"
    "<d:href>/dav.php/addressbooks/testuser/default/</d:href>"
    "<d:propstat><d:prop><d:displayname>Default</d:displayname></d:prop>"
    "<d:status>HTTP/1.1 200 OK</d:status></d:propstat>"
    "</d:response>"
    "<d:response>"
    "<d:href>/dav.php/addressbooks/testuser/leads/</d:href>"
    "<d:propstat><d:prop><d:displayname>Leads</d:displayname></d:prop>"
    "<d:status>HTTP/1.1 200 OK</d:status></d:propstat>"
    "</d:response>"
    "</d:multistatus>"
)

PRINCIPAL_URL = "http://baikal/dav.php/addressbooks/testuser/"


def test_parse_addressbooks_returns_books_without_principal():
    results = parse_addressbooks(PROPFIND_ADDRESSBOOKS, PRINCIPAL_URL)
    assert len(results) == 2
    assert {"name": "default", "displayname": "Default"} in results
    assert {"name": "leads", "displayname": "Leads"} in results


def test_parse_addressbooks_empty_principal():
    xml = (
        '<?xml version="1.0"?>'
        '<d:multistatus xmlns:d="DAV:">'
        "<d:response>"
        "<d:href>/dav.php/addressbooks/testuser/</d:href>"
        "<d:propstat><d:prop><d:displayname>testuser</d:displayname></d:prop>"
        "<d:status>HTTP/1.1 200 OK</d:status></d:propstat>"
        "</d:response>"
        "</d:multistatus>"
    )
    assert parse_addressbooks(xml, PRINCIPAL_URL) == []


STAT_PROPFIND_TWO = (
    '<?xml version="1.0"?>'
    '<d:multistatus xmlns:d="DAV:">'
    '<d:response>'
    '<d:href>/dav.php/addressbooks/testuser/default/</d:href>'
    '<d:propstat><d:prop>'
    '<d:getlastmodified>Mon, 17 Jun 2026 14:00:00 GMT</d:getlastmodified>'
    '</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>'
    '</d:response>'
    '<d:response>'
    '<d:href>/dav.php/addressbooks/testuser/default/uid1.vcf</d:href>'
    '<d:propstat><d:prop>'
    '<d:getetag>"etag-1"</d:getetag>'
    '<d:getlastmodified>Mon, 17 Jun 2026 14:00:00 GMT</d:getlastmodified>'
    '<d:getcontentlength>512</d:getcontentlength>'
    '</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>'
    '</d:response>'
    '<d:response>'
    '<d:href>/dav.php/addressbooks/testuser/default/uid2.vcf</d:href>'
    '<d:propstat><d:prop>'
    '<d:getetag>"etag-2"</d:getetag>'
    '<d:getlastmodified>Tue, 15 Jan 2024 10:00:00 GMT</d:getlastmodified>'
    '<d:getcontentlength>256</d:getcontentlength>'
    '</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>'
    '</d:response>'
    '</d:multistatus>'
)

STAT_PROPFIND_EMPTY = (
    '<?xml version="1.0"?>'
    '<d:multistatus xmlns:d="DAV:">'
    '<d:response>'
    '<d:href>/dav.php/addressbooks/testuser/default/</d:href>'
    '<d:propstat><d:prop>'
    '<d:getlastmodified>Mon, 17 Jun 2026 14:00:00 GMT</d:getlastmodified>'
    '</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>'
    '</d:response>'
    '</d:multistatus>'
)

STAT_PROPFIND_NO_CONTENTLENGTH = (
    '<?xml version="1.0"?>'
    '<d:multistatus xmlns:d="DAV:">'
    '<d:response>'
    '<d:href>/dav.php/addressbooks/testuser/default/</d:href>'
    '<d:propstat><d:prop>'
    '</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>'
    '</d:response>'
    '<d:response>'
    '<d:href>/dav.php/addressbooks/testuser/default/uid1.vcf</d:href>'
    '<d:propstat><d:prop>'
    '<d:getetag>"etag-1"</d:getetag>'
    '<d:getlastmodified>Mon, 17 Jun 2026 14:00:00 GMT</d:getlastmodified>'
    '</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat>'
    '</d:response>'
    '</d:multistatus>'
)


def test_parse_stat_propfind_count_and_size():
    count, last_mod, oldest_mod, total_size = parse_stat_propfind(STAT_PROPFIND_TWO)
    assert count == 2
    assert total_size == 768


def test_parse_stat_propfind_dates_two_contacts():
    _, last_mod, oldest_mod, _ = parse_stat_propfind(STAT_PROPFIND_TWO)
    assert last_mod != oldest_mod
    assert last_mod == "2026-06-17T14:00:00+00:00"
    assert oldest_mod == "2024-01-15T10:00:00+00:00"


def test_parse_stat_propfind_empty_book():
    count, last_mod, oldest_mod, total_size = parse_stat_propfind(STAT_PROPFIND_EMPTY)
    assert count == 0
    assert last_mod is None
    assert oldest_mod is None
    assert total_size == 0


def test_parse_stat_propfind_no_content_length():
    count, last_mod, oldest_mod, total_size = parse_stat_propfind(STAT_PROPFIND_NO_CONTENTLENGTH)
    assert count == 1
    assert total_size == 0
    assert last_mod is not None
    assert oldest_mod is not None
