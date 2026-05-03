"""KOSPI + KOSDAQ universe loader and DART corp_code mapping.

Generalizes `kospi200.py` to the v0.5 universe. The CSV format is identical
to v0's `data/reference/kospi200.csv` (columns `ticker,name`, UTF-8); this
module just stamps the source market on each row and concatenates the two
markets into one constituent list.

Raw EUC-KR KRX exports are kept under `data/raw/krx/` and converted to the
UTF-8 reference CSVs upstream — this module never touches the raw side.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from pydantic import ValidationError

from k_fingraph.errors import KFinGraphError
from k_fingraph.schemas.dart import CorpCodeRecord
from k_fingraph.schemas.universe import (
    Market,
    UniverseConstituent,
    UniverseMembership,
)

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ("ticker", "name")


class ExtendedUniverseLoadError(KFinGraphError):
    """Extended universe CSV is missing, malformed, or schema-mismatched."""


def load_market_csv(csv_path: Path, market: Market) -> list[UniverseConstituent]:
    """Load one market's constituents from a UTF-8 CSV with `ticker,name` columns.

    Empty rows are skipped. Raises ExtendedUniverseLoadError on missing file,
    missing required columns, or any row that fails Pydantic validation.
    """
    if not csv_path.exists():
        raise ExtendedUniverseLoadError(f"{market} universe CSV not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not set(REQUIRED_COLUMNS).issubset(reader.fieldnames):
            raise ExtendedUniverseLoadError(
                f"{market} universe CSV must have columns {REQUIRED_COLUMNS}, "
                f"got {reader.fieldnames!r}"
            )

        constituents: list[UniverseConstituent] = []
        for row_num, row in enumerate(reader, start=2):
            ticker = (row.get("ticker") or "").strip()
            name = (row.get("name") or "").strip()
            if not ticker and not name:
                continue
            try:
                constituents.append(UniverseConstituent(ticker=ticker, name=name, market=market))
            except ValidationError as exc:
                raise ExtendedUniverseLoadError(
                    f"{market} row {row_num} failed validation: {exc.errors()}"
                ) from exc

    logger.info("Loaded %d %s constituents from %s", len(constituents), market, csv_path)
    return constituents


def load_extended_universe(
    kospi_csv: Path,
    kosdaq_csv: Path,
) -> list[UniverseConstituent]:
    """Load both markets and concatenate. Raises if any ticker appears in both.

    Korean exchange tickers are partitioned by market in practice; a collision
    would mean a data-source error rather than an ambiguity to resolve.
    """
    kospi = load_market_csv(kospi_csv, "KOSPI")
    kosdaq = load_market_csv(kosdaq_csv, "KOSDAQ")

    kospi_tickers = {c.ticker for c in kospi}
    collisions = sorted({c.ticker for c in kosdaq} & kospi_tickers)
    if collisions:
        raise ExtendedUniverseLoadError(
            f"ticker collision across KOSPI and KOSDAQ: {collisions[:5]} ({len(collisions)} total)"
        )

    return [*kospi, *kosdaq]


def map_universe_to_corp_codes(
    constituents: list[UniverseConstituent],
    corp_codes: list[CorpCodeRecord],
) -> list[UniverseMembership]:
    """Join universe constituents against DART corp_code records by ticker.

    Same join shape as `sources.kospi200.map_to_corp_codes` — only listed
    corp_codes participate (per ADR 0008's exclusion of unlisted entities)
    and `market` is carried through to the membership row.
    """
    listed_by_ticker = {r.stock_code: r for r in corp_codes if r.stock_code is not None}

    memberships: list[UniverseMembership] = []
    for constituent in constituents:
        record = listed_by_ticker.get(constituent.ticker)
        memberships.append(
            UniverseMembership(
                ticker=constituent.ticker,
                name=constituent.name,
                market=constituent.market,
                corp_code=record.corp_code if record else None,
                corp_name=record.corp_name if record else None,
            )
        )

    matched = sum(1 for m in memberships if m.is_matched)
    logger.info(
        "Mapped %d/%d extended universe constituents to DART corp_code (%.1f%%)",
        matched,
        len(memberships),
        100.0 * matched / max(len(memberships), 1),
    )
    return memberships
