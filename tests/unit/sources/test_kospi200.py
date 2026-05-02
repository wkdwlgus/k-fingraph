"""Unit tests for the KOSPI 200 loader and DART corp_code mapper."""

from pathlib import Path

import pytest

from k_fingraph.schemas.dart import CorpCodeRecord
from k_fingraph.schemas.kospi200 import Kospi200Constituent
from k_fingraph.sources.kospi200 import (
    Kospi200LoadError,
    load_kospi200_csv,
    map_to_corp_codes,
)

FIXTURE = Path(__file__).parent.parent.parent / "fixtures" / "krx" / "kospi200_sample.csv"


@pytest.mark.unit
def test_load_csv_returns_all_rows() -> None:
    rows = load_kospi200_csv(FIXTURE)
    assert len(rows) == 5
    assert rows[0].ticker == "005930"
    assert rows[0].name == "삼성전자"


@pytest.mark.unit
def test_load_csv_skips_blank_lines(tmp_path: Path) -> None:
    csv_path = tmp_path / "with_blanks.csv"
    csv_path.write_text(
        "ticker,name\n005930,삼성전자\n,\n000660,SK하이닉스\n",
        encoding="utf-8",
    )
    rows = load_kospi200_csv(csv_path)
    assert [r.ticker for r in rows] == ["005930", "000660"]


@pytest.mark.unit
def test_load_csv_missing_required_column_raises(tmp_path: Path) -> None:
    csv_path = tmp_path / "wrong_cols.csv"
    csv_path.write_text("symbol,company\n005930,삼성전자\n", encoding="utf-8")
    with pytest.raises(Kospi200LoadError, match="must have columns"):
        load_kospi200_csv(csv_path)


@pytest.mark.unit
def test_map_keeps_unmatched_with_none() -> None:
    constituents = [
        Kospi200Constituent(ticker="005930", name="삼성전자"),
        Kospi200Constituent(ticker="000660", name="SK하이닉스"),
        Kospi200Constituent(ticker="005380", name="현대차"),
        Kospi200Constituent(ticker="373220", name="LG에너지솔루션"),
        Kospi200Constituent(ticker="999999", name="존재하지않는종목"),  # unmatched
    ]
    corp_codes = [
        CorpCodeRecord(
            corp_code="00126380",
            corp_name="삼성전자",
            stock_code="005930",
            modify_date="20240101",
        ),
        CorpCodeRecord(
            corp_code="00164779",
            corp_name="SK하이닉스",
            stock_code="000660",
            modify_date="20240101",
        ),
        CorpCodeRecord(
            corp_code="00138224",
            corp_name="현대자동차",
            stock_code="005380",
            modify_date="20240101",
        ),
        CorpCodeRecord(
            corp_code="01515323",
            corp_name="LG에너지솔루션",
            stock_code="373220",
            modify_date="20240101",
        ),
    ]

    memberships = map_to_corp_codes(constituents, corp_codes)

    assert len(memberships) == 5
    assert sum(m.is_matched for m in memberships) == 4

    samsung = next(m for m in memberships if m.ticker == "005930")
    assert samsung.corp_code == "00126380"
    assert samsung.corp_name == "삼성전자"

    unmatched = next(m for m in memberships if m.ticker == "999999")
    assert unmatched.corp_code is None
    assert unmatched.corp_name is None
    assert unmatched.name == "존재하지않는종목"  # original name preserved


@pytest.mark.unit
def test_map_ignores_unlisted_corp_codes() -> None:
    # An unlisted corp_code (stock_code=None) must not match a constituent
    # even if their tickers happen to collide on something.
    constituents = [Kospi200Constituent(ticker="005930", name="삼성전자")]
    corp_codes = [
        CorpCodeRecord(
            corp_code="99999999",
            corp_name="비상장유령회사",
            stock_code=None,
            modify_date="20240101",
        ),
    ]

    memberships = map_to_corp_codes(constituents, corp_codes)

    assert len(memberships) == 1
    assert memberships[0].is_matched is False
