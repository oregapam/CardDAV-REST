import logging
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import httpx

from app.config import Settings

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


def build_quick_search_xml(q: str) -> bytes:
    root = ET.Element(f"{_C}addressbook-query")
    prop = ET.SubElement(root, f"{_D}prop")
    ET.SubElement(prop, f"{_D}getetag")
    ET.SubElement(prop, f"{_C}address-data")
    filt = ET.SubElement(root, f"{_C}filter", {"test": "anyof"})

    for prop_name in ("FN", "EMAIL", "TEL"):
        pf = ET.SubElement(filt, f"{_C}prop-filter", {"name": prop_name})
        tm = ET.SubElement(
            pf,
            f"{_C}text-match",
            {"collation": "i;unicode-casemap", "match-type": "contains"},
        )
        tm.text = q

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


def parse_addressbooks(xml_text: str, principal_url: str) -> list[dict]:
    """Returns [{name, displayname}] for each addressbook, excluding the principal itself."""
    principal_path = urlparse(principal_url).path.rstrip("/")
    root = ET.fromstring(xml_text)
    results = []
    for response in root.findall("d:response", NS):
        href = response.findtext("d:href", "", NS).rstrip("/")
        if href == principal_path:
            continue
        name = href.rsplit("/", 1)[-1]
        if not name:
            continue
        displayname = response.findtext(".//d:displayname", None, NS) or name
        results.append({"name": name, "displayname": displayname})
    return results


logger = logging.getLogger("carddav")


class CardDAVError(Exception):
    """Base class for adapter-level CardDAV errors."""


class NotFoundError(CardDAVError):
    """Upstream returned 404."""


class ConflictError(CardDAVError):
    """Upstream returned 412 (etag mismatch or resource already exists)."""


class UpstreamError(CardDAVError):
    """Upstream unreachable or returned an unexpected error."""


class CardDAVClient:
    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        self._http = http
        self._principal = settings.principal_url

    def _book_url(self, book: str) -> str:
        return f"{self._principal}{book}/"

    def _contact_url(self, book: str, uid: str) -> str:
        return f"{self._book_url(book)}{uid}.vcf"

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            resp = await self._http.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            logger.error("CardDAV request failed: %s %s (%s)", method, url, exc)
            raise UpstreamError("CardDAV server unreachable") from exc
        if resp.status_code in (401, 403):
            logger.error("CardDAV auth rejected (%s) for %s %s", resp.status_code, method, url)
            raise UpstreamError("CardDAV server rejected the adapter's credentials")
        if resp.status_code == 404:
            raise NotFoundError("Contact not found")
        if resp.status_code == 412:
            raise ConflictError("Contact was modified concurrently or already exists")
        if resp.status_code >= 400:
            logger.error("CardDAV error %s for %s %s: %s", resp.status_code, method, url, resp.text[:500])
            raise UpstreamError(f"CardDAV server returned HTTP {resp.status_code}")
        return resp

    async def list_addressbooks(self) -> list[dict]:
        body = (
            '<?xml version="1.0"?>'
            '<d:propfind xmlns:d="DAV:">'
            "<d:prop><d:displayname/></d:prop>"
            "</d:propfind>"
        )
        resp = await self._request(
            "PROPFIND",
            self._principal,
            content=body.encode("utf-8"),
            headers={"Depth": "1", "Content-Type": "application/xml; charset=utf-8"},
        )
        return parse_addressbooks(resp.text, self._principal)

    async def list_all(self, book: str) -> list[tuple[str, str]]:
        root = ET.Element(f"{_C}addressbook-query")
        prop = ET.SubElement(root, f"{_D}prop")
        ET.SubElement(prop, f"{_D}getetag")
        ET.SubElement(prop, f"{_C}address-data")
        ET.SubElement(root, f"{_C}filter", {"test": "anyof"})
        body = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        resp = await self._request(
            "REPORT",
            self._book_url(book),
            content=body,
            headers={"Depth": "1", "Content-Type": "application/xml; charset=utf-8"},
        )
        return parse_multistatus(resp.text)

    async def quick_search(self, book: str, q: str) -> list[tuple[str, str]]:
        body = build_quick_search_xml(q)
        resp = await self._request(
            "REPORT",
            self._book_url(book),
            content=body,
            headers={"Depth": "1", "Content-Type": "application/xml; charset=utf-8"},
        )
        return parse_multistatus(resp.text)

    async def search(
        self,
        book: str,
        email: str | None = None,
        phone: str | None = None,
        name: str | None = None,
        match_condition: str = "allof",
    ) -> list[tuple[str, str]]:
        body = build_search_xml(email, phone, name, match_condition)
        resp = await self._request(
            "REPORT",
            self._book_url(book),
            content=body,
            headers={"Depth": "1", "Content-Type": "application/xml; charset=utf-8"},
        )
        return parse_multistatus(resp.text)

    async def get(self, book: str, uid: str) -> tuple[str, str]:
        resp = await self._request("GET", self._contact_url(book, uid))
        return resp.text, resp.headers.get("ETag", "")

    async def create(self, book: str, uid: str, vcf: str) -> None:
        await self._request(
            "PUT",
            self._contact_url(book, uid),
            content=vcf.encode("utf-8"),
            headers={"Content-Type": "text/vcard; charset=utf-8", "If-None-Match": "*"},
        )

    async def update(self, book: str, uid: str, vcf: str, etag: str) -> None:
        headers = {"Content-Type": "text/vcard; charset=utf-8"}
        if etag:
            headers["If-Match"] = etag
        else:
            logger.warning(
                "Updating %s/%s without ETag — concurrent-write protection not active", book, uid
            )
        await self._request(
            "PUT", self._contact_url(book, uid), content=vcf.encode("utf-8"), headers=headers
        )

    async def delete(self, book: str, uid: str) -> None:
        await self._request("DELETE", self._contact_url(book, uid))
