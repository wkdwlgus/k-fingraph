"""Diagnostic classifier for OwnsCandidate values that ADR 0007 drops.

The loader (`graph/load.upsert_owns`) drops anything whose endpoints are not
both inside the KOSPI 200 universe. This module re-classifies those drops
into the (A) / (B-1) / (B-2) categories defined in the ADR 0007 follow-up
section, so the v0.5 universe-expansion sprint has an honest baseline.

Categories (verbatim from ADR 0007):

- **A** — Universe limit. The unresolved endpoint matches a corp_code in the
  DART corpCode table AND that corp_code has a `stock_code` (i.e. it's a
  listed company), but is not in the v0 KOSPI 200 universe. Will be recovered
  by v0.5's universe expansion to all KOSPI + KOSDAQ.
- **B-1** — Schema limit, recoverable. The unresolved endpoint matches a
  corp_code with no `stock_code` (an unlisted company DART knows about), OR
  reverse-direction `relate` is "최대주주 본인" / "임원" / "특수관계인"
  (signaling an executive / related party). Recoverable by future schema
  expansions (Person / unlisted-Company nodes).
- **B-2** — True data limit. None of the above signals fit. Free text only —
  foreign legal entity, anonymous SPC, fund, etc. Permanently un-loadable
  in this system.

Forward extraction (`otrCprInvstmntSttus`) carries no `relate` field, so for
forward-direction candidates B-1 detection is limited to the unlisted
corp_code signal. Reverse-direction candidates additionally consult `relate`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from k_fingraph.schemas.dart import CorpCodeRecord
from k_fingraph.schemas.graph import OwnsCandidate
from k_fingraph.sources.dart_reports import normalize_company_name

DropCategory = Literal["A", "B1", "B2"]

# Reverse-direction `relate` values that mark the holder as a person rather
# than a company. Matched by substring (DART writes both "최대주주 본인" and
# variants like "본인", "임원", "친인척" depending on the report).
_PERSON_RELATE_HINTS: tuple[str, ...] = (
    "본인",
    "임원",
    "특수관계인",
    "친인척",
)

# Cap the number of raw-text samples kept per category. Enough to spot
# patterns when reading progress.md, small enough to stay readable.
SAMPLE_CAP = 5


@dataclass(frozen=True)
class DropClassification:
    """Aggregate of `classify_unloaded_candidate` over many candidates.

    `counts` is exhaustive — every dropped candidate lands in exactly one
    bucket. `samples` keeps up to `SAMPLE_CAP` raw text strings per bucket
    so the v0.5 sprint can eyeball what the categories actually contain.
    """

    counts: dict[DropCategory, int]
    samples: dict[DropCategory, list[str]]

    @property
    def total(self) -> int:
        return sum(self.counts.values())


def classify_unloaded_candidate(
    candidate: OwnsCandidate,
    corp_codes_by_normalized_name: dict[str, CorpCodeRecord],
    universe_corp_codes: set[str],
    *,
    relate: str | None = None,
) -> DropCategory:
    """Decide which (A)/(B-1)/(B-2) bucket a dropped candidate falls into.

    The caller is responsible for only passing in candidates that actually
    failed the loader's filter — this function does not re-check whether the
    candidate would have loaded.

    `relate` is the reverse-direction shareholder relation label, when
    available. None for forward-direction candidates and for reverse-direction
    candidates whose `relate` field was empty.
    """
    src_corp = candidate.source.corp_code
    tgt_corp = candidate.target.corp_code

    # If both endpoints are resolved corp_codes but the loader still dropped
    # the candidate, it must be the universe filter — at least one corp_code
    # is outside KOSPI 200. That outside-universe corp_code is by construction
    # a listed company (DART resolved it with a stock_code), so this is (A).
    if src_corp is not None and tgt_corp is not None:
        if src_corp not in universe_corp_codes or tgt_corp not in universe_corp_codes:
            return "A"
        # Both in universe but loader still dropped (e.g. missing stake_pct or
        # as_of). Treat as B-2 — data incompleteness on a known company is
        # not something v0.5 universe expansion fixes.
        return "B2"

    # One endpoint is text only. Apply the unresolved-side signals.
    text_endpoint = candidate.source if src_corp is None else candidate.target
    text_value = text_endpoint.name_text or ""

    # Reverse-direction person hint takes precedence over corp_code lookup —
    # an executive who happens to share a name with a registered company
    # should still be classified as B-1 (person), not A.
    if relate is not None and any(hint in relate for hint in _PERSON_RELATE_HINTS):
        return "B1"

    # corp_code table lookup by normalized name.
    normalized = text_endpoint.name_normalized or normalize_company_name(text_value)
    record = corp_codes_by_normalized_name.get(normalized)
    if record is None:
        return "B2"

    if record.stock_code is None:
        # Listed in DART but unlisted on the exchange — schema-extension
        # territory, not universe expansion.
        return "B1"

    # Listed company with a real stock_code, but corp_code is outside the
    # v0 universe → recoverable by v0.5 universe expansion.
    if record.corp_code not in universe_corp_codes:
        return "A"

    # Listed AND inside universe — but the candidate's endpoint was unresolved,
    # i.e. the resolver in extraction failed to map this name to its corp_code.
    # That's an Entity Resolution gap, not a universe / schema gap. Bucket as
    # B-1 — Entity Resolution is a future capability (v2 sprint).
    return "B1"


def summarize_drops(
    candidates: Iterable[OwnsCandidate],
    corp_code_records: Iterable[CorpCodeRecord],
    universe_corp_codes: set[str],
    *,
    relate_by_candidate: dict[int, str | None] | None = None,
) -> DropClassification:
    """Classify a batch of dropped candidates and aggregate counts + samples.

    `relate_by_candidate` maps id(candidate) → `relate` field for reverse
    candidates. Forward candidates may be omitted from the dict (treated as
    relate=None).
    """
    by_name: dict[str, CorpCodeRecord] = {}
    for record in corp_code_records:
        by_name.setdefault(normalize_company_name(record.corp_name), record)

    counts: dict[DropCategory, int] = {"A": 0, "B1": 0, "B2": 0}
    samples: dict[DropCategory, list[str]] = {"A": [], "B1": [], "B2": []}

    relate_lookup = relate_by_candidate or {}
    for candidate in candidates:
        relate = relate_lookup.get(id(candidate))
        category = classify_unloaded_candidate(
            candidate, by_name, universe_corp_codes, relate=relate
        )
        counts[category] += 1
        if len(samples[category]) < SAMPLE_CAP:
            unresolved = (
                candidate.source if candidate.source.corp_code is None else candidate.target
            )
            sample_text = unresolved.name_text or ""
            if sample_text and sample_text not in samples[category]:
                samples[category].append(sample_text)

    return DropClassification(counts=counts, samples=samples)
