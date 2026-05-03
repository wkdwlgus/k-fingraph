"""Unit tests for OWNS extraction from forward (otrCprInvstmnt) and reverse
(hyslrSttus) DART reports. Drives the parsers to load fixtures, then asserts
on extractor output (resolved/unresolved endpoints, relation classification,
zero-stake filtering)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from k_fingraph.extract.owns import (
    AFFILIATE_MIN_PCT,
    SUBSIDIARY_MIN_PCT,
    classify_relation,
    extract_owns_from_major_shareholders,
    extract_owns_from_other_corp_investments,
)
from k_fingraph.schemas.graph import RelationType
from k_fingraph.sources.dart_reports import (
    parse_major_shareholders_json,
    parse_other_corp_investments_json,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "dart"
SAMSUNG_CORP_CODE = "00126380"
BSNS_YEAR = "2024"
REPRT_CODE_ANNUAL = "11011"
FIXED_FETCHED_AT = datetime(2026, 5, 3, 12, 0, 0, tzinfo=UTC)


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Relation classification (ADR 0006 thresholds)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestClassifyRelation:
    @pytest.mark.parametrize(
        ("pct", "expected"),
        [
            (100.0, RelationType.SUBSIDIARY),
            (84.78, RelationType.SUBSIDIARY),
            (50.0, RelationType.SUBSIDIARY),
            (49.99, RelationType.AFFILIATE),
            (26.0, RelationType.AFFILIATE),
            (20.0, RelationType.AFFILIATE),
            (19.99, RelationType.OTHER),
            (5.01, RelationType.OTHER),
            (0.0, RelationType.OTHER),
            (None, RelationType.OTHER),
        ],
    )
    def test_threshold_boundaries(self, pct: float | None, expected: RelationType) -> None:
        assert classify_relation(pct) == expected

    def test_threshold_constants_match_adr_0006(self) -> None:
        # If these constants change, ADR 0006 must be superseded.
        assert SUBSIDIARY_MIN_PCT == 50.0
        assert AFFILIATE_MIN_PCT == 20.0


# ---------------------------------------------------------------------------
# Forward extraction (source resolved, target unresolved)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestForwardExtraction:
    def test_emits_one_candidate_per_row(self) -> None:
        report = parse_other_corp_investments_json(
            _load("otr_cpr_invstmnt_sample.json"),
            corp_code=SAMSUNG_CORP_CODE,
            bsns_year=BSNS_YEAR,
            reprt_code=REPRT_CODE_ANNUAL,
            fetched_at=FIXED_FETCHED_AT,
        )
        candidates = extract_owns_from_other_corp_investments(report)
        assert len(candidates) == len(report.rows) == 4

    def test_source_is_resolved_target_is_text(self) -> None:
        report = parse_other_corp_investments_json(
            _load("otr_cpr_invstmnt_sample.json"),
            corp_code=SAMSUNG_CORP_CODE,
            bsns_year=BSNS_YEAR,
            reprt_code=REPRT_CODE_ANNUAL,
            fetched_at=FIXED_FETCHED_AT,
        )
        candidate = extract_owns_from_other_corp_investments(report)[0]

        assert candidate.source.is_resolved
        assert candidate.source.corp_code == SAMSUNG_CORP_CODE
        assert candidate.source.name_text is None

        assert not candidate.target.is_resolved
        assert candidate.target.corp_code is None
        assert candidate.target.name_text == "삼성디스플레이(주)"
        assert candidate.target.name_normalized == "삼성디스플레이"

    def test_relation_types_match_stake_pct(self) -> None:
        report = parse_other_corp_investments_json(
            _load("otr_cpr_invstmnt_sample.json"),
            corp_code=SAMSUNG_CORP_CODE,
            bsns_year=BSNS_YEAR,
            reprt_code=REPRT_CODE_ANNUAL,
            fetched_at=FIXED_FETCHED_AT,
        )
        candidates = extract_owns_from_other_corp_investments(report)
        # Fixture: 84.78 → SUBSIDIARY, 26.00 → AFFILIATE, 0.40 → OTHER, None → OTHER
        assert [c.relation_type for c in candidates] == [
            RelationType.SUBSIDIARY,
            RelationType.AFFILIATE,
            RelationType.OTHER,
            RelationType.OTHER,
        ]

    def test_provenance_carried_through(self) -> None:
        report = parse_other_corp_investments_json(
            _load("otr_cpr_invstmnt_sample.json"),
            corp_code=SAMSUNG_CORP_CODE,
            bsns_year=BSNS_YEAR,
            reprt_code=REPRT_CODE_ANNUAL,
            fetched_at=FIXED_FETCHED_AT,
        )
        candidate = extract_owns_from_other_corp_investments(report)[0]
        assert candidate.source_id == "20240315000001"
        assert candidate.extracted_at == FIXED_FETCHED_AT


# ---------------------------------------------------------------------------
# Reverse extraction (target resolved, source unresolved)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReverseExtraction:
    def test_drops_zero_and_missing_stake_rows(self) -> None:
        report = parse_major_shareholders_json(
            _load("hyslr_sttus_sample.json"),
            corp_code=SAMSUNG_CORP_CODE,
            bsns_year=BSNS_YEAR,
            reprt_code=REPRT_CODE_ANNUAL,
            fetched_at=FIXED_FETCHED_AT,
        )
        # Fixture has 5 rows; rows 4-5 are zero-holding 친인척 → dropped.
        candidates = extract_owns_from_major_shareholders(report)
        assert len(candidates) == 3

    def test_target_is_resolved_source_is_text(self) -> None:
        report = parse_major_shareholders_json(
            _load("hyslr_sttus_sample.json"),
            corp_code=SAMSUNG_CORP_CODE,
            bsns_year=BSNS_YEAR,
            reprt_code=REPRT_CODE_ANNUAL,
            fetched_at=FIXED_FETCHED_AT,
        )
        candidates = extract_owns_from_major_shareholders(report)
        samsung_life = candidates[1]

        assert not samsung_life.source.is_resolved
        assert samsung_life.source.name_text == "삼성생명보험㈜"
        assert samsung_life.source.name_normalized == "삼성생명보험"

        assert samsung_life.target.is_resolved
        assert samsung_life.target.corp_code == SAMSUNG_CORP_CODE

        assert samsung_life.stake_pct == 8.51
        assert samsung_life.relation_type == RelationType.OTHER

    def test_paren_prefix_normalized(self) -> None:
        report = parse_major_shareholders_json(
            _load("hyslr_sttus_sample.json"),
            corp_code=SAMSUNG_CORP_CODE,
            bsns_year=BSNS_YEAR,
            reprt_code=REPRT_CODE_ANNUAL,
            fetched_at=FIXED_FETCHED_AT,
        )
        candidates = extract_owns_from_major_shareholders(report)
        samsung_cnt = candidates[2]
        assert samsung_cnt.source.name_text == "(주)삼성물산"
        assert samsung_cnt.source.name_normalized == "삼성물산"
