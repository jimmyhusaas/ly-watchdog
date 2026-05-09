"""Pydantic schemas for legislator endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LegislatorRead(BaseModel):
    """API response shape for a single legislator record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    legislator_uid: str = Field(description="立法院資料源的自然鍵")
    name: str
    district: str | None
    party: str | None
    term: int = Field(description="屆別")

    valid_from: datetime
    valid_to: datetime | None = Field(
        default=None,
        description="null 表示事實在現實世界中仍有效",
    )
    recorded_at: datetime
    superseded_at: datetime | None = Field(
        default=None,
        description="null 表示系統目前仍以此筆為該立委的記錄",
    )


class LegislatorDetail(LegislatorRead):
    """立委個人頁 — 基本資料 + 活動統計。"""

    bill_count: int = Field(description="本屆提案數 (含連署)")
    speech_count: int = Field(description="本屆院會發言次數")
