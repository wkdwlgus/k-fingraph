"""Unit tests for the v0.5 extended universe loader and DART corp_code mapper."""

from pathlib import Path

import pytest

from k_fingraph.schemas.dart import CorpCodeRecord
from k_fingraph.schemas.universe import UniverseConstituent
from k_fingraph.sources.extended_universe import (
    ExtendedUniverseLoadError,
    load_extended_universe,
    load_market_csv,
    map_universe_to_corp_codes,
)

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "krx"
KOSPI_FIXTURE = FIXTURES / "kospi_sample.csv"
KOSDAQ_FIXTURE = FIXTURES / "kosdaq_sample.csv"


@pytest.mark.unit
def test_load_market_csv_stamps_market() -> None:
    rows = load_market_csv(KOSPI_FIXTURE, "KOSPI")
    assert len(rows) == 4
    assert all(r.market == "KOSPI" for r in rows)
    assert rows[0].ticker == "005930"
    assert rows[0].name == "삼성전자"


@pytest.mark.unit
def test_load_market_csv_skips_blank_lines(tmp_path: Path) -> None:
    csv_path = tmp_path / "with_blanks.csv"
    csv_path.write_text(
        "ticker,name\n005930,삼성전자\n,\n000660,SK하이닉스\n",
        encoding="utf-8",
    )
    rows = load_market_csv(csv_path, "KOSPI")
    assert [r.ticker for r in rows] == ["005930", "000660"]


@pytest.mark.unit
def test_load_market_csv_missing_required_column_raises(tmp_path: Path) -> None:
    csv_path = tmp_path / "wrong_cols.csv"
    csv_path.write_text("symbol,company\n005930,삼성전자\n", encoding="utf-8")
    with pytest.raises(ExtendedUniverseLoadError, match="must have columns"):
        load_market_csv(csv_path, "KOSPI")


@pytest.mark.unit
def test_load_extended_universe_concatenates() -> None:
    rows = load_extended_universe(KOSPI_FIXTURE, KOSDAQ_FIXTURE)
    assert len(rows) == 8
    by_market = {m: [r for r in rows if r.market == m] for m in ("KOSPI", "KOSDAQ")}
    assert len(by_market["KOSPI"]) == 4
    assert len(by_market["KOSDAQ"]) == 4


@pytest.mark.unit
def test_load_extended_universe_rejects_duplicate_ticker(tmp_path: Path) -> None:
    kospi = tmp_path / "kospi.csv"
    kosdaq = tmp_path / "kosdaq.csv"
    kospi.write_text("ticker,name\n005930,삼성전자\n", encoding="utf-8")
    kosdaq.write_text("ticker,name\n005930,누군가\n", encoding="utf-8")
    with pytest.raises(ExtendedUniverseLoadError, match="ticker collision"):
        load_extended_universe(kospi, kosdaq)


@pytest.mark.unit
def test_map_universe_keeps_unmatched_with_none() -> None:
    constituents = [
        UniverseConstituent(ticker="005930", name="삼성전자", market="KOSPI"),
        UniverseConstituent(ticker="247540", name="에코프로비엠", market="KOSDAQ"),
        UniverseConstituent(ticker="999999", name="존재하지않는종목", market="KOSDAQ"),
    ]
    corp_codes = [
        CorpCodeRecord(
            corp_code="00126380",
            corp_name="삼성전자",
            stock_code="005930",
            modify_date="20240101",
        ),
        CorpCodeRecord(
            corp_code="01361003",
            corp_name="에코프로비엠",
            stock_code="247540",
            modify_date="20240101",
        ),
    ]

    memberships = map_universe_to_corp_codes(constituents, corp_codes)

    assert len(memberships) == 3
    assert sum(m.is_matched for m in memberships) == 2

    samsung = next(m for m in memberships if m.ticker == "005930")
    assert samsung.corp_code == "00126380"
    assert samsung.market == "KOSPI"

    ecopro = next(m for m in memberships if m.ticker == "247540")
    assert ecopro.market == "KOSDAQ"

    unmatched = next(m for m in memberships if m.ticker == "999999")
    assert unmatched.corp_code is None
    assert unmatched.market == "KOSDAQ"


@pytest.mark.unit
def test_map_universe_ignores_unlisted_corp_codes() -> None:
    # ADR 0008 exclusion: unlisted DART entities (stock_code is None) must
    # never participate in the join, even if a ticker collision were possible.
    constituents = [
        UniverseConstituent(ticker="005930", name="삼성전자", market="KOSPI"),
    ]
    corp_codes = [
        CorpCodeRecord(
            corp_code="99999999",
            corp_name="비상장유령회사",
            stock_code=None,
            modify_date="20240101",
        ),
    ]

    memberships = map_universe_to_corp_codes(constituents, corp_codes)

    assert len(memberships) == 1
    assert memberships[0].is_matched is False


@pytest.mark.unit
def test_map_universe_carries_market_through() -> None:
    constituents = [
        UniverseConstituent(ticker="005930", name="삼성전자", market="KOSPI"),
        UniverseConstituent(ticker="247540", name="에코프로비엠", market="KOSDAQ"),
    ]
    corp_codes = [
        CorpCodeRecord(
            corp_code="00126380",
            corp_name="삼성전자",
            stock_code="005930",
            modify_date="20240101",
        ),
        CorpCodeRecord(
            corp_code="01361003",
            corp_name="에코프로비엠",
            stock_code="247540",
            modify_date="20240101",
        ),
    ]

    memberships = map_universe_to_corp_codes(constituents, corp_codes)
    by_ticker = {m.ticker: m for m in memberships}
    assert by_ticker["005930"].market == "KOSPI"
    assert by_ticker["247540"].market == "KOSDAQ"
