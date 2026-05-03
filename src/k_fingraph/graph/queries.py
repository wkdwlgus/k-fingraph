"""Read-side Cypher queries for v0 (Company + OWNS).

These are the building blocks Layer 2 workflows and the Streamlit interface
consume. Each query is documented with its scope decision so future-you can
see what was deliberately left out.

v0 scope decisions (parked in tasks/backlog.md for v1 / v3 re-evaluation):

* `get_subsidiaries` returns 1-hop only. Transitive descendants
  (손자회사 / 증손회사) belong to the v3 shock simulator and need a
  cycle-safe traversal — see backlog v3.
* `get_within_2hop` ignores edge direction. Streamlit visualization wants
  both parents and children of the focal node. Direction-aware variants
  belong to specific workflows in v3+.
* `as_of` dedupe: when multiple OWNS edges exist for the same
  (source, target, source_id) but different `as_of`, we surface only the
  latest one. v0 ingests a single annual cycle so this almost never fires;
  the policy itself (latest collapse vs. time-slice) gets re-evaluated when
  v1 introduces real time-series data — see backlog v1.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from neo4j.exceptions import Neo4jError

from k_fingraph.errors import GraphWriteError
from k_fingraph.graph.client import Neo4jClient
from k_fingraph.schemas.graph import RelationType
from k_fingraph.schemas.queries import (
    CommonParentRow,
    Subgraph,
    SubgraphEdge,
    SubgraphNode,
    SubsidiaryRow,
)

logger = logging.getLogger(__name__)


_GET_SUBSIDIARIES_CYPHER = """
MATCH (p:Company {ticker: $ticker})-[r:OWNS]->(c:Company)
WHERE r.relation_type IN $relation_types
WITH p, c, r ORDER BY r.as_of DESC
WITH p, c, head(collect(r)) AS r
RETURN p.ticker AS parent_ticker,
       p.name_kr AS parent_name,
       c.ticker AS child_ticker,
       c.name_kr AS child_name,
       r.stake_pct AS stake_pct,
       r.relation_type AS relation_type,
       r.as_of AS as_of,
       r.source_id AS source_id
ORDER BY stake_pct DESC, child_ticker ASC
"""


def get_subsidiaries(
    client: Neo4jClient,
    ticker: str,
    *,
    relation_types: Sequence[RelationType] = (RelationType.SUBSIDIARY,),
) -> list[SubsidiaryRow]:
    """Direct (1-hop) OWNS children of `ticker`, filtered by relation_type.

    Default returns SUBSIDIARY only (≥50% per ADR 0006). Pass an explicit
    sequence to widen — e.g. `(SUBSIDIARY, AFFILIATE)`.

    For multiple disclosures of the same (parent, child) pair across time,
    only the row with the latest `as_of` is returned (see module docstring).
    """
    rt_values = [rt.value for rt in relation_types]
    try:
        with client.session() as session:
            records = session.run(
                _GET_SUBSIDIARIES_CYPHER,
                ticker=ticker,
                relation_types=rt_values,
            ).data()
    except Neo4jError as exc:
        raise GraphWriteError(f"get_subsidiaries failed: {exc}") from exc

    return [
        SubsidiaryRow(
            parent_ticker=row["parent_ticker"],
            parent_name=row["parent_name"],
            child_ticker=row["child_ticker"],
            child_name=row["child_name"],
            stake_pct=row["stake_pct"],
            relation_type=RelationType(row["relation_type"]),
            as_of=row["as_of"].to_native(),
            source_id=row["source_id"],
        )
        for row in records
    ]


_FIND_COMMON_PARENTS_CYPHER = """
MATCH (p:Company)-[ra:OWNS]->(:Company {ticker: $ticker_a})
WITH p, ra ORDER BY ra.as_of DESC
WITH p, head(collect(ra)) AS ra
MATCH (p)-[rb:OWNS]->(:Company {ticker: $ticker_b})
WITH p, ra, rb ORDER BY rb.as_of DESC
WITH p, ra, head(collect(rb)) AS rb
RETURN p.ticker AS parent_ticker,
       p.name_kr AS parent_name,
       ra.stake_pct AS stake_to_a,
       rb.stake_pct AS stake_to_b,
       ra.relation_type AS relation_type_a,
       rb.relation_type AS relation_type_b
