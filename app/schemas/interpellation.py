"""Pydantic schemas for interpellation endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InterpellationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    interp_uid: str
    term: int
    session_period: int
    meeting_times: int
    legislator_name: str
    interp_content: str
    valid_from: datetime
    valid_to: datetime | None
    recorded_at: datetime
    superseded_at: datetime | None
