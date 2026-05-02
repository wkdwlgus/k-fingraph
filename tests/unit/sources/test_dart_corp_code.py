"""Unit tests for the corpCode parser (no network)."""

from pathlib import Path

import pytest

from k_fingraph.errors import DartParseError
from k_fingraph.sources.dart import parse_corp_code_xml

FIXTURE = Path(__file__).parent.parent.parent / "fixtures" / "dart" / "corp_code_sample.xml"


@pytest.mark.unit
def test_parses_listed_company() -> None:
    records = parse_corp_code_xml(FIXTURE)
    samsung = next(r for r in records if r.corp_code == "00126380")

    assert samsung.corp_name == "삼성전자"
    assert samsung.corp_eng_name == "SAMSUNG ELECTRONICS CO,.LTD"
    assert samsung.stock_code == "005930"
    assert samsung.modify_date == "20230718"


@pytest.mark.unit
def test_normalizes_empty_stock_code_to_none() -> None:
    records = parse_corp_code_xml(FIXTURE)
    by_code = {r.corp_code: r for r in records}

    # DART emits a single space for unlisted entities; we normalize to None.
    assert by_code["00999999"].stock_code is None
    # Also covers the truly empty <stock_code></stock_code> case.
    assert by_code["00888888"].stock_code is None


@pytest.mark.unit
def test_normalizes_empty_eng_name_to_none() -> None:
    records = parse_corp_code_xml(FIXTURE)
    unlisted = next(r for r in records if r.corp_code == "00999999")

    assert unlisted.corp_eng_name is None
    assert unlisted.corp_name == "가상비상장법인"


@pytest.mark.unit
def test_parses_all_fixture_records() -> None:
    records = parse_corp_code_xml(FIXTURE)
    assert len(records) == 5


@pytest.mark.unit
def test_malformed_xml_raises_dart_parse_error(tmp_path: Path) -> None:
    bad = tmp_path / "broken.xml"
    bad.write_text("<result><list><corp_code>00126380</corp_code")  # truncated

    with pytest.raises(DartParseError):
        parse_corp_code_xml(bad)
