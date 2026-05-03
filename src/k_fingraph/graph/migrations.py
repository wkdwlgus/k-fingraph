"""Schema DDL for the v0 graph.

Mirrors the constraint/index block in docs/schema.md verbatim. Each statement
uses `IF NOT EXISTS` so `apply_schema()` is safe to re-run on every startup.
"""

from __future__ import annotations

import logging

from neo4j.exceptions import Neo4jError

from k_fingraph.errors import GraphWriteError
from k_fingraph.graph.client import Neo4jClient

logger = logging.getLogger(__name__)

SCHEMA_STATEMENTS: tuple[str, ...] = (
    "CREATE CONSTRAINT company_ticker IF NOT EXISTS FOR (c:Company) REQUIRE c.ticker IS UNIQUE",
    "CREATE CONSTRAINT company_corp_code IF NOT EXISTS "
    "FOR (c:Company) REQUIRE c.corp_code IS UNIQUE",
    "CREATE INDEX company_name_normalized IF NOT EXISTS FOR (c:Company) ON (c.name_normalized)",
)


def apply_schema(client: Neo4jClient) -> None:
    """Apply every DDL statement in `SCHEMA_STATEMENTS`. Idempotent."""
    try:
        with client.session() as session:
            for stmt in SCHEMA_STATEMENTS:
                session.run(stmt).consume()
                logger.info("Applied schema statement: %s", stmt)
    except Neo4jError as exc:
        raise GraphWriteError(f"Schema migration failed: {exc}") from exc
