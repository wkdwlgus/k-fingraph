"""Thin wrapper around the Neo4j Python driver.

Connection settings are read from `k_fingraph.config.Settings` so that the same
codebase runs against Aura today and a Docker instance later (ADR 0002) by
swapping environment variables only. All driver-level exceptions surfacing out
of the wrapper are converted to `GraphWriteError` so callers depend on a single
domain exception family.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Self

from neo4j import Driver, GraphDatabase, Session
from neo4j.exceptions import Neo4jError

from k_fingraph.config import get_settings
from k_fingraph.errors import GraphWriteError

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Owns a Neo4j driver and hands out sessions bound to a fixed database."""

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j",
    ) -> None:
        self._uri = uri
        self._database = database
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    @classmethod
    def from_settings(cls) -> Self:
        settings = get_settings()
        return cls(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )

    @property
    def database(self) -> str:
        return self._database

    def close(self) -> None:
        self._driver.close()

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self._driver.session(database=self._database)
        try:
            yield session
        finally:
            session.close()

    def ping(self) -> bool:
        """Sanity check — runs `RETURN 1` and returns True on success.

        Wraps any driver error into GraphWriteError so callers don't need to
        import neo4j-specific exception types.
        """
        try:
            with self.session() as session:
                record = session.run("RETURN 1 AS ok").single()
        except Neo4jError as exc:
            logger.exception("Neo4j ping failed: %s", exc)
            raise GraphWriteError(f"Neo4j ping failed: {exc}") from exc
        return record is not None and record["ok"] == 1

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()
