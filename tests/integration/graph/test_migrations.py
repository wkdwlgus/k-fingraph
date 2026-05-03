"""Integration tests for schema migrations against a real Neo4j container."""

from __future__ import annotations

import pytest

from k_fingraph.graph.client import Neo4jClient
from k_fingraph.graph.migrations import SCHEMA_STATEMENTS, apply_schema


def _constraint_names(client: Neo4jClient) -> set[str]:
    with client.session() as session:
        records = list(session.run("SHOW CONSTRAINTS YIELD name"))
    return {r["name"] for r in records}


def _index_names(client: Neo4jClient) -> set[str]:
    with client.session() as session:
        records = list(session.run("SHOW INDEXES YIELD name"))
    return {r["name"] for r in records}


@pytest.mark.integration
class TestApplySchema:
    def test_creates_all_constraints_and_indexes(self, neo4j_client: Neo4jClient) -> None:
        apply_schema(neo4j_client)

        constraints = _constraint_names(neo4j_client)
        indexes = _index_names(neo4j_client)

        assert "company_ticker" in constraints
        assert "company_corp_code" in constraints
        assert "company_name_normalized" in indexes

    def test_idempotent_on_repeat(self, neo4j_client: Neo4jClient) -> None:
        apply_schema(neo4j_client)
        before = _constraint_names(neo4j_client) | _index_names(neo4j_client)
        # Re-applying must neither error nor create duplicates.
        apply_schema(neo4j_client)
        after = _constraint_names(neo4j_client) | _index_names(neo4j_client)
        assert before == after

    def test_schema_statement_count_matches_objects(self, neo4j_client: Neo4jClient) -> None:
        apply_schema(neo4j_client)
        names = _constraint_names(neo4j_client) | _index_names(neo4j_client)
        # Every DDL we ship should produce at least one named object.
        assert len(SCHEMA_STATEMENTS) <= len(names)
