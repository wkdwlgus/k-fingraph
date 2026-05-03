"""DART periodic report endpoints used for OWNS edge extraction.

Two endpoints are scoped here:

- `otrCprInvstmntSttus.json` — forward direction: "the calling company invests
  in these other companies". Source endpoint is resolved (the caller's
  corp_code); target is text only.
- `hyslrSttus.json` — reverse direction: "these shareholders hold the calling
  company". Target endpoint is resolved; source is text only.

Fetchers do I/O; parsers are pure functions taking the JSON body, so unit
tests exercise the parsing/normalization logic against fixture files without
hitting the network.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, date, datetime
from typing import Any

import httpx
from pydantic import ValidationError

from k_fingraph.config import get_settings
from k_fingraph.errors import DartAPIError, DartParseError
from k_fingraph.schemas.dart import (
    DartMajorShareholderRow,
    DartMajorShareholdersReport,
    DartOtherCorpInvestmentReport,
    DartOtherCorpInvestmentRow,
)

logger = logging.getLogger(__name__)

DART_BASE = "https://opendart.fss.or.kr/api"
HTTP_TIMEOUT = 30.0
DART_OK_STATUS = "000"

# DART responses use three sentinel strings for missing values; see
# docs/data-notes.md "공통 규칙".
_MISSING_SENTINELS = frozenset({"", "-", None})

# Date formats observed across DART endpoints (single payload may mix them).
_DATE_FORMATS = ("%Y%m%d", "%Y-%m-%d", "%Y.%m.%d")

# Strip Korean corporate-form suffixes when normalizing company names.
# Order matters: longer suffixes first so "주식회사" doesn't leave "회사".
_CORP_FORM_SUFFIXES = ("주식회사", "(주)", "㈜", "Co., Ltd.", "Co.,Ltd.", "Ltd.", "Inc.")
_WHITESPACE_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Fetchers (I/O)
# ---------------------------------------------------------------------------


def fetch_other_corp_investments(
    corp_code: str, bsns_year: str, reprt_code: str
) -> DartOtherCorpInvestmentReport:
    """Call otrCprInvstmntSttus.json and parse into a typed report."""
    body = _call_dart("otrCprInvstmntSttus.json", corp_code, bsns_year, reprt_code)
    return parse_other_corp_investments_json(
        body,
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fetched_at=datetime.now(UTC),
    )


def fetch_major_shareholders(
    corp_code: str, bsns_year: str, reprt_code: str
) -> DartMajorShareholdersReport:
    """Call hyslrSttus.json and parse into a typed report."""
    body = _call_dart("hyslrSttus.json", corp_code, bsns_year, reprt_code)
    return parse_major_shareholders_json(
        body,
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fetched_at=datetime.now(UTC),
    )


def _call_dart(endpoint: str, corp_code: str, bsns_year: str, reprt_code: str) -> dict[str, Any]:
    api_key = get_settings().dart_api_key
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
    }
    try:
        response = httpx.get(f"{DART_BASE}/{endpoint}", params=params, timeout=HTTP_TIMEOUT)
    except httpx.HTTPError as exc:
        raise DartAPIError(f"{endpoint} request failed: {exc}") from exc

    if response.status_code != 200:
        raise DartAPIError(
            f"{endpoint} returned HTTP {response.status_code}: {response.text[:200]}"
        )

    try:
        body = response.json()
    except ValueError as exc:
        raise DartAPIError(f"{endpoint} returned non-JSON body: {response.text[:200]}") from exc

    if not isinstance(body, dict):
        raise DartAPIError(f"{endpoint} returned non-dict body: {type(body).__name__}")

    status = body.get("status")
    if status != DART_OK_STATUS:
        # Status "013" = no data, which is a valid empty result for some companies.
        if status == "013":
            logger.info("%s returned status 013 (no data) for corp_code=%s", endpoint, corp_code)
            return body
        raise DartAPIError(
            f"{endpoint} returned error status={status!r} message={body.get('message')!r}"
        )

    return body


# ---------------------------------------------------------------------------
# Parsers (pure)
# ---------------------------------------------------------------------------


def parse_other_corp_investments_json(
    body: dict[str, Any],
    *,
    corp_code: str,
    bsns_year: str,
    reprt_code: str,
    fetched_at: datetime,
) -> DartOtherCorpInvestmentReport:
    """Parse an otrCprInvstmntSttus.json response into a typed report."""
    rows: list[DartOtherCorpInvestmentRow] = []
    for raw in _iter_list(body):
        try:
            rows.append(
                DartOtherCorpInvestmentRow(
                    rcept_no=str(raw.get("rcept_no", "")),
                    holder_corp_code=str(raw.get("corp_code", "")),
                    holder_corp_name=str(raw.get("corp_name", "")),
                    target_name_text=str(raw.get("inv_prm", "")).strip(),
                    stake_pct=parse_dart_pct(raw.get("trmend_blce_qota_rt")),
                    settlement_date=parse_dart_date(raw.get("stlm_dt")),
                )
            )
        except ValidationError as exc:
            raise DartParseError(
                f"otrCprInvstmntSttus row failed schema validation: {exc.errors()}"
            ) from exc

    return DartOtherCorpInvestmentReport(
        holder_corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fetched_at=fetched_at,
        rows=rows,
    )


def parse_major_shareholders_json(
    body: dict[str, Any],
    *,
    corp_code: str,
    bsns_year: str,
    reprt_code: str,
    fetched_at: datetime,
) -> DartMajorShareholdersReport:
    """Parse a hyslrSttus.json response into a typed report."""
    rows: list[DartMajorShareholderRow] = []
    for raw in _iter_list(body):
        try:
            rows.append(
                DartMajorShareholderRow(
                    rcept_no=str(raw.get("rcept_no", "")),
                    held_corp_code=str(raw.get("corp_code", "")),
                    held_corp_name=str(raw.get("corp_name", "")),
                    holder_name_text=str(raw.get("nm", "")).strip(),
                    relate=_clean_optional_text(raw.get("relate")),
                    stake_pct=parse_dart_pct(raw.get("trmend_posesn_stock_qota_rt")),
                    settlement_date=parse_dart_date(raw.get("stlm_dt")),
                )
            )
        except ValidationError as exc:
            raise DartParseError(
                f"hyslrSttus row failed schema validation: {exc.errors()}"
            ) from exc

    return DartMajorShareholdersReport(
        held_corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fetched_at=fetched_at,
        rows=rows,
    )


def _iter_list(body: dict[str, Any]) -> list[dict[str, Any]]:
    raw_list = body.get("list", [])
    if not isinstance(raw_list, list):
        raise DartParseError(f"DART response 'list' is not a list: {type(raw_list).__name__}")
    return [r for r in raw_list if isinstance(r, dict)]


# ---------------------------------------------------------------------------
# Value normalization helpers (shared with other DART parsers)
# ---------------------------------------------------------------------------


def parse_dart_int(value: Any) -> int | None:
    """Parse a DART integer field, handling comma-separated digits, missing
    sentinels (`""`, `"-"`, None), and negative signs ("-62,823" → -62823)."""
    if value is None:
        return None
    text = str(value).strip()
    if text in _MISSING_SENTINELS:
        return None
    cleaned = text.replace(",", "")
    try:
        return int(cleaned)
    except ValueError as exc:
        raise DartParseError(f"cannot parse DART int from {value!r}") from exc


def parse_dart_float(value: Any) -> float | None:
    """Parse a DART float field. Same sentinel handling as parse_dart_int."""
    if value is None:
        return None
    text = str(value).strip()
    if text in _MISSING_SENTINELS:
        return None
    cleaned = text.replace(",", "")
    try:
        return float(cleaned)
    except ValueError as exc:
        raise DartParseError(f"cannot parse DART float from {value!r}") from exc


def parse_dart_pct(value: Any) -> float | None:
    """Parse a percentage value expected to be in [0, 100]. Out-of-range
    values raise DartParseError so bad data is loud, not silent."""
    parsed = parse_dart_float(value)
    if parsed is None:
        return None
    if not 0.0 <= parsed <= 100.0:
        raise DartParseError(f"DART percentage out of range [0, 100]: {parsed}")
    return parsed


def parse_dart_date(value: Any) -> date | None:
    """Parse a DART date field across the three observed formats (YYYYMMDD,
    YYYY-MM-DD, YYYY.MM.DD)."""
    if value is None:
        return None
    text = str(value).strip()
    if text in _MISSING_SENTINELS:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise DartParseError(f"cannot parse DART date from {value!r} (tried {_DATE_FORMATS})")


def normalize_company_name(value: str) -> str:
    """Strip Korean corporate-form suffixes ((주), 주식회사, ㈜) and collapse
    whitespace. Used by Entity Resolution to compare DART company names."""
    text = value.strip()
    for suffix in _CORP_FORM_SUFFIXES:
        # Apply both as suffix and as embedded substring — DART payloads place
        # the form indicator anywhere ("삼성생명보험㈜", "(주)카카오").
        text = text.replace(suffix, "")
    return _WHITESPACE_RE.sub("", text)


def _clean_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text in _MISSING_SENTINELS:
        return None
    return text
