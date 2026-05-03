"""v0 Entity Resolution for OWNS endpoints.

DART responses identify only the calling company by `corp_code` — the other
endpoint arrives as text only. This module fills in `corp_code` on the
text-only side by exact normalized-name lookup against the DART corp_code
reference table.

Per `docs/architecture.md` "Ingestion 4. Entity Resolution — v0: 단순 키 매칭",
v0 ER is exact match only. Embedding-based fuzzy matching is the v2 sprint's
responsibility.

Resolution priority handles ambiguity (multiple corp_codes share a normalized
name; ~117k corp_codes vs ~2k listed):

1. **Universe match first** — if the name resolves to a KOSPI 200 corp_code,
   use it. This is the v0 happy path: a candidate that resolves into the
   universe will load as an OWNS edge.
2. **Listed match second** — if no universe hit, but the name resolves to a
   listed company (`stock_code is not None`), use that corp_code. The loader
   then drops it as outside-universe (still classified A by diagnostics, so
   v0.5's universe expansion will recover it).
3. **No match** — leave `corp_code` as None. Loader drops as endpoint-
   unresolved; classifier categorizes as B-1 / B-2.

Unlisted corp_codes (`stock_code is None`) are deliberately excluded from
the lookup — resolving an OWNS endpoint to an unlisted corp_code would put
it on the loader's "outside universe" path, hiding the fact that v0's schema
has no `:UnlistedCompany` node. Better to leave it unresolved and let the
diagnostic classifier surface it as B-1.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from k_fingraph.schemas.dart import CorpCodeRecord
from k_fingraph.schemas.graph import OwnsCandidate, OwnsEndpoint
from k_fingraph.sources.dart_reports import normalize_company_name

logger = logging.getLogger(__name__)


def build_resolution_index(
    corp_codes: Iterable[CorpCodeRecord],
    universe_corp_codes: set[str],
) -> dict[str, str]:
    """Build a `normalized_name -> corp_code` lookup with universe priority.

    Iteration order:

    1. First pass — universe records. Inserts win.
    2. Second pass — non-universe LISTED records (have a stock_code). Only
       fills in entries the universe pass didn't claim.

    Unlisted records never enter the index — see module docstring.
    """
    index: dict[str, str] = {}
    universe_records: list[CorpCodeRecord] = []
    listed_outside: list[CorpCodeRecord] = []

    for record in corp_codes:
        if record.corp_code in universe_corp_codes:
            universe_records.append(record)
        elif record.stock_code is not None:
            listed_outside.append(record)

    for record in universe_records:
        normalized = normalize_company_name(record.corp_name)
        # `setdefault` so the first universe record per name wins (KOSPI 200
        # internal duplicates are extremely rare; this just makes behavior
        # deterministic if they occur).
        index.setdefault(normalized, record.corp_code)

    for record in listed_outside:
        normalized = normalize_company_name(record.corp_name)
        index.setdefault(normalized, record.corp_code)

    return index


def resolve_endpoints(
    candidates: Iterable[OwnsCandidate],
    name_to_corp_code: dict[str, str],
) -> list[OwnsCandidate]:
    """Fill in `corp_code` on text-only endpoints when the normalized name
    is found in the resolution index. Already-resolved endpoints pass through
    untouched.

    Returns a new list — input candidates are not mutated.
    """
    out: list[OwnsCandidate] = []
    resolved = 0
    for candidate in candidates:
        new_source = _resolve_endpoint(candidate.source, name_to_corp_code)
        new_target = _resolve_endpoint(candidate.target, name_to_corp_code)
        if new_source is candidate.source and new_target is candidate.target:
            out.append(candidate)
            continue
        resolved += 1
        out.append(candidate.model_copy(update={"source": new_source, "target": new_target}))
    logger.info("Resolved corp_code on %d / %d candidates", resolved, len(out))
    return out


def _resolve_endpoint(
    endpoint: OwnsEndpoint,
    name_to_corp_code: dict[str, str],
) -> OwnsEndpoint:
    if endpoint.corp_code is not None:
        return endpoint
    normalized = endpoint.name_normalized
    if normalized is None and endpoint.name_text is not None:
        normalized = normalize_company_name(endpoint.name_text)
    if normalized is None:
        return endpoint
    corp_code = name_to_corp_code.get(normalized)
    if corp_code is None:
        return endpoint
    return endpoint.model_copy(update={"corp_code": corp_code, "name_normalized": normalized})
