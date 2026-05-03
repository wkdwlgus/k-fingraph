"""In-memory ticker / name index loaded from the Company nodes.

KOSPI 200 fits comfortably in memory and the Streamlit selectbox needs the
full list, so we read everything up front and search in Python. When the
universe expands (v0.5: KOSPI + KOSDAQ ~2,400) the load is still O(seconds).
A TTL / cache invalidation policy is parked for v0.5 — see backlog.
"""

from __future__ import annotations

from dataclasses import dataclass

from neo4j.exceptions import Neo4jError

from k_fingraph.errors import GraphWriteError
from k_fingraph.graph.client import Neo4jClient


@dataclass(frozen=True)
class CompanyRef:
    ticker: str
    name_kr: str
    name_normalized: str

    @property
    def display(self) -> str:
        return f"{self.name_kr} ({self.ticker})"


_LOAD_CYPHER = """
MATCH (c:Company)
RETURN c.ticker AS ticker,
       c.name_kr AS name_kr,
       c.name_normalized AS name_normalized
ORDER BY c.name_kr ASC
"""


def load_company_index(client: Neo4jClient) -> list[CompanyRef]:
    """Read all Company nodes into a list, sorted by name_kr."""
    try:
        with client.session() as session:
            records = session.run(_LOAD_CYPHER).data()
    except Neo4jError as exc:
        raise GraphWriteError(f"Company index load failed: {exc}") from exc
    return [
        CompanyRef(
            ticker=row["ticker"],
            name_kr=row["name_kr"],
            name_normalized=row["name_normalized"],
        )
        for row in records
    ]


def search_companies(
    index: list[CompanyRef],
    query: str,
    limit: int = 20,
) -> list[CompanyRef]:
    """Filter `index` by query string. Empty query returns the first `limit` rows.

    Match priority:
      1. ticker exact match
      2. ticker prefix
      3. name_normalized substring (whitespace-insensitive)
    Results within each tier preserve the input order (alphabetical by name_kr).
    """
    if not query:
        return index[:limit]

    q = query.strip()
    q_norm = q.replace(" ", "")
    exact_ticker: list[CompanyRef] = []
    prefix_ticker: list[CompanyRef] = []
    name_match: list[CompanyRef] = []

    for ref in index:
        if ref.ticker == q:
            exact_ticker.append(ref)
        elif ref.ticker.startswith(q):
            prefix_ticker.append(ref)
        elif q_norm and q_norm in ref.name_normalized:
            name_match.append(ref)

    merged = exact_ticker + prefix_ticker + name_match
    return merged[:limit]
