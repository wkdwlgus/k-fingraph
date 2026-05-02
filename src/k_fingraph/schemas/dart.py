"""Pydantic schemas for DART OpenAPI payloads."""

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
