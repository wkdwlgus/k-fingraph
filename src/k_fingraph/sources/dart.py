"""DART OpenAPI client. Currently scoped to the corpCode endpoint."""

from __future__ import annotations

import io
import logging
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import httpx
from pydantic import ValidationError

from k_fingraph.config import get_settings
from k_fingraph.errors import DartAPIError, DartParseError
from k_fingraph.schemas.dart import CorpCodeRecord

logger = logging.getLogger(__name__)

CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"
ZIP_MAGIC = b"PK"
HTTP_TIMEOUT = 30.0


def download_corp_code_zip(api_key: str, dest_dir: Path) -> Path:
    """Fetch corpCode.xml.zip from DART, extract into dest_dir, and return the
    path to the extracted XML file.

    Raises DartAPIError on HTTP failure or non-ZIP responses (e.g. when DART
    returns an HTML error page because the API key is invalid or the daily
    quota is exhausted).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        response = httpx.get(
            CORP_CODE_URL,
            params={"crtfc_key": api_key},
            timeout=HTTP_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise DartAPIError(f"corpCode request failed: {exc}") from exc

    if response.status_code != 200:
        raise DartAPIError(f"corpCode returned HTTP {response.status_code}: {response.text[:200]}")

    body = response.content
    if not body.startswith(ZIP_MAGIC):
        # DART responds with HTML/XML (not ZIP) when the key is rejected or quota is hit.
        snippet = body[:200].decode("utf-8", errors="replace")
        raise DartAPIError(f"corpCode response is not a ZIP archive: {snippet!r}")

    try:
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            archive.extractall(dest_dir)
            xml_names = [n for n in archive.namelist() if n.lower().endswith(".xml")]
    except zipfile.BadZipFile as exc:
        raise DartAPIError(f"corpCode response is a corrupt ZIP: {exc}") from exc

    if not xml_names:
        raise DartAPIError(f"corpCode ZIP contained no XML file (members={archive.namelist()!r})")

    xml_path = dest_dir / xml_names[0]
    logger.info("Downloaded DART corpCode XML to %s (%d bytes)", xml_path, xml_path.stat().st_size)
    return xml_path


def parse_corp_code_xml(xml_path: Path) -> list[CorpCodeRecord]:
    """Parse DART's corpCode XML into a list of CorpCodeRecord.

    Empty `stock_code` (typical for unlisted companies — DART emits a single
    space) is normalized to None.
    """
    try:
        tree = ElementTree.parse(xml_path)
    except ElementTree.ParseError as exc:
        raise DartParseError(f"corpCode XML is malformed: {exc}") from exc

    records: list[CorpCodeRecord] = []
    for entry in tree.getroot().findall("list"):
        try:
            records.append(
                CorpCodeRecord(
                    corp_code=_text(entry, "corp_code") or "",
                    corp_name=_text(entry, "corp_name") or "",
                    corp_eng_name=_text(entry, "corp_eng_name"),
                    stock_code=_text(entry, "stock_code"),
                    modify_date=_text(entry, "modify_date") or "",
                )
            )
        except ValidationError as exc:
            raise DartParseError(
                f"corpCode entry failed schema validation: {exc.errors()}"
            ) from exc

    logger.info("Parsed %d corpCode records from %s", len(records), xml_path)
    return records


def fetch_corp_codes(dest_dir: Path | None = None) -> list[CorpCodeRecord]:
    """Download + parse corpCode in one call. When dest_dir is omitted, a
    temporary directory is used and cleaned up automatically.

    The DART API key is read from Settings (.env).
    """
    api_key = get_settings().dart_api_key

    if dest_dir is not None:
        xml_path = download_corp_code_zip(api_key, dest_dir)
        return parse_corp_code_xml(xml_path)

    with tempfile.TemporaryDirectory(prefix="dart_corp_code_") as tmp:
        xml_path = download_corp_code_zip(api_key, Path(tmp))
        return parse_corp_code_xml(xml_path)


def _text(element: ElementTree.Element, tag: str) -> str | None:
    """Return stripped element text, treating empty/whitespace-only as None."""
    child = element.find(tag)
    if child is None or child.text is None:
        return None
    stripped = child.text.strip()
    return stripped or None
