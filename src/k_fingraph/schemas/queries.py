"""Result models for graph read queries (graph/queries.py).

These mirror the v0 graph schema (Company + OWNS) but project only the fields
each query surfaces, so that consumers (Streamlit, future workflows) do not
need to know the wire shape of Neo4j Records.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from k_fingraph.schemas.graph import RelationType


class SubsidiaryRow(BaseModel):
    """One direct (1-hop) OWNS edge from `parent_ticker` to `child_ticker`."""

    parent_ticker: str
    parent_name: str
    child_ticker: str
    child_name: str
    stake_pct: float
    relation_type: RelationType
    as_of: date
    source_id: str


class CommonParentRow(BaseModel):
    """A Company that directly owns both ticker_a and ticker_b."""

    parent_ticker: str
    parent_name: str
    stake_to_a: float
    stake_to_b: float
    relation_type_a: RelationType
    relation_type_b: RelationType


class SubgraphNode(BaseModel):
    ticker: str
    name: str
    is_center: bool


class SubgraphEdge(BaseModel):
    source_ticker: str
    target_ticker: str
    stake_pct: float
    relation_type: RelationType
    as_of: date


class Subgraph(BaseModel):
    """Result of `get_within_2hop` — a small induced subgraph for visualization."""

    nodes: list[SubgraphNode]
    edges: list[SubgraphEdge]
