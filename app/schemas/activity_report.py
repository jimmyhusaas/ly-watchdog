"""Pydantic schemas for activity report endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ActivityReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    activity_uid: str
    term: int
    session_period: int
    lgno: str
    legislator_name: str
    subject: str
    content: str
    published_at: datetime
    valid_from: datetime
    valid_to: datetime | None
    recorded_at: datetime
    superseded_at: datetime | None
