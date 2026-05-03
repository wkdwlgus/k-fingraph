"""Unit tests for the pure search logic in interfaces._company_index."""

from __future__ import annotations

import pytest

from k_fingraph.interfaces._company_index import CompanyRef, search_companies


def _ref(ticker: str, name: str) -> CompanyRef:
    return CompanyRef(
        ticker=ticker,
        name_kr=name,
        name_normalized=name.replace(" ", "").replace("(주)", ""),
    )


@pytest.fixture
def index() -> list[CompanyRef]:
    return [
        _ref("005930", "삼성전자"),
        _ref("207940", "삼성바이오로직스"),
        _ref("051910", "LG화학"),
        _ref("373220", "LG에너지솔루션"),
        _ref("000660", "SK하이닉스"),
    ]


@pytest.mark.unit
class TestSearchCompanies:
    def test_empty_query_returns_first_n(self, index: list[CompanyRef]) -> None:
        result = search_companies(index, "", limit=3)
        assert [r.ticker for r in result] == ["005930", "207940", "051910"]

    def test_exact_ticker_wins_over_name(self, index: list[CompanyRef]) -> None:
        # 005930 is an exact ticker; "삼성" would also name-match it,
        # but exact ticker should be the only result here.
        result = search_companies(index, "005930")
        assert [r.ticker for r in result] == ["005930"]

    def test_ticker_prefix_match(self, index: list[CompanyRef]) -> None:
        result = search_companies(index, "0509")
        assert result == []
        result = search_companies(index, "0519")
        assert [r.ticker for r in result] == ["051910"]

    def test_name_substring_match_whitespace_insensitive(self, index: list[CompanyRef]) -> None:
        result = search_companies(index, "삼성")
        assert [r.ticker for r in result] == ["005930", "207940"]

    def test_name_match_finds_lg(self, index: list[CompanyRef]) -> None:
        result = search_companies(index, "LG")
        assert {r.ticker for r in result} == {"051910", "373220"}

    def test_no_match_returns_empty(self, index: list[CompanyRef]) -> None:
        assert search_companies(index, "존재하지않음") == []

    def test_limit_caps_results(self, index: list[CompanyRef]) -> None:
        result = search_companies(index, "삼성", limit=1)
        assert len(result) == 1

    def test_priority_order_ticker_then_name(self) -> None:
        # Construct: "100"-prefix ticker AND a separate company whose name
        # contains "100". Prefix match should come before name match.
        idx = [
            _ref("100200", "AlphaCo"),
            _ref("999999", "100주년"),
        ]
        result = search_companies(idx, "100")
        assert [r.ticker for r in result] == ["100200", "999999"]
