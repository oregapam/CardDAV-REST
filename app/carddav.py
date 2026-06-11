import logging
import xml.etree.ElementTree as ET

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
        self._base = settings.addressbook_url

    def _url(self, uid: str) -> str:
        return f"{self._base}{uid}.vcf"

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

    async def search(
        self,
        email: str | None = None,
        phone: str | None = None,
        name: str | None = None,
        match_condition: str = "allof",
    ) -> list[tuple[str, str]]:
        body = build_search_xml(email, phone, name, match_condition)
        resp = await self._request(
            "REPORT",
            self._base,
            content=body,
            headers={"Depth": "1", "Content-Type": "application/xml; charset=utf-8"},
        )
        return parse_multistatus(resp.text)

    async def get(self, uid: str) -> tuple[str, str]:
        resp = await self._request("GET", self._url(uid))
        return resp.text, resp.headers.get("ETag", "")

    async def create(self, uid: str, vcf: str) -> None:
        await self._request(
            "PUT",
            self._url(uid),
            content=vcf.encode("utf-8"),
            headers={"Content-Type": "text/vcard; charset=utf-8", "If-None-Match": "*"},
        )

    async def update(self, uid: str, vcf: str, etag: str) -> None:
        headers = {"Content-Type": "text/vcard; charset=utf-8"}
        if etag:
            headers["If-Match"] = etag
        await self._request("PUT", self._url(uid), content=vcf.encode("utf-8"), headers=headers)

    async def delete(self, uid: str) -> None:
        await self._request("DELETE", self._url(uid))
