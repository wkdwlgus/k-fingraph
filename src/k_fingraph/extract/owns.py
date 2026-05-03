"""OWNS edge extraction from parsed DART periodic reports.

Both directions produce `OwnsCandidate` objects in which one endpoint is
resolved (corp_code) and the other carries text only — Entity Resolution
runs in the v2 sprint. ADR 0007 spells out which candidates survive to the
graph at v0 (KOSPI 200 ↔ KOSPI 200 only).

Relation type thresholds are fixed by ADR 0006.
"""

from __future__ import annotations

from k_fingraph.schemas.dart import (
    DartMajorShareholdersReport,
    DartOtherCorpInvestmentReport,
)
from k_fingraph.schemas.graph import OwnsCandidate, OwnsEndpoint, RelationType
from k_fingraph.sources.dart_reports import normalize_company_name

# ADR 0006 thresholds (K-IFRS 1110 / 1028 estimate boundaries).
SUBSIDIARY_MIN_PCT = 50.0
AFFILIATE_MIN_PCT = 20.0


def extract_owns_from_other_corp_investments(
    report: DartOtherCorpInvestmentReport,
) -> list[OwnsCandidate]:
    """Forward extraction: holder is resolved (caller's corp_code), target is
    text only (DART's `inv_prm`)."""
    candidates: list[OwnsCandidate] = []
    for row in report.rows:
        candidates.append(
            OwnsCandidate(
                source=OwnsEndpoint(corp_code=row.holder_corp_code),
                target=OwnsEndpoint(
                    name_text=row.target_name_text,
                    name_normalized=normalize_company_name(row.target_name_text),
                ),
                stake_pct=row.stake_pct,
                relation_type=classify_relation(row.stake_pct),
                as_of=row.settlement_date,
                source_id=row.rcept_no,
                extracted_at=report.fetched_at,
            )
        )
    return candidates


def extract_owns_from_major_shareholders(
    report: DartMajorShareholdersReport,
) -> list[OwnsCandidate]:
    """Reverse extraction: held company is resolved (caller's corp_code),
    holder is text only (DART's `nm`).

    Rows where the holder owns no stake (`stake_pct` is None or 0.0) are
    dropped — these are special-related-party listings (친인척 등) that appear
    in the same response but represent no direct ownership edge.
    """
    candidates: list[OwnsCandidate] = []
    for row in report.rows:
        if not row.stake_pct:
            continue
        candidates.append(
            OwnsCandidate(
                source=OwnsEndpoint(
                    name_text=row.holder_name_text,
                    name_normalized=normalize_company_name(row.holder_name_text),
                ),
                target=OwnsEndpoint(corp_code=row.held_corp_code),
                stake_pct=row.stake_pct,
                relation_type=classify_relation(row.stake_pct),
                as_of=row.settlement_date,
                source_id=row.rcept_no,
                extracted_at=report.fetched_at,
            )
        )
    return candidates


def classify_relation(stake_pct: float | None) -> RelationType:
    """Map a stake percentage to a RelationType per ADR 0006."""
    if stake_pct is None:
        return RelationType.OTHER
    if stake_pct >= SUBSIDIARY_MIN_PCT:
        return RelationType.SUBSIDIARY
    if stake_pct >= AFFILIATE_MIN_PCT:
        return RelationType.AFFILIATE
    return RelationType.OTHER
