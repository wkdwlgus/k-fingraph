"""Idempotent loaders for v0 nodes and edges.

`upsert_companies` is straightforward — `MERGE` on the Company.ticker key.

`upsert_owns` enforces the ADR 0007 filter: a candidate is loaded only when
both endpoints are resolved to a corp_code AND both corp_codes lie inside the
KOSPI 200 universe passed in. Candidates failing either check are counted in
`OwnsLoadStats` and dropped, never reaching the graph.

OWNS edge identity is the compound key (source_corp_code, target_corp_code,
source_id, as_of) so that multiple disclosures across time produce separate
edges (per docs/schema.md "A→B 다중 가능"), while re-loading the same
disclosure remains idempotent.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass

from neo4j.exceptions import Neo4jError

from k_fingraph.errors import GraphWriteError
from k_fingraph.graph.client import Neo4jClient
from k_fingraph.schemas.graph import Company, OwnsCandidate, OwnsRelation

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OwnsLoadStats:
    """Accounting for one `upsert_owns` invocation.

    The three drop counters are mutually exclusive and together with `loaded`
    sum to `candidates_total`. They are coarser than the (A)/(B-1)/(B-2)
    classification in ADR 0007 — the rich classification is computed by a
    separate diagnostic helper that has access to the corp_code reference table.
    """

    candidates_total: int
    loaded: int
    dropped_endpoint_unresolved: int
    dropped_outside_universe: int


def filter_loadable_candidates(
    candidates: Iterable[OwnsCandidate],
    universe_corp_codes: set[str],
) -> tuple[list[OwnsRelation], OwnsLoadStats]:
    """Apply the ADR 0007 filter and project survivors to `OwnsRelation`.

    Pure function — no Neo4j access — so the filter can be unit tested.
    """
    loaded: list[OwnsRelation] = []
    total = 0
    dropped_unresolved = 0
    dropped_outside = 0

    for candidate in candidates:
        total += 1
        src = candidate.source.corp_code
        tgt = candidate.target.corp_code
        if src is None or tgt is None:
            dropped_unresolved += 1
            continue
        if src not in universe_corp_codes or tgt not in universe_corp_codes:
            dropped_outside += 1
            continue
        if candidate.stake_pct is None or candidate.as_of is None:
            # Schema requires both for OwnsRelation; treat missing as
            # "endpoint-resolved but data-incomplete" → conservative drop.
            dropped_unresolved += 1
            continue
        loaded.append(
            OwnsRelation(
                source_corp_code=src,
                target_corp_code=tgt,
                stake_pct=candidate.stake_pct,
                relation_type=candidate.relation_type,
                as_of=candidate.as_of,
                source_id=candidate.source_id,
                extracted_at=candidate.extracted_at,
            )
        )

    stats = OwnsLoadStats(
        candidates_total=total,
        loaded=len(loaded),
        dropped_endpoint_unresolved=dropped_unresolved,
        dropped_outside_universe=dropped_outside,
    )
    return loaded, stats


_UPSERT_COMPANY_CYPHER = """
UNWIND $rows AS row
MERGE (c:Company {ticker: row.ticker})
ON CREATE SET c.created_at = datetime(row.created_at)
SET c.corp_code = row.corp_code,
    c.name_kr = row.name_kr,
    c.name_normalized = row.name_normalized,
    c.name_en = row.name_en,
    c.market = row.market,
    c.industry_krx = row.industry_krx,
    c.updated_at = datetime(row.updated_at)
"""

_UPSERT_OWNS_CYPHER = """
UNWIND $rows AS row
MATCH (s:Company {corp_code: row.source_corp_code})
MATCH (t:Company {corp_code: row.target_corp_code})
MERGE (s)-[r:OWNS {source_id: row.source_id, as_of: date(row.as_of)}]->(t)
SET r.stake_pct = row.stake_pct,
    r.relation_type = row.relation_type,
    r.extracted_at = datetime(row.extracted_at)
"""


def upsert_companies(
    client: Neo4jClient,
    companies: Iterable[Company],
) -> int:
    """MERGE Company nodes by ticker. Returns the number of rows submitted."""
    rows = [
        {
            "ticker": c.ticker,
            "corp_code": c.corp_code,
            "name_kr": c.name_kr,
            "name_normalized": c.name_normalized,
            "name_en": c.name_en,
            "market": c.market,
            "industry_krx": c.industry_krx,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        }
        for c in companies
    ]
    if not rows:
        return 0
    try:
        with client.session() as session:
            session.run(_UPSERT_COMPANY_CYPHER, rows=rows).consume()
    except Neo4jError as exc:
        raise GraphWriteError(f"Company upsert failed: {exc}") from exc
    logger.info("Upserted %d Company rows", len(rows))
    return len(rows)


def upsert_owns(
    client: Neo4jClient,
    candidates: Iterable[OwnsCandidate],
    universe_corp_codes: set[str],
) -> OwnsLoadStats:
    """Filter per ADR 0007, then MERGE surviving OWNS edges.

    Both endpoint Company nodes must already exist (typically via a prior
    `upsert_companies` call). The MATCH-then-MERGE pattern keeps endpoint
    creation out of this function so an unmatched corp_code surfaces as a
    silent skip in Cypher rather than a stub Company node — which would
    violate the ADR 0007 guarantee that v0 nodes only come from the curated
    universe.
    """
    relations, stats = filter_loadable_candidates(candidates, universe_corp_codes)
    if relations:
        rows = [
            {
                "source_corp_code": r.source_corp_code,
                "target_corp_code": r.target_corp_code,
                "stake_pct": r.stake_pct,
                "relation_type": r.relation_type.value,
                "as_of": r.as_of.isoformat(),
                "source_id": r.source_id,
                "extracted_at": r.extracted_at.isoformat(),
            }
            for r in relations
        ]
        try:
            with client.session() as session:
                session.run(_UPSERT_OWNS_CYPHER, rows=rows).consume()
        except Neo4jError as exc:
            raise GraphWriteError(f"OWNS upsert failed: {exc}") from exc

    logger.info(
        "OWNS load — total=%d loaded=%d dropped_endpoint_unresolved=%d dropped_outside_universe=%d",
        stats.candidates_total,
        stats.loaded,
        stats.dropped_endpoint_unresolved,
        stats.dropped_outside_universe,
    )
    return stats
