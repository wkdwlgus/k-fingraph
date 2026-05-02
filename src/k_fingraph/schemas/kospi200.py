"""Pydantic schemas for KOSPI 200 constituents and DART corp_code mapping."""

from pydantic import BaseModel, Field


class Kospi200Constituent(BaseModel):
    """One KOSPI 200 member as observed from a KRX export.

    `ticker` is the 6-digit exchange code; `name` is the Korean security name.
    """

    ticker: str = Field(min_length=6, max_length=6)
    name: str


class Kospi200Membership(BaseModel):
    """Result of joining a KOSPI 200 constituent against the DART corp_code table.

    All 200 constituents are present in the output; rows that failed to match
    have `corp_code` and `corp_name` set to None so unmatched cases are visible
    rather than silently dropped.
    """

    ticker: str
    name: str
    corp_code: str | None = None
    corp_name: str | None = None

    @property
    def is_matched(self) -> bool:
        return self.corp_code is not None
