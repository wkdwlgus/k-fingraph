"""Pydantic schemas for DART OpenAPI payloads."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class CorpCodeRecord(BaseModel):
    """One row of DART's corpCode.xml — the master table that maps every
    DART-registered company to a stable 8-digit identifier.

    Unlisted companies have no exchange ticker, so `stock_code` is None.
    """

    corp_code: str = Field(min_length=8, max_length=8)
    corp_name: str
    corp_eng_name: str | None = None
    stock_code: str | None = None
    modify_date: str = Field(min_length=8, max_length=8)


class DartOtherCorpInvestmentRow(BaseModel):
    """One row of `otrCprInvstmntSttus.json`'s `list[]` — the OWNS edge in the
    "A invests in B" direction. Only fields needed for OWNS extraction are
    kept; the full 20-field payload is documented in docs/data-notes.md.

    `target_name_text` (DART's `inv_prm`) carries the investee name as text;
    Entity Resolution to a corp_code is the v2 sprint's responsibility.
    """

    rcept_no: str
    holder_corp_code: str = Field(min_length=8, max_length=8)
    holder_corp_name: str
    target_name_text: str
    stake_pct: float | None = Field(default=None, ge=0, le=100)
    settlement_date: date | None = None


class DartOtherCorpInvestmentReport(BaseModel):
    """Parsed `otrCprInvstmntSttus.json` response for a single (corp_code,
    bsns_year, reprt_code) call."""

    holder_corp_code: str = Field(min_length=8, max_length=8)
    bsns_year: str = Field(min_length=4, max_length=4)
    reprt_code: str = Field(min_length=5, max_length=5)
    fetched_at: datetime
    rows: list[DartOtherCorpInvestmentRow]


class DartMajorShareholderRow(BaseModel):
    """One row of `hyslrSttus.json`'s `list[]` — the OWNS edge in the reverse
    direction ("X is a major shareholder of A"). The held company arrives
    resolved (`held_corp_code`); the holder arrives as text (`holder_name_text`).

    `relate` carries the relationship label as free text ("최대주주 본인",
    "특수관계인", "친인척" etc.) — used by extraction to filter zero-stake
    rows that represent related parties without direct holdings.
    """

    rcept_no: str
    held_corp_code: str = Field(min_length=8, max_length=8)
    held_corp_name: str
    holder_name_text: str
    relate: str | None = None
    stake_pct: float | None = Field(default=None, ge=0, le=100)
    settlement_date: date | None = None


class DartMajorShareholdersReport(BaseModel):
    """Parsed `hyslrSttus.json` response for a single (corp_code, bsns_year,
    reprt_code) call."""

    held_corp_code: str = Field(min_length=8, max_length=8)
    bsns_year: str = Field(min_length=4, max_length=4)
    reprt_code: str = Field(min_length=5, max_length=5)
    fetched_at: datetime
    rows: list[DartMajorShareholderRow]
