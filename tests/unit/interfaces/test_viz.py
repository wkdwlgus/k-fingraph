"""Unit tests for interfaces._viz.

These poke at the Plotly Figure structure rather than rendered pixels:
the figure must contain the right number of traces, the right annotations
(one arrow per directed edge), and a marker for every node — including the
center node tagged with the gold highlight color.
"""

from __future__ import annotations

from datetime import date

import pytest

from k_fingraph.interfaces._viz import _CENTER_NODE_COLOR, subgraph_to_plotly_figure
from k_fingraph.schemas.graph import RelationType
from k_fingraph.schemas.queries import Subgraph, SubgraphEdge, SubgraphNode

AS_OF = date(2024, 12, 31)


def _node(ticker: str, *, is_center: bool = False) -> SubgraphNode:
    return SubgraphNode(ticker=ticker, name=f"Co-{ticker}", is_center=is_center)


def _edge(src: str, tgt: str, *, rel: RelationType, stake: float) -> SubgraphEdge:
    return SubgraphEdge(
        source_ticker=src,
        target_ticker=tgt,
        stake_pct=stake,
        relation_type=rel,
        as_of=AS_OF,
    )


@pytest.mark.unit
class TestSubgraphToPlotlyFigure:
    def test_empty_subgraph_yields_empty_figure(self) -> None:
        fig = subgraph_to_plotly_figure(Subgraph(nodes=[], edges=[]))
        assert fig.data == ()
        assert fig.layout.annotations in ((), None)

    def test_isolated_center_only(self) -> None:
        sub = Subgraph(nodes=[_node("000001", is_center=True)], edges=[])
        fig = subgraph_to_plotly_figure(sub)
        # No edges → only the node trace.
        assert len(fig.data) == 1
        node_trace = fig.data[0]
        assert list(node_trace.x) == [0.0]
        assert list(node_trace.y) == [0.0]
        # Center color shows up in the marker.
        assert _CENTER_NODE_COLOR in tuple(node_trace.marker.color)
        assert fig.layout.annotations in ((), None)

    def test_three_node_chain_has_arrows_and_node_trace(self) -> None:
        # A → B → C, two SUBSIDIARY edges
        sub = Subgraph(
            nodes=[
                _node("A", is_center=True),
                _node("B"),
                _node("C"),
            ],
            edges=[
                _edge("A", "B", rel=RelationType.SUBSIDIARY, stake=80.0),
                _edge("B", "C", rel=RelationType.SUBSIDIARY, stake=60.0),
            ],
        )
        fig = subgraph_to_plotly_figure(sub)

        # 1 line trace + 1 hover-marker trace per relation_type, + 1 node trace.
        # SUBSIDIARY only here → 2 + 1 = 3.
        assert len(fig.data) == 3

        # One arrow annotation per directed edge.
        arrow_annotations = [a for a in fig.layout.annotations if a.showarrow]
        assert len(arrow_annotations) == 2

        # Node trace is the last; it carries one marker per node.
        node_trace = fig.data[-1]
        assert len(node_trace.x) == 3
        assert "Co-A" in tuple(node_trace.text)

    def test_separates_traces_per_relation_type(self) -> None:
        # Two relation_types → 2 line traces + 2 hover traces + 1 node trace = 5
        sub = Subgraph(
            nodes=[_node("A", is_center=True), _node("B"), _node("C")],
            edges=[
                _edge("A", "B", rel=RelationType.SUBSIDIARY, stake=80.0),
                _edge("A", "C", rel=RelationType.AFFILIATE, stake=20.0),
            ],
        )
        fig = subgraph_to_plotly_figure(sub)
        assert len(fig.data) == 5

    def test_center_node_has_distinct_color(self) -> None:
        sub = Subgraph(
            nodes=[_node("A", is_center=True), _node("B")],
            edges=[_edge("A", "B", rel=RelationType.SUBSIDIARY, stake=80.0)],
        )
        fig = subgraph_to_plotly_figure(sub)
        node_trace = fig.data[-1]
        colors = list(node_trace.marker.color)
        # Exactly one node colored as center.
        assert colors.count(_CENTER_NODE_COLOR) == 1
