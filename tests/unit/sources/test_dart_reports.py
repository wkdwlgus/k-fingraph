"""Unit tests for DART periodic-report parsers and value normalization helpers.

The parser tests load fixture JSON snapshots saved from real DART responses
(see tests/fixtures/dart/) — no network is touched. The helper tests exercise
edge cases (commas, missing sentinels, negative signs, three date formats)
documented in docs/data-notes.md.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from k_fingraph.errors import DartParseError
from k_fingraph.sources.dart_reports import (
    normalize_company_name,
    parse_dart_date,
    parse_dart_float,
    parse_dart_int,
    parse_dart_pct,
    parse_major_shareholders_json,
    parse_other_corp_investments_json,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "dart"
SAMSUNG_CORP_CODE = "00126380"
BSNS_YEAR = "2024"
REPRT_CODE_ANNUAL = "11011"
FIXED_FETCHED_AT = datetime(2026, 5, 3, 12, 0, 0, tzinfo=UTC)


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Value normalization helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseDartInt:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("508,157,148", 508_157_148),
            ("0", 0),
            ("-62,823", -62_823),
            ("1565177", 1_565_177),
            ("-", None),
            ("", None),
            (None, None),
        ],
    )
    def test_parses_or_returns_none(self, raw: str | None, expected: int | None) -> None:
        assert parse_dart_int(raw) == expected

    def test_raises_on_garbage(self) -> None:
        with pytest.raises(DartParseError):
            parse_dart_int("not a number")


@pytest.mark.unit
class TestParseDartFloat:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [("84.78", 84.78), ("0", 0.0), ("-0.5", -0.5), ("-", None), ("", None)],
    )
    def test_parses_or_returns_none(self, raw: str, expected: float | None) -> None:
        assert parse_dart_float(raw) == expected


@pytest.mark.unit
class TestParseDartPct:
    @pytest.mark.parametrize(("raw", "expected"), [("84.78", 84.78), ("0", 0.0), ("-", None)])
    def test_in_range(self, raw: str, expected: float | None) -> None:
        assert parse_dart_pct(raw) == expected

    @pytest.mark.parametrize("raw", ["100.01", "-0.01", "150"])
    def test_out_of_range_raises(self, raw: str) -> None:
        with pytest.raises(DartParseError, match="out of range"):
            parse_dart_pct(raw)


@pytest.mark.unit
class TestParseDartDate:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("20241231", date(2024, 12, 31)),
            ("2024-12-31", date(2024, 12, 31)),
            ("2024.12.31", date(2024, 12, 31)),
            ("-", None),
            ("", None),
            (None, None),
        ],
    )
    def test_handles_three_formats(self, raw: str | None, expected: date | None) -> None:
        assert parse_dart_date(raw) == expected

    def test_unknown_format_raises(self) -> None:
        with pytest.raises(DartParseError):
            parse_dart_date("31/12/2024")


@pytest.mark.unit
class TestNormalizeCompanyName:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("삼성생명보험㈜", "삼성생명보험"),
            ("(주)삼성물산", "삼성물산"),
            ("주식회사 카카오", "카카오"),
            ("삼성디스플레이(주)", "삼성디스플레이"),
            ("ASML Holding N.V.", "ASMLHoldingN.V."),
            ("  공백  많은  이름  ", "공백많은이름"),
        ],
    )
    def test_strips_corp_forms_and_whitespace(self, raw: str, expected: str) -> None:
        assert normalize_company_name(raw) == expected


# ---------------------------------------------------------------------------
# Forward parser (otrCprInvstmntSttus)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseOtherCorpInvestments:
    def test_parses_all_rows(self) -> None:
        body = _load("otr_cpr_invstmnt_sample.json")
        report = parse_other_corp_investments_json(
            body,
            corp_code=SAMSUNG_CORP_CODE,
            bsns_year=BSNS_YEAR,
            reprt_code=REPRT_CODE_ANNUAL,
            fetched_at=FIXED_FETCHED_AT,
        )

        assert report.holder_corp_code == SAMSUNG_CORP_CODE
        assert report.bsns_year == BSNS_YEAR
        assert report.reprt_code == REPRT_CODE_ANNUAL
        assert len(report.rows) == 4

    def test_first_row_is_subsidiary_with_full_fields(self) -> None:
        body = _load("otr_cpr_invstmnt_sample.json")
        report = parse_other_corp_investments_json(
            body,
            corp_code=SAMSUNG_CORP_CODE,
            bsns_year=BSNS_YEAR,
            reprt_code=REPRT_CODE_ANNUAL,
            fetched_at=FIXED_FETCHED_AT,
        )
        row = report.rows[0]
        assert row.target_name_text == "삼성디스플레이(주)"
        assert row.stake_pct == 84.78
        assert row.settlement_date == date(2024, 12, 31)
        assert row.holder_corp_code == SAMSUNG_CORP_CODE
        assert row.rcept_no == "20240315000001"

    def test_missing_pct_normalizes_to_none(self) -> None:
        body = _load("otr_cpr_invstmnt_sample.json")
        report = parse_other_corp_investments_json(
            body,
            corp_code=SAMSUNG_CORP_CODE,
            bsns_year=BSNS_YEAR,
            reprt_code=REPRT_CODE_ANNUAL,
            fetched_at=FIXED_FETCHED_AT,
        )
        # Last fixture row uses "-" for trmend_blce_qota_rt.
        assert report.rows[-1].stake_pct is None
        assert report.rows[-1].target_name_text == "Project Alpha LLC"

    def test_empty_list_yields_empty_report(self) -> None:
        report = parse_other_corp_investments_json(
            {"status": "000", "list": []},
            corp_code=SAMSUNG_CORP_CODE,
            bsns_year=BSNS_YEAR,
            reprt_code=REPRT_CODE_ANNUAL,
            fetched_at=FIXED_FETCHED_AT,
        )
        assert report.rows == []

    def test_pct_out_of_range_raises(self) -> None:
        body = {
            "status": "000",
            "list": [
                {
                    "rcept_no": "20240315000001",
                    "corp_code": SAMSUNG_CORP_CODE,
                    "corp_name": "삼성전자",
                    "inv_prm": "Bad Co",
                    "trmend_blce_qota_rt": "150.00",
                    "stlm_dt": "2024-12-31",
                }
            ],
        }
        with pytest.raises(DartParseError, match="out of range"):
            parse_other_corp_investments_json(
                body,
                corp_code=SAMSUNG_CORP_CODE,
                bsns_year=BSNS_YEAR,
                reprt_code=REPRT_CODE_ANNUAL,
                fetched_at=FIXED_FETCHED_AT,
            )


# ---------------------------------------------------------------------------
# Reverse parser (hyslrSttus)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseMajorShareholders:
    def test_parses_all_rows_including_zero_stake(self) -> None:
        body = _load("hyslr_sttus_sample.json")
        report = parse_major_shareholders_json(
            body,
            corp_code=SAMSUNG_CORP_CODE,
            bsns_year=BSNS_YEAR,
            reprt_code=REPRT_CODE_ANNUAL,
            fetched_at=FIXED_FETCHED_AT,
        )
        # Parser preserves all rows; zero-stake filtering is the extractor's job.
        assert len(report.rows) == 5
        assert report.held_corp_code == SAMSUNG_CORP_CODE

    def test_holder_text_and_relate_preserved(self) -> None:
        body = _load("hyslr_sttus_sample.json")
        report = parse_major_shareholders_json(
            body,
            corp_code=SAMSUNG_CORP_CODE,
            bsns_year=BSNS_YEAR,
            reprt_code=REPRT_CODE_ANNUAL,
            fetched_at=FIXED_FETCHED_AT,
        )
        samsung_life = report.rows[1]
        assert samsung_life.holder_name_text == "삼성생명보험㈜"
        assert samsung_life.relate == "특수관계인"
        assert samsung_life.stake_pct == 8.51

    def test_zero_stake_row_normalizes_to_zero_not_none(self) -> None:
        body = _load("hyslr_sttus_sample.json")
        report = parse_major_shareholders_json(
            body,
            corp_code=SAMSUNG_CORP_CODE,
            bsns_year=BSNS_YEAR,
            reprt_code=REPRT_CODE_ANNUAL,
            fetched_at=FIXED_FETCHED_AT,
        )
        # "0" parses to 0.0; "-" parses to None — both are valid no-holding signals
        # that the extractor treats identically.
        assert report.rows[3].stake_pct == 0.0
        assert report.rows[4].stake_pct is None
