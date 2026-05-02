"""KOSPI 200 constituent loader and DART corp_code mapping.

Data source: a CSV exported from KRX 정보데이터시스템 (data.krx.co.kr),
re-encoded to UTF-8 and trimmed to the (ticker, name) columns. The current
snapshot lives at data/reference/kospi200.csv. See backlog "잡일 풀" for
auto-refresh plans.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from pydantic import ValidationError

from k_fingraph.errors import KFinGraphError
from k_fingraph.schemas.dart import CorpCodeRecord
from k_fingraph.schemas.kospi200 import Kospi200Constituent, Kospi200Membership

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ("ticker", "name")


class Kospi200LoadError(KFinGraphError):
    """KOSPI 200 reference CSV is missing, malformed, or schema-mismatched."""


def load_kospi200_csv(csv_path: Path) -> list[Kospi200Constituent]:
    """Load KOSPI 200 constituents from a UTF-8 CSV with `ticker,name` columns.

    Empty rows are skipped. Raises Kospi200LoadError on missing file, missing
    required columns, or any row that fails Pydantic validation.
    """
    if not csv_path.exists():
        raise Kospi200LoadError(f"KOSPI 200 CSV not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not set(REQUIRED_COLUMNS).issubset(reader.fieldnames):
            raise Kospi200LoadError(
                f"KOSPI 200 CSV must have columns {REQUIRED_COLUMNS}, got {reader.fieldnames!r}"
            )

        constituents: list[Kospi200Constituent] = []
        for row_num, row in enumerate(reader, start=2):  # row 1 is the header
            ticker = (row.get("ticker") or "").strip()
            name = (row.get("name") or "").strip()
            if not ticker and not name:
                continue
            try:
                constituents.append(Kospi200Constituent(ticker=ticker, name=name))
            except ValidationError as exc:
                raise Kospi200LoadError(f"row {row_num} failed validation: {exc.errors()}") from exc

    logger.info("Loaded %d KOSPI 200 constituents from %s", len(constituents), csv_path)
    return constituents


def map_to_corp_codes(
    constituents: list[Kospi200Constituent],
    corp_codes: list[CorpCodeRecord],
) -> list[Kospi200Membership]:
    """Join KOSPI 200 constituents against DART corp_code records by ticker.

    Only listed corp_code rows (stock_code is not None) participate in the
    join, which prevents false matches against unlisted entities. Constituents
    that fail to match are kept in the output with corp_code=None so the
    caller can audit unmatched tickers.
    """
    listed_by_ticker = {r.stock_code: r for r in corp_codes if r.stock_code is not None}

    memberships: list[Kospi200Membership] = []
    for constituent in constituents:
        record = listed_by_ticker.get(constituent.ticker)
        memberships.append(
            Kospi200Membership(
                ticker=constituent.ticker,
                name=constituent.name,
                corp_code=record.corp_code if record else None,
                corp_name=record.corp_name if record else None,
            )
        )

    matched = sum(1 for m in memberships if m.is_matched)
    logger.info(
        "Mapped %d/%d KOSPI 200 constituents to DART corp_code (%.1f%%)",
        matched,
        len(memberships),
        100.0 * matched / max(len(memberships), 1),
    )
    return memberships
