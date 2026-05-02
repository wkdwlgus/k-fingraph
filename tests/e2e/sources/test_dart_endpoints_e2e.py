"""End-to-end smoke test for the 5 DART endpoints scoped for v0 ingestion.

Each call hits the real DART API and checks that the response is JSON with
DART's success status code "000" and the documented top-level keys. Schema-level
validation is intentionally out of scope here — that arrives in Day 3 with the
Pydantic models for each endpoint.

Run explicitly with `uv run pytest -m e2e`. Consumes 5 of the 20,000 daily
free quota calls.
"""

from typing import Any

import httpx
import pytest

from k_fingraph.config import get_settings

DART_BASE = "https://opendart.fss.or.kr/api"
SAMSUNG_CORP_CODE = "00126380"
BSNS_YEAR = "2024"
REPRT_CODE_ANNUAL = "11011"


def _get(endpoint: str, **params: str) -> dict[str, Any]:
    params["crtfc_key"] = get_settings().dart_api_key
    response = httpx.get(f"{DART_BASE}/{endpoint}", params=params, timeout=30.0)
    response.raise_for_status()
    body = response.json()
    assert isinstance(body, dict), f"{endpoint} returned non-dict body: {type(body)}"
    return body


@pytest.mark.e2e
def test_list_disclosure_search_responds_ok() -> None:
    body = _get(
        "list.json",
        corp_code=SAMSUNG_CORP_CODE,
        bgn_de="20240101",
        end_de="20240131",
        page_count="3",
    )
    assert body["status"] == "000", body
    for key in ("page_no", "page_count", "total_count", "total_page", "list"):
        assert key in body, f"list.json missing {key!r}; got {list(body)}"
    assert isinstance(body["list"], list)


@pytest.mark.e2e
def test_company_overview_responds_ok() -> None:
    body = _get("company.json", corp_code=SAMSUNG_CORP_CODE)
    assert body["status"] == "000", body
    for key in ("corp_name", "corp_name_eng", "stock_code", "ceo_nm", "induty_code", "est_dt"):
        assert key in body, f"company.json missing {key!r}; got {list(body)}"
    # corpCode 표는 "삼성전자"로 짧게, company.json은 "삼성전자(주)"로 법인형까지
    # 포함해서 응답한다. 표기 차이는 docs/data-notes.md "기업개황" 섹션 참조.
    assert "삼성전자" in body["corp_name"]
    assert body["stock_code"] == "005930"


@pytest.mark.e2e
def test_major_shareholders_responds_ok() -> None:
    body = _get(
        "hyslrSttus.json",
        corp_code=SAMSUNG_CORP_CODE,
        bsns_year=BSNS_YEAR,
        reprt_code=REPRT_CODE_ANNUAL,
    )
    assert body["status"] == "000", body
    assert isinstance(body.get("list"), list) and body["list"], body
    for key in ("nm", "relate", "trmend_posesn_stock_qota_rt", "stlm_dt"):
        assert key in body["list"][0], f"hyslrSttus list[0] missing {key!r}"


@pytest.mark.e2e
def test_other_corp_investments_responds_ok() -> None:
    body = _get(
        "otrCprInvstmntSttus.json",
        corp_code=SAMSUNG_CORP_CODE,
        bsns_year=BSNS_YEAR,
        reprt_code=REPRT_CODE_ANNUAL,
    )
    assert body["status"] == "000", body
    assert isinstance(body.get("list"), list) and body["list"], body
    # inv_prm = 피투자회사명, trmend_blce_qota_rt = 기말 지분율 → OWNS 엣지의 핵심
    for key in ("inv_prm", "trmend_blce_qota_rt", "frst_acqs_de"):
        assert key in body["list"][0], f"otrCprInvstmntSttus list[0] missing {key!r}"


@pytest.mark.e2e
def test_major_stock_holdings_responds_ok() -> None:
    # majorstock takes only crtfc_key + corp_code (no bsns_year/reprt_code) —
    # 5% reports are event-driven, not periodic.
    body = _get("majorstock.json", corp_code=SAMSUNG_CORP_CODE)
    assert body["status"] == "000", body
    assert isinstance(body.get("list"), list) and body["list"], body
    for key in ("repror", "stkrt", "report_resn", "rcept_dt"):
        assert key in body["list"][0], f"majorstock list[0] missing {key!r}"
