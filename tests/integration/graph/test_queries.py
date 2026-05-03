"""Integration tests for graph/queries.py against real Neo4j.

Each test seeds a small fixture graph via the existing upsert_* loaders so we
exercise the same write path the real ingest uses. Reads then run through
get_subsidiaries / find_common_parents / get_within_2hop.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from k_fingraph.graph.client import Neo4jClient
from k_fingraph.graph.load import upsert_companies, upsert_owns
from k_fingraph.graph.migrations import apply_schema
from k_fingraph.graph.queries import (
    find_common_parents,
    get_subsidiaries,
    get_within_2hop,
)
from k_fingraph.schemas.graph import (
    Company,
    OwnsCandidate,
    OwnsEndpoint,
    RelationType,
)

NOW = datetime(2026, 5, 3, 12, 0, 0, tzinfo=UTC)
AS_OF_2023 = date(2023, 12, 31)
AS_OF_2024 = date(2024, 12, 31)


def _company(*, ticker: str, corp_code: str, name_kr: str) -> Company:
    return Company(
        ticker=ticker,
        corp_code=corp_code,
        name_kr=name_kr,
        name_normalized=name_kr.replace(" ", ""),
        name_en=None,
        market="KOSPI",
        industry_krx=None,
        created_at=NOW,
        updated_at=NOW,
    )


def _owns(
    *,
    src: str,
    tgt: str,
    stake: float,
    rel: RelationType,
    as_of: date = AS_OF_2024,
    source_id: str = "rcept-1",
) -> OwnsCandidate:
    return OwnsCandidate(
        source=OwnsEndpoint(corp_code=src),
        target=OwnsEndpoint(corp_code=tgt),
        stake_pct=stake,
        relation_type=rel,
        as_of=as_of,
        source_id=source_id,
        extracted_at=NOW,
    )


@pytest.fixture
def graph(clean_neo4j: Neo4jClient) -> Neo4jClient:
    apply_schema(clean_neo4j)
    return clean_neo4j


# Reusable family graph used by most tests.
#
# parent (P) ──SUBSIDIARY 60%──▶ child_a (A)
#   │ ──SUBSIDIARY 80%──▶ child_b (B)
#   │ ──AFFILIATE  30%──▶ affiliate (X)
# grandparent (G) ──SUBSIDIARY 51%──▶ parent (P)
# unrelated (U) — isolated, no edges
def _seed_family(graph: Neo4jClient) -> set[str]:
    companies = [
        _company(ticker="000001", corp_code="00000001", name_kr="GrandParent"),
        _company(ticker="000002", corp_code="00000002", name_kr="Parent"),
        _company(ticker="000003", corp_code="00000003", name_kr="ChildA"),
        _company(ticker="000004", corp_code="00000004", name_kr="ChildB"),
        _company(ticker="000005", corp_code="00000005", name_kr="Affiliate"),
        _company(ticker="000006", corp_code="00000006", name_kr="Unrelated"),
    ]
    upsert_companies(graph, companies)
    universe = {c.corp_code for c in companies}
    candidates = [
        _owns(
            src="00000001",
            tgt="00000002",
            stake=51.0,
            rel=RelationType.SUBSIDIARY,
            source_id="rcept-G-P",
        ),
        _owns(
            src="00000002",
            tgt="00000003",
            stake=60.0,
            rel=RelationType.SUBSIDIARY,
            source_id="rcept-P-A",
        ),
        _owns(
            src="00000002",
            tgt="00000004",
            stake=80.0,
            rel=RelationType.SUBSIDIARY,
            source_id="rcept-P-B",
        ),
        _owns(
            src="00000002",
            tgt="00000005",
            stake=30.0,
            rel=RelationType.AFFILIATE,
            source_id="rcept-P-X",
        ),
    ]
    upsert_owns(graph, candidates, universe)
    return universe


@pytest.mark.integration
class TestGetSubsidiaries:
    def test_returns_only_subsidiary_by_default(self, graph: Neo4jClient) -> None:
        _seed_family(graph)
        rows = get_subsidiaries(graph, "000002")

        children = [(r.child_ticker, r.stake_pct) for r in rows]
        assert children == [("000004", 80.0), ("000003", 60.0)]
        assert all(r.relation_type is RelationType.SUBSIDIARY for r in rows)
        assert all(r.parent_ticker == "000002" for r in rows)

    def test_includes_affiliate_when_requested(self, graph: Neo4jClient) -> None:
        _seed_family(graph)
        rows = get_subsidiaries(
            graph,
            "000002",
            relation_types=(RelationType.SUBSIDIARY, RelationType.AFFILIATE),
        )
        children = {r.child_ticker for r in rows}
        assert children == {"000003", "000004", "000005"}

    def test_unknown_ticker_returns_empty(self, graph: Neo4jClient) -> None:
        _seed_family(graph)
        assert get_subsidiaries(graph, "999999") == []

    def test_isolated_node_returns_empty(self, graph: Neo4jClient) -> None:
        _seed_family(graph)
        assert get_subsidiaries(graph, "000006") == []

    def test_collapses_to_latest_as_of(self, graph: Neo4jClient) -> None:
        # Two disclosures for the same (parent, child): older 50%, newer 60%.
        # Expect only the 60% / 2024 row.
        companies = [
            _company(ticker="000010", corp_code="00000010", name_kr="HoldCo"),
            _company(ticker="000011", corp_code="00000011", name_kr="Sub"),
        ]
        upsert_companies(graph, companies)
        universe = {c.corp_code for c in companies}
        upsert_owns(
            graph,
            [
                _owns(
                    src="00000010",
                    tgt="00000011",
                    stake=50.0,
                    rel=RelationType.SUBSIDIARY,
                    as_of=AS_OF_2023,
                    source_id="rcept-old",
                ),
                _owns(
                    src="00000010",
                    tgt="00000011",
                    stake=60.0,
                    rel=RelationType.SUBSIDIARY,
                    as_of=AS_OF_2024,
                    source_id="rcept-new",
                ),
            ],
            universe,
        )
        rows = get_subsidiaries(graph, "000010")
        assert len(rows) == 1
        assert rows[0].stake_pct == 60.0
        assert rows[0].as_of == AS_OF_2024


@pytest.mark.integration
class TestFindCommonParents:
    def test_finds_single_parent(self, graph: Neo4jClient) -> None:
        _seed_family(graph)
        rows = find_common_parents(graph, "000003", "000004")
        assert len(rows) == 1
        row = rows[0]
        assert row.parent_ticker == "000002"
        assert row.stake_to_a == 60.0
        assert row.stake_to_b == 80.0
        assert row.relation_type_a is RelationType.SUBSIDIARY
        assert row.relation_type_b is RelationType.SUBSIDIARY

    def test_no_common_parent_returns_empty(self, graph: Neo4jClient) -> None:
        _seed_family(graph)
        # ChildA shares parent only with ChildB/Affiliate, not GrandParent.
        assert find_common_parents(graph, "000003", "000001") == []

    def test_unknown_ticker_returns_empty(self, graph: Neo4jClient) -> None:
        _seed_family(graph)
        assert find_common_parents(graph, "000003", "999999") == []

    def test_multiple_common_parents_ordered_by_total_stake(self, graph: Neo4jClient) -> None:
        # Two parents (P1, P2) both own A and B; P2 has higher total stake.
        companies = [
            _company(ticker="100001", corp_code="10000001", name_kr="P1"),
            _company(ticker="100002", corp_code="10000002", name_kr="P2"),
            _company(ticker="100003", corp_code="10000003", name_kr="A"),
            _company(ticker="100004", corp_code="10000004", name_kr="B"),
        ]
        upsert_companies(graph, companies)
        universe = {c.corp_code for c in companies}
        upsert_owns(
            graph,
            [
                _owns(
                    src="10000001",
                    tgt="10000003",
                    stake=20.0,
                    rel=RelationType.AFFILIATE,
                    source_id="P1-A",
                ),
                _owns(
                    src="10000001",
                    tgt="10000004",
                    stake=20.0,
                    rel=RelationType.AFFILIATE,
                    source_id="P1-B",
                ),
                _owns(
                    src="10000002",
                    tgt="10000003",
                    stake=55.0,
                    rel=RelationType.SUBSIDIARY,
                    source_id="P2-A",
                ),
                _owns(
                    src="10000002",
                    tgt="10000004",
                    stake=55.0,
                    rel=RelationType.SUBSIDIARY,
                    source_id="P2-B",
                ),
            ],
            universe,
        )
        rows = find_common_parents(graph, "100003", "100004")
        assert [r.parent_ticker for r in rows] == ["100002", "100001"]


@pytest.mark.integration
class TestGetWithin2Hop:
    def test_isolated_center_yields_self_only(self, graph: Neo4jClient) -> None:
        _seed_family(graph)
        sub = get_within_2hop(graph, "000006")
        assert len(sub.nodes) == 1
        assert sub.nodes[0].ticker == "000006"
        assert sub.nodes[0].is_center is True
        assert sub.edges == []

    def test_unknown_ticker_yields_empty(self, graph: Neo4jClient) -> None:
        _seed_family(graph)
        sub = get_within_2hop(graph, "999999")
        assert sub.nodes == []
        assert sub.edges == []

    def test_includes_parents_and_children_within_2hop(self, graph: Neo4jClient) -> None:
        _seed_family(graph)
        # Center = Parent (000002). Within 2 hops (any direction):
        #   1-hop:  GrandParent (in), ChildA / ChildB / Affiliate (out)
        #   2-hop:  none beyond that (children have no further OWNS)
        # Unrelated (000006) must be excluded.
        sub = get_within_2hop(graph, "000002")
        tickers = {n.ticker for n in sub.nodes}
        assert tickers == {"000001", "000002", "000003", "000004", "000005"}
        assert sum(1 for n in sub.nodes if n.is_center) == 1
        center = next(n for n in sub.nodes if n.is_center)
        assert center.ticker == "000002"

        edge_pairs = {(e.source_ticker, e.target_ticker) for e in sub.edges}
        assert edge_pairs == {
            ("000001", "000002"),
            ("000002", "000003"),
            ("000002", "000004"),
            ("000002", "000005"),
        }

    def test_two_hop_reach_via_grandparent(self, graph: Neo4jClient) -> None:
        # Center = ChildA (000003). 2-hop reach pulls GrandParent in
        # (ChildA ◀── Parent ◀── GrandParent), but not Unrelated.
        _seed_family(graph)
        sub = get_within_2hop(graph, "000003")
        tickers = {n.ticker for n in sub.nodes}
        # Includes self, Parent (1-hop), Sibling ChildB (2-hop via Parent),
        # Affiliate (2-hop via Parent), and GrandParent (2-hop via Parent).
        assert tickers == {"000001", "000002", "000003", "000004", "000005"}
