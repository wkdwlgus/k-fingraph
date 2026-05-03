"""Integration tests for upsert_companies / upsert_owns against real Neo4j.

Each test depends on the `clean_neo4j` fixture, which DETACH DELETEs the graph
before the test runs (constraints/indexes survive). The migration is applied
once per test that needs it — `apply_schema` is idempotent.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from k_fingraph.graph.client import Neo4jClient
from k_fingraph.graph.load import upsert_companies, upsert_owns
from k_fingraph.graph.migrations import apply_schema
from k_fingraph.schemas.graph import (
    Company,
    OwnsCandidate,
    OwnsEndpoint,
    RelationType,
)

NOW = datetime(2026, 5, 3, 12, 0, 0, tzinfo=UTC)
AS_OF_2024 = date(2024, 12, 31)
AS_OF_2025 = date(2025, 12, 31)


def _company(
    *,
    ticker: str,
    corp_code: str,
    name_kr: str,
    name_en: str | None = None,
) -> Company:
    return Company(
        ticker=ticker,
        corp_code=corp_code,
        name_kr=name_kr,
        name_normalized=name_kr.replace(" ", ""),
        name_en=name_en,
        market="KOSPI",
        industry_krx=None,
        created_at=NOW,
        updated_at=NOW,
    )


def _owns_candidate(
    *,
    source_corp: str | None,
    target_corp: str | None,
    source_text: str | None = None,
    target_text: str | None = None,
    stake_pct: float | None = 30.0,
    as_of: date | None = AS_OF_2024,
    source_id: str = "rcept-1",
) -> OwnsCandidate:
    return OwnsCandidate(
        source=OwnsEndpoint(corp_code=source_corp, name_text=source_text),
        target=OwnsEndpoint(corp_code=target_corp, name_text=target_text),
        stake_pct=stake_pct,
        relation_type=RelationType.AFFILIATE,
        as_of=as_of,
        source_id=source_id,
        extracted_at=NOW,
    )


def _company_count(client: Neo4jClient) -> int:
    with client.session() as session:
        record = session.run("MATCH (c:Company) RETURN count(c) AS n").single()
    assert record is not None
    return int(record["n"])


def _owns_count(client: Neo4jClient) -> int:
    with client.session() as session:
        record = session.run("MATCH ()-[r:OWNS]->() RETURN count(r) AS n").single()
    assert record is not None
    return int(record["n"])


@pytest.fixture
def graph(clean_neo4j: Neo4jClient) -> Neo4jClient:
    apply_schema(clean_neo4j)
    return clean_neo4j


@pytest.mark.integration
class TestUpsertCompanies:
    def test_inserts_new_companies(self, graph: Neo4jClient) -> None:
        companies = [
            _company(ticker="005930", corp_code="00126380", name_kr="삼성전자"),
            _company(ticker="000660", corp_code="00164779", name_kr="SK하이닉스"),
        ]
        rows = upsert_companies(graph, companies)
        assert rows == 2
        assert _company_count(graph) == 2

    def test_idempotent_on_repeat(self, graph: Neo4jClient) -> None:
        company = _company(ticker="005930", corp_code="00126380", name_kr="삼성전자")
        upsert_companies(graph, [company])
        upsert_companies(graph, [company])
        assert _company_count(graph) == 1

    def test_updates_mutable_props_on_repeat(self, graph: Neo4jClient) -> None:
        original = _company(ticker="005930", corp_code="00126380", name_kr="삼성전자")
        upsert_companies(graph, [original])

        updated = _company(
            ticker="005930",
            corp_code="00126380",
            name_kr="삼성전자",
            name_en="Samsung Electronics",
        )
        upsert_companies(graph, [updated])

        with graph.session() as session:
            record = session.run(
                "MATCH (c:Company {ticker: '005930'}) RETURN c.name_en AS en"
            ).single()
        assert record is not None
        assert record["en"] == "Samsung Electronics"

    def test_empty_input_is_noop(self, graph: Neo4jClient) -> None:
        assert upsert_companies(graph, []) == 0
        assert _company_count(graph) == 0


@pytest.mark.integration
class TestUpsertOwns:
    def _seed_universe(self, graph: Neo4jClient) -> set[str]:
        companies = [
            _company(ticker="005930", corp_code="00126380", name_kr="삼성전자"),
            _company(ticker="000660", corp_code="00164779", name_kr="SK하이닉스"),
            _company(ticker="207940", corp_code="00877059", name_kr="삼성바이오로직스"),
        ]
        upsert_companies(graph, companies)
        return {c.corp_code for c in companies}

    def test_filters_per_adr_0007_and_loads_only_universe(self, graph: Neo4jClient) -> None:
        universe = self._seed_universe(graph)
        candidates = [
            # Loads — both endpoints in universe
            _owns_candidate(source_corp="00126380", target_corp="00877059"),
            # Drops — source unresolved
            _owns_candidate(source_corp=None, source_text="국민연금", target_corp="00126380"),
            # Drops — target unresolved
            _owns_candidate(
                source_corp="00126380",
                target_corp=None,
                target_text="삼성디스플레이",
            ),
            # Drops — both resolved but target outside universe
            _owns_candidate(source_corp="00126380", target_corp="99999999"),
        ]
        stats = upsert_owns(graph, candidates, universe)

        assert stats.candidates_total == 4
        assert stats.loaded == 1
        assert stats.dropped_endpoint_unresolved == 2
        assert stats.dropped_outside_universe == 1
        assert _owns_count(graph) == 1

    def test_idempotent_on_same_disclosure(self, graph: Neo4jClient) -> None:
        universe = self._seed_universe(graph)
        cand = _owns_candidate(
            source_corp="00126380",
            target_corp="00877059",
            stake_pct=43.4,
            as_of=AS_OF_2024,
            source_id="rcept-A",
        )
        upsert_owns(graph, [cand], universe)
        upsert_owns(graph, [cand], universe)
        assert _owns_count(graph) == 1

    def test_repeat_with_updated_stake_overwrites(self, graph: Neo4jClient) -> None:
        universe = self._seed_universe(graph)
        first = _owns_candidate(
            source_corp="00126380",
            target_corp="00877059",
            stake_pct=43.4,
            as_of=AS_OF_2024,
            source_id="rcept-A",
        )
        revised = _owns_candidate(
            source_corp="00126380",
            target_corp="00877059",
            stake_pct=44.0,
            as_of=AS_OF_2024,
            source_id="rcept-A",
        )
        upsert_owns(graph, [first], universe)
        upsert_owns(graph, [revised], universe)

        with graph.session() as session:
            record = session.run(
                "MATCH (:Company {corp_code: '00126380'})"
                "-[r:OWNS]->(:Company {corp_code: '00877059'}) "
                "RETURN r.stake_pct AS pct"
            ).single()
        assert record is not None
        assert record["pct"] == pytest.approx(44.0)
        assert _owns_count(graph) == 1

    def test_different_as_of_creates_separate_edges(self, graph: Neo4jClient) -> None:
        universe = self._seed_universe(graph)
        cand_2024 = _owns_candidate(
            source_corp="00126380",
            target_corp="00877059",
            as_of=AS_OF_2024,
            source_id="rcept-2024",
        )
        cand_2025 = _owns_candidate(
            source_corp="00126380",
            target_corp="00877059",
            as_of=AS_OF_2025,
            source_id="rcept-2025",
        )
        upsert_owns(graph, [cand_2024, cand_2025], universe)
        assert _owns_count(graph) == 2

    def test_no_loadable_candidates_leaves_graph_unchanged(self, graph: Neo4jClient) -> None:
        universe = self._seed_universe(graph)
        candidates = [
            _owns_candidate(source_corp=None, source_text="국민연금", target_corp="00126380"),
        ]
        stats = upsert_owns(graph, candidates, universe)
        assert stats.loaded == 0
        assert _owns_count(graph) == 0
