"""Unit tests for the v0 OWNS endpoint resolver."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from k_fingraph.resolve.owns import build_resolution_index, resolve_endpoints
from k_fingraph.schemas.dart import CorpCodeRecord
from k_fingraph.schemas.graph import OwnsCandidate, OwnsEndpoint, RelationType

NOW = datetime(2026, 5, 3, 12, 0, 0, tzinfo=UTC)
AS_OF = date(2024, 12, 31)

SAMSUNG = CorpCodeRecord(
    corp_code="00126380", corp_name="삼성전자", stock_code="005930", modify_date="20250101"
)
SAMSUNG_ELEC_PARTS = CorpCodeRecord(
    corp_code="00256500", corp_name="삼성전기", stock_code="009150", modify_date="20250101"
)
SK_HYNIX = CorpCodeRecord(
    corp_code="00164779", corp_name="SK하이닉스", stock_code="000660", modify_date="20250101"
)
# Listed but outside the v0 universe.
HYUNDAI_MIPO = CorpCodeRecord(
    corp_code="00164742", corp_name="현대미포조선", stock_code="010620", modify_date="20250101"
)
# Unlisted — must NOT enter the index.
SAMSUNG_DISPLAY = CorpCodeRecord(
    corp_code="00258801", corp_name="삼성디스플레이", stock_code=None, modify_date="20250101"
)
# Ambiguity case — fake duplicate normalized name to force the universe-wins
# tie-breaker. Both records are listed, but only one is in the universe.
DUPE_OUTSIDE = CorpCodeRecord(
    corp_code="99999999", corp_name="삼성전자", stock_code="999999", modify_date="20250101"
)

UNIVERSE = {SAMSUNG.corp_code, SAMSUNG_ELEC_PARTS.corp_code, SK_HYNIX.corp_code}
ALL_RECORDS = [SAMSUNG, SAMSUNG_ELEC_PARTS, SK_HYNIX, HYUNDAI_MIPO, SAMSUNG_DISPLAY, DUPE_OUTSIDE]


def _candidate(
    *,
    source_corp: str | None = None,
    target_corp: str | None = None,
    source_text: str | None = None,
    target_text: str | None = None,
) -> OwnsCandidate:
    return OwnsCandidate(
        source=OwnsEndpoint(corp_code=source_corp, name_text=source_text),
        target=OwnsEndpoint(corp_code=target_corp, name_text=target_text),
        stake_pct=30.0,
        relation_type=RelationType.AFFILIATE,
        as_of=AS_OF,
        source_id="rcept-1",
        extracted_at=NOW,
    )


@pytest.mark.unit
class TestBuildResolutionIndex:
    def test_universe_records_are_indexed(self) -> None:
        index = build_resolution_index(ALL_RECORDS, UNIVERSE)
        assert index["삼성전자"] == SAMSUNG.corp_code
        assert index["삼성전기"] == SAMSUNG_ELEC_PARTS.corp_code
        assert index["SK하이닉스"] == SK_HYNIX.corp_code

    def test_listed_outside_universe_is_indexed(self) -> None:
        index = build_resolution_index(ALL_RECORDS, UNIVERSE)
        assert index["현대미포조선"] == HYUNDAI_MIPO.corp_code

    def test_unlisted_is_not_indexed(self) -> None:
        index = build_resolution_index(ALL_RECORDS, UNIVERSE)
        assert "삼성디스플레이" not in index

    def test_universe_wins_on_ambiguous_name(self) -> None:
        # Both SAMSUNG (universe) and DUPE_OUTSIDE (listed, not universe) share
        # normalized name "삼성전자". Universe must win.
        index = build_resolution_index(ALL_RECORDS, UNIVERSE)
        assert index["삼성전자"] == SAMSUNG.corp_code

    def test_corporate_form_suffix_is_normalized(self) -> None:
        # corp_code table can carry suffixes too — make sure both sides of the
        # match key are normalized identically.
        suffixed = CorpCodeRecord(
            corp_code="00777777",
            corp_name="㈜더미코퍼레이션",
            stock_code="077777",
            modify_date="20250101",
        )
        index = build_resolution_index([suffixed], UNIVERSE)
        assert index["더미코퍼레이션"] == suffixed.corp_code


@pytest.mark.unit
class TestResolveEndpoints:
    def test_unresolved_endpoint_in_universe_gets_corp_code(self) -> None:
        index = build_resolution_index(ALL_RECORDS, UNIVERSE)
        cand = _candidate(source_corp=SAMSUNG.corp_code, target_text="삼성전기㈜")
        out = resolve_endpoints([cand], index)
        assert len(out) == 1
        assert out[0].target.corp_code == SAMSUNG_ELEC_PARTS.corp_code
        assert out[0].source.corp_code == SAMSUNG.corp_code  # unchanged

    def test_unresolved_endpoint_listed_outside_universe_gets_corp_code(self) -> None:
        index = build_resolution_index(ALL_RECORDS, UNIVERSE)
        cand = _candidate(source_corp=SAMSUNG.corp_code, target_text="현대미포조선")
        out = resolve_endpoints([cand], index)
        assert out[0].target.corp_code == HYUNDAI_MIPO.corp_code

    def test_unresolved_unlisted_text_stays_unresolved(self) -> None:
        index = build_resolution_index(ALL_RECORDS, UNIVERSE)
        cand = _candidate(source_corp=SAMSUNG.corp_code, target_text="삼성디스플레이")
        out = resolve_endpoints([cand], index)
        assert out[0].target.corp_code is None

    def test_unknown_text_stays_unresolved(self) -> None:
        index = build_resolution_index(ALL_RECORDS, UNIVERSE)
        cand = _candidate(source_corp=SAMSUNG.corp_code, target_text="Apple Inc.")
        out = resolve_endpoints([cand], index)
        assert out[0].target.corp_code is None

    def test_already_resolved_endpoint_passes_through_unchanged(self) -> None:
        index = build_resolution_index(ALL_RECORDS, UNIVERSE)
        cand = _candidate(source_corp=SAMSUNG.corp_code, target_corp=SAMSUNG_ELEC_PARTS.corp_code)
        out = resolve_endpoints([cand], index)
        assert out[0] is cand  # identity preserved when nothing changes

    def test_reverse_direction_resolves_source_text(self) -> None:
        index = build_resolution_index(ALL_RECORDS, UNIVERSE)
        cand = _candidate(source_text="삼성전기", target_corp=SAMSUNG.corp_code)
        out = resolve_endpoints([cand], index)
        assert out[0].source.corp_code == SAMSUNG_ELEC_PARTS.corp_code
        assert out[0].target.corp_code == SAMSUNG.corp_code

    def test_idempotent_on_repeat(self) -> None:
        index = build_resolution_index(ALL_RECORDS, UNIVERSE)
        cand = _candidate(source_corp=SAMSUNG.corp_code, target_text="삼성전기㈜")
        once = resolve_endpoints([cand], index)
        twice = resolve_endpoints(once, index)
        assert twice[0].target.corp_code == SAMSUNG_ELEC_PARTS.corp_code
        # Second pass should be a no-op (target was already resolved on pass 1).
        assert twice[0] is once[0]

    def test_empty_input(self) -> None:
        assert resolve_endpoints([], {}) == []
