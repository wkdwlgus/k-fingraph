"""Pure-logic tests for the ADR 0007 OWNS filter (no Neo4j)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from k_fingraph.graph.load import filter_loadable_candidates
from k_fingraph.schemas.graph import OwnsCandidate, OwnsEndpoint, RelationType

UNIVERSE = {"00000001", "00000002", "00000003"}
FIXED_AS_OF = date(2025, 12, 31)
FIXED_EXTRACTED_AT = datetime(2026, 5, 3, 12, 0, 0, tzinfo=UTC)


def _candidate(
    *,
    source_corp: str | None = None,
    target_corp: str | None = None,
    source_text: str | None = None,
    target_text: str | None = None,
    stake_pct: float | None = 30.0,
    as_of: date | None = FIXED_AS_OF,
    relation_type: RelationType = RelationType.AFFILIATE,
    source_id: str = "rcept-1",
) -> OwnsCandidate:
    return OwnsCandidate(
        source=OwnsEndpoint(corp_code=source_corp, name_text=source_text),
        target=OwnsEndpoint(corp_code=target_corp, name_text=target_text),
        stake_pct=stake_pct,
        relation_type=relation_type,
        as_of=as_of,
        source_id=source_id,
        extracted_at=FIXED_EXTRACTED_AT,
    )


@pytest.mark.unit
class TestFilterLoadableCandidates:
    def test_both_endpoints_resolved_and_in_universe_loads(self) -> None:
        cand = _candidate(source_corp="00000001", target_corp="00000002")
        relations, stats = filter_loadable_candidates([cand], UNIVERSE)

        assert stats.candidates_total == 1
        assert stats.loaded == 1
        assert stats.dropped_endpoint_unresolved == 0
        assert stats.dropped_outside_universe == 0
        assert len(relations) == 1
        assert relations[0].source_corp_code == "00000001"
        assert relations[0].target_corp_code == "00000002"
        assert relations[0].stake_pct == 30.0
        assert relations[0].relation_type is RelationType.AFFILIATE
        assert relations[0].as_of == FIXED_AS_OF

    def test_unresolved_source_drops(self) -> None:
        cand = _candidate(target_corp="00000001", source_text="삼성생명")
        relations, stats = filter_loadable_candidates([cand], UNIVERSE)

        assert relations == []
        assert stats.candidates_total == 1
        assert stats.loaded == 0
        assert stats.dropped_endpoint_unresolved == 1
        assert stats.dropped_outside_universe == 0

    def test_unresolved_target_drops(self) -> None:
        cand = _candidate(source_corp="00000001", target_text="삼성디스플레이")
        relations, stats = filter_loadable_candidates([cand], UNIVERSE)

        assert relations == []
        assert stats.dropped_endpoint_unresolved == 1
        assert stats.dropped_outside_universe == 0

    def test_source_outside_universe_drops(self) -> None:
        cand = _candidate(source_corp="99999999", target_corp="00000001")
        relations, stats = filter_loadable_candidates([cand], UNIVERSE)

        assert relations == []
        assert stats.dropped_endpoint_unresolved == 0
        assert stats.dropped_outside_universe == 1

    def test_target_outside_universe_drops(self) -> None:
        cand = _candidate(source_corp="00000001", target_corp="99999999")
        relations, stats = filter_loadable_candidates([cand], UNIVERSE)

        assert relations == []
        assert stats.dropped_outside_universe == 1

    def test_missing_stake_pct_drops_as_unresolved(self) -> None:
        cand = _candidate(source_corp="00000001", target_corp="00000002", stake_pct=None)
        relations, stats = filter_loadable_candidates([cand], UNIVERSE)

        assert relations == []
        assert stats.dropped_endpoint_unresolved == 1
        assert stats.dropped_outside_universe == 0

    def test_missing_as_of_drops_as_unresolved(self) -> None:
        cand = _candidate(source_corp="00000001", target_corp="00000002", as_of=None)
        relations, stats = filter_loadable_candidates([cand], UNIVERSE)

        assert relations == []
        assert stats.dropped_endpoint_unresolved == 1

    def test_mixed_batch_accumulates_stats(self) -> None:
        cands = [
            _candidate(source_corp="00000001", target_corp="00000002"),
            _candidate(source_corp="00000001", target_corp="00000003"),
            _candidate(target_corp="00000001", source_text="국민연금"),
            _candidate(source_corp="00000001", target_text="삼성디스플레이"),
            _candidate(source_corp="00000001", target_corp="99999999"),
            _candidate(source_corp="99999999", target_corp="88888888"),
        ]
        relations, stats = filter_loadable_candidates(cands, UNIVERSE)

        assert stats.candidates_total == 6
        assert stats.loaded == 2
        assert stats.dropped_endpoint_unresolved == 2
        assert stats.dropped_outside_universe == 2
        assert (
            stats.loaded + stats.dropped_endpoint_unresolved + stats.dropped_outside_universe
            == stats.candidates_total
        )
        assert len(relations) == 2

    def test_empty_input(self) -> None:
        relations, stats = filter_loadable_candidates([], UNIVERSE)
        assert relations == []
        assert stats.candidates_total == 0
        assert stats.loaded == 0
        assert stats.dropped_endpoint_unresolved == 0
        assert stats.dropped_outside_universe == 0
