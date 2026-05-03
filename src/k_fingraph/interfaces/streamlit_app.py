"""Streamlit workbench for v0 graph queries.

Run with:
    uv run streamlit run src/k_fingraph/interfaces/streamlit_app.py

Three workflows are exposed in the sidebar; each pulls from the OWNS subgraph
loaded in v0 (KOSPI 200 ↔ KOSPI 200, ADR 0007). Streamlit caches the Neo4j
driver (`@st.cache_resource`) and the company index (`@st.cache_data`) so the
sidebar selectbox renders instantly on every rerun.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from k_fingraph.graph.client import Neo4jClient
from k_fingraph.graph.queries import (
    find_common_parents,
    get_subsidiaries,
    get_within_2hop,
)
from k_fingraph.interfaces._company_index import (
    CompanyRef,
    load_company_index,
)
from k_fingraph.interfaces._viz import subgraph_to_plotly_figure
from k_fingraph.schemas.graph import RelationType

_WORKFLOW_SUBSIDIARIES = "자회사 조회 (get_subsidiaries)"
_WORKFLOW_COMMON_PARENTS = "공통 부모 찾기 (find_common_parents)"
_WORKFLOW_2HOP = "2-hop 부분그래프 (get_within_2hop)"


@st.cache_resource
def _get_client() -> Neo4jClient:
    return Neo4jClient.from_settings()


@st.cache_data(show_spinner="회사 인덱스 로드 중…")
def _get_company_index() -> list[CompanyRef]:
    return load_company_index(_get_client())


def _ticker_selectbox(
    label: str,
    key: str,
    *,
    default_index: int | None = 0,
    placeholder: str = "종목을 선택하세요",
) -> str | None:
    """Selectbox of companies. `default_index=None` starts unselected and
    returns None until the user picks — used by panels where any default
    pair would imply a meaningless query (e.g. find_common_parents)."""
    index = _get_company_index()
    options = [ref.ticker for ref in index]
    label_map = {ref.ticker: ref.display for ref in index}
    return st.selectbox(
        label,
        options=options,
        index=default_index,
        format_func=lambda t: label_map.get(t, t),
        key=key,
        placeholder=placeholder,
    )


def _render_subsidiaries_panel() -> None:
    st.header("자회사 조회")
    st.caption(
        "선택한 종목이 직접 보유한 자회사(1-hop OWNS). "
        "기본은 SUBSIDIARY(≥50%, ADR 0006)만, 체크박스로 AFFILIATE 포함 가능."
    )
    ticker = _ticker_selectbox("부모 회사", key="subs_ticker")
    include_affiliate = st.checkbox("AFFILIATE도 포함", value=False)

    if ticker is None:
        return

    rels: tuple[RelationType, ...] = (RelationType.SUBSIDIARY,)
    if include_affiliate:
        rels = (RelationType.SUBSIDIARY, RelationType.AFFILIATE)

    rows = get_subsidiaries(_get_client(), ticker, relation_types=rels)
    if not rows:
        st.info("해당 종목의 자회사가 그래프에 없습니다.")
        return

    df = pd.DataFrame(
        [
            {
                "child_ticker": r.child_ticker,
                "child_name": r.child_name,
                "stake_pct": r.stake_pct,
                "relation_type": r.relation_type.value,
                "as_of": r.as_of,
                "source_id (DART rcept_no)": r.source_id,
            }
            for r in rows
        ]
    )
    st.dataframe(df, hide_index=True, use_container_width=True)


def _render_common_parents_panel() -> None:
    st.header("공통 부모 찾기")
    st.caption("두 종목을 모두 직접 보유한 회사를 찾습니다 (1-hop, 양쪽 모두 OWNS).")

    col_a, col_b = st.columns(2)
    with col_a:
        ticker_a = _ticker_selectbox("종목 A", key="cp_a", default_index=None)
    with col_b:
        ticker_b = _ticker_selectbox("종목 B", key="cp_b", default_index=None)

    if ticker_a is None or ticker_b is None:
        st.caption("두 종목을 모두 선택하면 결과가 표시됩니다.")
        return

    if ticker_a == ticker_b:
        st.warning("서로 다른 두 종목을 선택하세요.")
        return

    rows = find_common_parents(_get_client(), ticker_a, ticker_b)
    if not rows:
        st.info("두 종목을 동시에 직접 보유한 회사가 그래프에 없습니다.")
        return

    df = pd.DataFrame(
        [
            {
                "parent_ticker": r.parent_ticker,
                "parent_name": r.parent_name,
                "stake_to_a": r.stake_to_a,
                "stake_to_b": r.stake_to_b,
                "relation_type_a": r.relation_type_a.value,
                "relation_type_b": r.relation_type_b.value,
            }
            for r in rows
        ]
    )
    st.dataframe(df, hide_index=True, use_container_width=True)


def _render_2hop_panel() -> None:
    st.header("2-hop 부분그래프")
    st.caption(
        "선택한 종목과 OWNS로 2-hop 안에 닿는 모든 회사를 한 그래프로 묶습니다 "
        "(방향 무시 — 모회사·자회사·계열사·지주 모두 포함)."
    )
    ticker = _ticker_selectbox("중심 종목", key="hop_ticker")
    if ticker is None:
        return
    subgraph = get_within_2hop(_get_client(), ticker)

    if not subgraph.nodes:
        st.info("해당 종목이 그래프에 없습니다.")
        return

    st.write(f"노드 {len(subgraph.nodes)}개 · 엣지 {len(subgraph.edges)}개")
    fig = subgraph_to_plotly_figure(subgraph)
    st.plotly_chart(fig, use_container_width=True)

    if subgraph.edges:
        with st.expander("엣지 상세"):
            df = pd.DataFrame(
                [
                    {
                        "source": e.source_ticker,
                        "target": e.target_ticker,
                        "stake_pct": e.stake_pct,
                        "relation_type": e.relation_type.value,
                        "as_of": e.as_of,
                    }
                    for e in subgraph.edges
                ]
            )
            st.dataframe(df, hide_index=True, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="K-FinGraph 워크벤치 v0", layout="wide")
    st.title("K-FinGraph 워크벤치")
    st.caption(
        "KOSPI 200 + DART 지분 관계 그래프 위에서 결정론적 쿼리 3종을 실행합니다. "
        "데이터: 2024년 사업보고서 기준 (ADR 0007)."
    )

    workflow = st.sidebar.radio(
        "워크플로우",
        options=[_WORKFLOW_SUBSIDIARIES, _WORKFLOW_COMMON_PARENTS, _WORKFLOW_2HOP],
    )
    st.sidebar.markdown("---")
    st.sidebar.caption(
        f"Companies: {len(_get_company_index())} · "
        "출처는 모든 결과에 DART 공시번호(`source_id`)로 표시됩니다."
    )

    if workflow == _WORKFLOW_SUBSIDIARIES:
        _render_subsidiaries_panel()
    elif workflow == _WORKFLOW_COMMON_PARENTS:
        _render_common_parents_panel()
    else:
        _render_2hop_panel()


if __name__ == "__main__":
    main()