ORDER BY stake_to_a + stake_to_b DESC, parent_ticker ASC
"""


def find_common_parents(
    client: Neo4jClient,
    ticker_a: str,
    ticker_b: str,
) -> list[CommonParentRow]:
    """Companies that directly own BOTH `ticker_a` and `ticker_b` via OWNS.

    1-hop on both legs (no transitive ancestor search). Returns empty list
    when either ticker is unknown or no shared parent exists.
    """
    try:
        with client.session() as session:
            records = session.run(
                _FIND_COMMON_PARENTS_CYPHER,
                ticker_a=ticker_a,
                ticker_b=ticker_b,
            ).data()
    except Neo4jError as exc:
        raise GraphWriteError(f"find_common_parents failed: {exc}") from exc

    return [
        CommonParentRow(
            parent_ticker=row["parent_ticker"],
            parent_name=row["parent_name"],
            stake_to_a=row["stake_to_a"],
            stake_to_b=row["stake_to_b"],
            relation_type_a=RelationType(row["relation_type_a"]),
            relation_type_b=RelationType(row["relation_type_b"]),
        )
        for row in records
    ]


_GET_2HOP_NODES_CYPHER = """
MATCH (center:Company {ticker: $ticker})
OPTIONAL MATCH (center)-[:OWNS*1..2]-(other:Company)
WITH center, [n IN collect(DISTINCT other) WHERE n IS NOT NULL] AS others
RETURN center.ticker AS center_ticker,
       center.name_kr AS center_name,
       [n IN others | {ticker: n.ticker, name: n.name_kr}] AS others
"""

# Edges among the induced subgraph. We pull them in a separate query so that
# the latest-as_of dedupe can be expressed cleanly per (s, t) pair.
_GET_2HOP_EDGES_CYPHER = """
MATCH (s:Company)-[r:OWNS]->(t:Company)
WHERE s.ticker IN $tickers AND t.ticker IN $tickers
WITH s, t, r ORDER BY r.as_of DESC
WITH s, t, head(collect(r)) AS r
RETURN s.ticker AS source_ticker,
       t.ticker AS target_ticker,
       r.stake_pct AS stake_pct,
       r.relation_type AS relation_type,
       r.as_of AS as_of
"""


def get_within_2hop(client: Neo4jClient, ticker: str) -> Subgraph:
    """Subgraph of `ticker` plus all OWNS-reachable Companies within 2 hops.

    Direction is ignored (parents AND children are included), since the
    primary consumer is the Streamlit visualization. An isolated center
    yields nodes=[center], edges=[]. Unknown ticker yields an empty Subgraph.
    """
    try:
        with client.session() as session:
            node_record = session.run(
                _GET_2HOP_NODES_CYPHER,
                ticker=ticker,
            ).single()
            if node_record is None:
                return Subgraph(nodes=[], edges=[])

            center_ticker = node_record["center_ticker"]
            center_name = node_record["center_name"]
            others = node_record["others"]

            tickers = [center_ticker, *(o["ticker"] for o in others)]
            edge_records = session.run(
                _GET_2HOP_EDGES_CYPHER,
                tickers=tickers,
            ).data()
    except Neo4jError as exc:
        raise GraphWriteError(f"get_within_2hop failed: {exc}") from exc

    nodes = [
        SubgraphNode(ticker=center_ticker, name=center_name, is_center=True),
        *(SubgraphNode(ticker=o["ticker"], name=o["name"], is_center=False) for o in others),
    ]
    edges = [
        SubgraphEdge(
            source_ticker=row["source_ticker"],
            target_ticker=row["target_ticker"],
            stake_pct=row["stake_pct"],
            relation_type=RelationType(row["relation_type"]),
            as_of=row["as_of"].to_native(),
        )
        for row in edge_records
    ]
    return Subgraph(nodes=nodes, edges=edges)
