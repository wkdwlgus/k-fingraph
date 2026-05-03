"""Render a `Subgraph` as a Plotly Figure for embedding in Streamlit.

Layout is computed with networkx `spring_layout` using a fixed seed so the
same Subgraph always renders identically — useful for snapshot-style tests
and so re-runs of the app don't shuffle nodes around between clicks.

Edges are colored by relation_type and annotated with the stake_pct so the
graph carries enough signal without a separate legend lookup. The center
node is highlighted (color + size).
"""

from __future__ import annotations

from typing import Any

import networkx as nx
import plotly.graph_objects as go

from k_fingraph.schemas.graph import RelationType
from k_fingraph.schemas.queries import Subgraph

_LAYOUT_SEED = 42

_RELATION_COLORS: dict[RelationType, str] = {
    RelationType.SUBSIDIARY: "#d62728",  # strong red — high control
    RelationType.AFFILIATE: "#ff7f0e",  # orange — partial influence
    RelationType.OTHER: "#7f7f7f",  # grey — weak signal
}

_CENTER_NODE_COLOR = "#ffd700"  # gold
_OTHER_NODE_COLOR = "#1f77b4"  # plotly default blue
_CENTER_NODE_SIZE = 28
_OTHER_NODE_SIZE = 18


def subgraph_to_plotly_figure(subgraph: Subgraph) -> go.Figure:
    """Build a Plotly Figure from `subgraph`. Empty subgraphs yield an empty figure."""
    fig = go.Figure()
    fig.update_layout(
        showlegend=False,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        xaxis={"visible": False},
        yaxis={"visible": False},
        plot_bgcolor="white",
        height=600,
    )

    if not subgraph.nodes:
        return fig

    graph = nx.DiGraph()
    for node in subgraph.nodes:
        graph.add_node(node.ticker, name=node.name, is_center=node.is_center)
    for edge in subgraph.edges:
        graph.add_edge(
            edge.source_ticker,
            edge.target_ticker,
            stake_pct=edge.stake_pct,
            relation_type=edge.relation_type,
            as_of=edge.as_of,
        )

    if graph.number_of_nodes() == 1:
        positions: dict[str, tuple[float, float]] = {next(iter(graph.nodes)): (0.0, 0.0)}
    else:
        positions = nx.spring_layout(graph, seed=_LAYOUT_SEED)

    # One Scatter trace per relation_type so the line color can be set globally
    # for that trace (Plotly does not allow per-segment colors on a single
    # line trace without a workaround).
    edges_by_rel: dict[RelationType, list[tuple[str, str, dict[str, Any]]]] = {}
    for src, tgt, data in graph.edges(data=True):
        rel = data["relation_type"]
        edges_by_rel.setdefault(rel, []).append((src, tgt, data))

    for rel, items in edges_by_rel.items():
        xs: list[float | None] = []
        ys: list[float | None] = []
        hover_x: list[float] = []
        hover_y: list[float] = []
        hover_text: list[str] = []
        for src, tgt, data in items:
            x0, y0 = positions[src]
            x1, y1 = positions[tgt]
            xs.extend([x0, x1, None])
            ys.extend([y0, y1, None])
            hover_x.append((x0 + x1) / 2)
            hover_y.append((y0 + y1) / 2)
            hover_text.append(
                f"{graph.nodes[src]['name']} → {graph.nodes[tgt]['name']}<br>"
                f"{rel.value} {data['stake_pct']:.2f}%<br>"
                f"as_of {data['as_of'].isoformat()}"
            )
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line={"color": _RELATION_COLORS[rel], "width": 2},
                hoverinfo="skip",
                name=rel.value,
            )
        )
        # Invisible midpoint markers carry the hover text — Plotly line traces
        # don't support per-segment hover, so we overlay a marker layer.
        fig.add_trace(
            go.Scatter(
                x=hover_x,
                y=hover_y,
                mode="markers",
                marker={"size": 12, "color": _RELATION_COLORS[rel], "opacity": 0.0},
                hoverinfo="text",
                hovertext=hover_text,
                name=f"{rel.value} hover",
            )
        )
        # Direction arrows as annotations (one per edge).
        for src, tgt, _data in items:
            x0, y0 = positions[src]
            x1, y1 = positions[tgt]
            fig.add_annotation(
                x=x1,
                y=y1,
                ax=x0,
                ay=y0,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=3,
                arrowsize=1.2,
                arrowwidth=1.5,
                arrowcolor=_RELATION_COLORS[rel],
                standoff=14,
            )

    node_x: list[float] = []
    node_y: list[float] = []
    node_text: list[str] = []
    node_hover: list[str] = []
    node_color: list[str] = []
    node_size: list[int] = []
    for ticker, data in graph.nodes(data=True):
        x, y = positions[ticker]
        node_x.append(x)
        node_y.append(y)
        node_text.append(data["name"])
        node_hover.append(f"{data['name']}<br>ticker {ticker}")
        node_color.append(_CENTER_NODE_COLOR if data["is_center"] else _OTHER_NODE_COLOR)
        node_size.append(_CENTER_NODE_SIZE if data["is_center"] else _OTHER_NODE_SIZE)

    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=node_text,
            textposition="top center",
            hoverinfo="text",
            hovertext=node_hover,
            marker={
                "size": node_size,
                "color": node_color,
                "line": {"width": 1.5, "color": "#333333"},
            },
            name="nodes",
        )
    )

    return fig
