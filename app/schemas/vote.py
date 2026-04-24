"""Pydantic schemas for vote endpoints."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VoteRead(BaseModel):
    """One vote record (raw, bi-temporal)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vote_uid: str
    term: int
    session_period: int
    meeting_times: int
    vote_times: int
    vote_date: date
    bill_no: str | None
    bill_name: str
    legislator_name: str
    party: str | None
    vote_result: str
    valid_from: datetime
    valid_to: datetime | None
    recorded_at: datetime
    superseded_at: datetime | None


class PartyDisciplineRow(BaseModel):
    """One legislator's party discipline stats for a given term/session."""

    model_config = ConfigDict(from_attributes=True)

    legislator_name: str
    party: str | None
    term: int
    session_period: int
    votes_with_party_position: int = Field(description="表決中黨有明確立場的次數 (作為分母)")
    deviations: int = Field(description="偏離黨紀次數")
    deviation_rate: float = Field(description="偏離率 (0-100)")
