"""Shared fixtures for integration tests.

`neo4j_client` boots a Neo4j 5.x container once per test session and yields a
`Neo4jClient` connected to it. Each test that uses the client is responsible
for cleaning up data it wrote (the `clean_neo4j` fixture below provides a
DETACH DELETE before each test).

If Docker is not available locally, every integration test is skipped rather
than failing — this keeps `uv run pytest -m "not e2e"` green on machines
without Docker, while CI still exercises the full suite.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from k_fingraph.graph.client import Neo4jClient

NEO4J_IMAGE = "neo4j:5.23"


@pytest.fixture(scope="session")
def neo4j_client() -> Iterator[Neo4jClient]:
    try:
        from testcontainers.neo4j import Neo4jContainer
    except ImportError:
        pytest.skip("testcontainers[neo4j] not installed")

    try:
        container = Neo4jContainer(NEO4J_IMAGE)
        container.start()
    except Exception as exc:  # docker daemon down, image pull failure, etc.
        pytest.skip(f"Neo4j testcontainer unavailable: {exc}")

    try:
        client = Neo4jClient(
            uri=container.get_connection_url(),
            user=container.username,
            password=container.password,
        )
        try:
            yield client
        finally:
            client.close()
    finally:
        container.stop()


@pytest.fixture
def clean_neo4j(neo4j_client: Neo4jClient) -> Neo4jClient:
    """Wipe nodes/edges before the test runs. Constraints/indexes survive."""
    with neo4j_client.session() as session:
        session.run("MATCH (n) DETACH DELETE n").consume()
    return neo4j_client
