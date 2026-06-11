import xml.etree.ElementTree as ET

NS = {"d": "DAV:", "c": "urn:ietf:params:xml:ns:carddav"}
_D = "{DAV:}"
_C = "{urn:ietf:params:xml:ns:carddav}"


def build_search_xml(
    email: str | None,
    phone: str | None,
    name: str | None,
    match_condition: str,
) -> bytes:
    root = ET.Element(f"{_C}addressbook-query")
    prop = ET.SubElement(root, f"{_D}prop")
    ET.SubElement(prop, f"{_D}getetag")
    ET.SubElement(prop, f"{_C}address-data")
    filt = ET.SubElement(root, f"{_C}filter", {"test": match_condition})

    def add_filter(prop_name: str, value: str, match_type: str) -> None:
        pf = ET.SubElement(filt, f"{_C}prop-filter", {"name": prop_name})
        tm = ET.SubElement(
            pf,
            f"{_C}text-match",
            {"collation": "i;unicode-casemap", "match-type": match_type},
        )
        tm.text = value

    if email:
        add_filter("EMAIL", email, "equals")
    if phone:
        add_filter("TEL", phone, "contains")
    if name:
        add_filter("FN", name, "contains")

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def parse_multistatus(xml_text: str) -> list[tuple[str, str]]:
    root = ET.fromstring(xml_text)
    results: list[tuple[str, str]] = []
    for response in root.findall("d:response", NS):
        href = response.findtext("d:href", "", NS)
        vcf = response.findtext(".//c:address-data", None, NS)
        if vcf is None:
            continue
        uid = href.rstrip("/").rsplit("/", 1)[-1].removesuffix(".vcf")
        results.append((uid, vcf))
    return results
