"""v0 ingestion entrypoint — KOSPI 200 + DART OWNS into a Neo4j instance.

Run:
    uv run python -m k_fingraph.scripts.load_v0

Outputs a JSON report on stdout summarizing graph counts, the loader's
OwnsLoadStats, and the (A)/(B-1)/(B-2) classification of dropped candidates
per ADR 0007.

Network footprint: 1 corpCode download (cached at data/raw/dart/corp_codes/)
+ 200 forward + 200 reverse DART calls. Spaced by SLEEP_BETWEEN_CALLS to stay
under DART's per-IP burst limit. Single-call failures are logged and the run
continues.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from k_fingraph.errors import DartAPIError, DartParseError
from k_fingraph.extract.owns import (
    extract_owns_from_major_shareholders,
    extract_owns_from_other_corp_investments,
)
from k_fingraph.extract.owns_diagnostics import DropClassification, summarize_drops
from k_fingraph.graph.client import Neo4jClient
from k_fingraph.graph.load import OwnsLoadStats, upsert_companies, upsert_owns
from k_fingraph.graph.migrations import apply_schema
from k_fingraph.resolve.owns import build_resolution_index, resolve_endpoints
from k_fingraph.schemas.dart import CorpCodeRecord
from k_fingraph.schemas.graph import Company, OwnsCandidate
from k_fingraph.sources.dart import download_corp_code_zip, parse_corp_code_xml
from k_fingraph.sources.dart_reports import (
    fetch_major_shareholders,
    fetch_other_corp_investments,
    normalize_company_name,
)
from k_fingraph.sources.kospi200 import load_kospi200_csv, map_to_corp_codes

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_KOSPI200_CSV = PROJECT_ROOT / "data" / "reference" / "kospi200.csv"
DEFAULT_CORP_CODE_DIR = PROJECT_ROOT / "data" / "raw" / "dart" / "corp_codes"
DEFAULT_CORP_CODE_XML = DEFAULT_CORP_CODE_DIR / "CORPCODE.xml"

# DART OpenAPI tolerates ~200 calls/min per IP. 0.5s = 120 calls/min, leaving
# headroom. 200 companies × 2 endpoints × 0.5s ≈ 3.5 min total.
SLEEP_BETWEEN_CALLS = 0.5

# Sufficient for the v0 disclosure year. Annual report (사업보고서).
DEFAULT_BSNS_YEAR = "2024"
REPRT_CODE_ANNUAL = "11011"


def _load_or_fetch_corp_codes(
    cache_xml: Path,
    cache_dir: Path,
    api_key_supplier: Callable[[], str],
) -> list[CorpCodeRecord]:
    if cache_xml.exists():
        logger.info("Reusing cached corpCode XML at %s", cache_xml)
        return parse_corp_code_xml(cache_xml)

    logger.info("corpCode cache miss — downloading to %s", cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    xml_path = download_corp_code_zip(api_key_supplier(), cache_dir)
    return parse_corp_code_xml(xml_path)


def _build_companies(
    matched: list[tuple[str, str, str]],
    now: datetime,
) -> list[Company]:
    """matched = list of (ticker, corp_code, name_kr)."""
    companies: list[Company] = []
    for ticker, corp_code, name in matched:
        companies.append(
            Company(
                ticker=ticker,
                corp_code=corp_code,
                name_kr=name,
                name_normalized=normalize_company_name(name),
                name_en=None,
                market="KOSPI",
                industry_krx=None,
                created_at=now,
                updated_at=now,
            )
        )
    return companies


def _fetch_all_candidates(
    matched: list[tuple[str, str, str]],
    bsns_year: str,
) -> tuple[list[OwnsCandidate], dict[int, str | None]]:
    """Hit forward + reverse for every matched corp_code. Returns flat
    candidate list plus an id(candidate) → relate map for reverse rows.
    """
    candidates: list[OwnsCandidate] = []
    relate_lookup: dict[int, str | None] = {}
    n = len(matched)

    for i, (_ticker, corp_code, name) in enumerate(matched, start=1):
        try:
            forward = fetch_other_corp_investments(corp_code, bsns_year, REPRT_CODE_ANNUAL)
            forward_cands = extract_owns_from_other_corp_investments(forward)
            candidates.extend(forward_cands)
            logger.info(
                "[%d/%d] forward %s (%s): %d rows", i, n, name, corp_code, len(forward.rows)
            )
        except (DartAPIError, DartParseError) as exc:
            # Per-company isolation: a single bad row (e.g. percentage field
            # mis-populated with a share count) shouldn't kill the entire run.
            logger.warning("forward fetch/parse failed for %s (%s): %s", name, corp_code, exc)
        time.sleep(SLEEP_BETWEEN_CALLS)

        try:
            reverse = fetch_major_shareholders(corp_code, bsns_year, REPRT_CODE_ANNUAL)
            reverse_cands = extract_owns_from_major_shareholders(reverse)
            # Build relate lookup BEFORE extending the master list so id() is
            # stable (extend doesn't move objects, but this keeps the order
            # explicit). Reverse extractor drops zero-stake rows internally;
            # the row order vs. candidate order matches because both iterate
            # the same `report.rows` and skip on the same condition.
            non_zero_rows = [r for r in reverse.rows if r.stake_pct]
            for cand, row in zip(reverse_cands, non_zero_rows, strict=True):
                relate_lookup[id(cand)] = row.relate
            candidates.extend(reverse_cands)
            logger.info(
                "[%d/%d] reverse %s (%s): %d rows", i, n, name, corp_code, len(reverse.rows)
            )
        except (DartAPIError, DartParseError) as exc:
            logger.warning("reverse fetch/parse failed for %s (%s): %s", name, corp_code, exc)
        time.sleep(SLEEP_BETWEEN_CALLS)

    return candidates, relate_lookup


def _query_graph_counts(client: Neo4jClient) -> dict[str, int]:
    with client.session() as session:
        company = session.run("MATCH (c:Company) RETURN count(c) AS n").single()
        owns = session.run("MATCH ()-[r:OWNS]->() RETURN count(r) AS n").single()
    assert company is not None and owns is not None
    return {"companies": int(company["n"]), "owns_edges": int(owns["n"])}


def _build_report(
    *,
    matched_count: int,
    unmatched_count: int,
    companies_loaded: int,
    candidates_total: int,
    stats: OwnsLoadStats,
    drops: DropClassification,
    graph_counts: dict[str, int],
    started_at: datetime,
    finished_at: datetime,
) -> dict[str, object]:
    return {
        "kospi200": {
            "matched_to_corp_code": matched_count,
            "unmatched": unmatched_count,
        },
        "candidates_extracted": candidates_total,
        "owns_load_stats": {
            "candidates_total": stats.candidates_total,
            "loaded": stats.loaded,
            "dropped_endpoint_unresolved": stats.dropped_endpoint_unresolved,
            "dropped_outside_universe": stats.dropped_outside_universe,
        },
        "drop_classification": {
            "counts": dict(drops.counts),
            "samples": {k: list(v) for k, v in drops.samples.items()},
        },
        "graph_counts": graph_counts,
        "companies_upserted": companies_loaded,
        "duration_seconds": (finished_at - started_at).total_seconds(),
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="v0 KOSPI 200 + OWNS ingestion")
    parser.add_argument(
        "--kospi200-csv",
        type=Path,
        default=DEFAULT_KOSPI200_CSV,
        help="Path to KOSPI 200 reference CSV",
    )
    parser.add_argument(
        "--corp-code-cache",
        type=Path,
        default=DEFAULT_CORP_CODE_XML,
        help="Path to cached corpCode XML (re-downloaded if missing)",
    )
    parser.add_argument(
        "--bsns-year",
        default=DEFAULT_BSNS_YEAR,
        help="DART business year (4 digits)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N matched companies (smoke testing)",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=None,
        help="Optional path to write the JSON report (also printed to stdout)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    started_at = datetime.now(UTC)

    constituents = load_kospi200_csv(args.kospi200_csv)

    from k_fingraph.config import get_settings  # local to keep import cost out of --help

    settings = get_settings()

    corp_code_cache_dir = args.corp_code_cache.parent
    corp_codes = _load_or_fetch_corp_codes(
        args.corp_code_cache, corp_code_cache_dir, lambda: settings.dart_api_key
    )

    memberships = map_to_corp_codes(constituents, corp_codes)
    matched = [(m.ticker, m.corp_code, m.name) for m in memberships if m.corp_code is not None]
    if args.limit is not None:
        matched = matched[: args.limit]
    unmatched_count = sum(1 for m in memberships if m.corp_code is None)
    universe = {corp_code for _, corp_code, _ in matched}

    now = datetime.now(UTC)
    companies = _build_companies(matched, now)

    client = Neo4jClient.from_settings()
    try:
        if not client.ping():
            logger.error("Neo4j ping returned falsy — aborting")
            return 1
        apply_schema(client)
        upserted = upsert_companies(client, companies)
        candidates, relate_lookup = _fetch_all_candidates(matched, args.bsns_year)

        # v0 ER: fill in corp_code on text-only endpoints by exact normalized
        # name match, with universe priority. Without this step every forward
        # candidate stays target-unresolved and every reverse stays source-
        # unresolved → the ADR 0007 filter drops everything.
        name_to_corp_code = build_resolution_index(corp_codes, universe)
        resolved_candidates = resolve_endpoints(candidates, name_to_corp_code)
        # resolve_endpoints returns new objects when it changed something; the
        # relate lookup was keyed on pre-resolve id(), so rebuild by position.
        relate_lookup = {
            id(new): relate_lookup.get(id(old))
            for old, new in zip(candidates, resolved_candidates, strict=True)
        }

        stats = upsert_owns(client, resolved_candidates, universe)

        # Re-classify the dropped candidates for the (A)/(B-1)/(B-2) report.
        # The loader's filter and this classifier follow the same drop rule;
        # we just enrich the breakdown.
        dropped = [
            c
            for c in resolved_candidates
            if c.source.corp_code is None
            or c.target.corp_code is None
            or c.source.corp_code not in universe
            or c.target.corp_code not in universe
        ]
        drops = summarize_drops(dropped, corp_codes, universe, relate_by_candidate=relate_lookup)

        graph_counts = _query_graph_counts(client)
    finally:
        client.close()

    finished_at = datetime.now(UTC)
    report = _build_report(
        matched_count=len(matched),
        unmatched_count=unmatched_count,
        companies_loaded=upserted,
        candidates_total=len(resolved_candidates),
        stats=stats,
        drops=drops,
        graph_counts=graph_counts,
        started_at=started_at,
        finished_at=finished_at,
    )

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.report_path is not None:
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
