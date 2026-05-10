"""Pydantic schemas for committee membership endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CommitteeMembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    committee_uid: str
    term: int
    session_period: int
    legislator_name: str
    committee: str
    is_convener: bool
    valid_from: datetime
    valid_to: datetime | None
    recorded_at: datetime
    superseded_at: datetime | None
