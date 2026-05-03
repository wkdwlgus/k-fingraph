"""Integration tests for Neo4jClient against a real Neo4j container."""

from __future__ import annotations

import pytest

from k_fingraph.graph.client import Neo4jClient


@pytest.mark.integration
class TestNeo4jClient:
    def test_ping_returns_true(self, neo4j_client: Neo4jClient) -> None:
        assert neo4j_client.ping() is True

    def test_session_runs_basic_query(self, neo4j_client: Neo4jClient) -> None:
        with neo4j_client.session() as session:
            record = session.run("RETURN $x AS value", x=42).single()
        assert record is not None
        assert record["value"] == 42
