"""Graph node and edge schemas.

These mirror docs/schema.md (v0): Company node + OWNS edge. The OwnsCandidate
type is an ingestion-time intermediate (not part of the graph) that represents
an OWNS relation prior to Entity Resolution — one endpoint resolved to a
corp_code, the other endpoint carrying only a text name.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class RelationType(StrEnum):
    """OWNS edge classification. Thresholds are defined by ADR 0006."""

    SUBSIDIARY = "SUBSIDIARY"
    AFFILIATE = "AFFILIATE"
    OTHER = "OTHER"


class Company(BaseModel):
    """Listed Korean company. Mirrors the v0 fields of docs/schema.md."""

    ticker: str = Field(min_length=6, max_length=6)
    corp_code: str = Field(min_length=8, max_length=8)
    name_kr: str
    name_normalized: str
    name_en: str | None = None
    market: Literal["KOSPI", "KOSDAQ", "KONEX"]
    industry_krx: str | None = None
    created_at: datetime
    updated_at: datetime


class OwnsEndpoint(BaseModel):
    """One end of an OWNS edge during ingestion. DART responses identify only
    the calling company by corp_code; the other side arrives as text only,
    so an endpoint may be in either resolved or unresolved state."""

    corp_code: str | None = None
    name_text: str | None = None
    name_normalized: str | None = None

    @property
    def is_resolved(self) -> bool:
        return self.corp_code is not None


class OwnsCandidate(BaseModel):
    """OWNS relation prior to Entity Resolution. Forward extraction yields a
    resolved source; reverse extraction yields a resolved target. The opposite
    endpoint is text only and will be resolved in the v2 ER sprint.

    Not part of the graph schema — discarded at load time if the unresolved
    endpoint cannot be matched to a KOSPI 200 corp_code (ADR 0007)."""

    source: OwnsEndpoint
    target: OwnsEndpoint
    stake_pct: float | None = Field(default=None, ge=0, le=100)
    relation_type: RelationType
    as_of: date | None
    source_id: str
    extracted_at: datetime


class OwnsRelation(BaseModel):
    """OWNS edge in its loadable form: both endpoints resolved to corp_code,
    stake_pct present. Mirrors docs/schema.md OWNS edge properties + the two
    endpoint identifiers required for a Pydantic representation."""

    source_corp_code: str = Field(min_length=8, max_length=8)
    target_corp_code: str = Field(min_length=8, max_length=8)
    stake_pct: float = Field(ge=0, le=100)
    relation_type: RelationType
    as_of: date
    source_id: str
    extracted_at: datetime
