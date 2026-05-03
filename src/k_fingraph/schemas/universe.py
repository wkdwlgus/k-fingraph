"""Pydantic schemas for the v0.5 extended universe (KOSPI + KOSDAQ).

Generalizes `kospi200.py` to carry a `market` discriminator on every row so
downstream loaders can stamp `Company.market` without re-deriving it from
the CSV source path.
"""

from typing import Literal

from pydantic import BaseModel, Field

Market = Literal["KOSPI", "KOSDAQ"]


class UniverseConstituent(BaseModel):
    """One listed common-stock issuer from a KRX 전종목 기본정보 export.

    Preferred shares and other 주식종류 variants are filtered upstream so
    that one constituent corresponds to one issuing legal entity.
    """

    ticker: str = Field(min_length=6, max_length=6)
    name: str
    market: Market


class UniverseMembership(BaseModel):
    """Result of joining a UniverseConstituent against the DART corp_code table.

    Unmatched constituents stay in the output with corp_code=None so callers
    can audit them rather than silently dropping rows.
    """

    ticker: str
    name: str
    market: Market
    corp_code: str | None = None
    corp_name: str | None = None

    @property
    def is_matched(self) -> bool:
        return self.corp_code is not None
