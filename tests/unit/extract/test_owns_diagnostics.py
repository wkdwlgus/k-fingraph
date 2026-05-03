"""Unit tests for the (A)/(B-1)/(B-2) OWNS-drop classifier."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from k_fingraph.extract.owns_diagnostics import (
    classify_unloaded_candidate,
    summarize_drops,
)
from k_fingraph.schemas.dart import CorpCodeRecord
from k_fingraph.schemas.graph import OwnsCandidate, OwnsEndpoint, RelationType
from k_fingraph.sources.dart_reports import normalize_company_name

NOW = datetime(2026, 5, 3, 12, 0, 0, tzinfo=UTC)
AS_OF = date(2024, 12, 31)

# Universe = the two listed companies present in the corp_code fixture.
SAMSUNG_CC = "00126380"
SK_HYNIX_CC = "00164779"
UNIVERSE = {SAMSUNG_CC, SK_HYNIX_CC}

# corp_code table fixture covering each classification branch:
#  - listed inside universe (Samsung, SK Hynix)
#  - listed outside universe (KOSDAQ-style — Hyundai Mipo for "A")
#  - unlisted (no stock_code — for "B-1")
LISTED_OUTSIDE = CorpCodeRecord(
    corp_code="00164742",
    corp_name="현대미포조선",
    stock_code="010620",
    modify_date="20250101",
)
UNLISTED = CorpCodeRecord(
    corp_code="00258801",
    corp_name="삼성디스플레이",
    stock_code=None,
    modify_date="20250101",
)
SAMSUNG_REC = CorpCodeRecord(
    corp_code=SAMSUNG_CC,
    corp_name="삼성전자",
    stock_code="005930",
    modify_date="20250101",
)
SK_REC = CorpCodeRecord(
    corp_code=SK_HYNIX_CC,
    corp_name="SK하이닉스",
    stock_code="000660",
    modify_date="20250101",
)
CORP_CODES = [SAMSUNG_REC, SK_REC, LISTED_OUTSIDE, UNLISTED]
BY_NAME = {normalize_company_name(r.corp_name): r for r in CORP_CODES}


def _candidate(
    *,
    source_corp: str | None = None,
    target_corp: str | None = None,
    source_text: str | None = None,
    target_text: str | None = None,
) -> OwnsCandidate:
    return OwnsCandidate(
        source=OwnsEndpoint(
            corp_code=source_corp,
            name_text=source_text,
            name_normalized=normalize_company_name(source_text) if source_text else None,
        ),
        target=OwnsEndpoint(
            corp_code=target_corp,
            name_text=target_text,
            name_normalized=normalize_company_name(target_text) if target_text else None,
        ),
        stake_pct=30.0,
        relation_type=RelationType.AFFILIATE,
        as_of=AS_OF,
        source_id="rcept-1",
        extracted_at=NOW,
    )


@pytest.mark.unit
class TestClassifyUnloadedCandidate:
    def test_resolved_endpoints_outside_universe_is_a(self) -> None:
        # Both endpoints resolved by extraction; loader dropped because target
        # is a listed company outside KOSPI 200.
        cand = _candidate(source_corp=SAMSUNG_CC, target_corp=LISTED_OUTSIDE.corp_code)
        assert classify_unloaded_candidate(cand, BY_NAME, UNIVERSE) == "A"

    def test_unresolved_text_matching_listed_outside_universe_is_a(self) -> None:
        # Forward direction — target name text matches a listed company that
        # is outside the v0 universe.
        cand = _candidate(source_corp=SAMSUNG_CC, target_text="현대미포조선")
        assert classify_unloaded_candidate(cand, BY_NAME, UNIVERSE) == "A"

    def test_unresolved_text_matching_unlisted_is_b1(self) -> None:
        cand = _candidate(source_corp=SAMSUNG_CC, target_text="삼성디스플레이")
        assert classify_unloaded_candidate(cand, BY_NAME, UNIVERSE) == "B1"

    def test_unresolved_text_no_corp_code_match_is_b2(self) -> None:
        cand = _candidate(source_corp=SAMSUNG_CC, target_text="Apple Inc.")
        assert classify_unloaded_candidate(cand, BY_NAME, UNIVERSE) == "B2"

    def test_reverse_relate_person_hint_overrides_to_b1(self) -> None:
        # Holder text matches a listed company (Samsung Electronics), but
        # `relate` says it's actually an executive sharing the name.
        cand = _candidate(source_text="삼성전자", target_corp=SAMSUNG_CC)
        result = classify_unloaded_candidate(cand, BY_NAME, UNIVERSE, relate="최대주주 본인")
        assert result == "B1"

    @pytest.mark.parametrize("relate", ["임원", "특수관계인", "친인척"])
    def test_other_person_relate_hints_classify_as_b1(self, relate: str) -> None:
        cand = _candidate(source_text="국민연금공단", target_corp=SAMSUNG_CC)
        result = classify_unloaded_candidate(cand, BY_NAME, UNIVERSE, relate=relate)
        assert result == "B1"

    def test_text_matching_in_universe_unresolved_is_b1(self) -> None:
        # Holder name matches a KOSPI 200 company by name but extraction
        # didn't resolve it — Entity Resolution gap, classify as B-1.
        cand = _candidate(source_text="SK하이닉스", target_corp=SAMSUNG_CC)
        assert classify_unloaded_candidate(cand, BY_NAME, UNIVERSE) == "B1"


@pytest.mark.unit
class TestSummarizeDrops:
    def test_aggregates_counts_and_keeps_samples(self) -> None:
        cands = [
            _candidate(source_corp=SAMSUNG_CC, target_text="현대미포조선"),  # A
            _candidate(source_corp=SAMSUNG_CC, target_text="현대미포조선"),  # A dup
            _candidate(source_corp=SAMSUNG_CC, target_text="삼성디스플레이"),  # B1
            _candidate(source_corp=SAMSUNG_CC, target_text="Apple Inc."),  # B2
            _candidate(source_corp=SAMSUNG_CC, target_text="SoftBank Vision Fund"),  # B2
        ]
        summary = summarize_drops(cands, CORP_CODES, UNIVERSE)

        assert summary.counts == {"A": 2, "B1": 1, "B2": 2}
        assert summary.total == 5
        assert "현대미포조선" in summary.samples["A"]
        assert "삼성디스플레이" in summary.samples["B1"]
        assert set(summary.samples["B2"]) == {"Apple Inc.", "SoftBank Vision Fund"}

    def test_relate_lookup_per_candidate(self) -> None:
        exec_holder = _candidate(source_text="삼성전자", target_corp=SAMSUNG_CC)
        listed_holder = _candidate(source_text="현대미포조선", target_corp=SAMSUNG_CC)
        relate_map = {id(exec_holder): "최대주주 본인"}
        summary = summarize_drops(
            [exec_holder, listed_holder],
            CORP_CODES,
            UNIVERSE,
            relate_by_candidate=relate_map,
        )

        # exec_holder → B1 by relate; listed_holder → A by name match
        assert summary.counts == {"A": 1, "B1": 1, "B2": 0}

    def test_empty_input_yields_zero_counts(self) -> None:
        summary = summarize_drops([], CORP_CODES, UNIVERSE)
        assert summary.counts == {"A": 0, "B1": 0, "B2": 0}
        assert summary.samples == {"A": [], "B1": [], "B2": []}
        assert summary.total == 0
